"""Testa diferenças pareadas entre modelos de uma rodada k-fold publicada."""
import argparse
from collections import Counter
import csv
from hashlib import sha256
from itertools import combinations
import io
import json
from math import isclose, isfinite, sqrt
from pathlib import Path
from statistics import mean, variance
import subprocess

from scipy.stats import t

from metricas_modelagem import holm

ROOT = Path(__file__).resolve().parents[1]
ROUND_ROOT = Path('resultados/experimentos/rodadas')
DEFAULT_ROUND = 'r01_5folds_2rep_12cand'
MODELS = ('floresta', 'boosting', 'arvore', 'knn', 'logistica')
ENDPOINTS = ('recall', 'specificity', 'error')
ALPHA = .05


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def published_inputs(ref, round_id):
    commit = git('rev-parse', '--verify', '--end-of-options', f'{ref}^{{commit}}').decode().strip()
    folder = ROUND_ROOT / round_id
    principal_path = Path('resultados/experimentos/v3/particao_principal.csv')
    # Commits anteriores à reorganização usam os caminhos originais.
    if not git('ls-tree', '-r', '--name-only', commit, '--', (folder / 'protocolo.json').as_posix()):
        folder = Path('resultado_experimentos_rodadas') / round_id
        principal_path = Path('resultado_experimentos_reduzido/particao_principal.csv')
    hashes = {}

    def read(path):
        data = git('show', f'{commit}:{path.as_posix()}')
        hashes[path.as_posix()] = sha256(data).hexdigest()
        return data.decode('utf-8-sig')

    protocol = json.loads(read(folder / 'protocolo.json'))
    status = json.loads(read(folder / 'estado_rodada.json'))
    cfg = protocol['inputs']['round']
    k, seeds = cfg['outer_folds'], cfg['outer_seeds']
    expected = k * len(seeds)
    if k < 3 or len(set(seeds)) < 2 or len(set(seeds)) != len(seeds):
        raise ValueError('O teste exige pelo menos duas repetições de k-fold com k ≥ 3')
    if status['status'] != 'concluida' or status['folds_completos'] != expected:
        raise ValueError('A rodada publicada não está completa')
    principal = csv.DictReader(io.StringIO(read(principal_path)))
    development = {row['ID']: row['y'] for row in principal if row['conjunto'] == 'desenvolvimento'}
    counts = {}
    for repetition, seed in enumerate(seeds):
        rows = csv.DictReader(io.StringIO(read(folder / f'particao_externa_r{repetition}.csv')))
        assigned = {}
        for row in rows:
            key = (repetition, int(row['fold']))
            record = row['ID']
            if (record in assigned or row['y'] != development.get(record) or
                    int(row['seed']) != seed or key[1] not in range(k)):
                raise ValueError(f'Partição inconsistente na repetição {repetition}')
            assigned[record] = row['y']
            counts.setdefault(key, Counter())[row['y']] += 1
        if assigned != development:
            raise ValueError(f'Cobertura incompleta da repetição {repetition}')
    expected_keys = {(r, f) for r in range(len(seeds)) for f in range(k)}
    if set(counts) != expected_keys or any(set(count) != {'0', '1'} for count in counts.values()):
        raise ValueError('Fold ausente ou sem ambas as classes')

    metrics = {name: {} for name in MODELS}
    rows = csv.DictReader(io.StringIO(read(folder / 'metricas_externas.csv')))
    for row in rows:
        name = row['model']
        if row['mode'] != 'aprendido' or name not in metrics:
            continue
        key = (int(row['repeat']), int(row['fold']))
        if row['rodada'] != round_id or key not in counts or key in metrics[name]:
            raise ValueError(f'Métrica duplicada ou fora das partições: {name} {key}')
        tp, tn, fp, fn = (int(row[m]) for m in ('tp', 'tn', 'fp', 'fn'))
        if (min(tp, tn, fp, fn) < 0 or tp + fn != counts[key]['1'] or
                tn + fp != counts[key]['0'] or int(row['n']) != counts[key].total()):
            raise ValueError(f'Contagens diferentes das classes da partição: {name} {key}')
        rates = {'recall': tp / (tp + fn), 'specificity': tn / (tn + fp),
                 'error': (fp + fn) / counts[key].total()}
        if any(not isclose(float(row[m]), v, abs_tol=1e-12) for m, v in rates.items()):
            raise ValueError(f'Métricas não correspondem às contagens: {name} {key}')
        metrics[name][key] = rates
    if any(set(table) != expected_keys for table in metrics.values()):
        raise ValueError('Todos os modelos exigem exatamente os mesmos folds')
    return dict(commit=commit, round_id=round_id, k=k, seeds=seeds, hashes=hashes,
                development=len(development), counts=counts, rates=metrics)


def corrected_t(deltas, ratio):
    if len(deltas) < 2 or not isfinite(ratio) or ratio <= 0 or not all(map(isfinite, deltas)):
        raise ValueError('Exige diferenças finitas e razão validação/treino positiva')
    estimate = mean(deltas)
    df = len(deltas) - 1
    standard_error = sqrt((1 / len(deltas) + ratio) * variance(deltas))
    if standard_error == 0:
        return dict(delta=estimate, se=0., t=None, p=None, ci95_low=None, ci95_high=None)
    statistic = estimate / standard_error
    margin = float(t.ppf(1 - ALPHA / 2, df)) * standard_error
    return dict(delta=estimate, se=standard_error, t=statistic,
                p=float(2 * t.sf(abs(statistic), df)), ci95_low=estimate - margin, ci95_high=estimate + margin)


def test_pairs(data):
    keys = sorted(data['counts'])
    sizes = [data['counts'][key].total() for key in keys]
    ratio = mean(n / (data['development'] - n) for n in sizes)
    result, individual = [], []
    for endpoint in ENDPOINTS:
        for first, second in combinations(MODELS, 2):
            common = dict(metric=endpoint, model_a=first, model_b=second)
            deltas = []
            for key, n in zip(keys, sizes):
                a, b = (data['rates'][name][key][endpoint] for name in (first, second))
                deltas.append(a - b)
                individual.append(dict(**common, repeat=key[0], fold=key[1], n_valid=n,
                                       n_train=data['development'] - n, value_a=a, value_b=b, delta=a - b))
            result.append(dict(**common, n_folds=len(keys), df=len(keys) - 1, test_train_ratio=ratio,
                               **corrected_t(deltas, ratio)))
    for row, adjusted in zip(result, holm([r['p'] for r in result])):
        row['p_holm'] = adjusted
        row['rejeita_h0'] = adjusted is not None and adjusted < ALPHA
    return result, individual


def write_csv(path, rows):
    with path.open('w', encoding='utf-8', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=rows[0], lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def write_report(output, data, result, individual):
    names = {'recall': 'Sensibilidade', 'specificity': 'Especificidade', 'error': 'Erro global'}
    decision = sum(row['rejeita_h0'] for row in result)
    table = ['| Métrica | Modelo A | Modelo B | Δ (p.p.) | IC95% nominal (p.p.) | p bruto | p Holm | Rejeita H₀ |',
             '| --- | --- | --- | ---: | ---: | ---: | ---: | --- |']
    for row in result:
        d = row['delta'] * 100
        if row['p'] is None:
            details = 'Indefinido | — | — | Indefinido'
        else:
            details = (f"{row['ci95_low'] * 100:+.2f} a {row['ci95_high'] * 100:+.2f} | "
                       f"{row['p']:.4g} | {row['p_holm']:.4g} | "
                       f"{'Sim' if row['rejeita_h0'] else 'Não'}")
        table.append(f"| {names[row['metric']]} | {row['model_a']} | {row['model_b']} | {d:+.2f} | {details} |")
    metadata = {'commit_publicado': data['commit'], 'rodada': data['round_id'],
                'folds_externos': data['k'], 'sementes': data['seeds'], 'n_desenvolvimento': data['development'],
                'alpha': ALPHA, 'familia_holm': len(result), 'rejeicoes': decision,
                'arquivos_fonte_git_sha256': data['hashes']}
    comparison_table = '\n'.join(table)
    text = f"""# Testes de hipótese exploratórios da {data['round_id']}

Foram comparados os cinco modelos treinados em {len(data['seeds'])} repetições de {data['k']} folds externos. A fonte é o commit publicado `{data['commit']}`. Cada comparação usa os mesmos folds com limiar aprendido no treino. As contagens de classe foram conferidas contra as partições publicadas dos {data['development']} registros de desenvolvimento. Dummy permanece como referência descritiva.

O teste t bilateral para validação cruzada repetida usa as diferenças A − B em cada fold. H₀ é diferença média igual a zero. Com m diferenças, a variância estimada da média é `(1/m + n_val/n_treino) × s²`. Usamos a média da razão entre tamanhos dos folds porque há pequenas diferenças de tamanho entre eles. A referência t usa m − 1 graus de liberdade. Diferença positiva favorece A em sensibilidade e especificidade, e negativa favorece A em erro. [Bouckaert e Frank](https://ml.cms.waikato.ac.nz/publications/2004/bouckaert-frank.pdf)

Holm a α = 0,05 ajusta a família inteira de {len(result)} contrastes (dez pares × três métricas). Os IC95% são nominais e individuais. Houve **{decision} de {len(result)} rejeições** após o ajuste. Variância nula torna o teste indefinido. [Holm](https://www.ime.usp.br/~abe/lista/pdf4R8xPVzCnX.pdf)

{comparison_table}

A análise é pós-hoc. A correção é aproximada para folds dependentes. Sua aplicação às taxas por classe é exploratória. Os folds usam os mesmos registros em repetições diferentes e a identidade dos pacientes não está disponível. Um resultado não significativo mantém a incerteza sobre a diferença e não demonstra equivalência. A análise usa somente previsões resumidas nos folds externos. O teste reservado segue como evidência histórica da v3.

Decompusemos cada contraste em [diferenças por fold](diferencas_por_fold.csv). Os valores completos estão em [resultados.csv](resultados.csv), com a [proveniência dos dados](analise.json).
"""
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / 'resultados.csv', result)
    write_csv(output / 'diferencas_por_fold.csv', individual)
    (output / 'analise.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (output / 'relatorio.md').write_text(text, encoding='utf-8')
    print(f'{len(result)} contrastes; {decision} rejeições após Holm. Saída: {output}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ref', default='origin/main')
    parser.add_argument('--rodada', default=DEFAULT_ROUND)
    parser.add_argument('--saida', type=Path)
    args = parser.parse_args()
    data = published_inputs(args.ref, args.rodada)
    result, individual = test_pairs(data)
    output = args.saida or ROOT / ROUND_ROOT / args.rodada / 'inferencia_exploratoria'
    write_report(output, data, result, individual)


if __name__ == '__main__':
    main()
