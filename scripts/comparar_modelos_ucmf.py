"""Extensão exploratória da v3, restrita ao desenvolvimento histórico."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import time
import warnings

from joblib import Parallel, delayed, parallel_config
import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.model_selection import ParameterGrid
from threadpoolctl import threadpool_limits

from metricas_modelagem import choose_threshold
from modelos_ucmf import SPACES, candidates, pipeline
from representacoes_ucmf import REPRESENTATIONS, input_frame
from treinar_modelos import (
    ROOT, _candidate_job, folds, load_frame, prediction_table, read_json,
    save_folds, sha, table_metrics, versions, write_json,
)

HISTORICO = ROOT / 'resultados/experimentos/v3'
PREPARO = ROOT / 'resultados/preparo'
SAIDA = ROOT / 'execucoes/ampliado'
MODELOS = ('dummy', 'logistica', 'floresta', 'boosting')
DESENHOS = {
    '5x2': (2, [101, 202, 303, 404, 505]),
    '2x5': (5, [6101, 6202]),
}


def grades(original):
    anteriores = original['candidates']
    sorteados = candidates(original['config']['seed'], 12)
    grade = {}
    for nome in MODELOS:
        grade[nome] = anteriores[nome].copy()
        for params in sorteados[nome] + ([] if nome == 'dummy' else list(ParameterGrid(SPACES[nome]))):
            if len(grade[nome]) == 12:
                break
            if params not in grade[nome]:
                grade[nome].append(params)
    extras = {
        'dummy': [],
        'logistica': [
            {'solver': 'saga', 'l1_ratio': ratio, 'C': c}
            for ratio in [.25, .75] for c in [.1, 1]
        ],
        'floresta': [
            {'n_estimators': trees, 'max_depth': depth, 'min_samples_leaf': 5, 'max_features': .7}
            for trees in [150, 300] for depth in [12, 24]
        ],
        'boosting': [
            {'max_iter': it, 'learning_rate': rate, 'max_leaf_nodes': 15,
             'min_samples_leaf': leaf, 'l2_regularization': 1}
            for it, rate in [(150, .06), (250, .02)] for leaf in [10, 40]
        ],
    }
    return grade, {name: grade[name] + extras[name] for name in MODELOS}


def desenvolvimento():
    metadata = read_json(HISTORICO / 'modelos_selecionados.json')
    source = PREPARO / 'UCMF_supervisionado.csv'
    if sha(source) != metadata['data_sha256']:
        raise ValueError('A base supervisionada difere da v3')
    assignment = pd.read_csv(HISTORICO / 'particao_principal.csv', dtype={'ID': str})
    if assignment.ID.duplicated().any() or set(assignment.conjunto) != {'desenvolvimento', 'teste'}:
        raise ValueError('Partição principal inválida')
    frame = load_frame(source)
    if list(assignment.ID) != list(frame.ID):
        raise ValueError('A ordem dos IDs difere da v3')
    dev = frame.loc[assignment.conjunto.eq('desenvolvimento')].reset_index(drop=True)
    if not np.array_equal(dev.y, assignment.loc[assignment.conjunto.eq('desenvolvimento'), 'y']):
        raise ValueError('Os rótulos de desenvolvimento diferem da v3')
    return dev, metadata


def search(name, train, splits, seed, profile, grid, cache, n_jobs):
    X, y = input_frame(train), train.y.to_numpy()
    with parallel_config(backend='loky', inner_max_num_threads=1):
        return Parallel(n_jobs=n_jobs)(
            delayed(_candidate_job)(name, index, params, X, y, splits, seed, cache, profile)
            for index, params in enumerate(grid)
        )


def evaluate(name, profile, train, valid, seed, trials, folder, cache, run_seconds):
    eligible = [trial for trial in trials if trial['eligible']]
    if not eligible:
        raise ValueError(f'Sem candidato convergente em {folder}')
    maximum = max(trial['mean_ap'] for trial in eligible)
    winner = min((t for t in eligible if maximum - t['mean_ap'] <= 1e-6), key=lambda t: t['candidate'])
    threshold = choose_threshold(train.y, winner['oof'], .8)
    start = time.perf_counter()
    model = pipeline(name, winner['params'], seed, cache, profile)
    with threadpool_limits(limits=1), warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        model.fit(input_frame(train), train.y.to_numpy())
    if any(issubclass(item.category, ConvergenceWarning) for item in caught):
        raise ValueError(f'Refit não convergiu em {folder}')
    table = prediction_table(model, valid, threshold['threshold'])
    train_metrics = table_metrics(prediction_table(model, train, threshold['threshold']))
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'previsoes.csv'
    table.to_csv(path, index=False, encoding='utf-8-sig')
    write_json(folder / 'concluido.json', dict(
        profile=profile, params=winner['params'], candidate=winner['candidate'],
        inner_ap=winner['mean_ap'], threshold=threshold,
        n_train=len(train), prediction_sha256=sha(path), metrics=table_metrics(table),
        train_metrics=train_metrics,
        refit_seconds=time.perf_counter() - start,
        inner_candidate_seconds=sum(t['seconds'] for t in trials),
        shared_search_wall_seconds=run_seconds,
        refit_warnings=list({str(w.message) for w in caught}),
        trials=[{k: v for k, v in t.items() if k != 'oof'} for t in trials],
    ))


def checkpoint_valid(folder):
    marker = folder / 'concluido.json'
    if not marker.exists():
        return False
    if sha(folder / 'previsoes.csv') != read_json(marker)['prediction_sha256']:
        raise ValueError(f'Previsões modificadas em {folder}')
    return True


def run_design(output, dev, design, budgets, n_jobs):
    k, seeds = DESENHOS[design]
    cache = output / '.cache_preparo' / design
    for rep, seed in enumerate(seeds):
        outer = folds(dev, k, seed)
        scope = output / design
        scope.mkdir(exist_ok=True)
        save_folds(dev, outer, scope / f'particao_r{rep}.csv', seed)
        if design == '5x2':
            historic = pd.read_csv(HISTORICO / f'particao_externa_r{rep}.csv', dtype=str)
            current = pd.read_csv(scope / f'particao_r{rep}.csv', dtype=str)
            if not current.equals(historic):
                raise ValueError(f'Fold histórico divergente na repetição {rep}')
        for fold, (a, b) in enumerate(outer):
            seed_inner = seed * 10 + fold
            train = dev.iloc[a].reset_index(drop=True)
            valid = dev.iloc[b].reset_index(drop=True)
            inner = folds(train, 3, seed_inner)
            work = scope / f'r{rep}_f{fold}'
            work.mkdir(exist_ok=True)
            save_folds(train, inner, work / 'particao_interna.csv', seed_inner)
            if design == '5x2':
                old_path = HISTORICO / f'externo_r{rep}_f{fold}' / 'particoes_internas.csv'
                if old_path.exists() and not pd.read_csv(old_path, dtype=str).equals(
                    pd.read_csv(work / 'particao_interna.csv', dtype=str)
                ):
                    raise ValueError(f'Fold interno histórico divergente em {work}')
            for name in MODELOS:
                for profile in ('continua',) if name == 'dummy' else REPRESENTATIONS:
                    pending = [
                        (label, grid[name], work / label / name / profile)
                        for label, grid in budgets.items()
                        if not checkpoint_valid(work / label / name / profile)
                    ]
                    if not pending:
                        continue
                    print(f'{design} r{rep+1} f{fold+1}/{k} {name} {profile}', flush=True)
                    start = time.perf_counter()
                    largest = max((grid for _, grid, _ in pending), key=len)
                    trials = search(name, train, inner, seed_inner, profile, largest, cache, n_jobs)
                    elapsed = time.perf_counter() - start
                    for label, grid, folder in pending:
                        if grid != largest[:len(grid)]:
                            raise ValueError(f'Grade de {label} não é prefixo da grade compartilhada')
                        evaluate(name, profile, train, valid, seed_inner, trials[:len(grid)], folder, cache, elapsed)


def progress(output):
    for design, (k, seeds) in DESENHOS.items():
        arms = 2 if design == '5x2' else 1
        count = len(list((output / design).glob('r*_f*/*/*/*/concluido.json')))
        print(f'{design}: {count}/{len(seeds) * k * 10 * arms} perfis concluídos')
    state = output / 'estado_execucao.json'
    if state.exists():
        print(read_json(state))


def run(output, n_jobs):
    from analises_comparacao_ucmf import complementary, report

    output = output.resolve()
    if output in {HISTORICO, PREPARO} or (output / 'teste_aberto.json').exists():
        raise ValueError('Use um diretório separado da execução histórica')
    output.mkdir(parents=True, exist_ok=True)
    protocol_path = output / 'protocolo.json'
    if not protocol_path.exists() and any(
        p.name not in {'execucao_stdout.log', 'execucao_stderr.log', 'estado_execucao.json', 'execucao.lock'}
        for p in output.iterdir()
    ):
        raise ValueError('Diretório de saída não vazio e sem protocolo')
    lock = output / 'execucao.lock'
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(descriptor)
    state_path = output / 'estado_execucao.json'
    state = dict(pid=os.getpid(), status='em_execucao', inicio=datetime.now(timezone.utc).isoformat())
    try:
        write_json(state_path, state)
        dev, original = desenvolvimento()
        base, expanded = grades(original)
        source_files = [
            Path(__file__), ROOT / 'scripts/analises_comparacao_ucmf.py',
            ROOT / 'scripts/treinar_modelos.py', ROOT / 'scripts/modelos_ucmf.py',
            ROOT / 'scripts/metricas_modelagem.py', ROOT / 'scripts/representacoes_ucmf.py',
            ROOT / 'scripts/preparar_modelagem.py',
            PREPARO / 'UCMF_supervisionado.csv', PREPARO / 'atributos_complementares.csv',
            PREPARO / 'conflitos_alvo.csv', ROOT / 'resultados/analise/UCMF_base_final.csv',
            HISTORICO / 'modelos_selecionados.json', HISTORICO / 'particao_principal.csv',
            HISTORICO / 'metricas_externas.csv', HISTORICO / 'metricas_por_representacao.csv',
            HISTORICO / 'metricas_teste.csv', *sorted(HISTORICO.glob('particao_externa_r*.csv')),
        ]
        protocol = dict(designs={k: list(v) for k, v in DESENHOS.items()},
                        grades=dict(base12=base, estendida16=expanded), versions=versions(),
                        development=len(dev), n_jobs=n_jobs, positive='Anormal',
                        minimum_specificity=.8, inner_folds=3,
                        files={p.relative_to(ROOT).as_posix(): sha(p) for p in source_files})
        if protocol_path.exists() and read_json(protocol_path) != protocol:
            raise ValueError('Protocolo divergente; use outro diretório')
        write_json(protocol_path, protocol)
        complementary(output, dev, original, n_jobs, only_audit=True)
        for design in DESENHOS:
            state['fase'] = design
            write_json(state_path, state)
            budgets = {'base12': base}
            if design == '5x2':
                budgets['estendida16'] = expanded
            run_design(output, dev, design, budgets, n_jobs)
            report(output, dev, complete=False)
        state['fase'] = 'complementares'
        write_json(state_path, state)
        complementary(output, dev, original, n_jobs)
        report(output, dev, complete=True)
        state.update(status='concluida', fim=datetime.now(timezone.utc).isoformat())
    except BaseException as error:
        state.update(status='falhou', erro=str(error), fim=datetime.now(timezone.utc).isoformat())
        raise
    finally:
        write_json(state_path, state)
        lock.unlink()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saida', type=Path, default=SAIDA)
    parser.add_argument('--jobs', type=int, choices=range(1, 5), default=4)
    parser.add_argument('--status', action='store_true')
    args = parser.parse_args()
    if args.status:
        progress(args.saida)
    else:
        run(args.saida, args.jobs)
