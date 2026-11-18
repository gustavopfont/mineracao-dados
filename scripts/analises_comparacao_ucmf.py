"""Análises e relatório da extensão exploratória do UCMF."""
import time

import numpy as np
import pandas as pd
from scipy.stats import binomtest
from sklearn.model_selection import StratifiedShuffleSplit

from comparar_modelos_ucmf import (
    DESENHOS, HISTORICO, MODELOS, PREPARO, checkpoint_valid, evaluate, search,
)
from metricas_modelagem import five_by_two, holm
from preparar_modelagem import HISTORY_COLUMN, TARGET
from representacoes_ucmf import REPRESENTATIONS, columns
from treinar_modelos import ROOT, folds, read_json, save_folds, write_json

METRICS = ['recall', 'specificity', 'precision', 'f1', 'accuracy', 'ap', 'roc_auc', 'brier', 'error']
FIXED_PROFILES = {'logistica': 'continua', 'floresta': 'clinica', 'boosting': 'combinada'}
FRACTIONS = [.25, .50, .75, 1.]
ABLATIONS = {
    'logistica': ['sem_exame_motivos', 'clinica_restrita', 'sem_imc_continuo'],
    'floresta': ['sem_exame_motivos', 'clinica_restrita', 'sem_ppa', 'sem_classificacao_imc'],
    'boosting': ['sem_exame_motivos', 'clinica_restrita', 'sem_ppa', 'sem_classificacao_imc', 'sem_imc_continuo'],
}
REFERRAL_PATTERN = r'1 - Cardiopatia (?:já estabelecida|congênita|adquirida)|6 - Sopro'


def save(table, path):
    table.to_csv(path, index=False, encoding='utf-8-sig')


def audits(output, dev):
    original = pd.read_csv(ROOT / 'resultado_analise/UCMF_base_final.csv', dtype={'ID': str})
    assignment = pd.read_csv(HISTORICO / 'particao_principal.csv', dtype={'ID': str})
    observed = original.loc[
        original[TARGET].isin(['Normal', 'Anormal']) &
        ~original.ID.isin(assignment.loc[assignment.conjunto.eq('teste'), 'ID'])
    ]
    conflicts = pd.read_csv(PREPARO / 'conflitos_alvo.csv')
    rows = []
    for source, frame in [('desenvolvimento', dev), ('base_auditavel_fora_do_teste', observed)]:
        y = frame[TARGET].map({'Normal': 0, 'Anormal': 1})
        for profile in REPRESENTATIONS:
            num, cat = columns(profile)
            profile_columns = num + cat + [HISTORY_COLUMN]
            groups = frame.assign(y=y).groupby(profile_columns, dropna=False).y.agg(['size', 'sum'])
            minority = np.minimum(groups['sum'], groups['size'] - groups['sum'])
            rows.append(dict(source=source, profile=profile, n=len(frame), profiles=len(groups),
                             conflicting_profiles=int((minority > 0).sum()),
                             rows_with_conflicts=int(groups.loc[minority.gt(0), 'size'].sum()),
                             minimum_errors_observed=int(minority.sum())))
    save(pd.DataFrame(rows), output / 'auditoria_conflitos.csv')
    save(conflicts.groupby(['grupo', TARGET], dropna=False).size().rename('n').reset_index(),
         output / 'rotulos_quarentena.csv')
    sensitive = dev.MOTIVO_UNIFICADO.str.contains(REFERRAL_PATTERN, na=False)
    coverage = dev.assign(motivo_mascarado=sensitive).groupby('y').agg(
        n=('ID', 'size'), motivo_mascarado=('motivo_mascarado', 'sum'),
        ppa_disponivel=('PPA_CALCULADA', 'count'), imc_class_disponivel=('CLASSIFICACAO IMC', 'count'),
    ).reset_index()
    save(coverage, output / 'cobertura_desenvolvimento.csv')


def ablate(frame, variant):
    frame = frame.copy()
    if variant == 'clinica_restrita':
        frame[['B2', 'PULSOS', 'MOTIVO_UNIFICADO', HISTORY_COLUMN]] = np.nan
    elif variant == 'sem_exame_motivos':
        frame[['B2', 'PULSOS']] = np.nan
        match = frame.MOTIVO_UNIFICADO.str.contains(REFERRAL_PATTERN, na=False)
        frame.loc[match, 'MOTIVO_UNIFICADO'] = pd.NA
    else:
        feature = {'sem_ppa': 'PPA_CALCULADA', 'sem_classificacao_imc': 'CLASSIFICACAO IMC',
                   'sem_imc_continuo': 'IMC'}[variant]
        frame[feature] = np.nan
    return frame


def fixed_evaluation(output, variant, train, valid, seed, name, params, profile, n_jobs):
    if checkpoint_valid(output):
        return read_json(output / 'concluido.json')
    inner = folds(train, 3, seed)
    output.mkdir(parents=True, exist_ok=True)
    save_folds(train, inner, output / 'particao_interna.csv', seed)
    print(f'{output.parent.parent.name} {name} {variant} ({len(train)} treino)', flush=True)
    start = time.perf_counter()
    trials = search(name, train, inner, seed, profile, [params], None, n_jobs)
    evaluate(name, profile, train, valid, seed, trials, output, None, time.perf_counter() - start)
    return read_json(output / 'concluido.json')


def complementary(output, dev, original, n_jobs, only_audit=False):
    audits(output, dev)
    if only_audit:
        return
    # Perfil da v3 e primeiro candidato da grade v3, definidos antes da extensão.
    # Em cada fração, o limiar é reaprendido usando apenas o treino daquela fração.
    seed = DESENHOS['2x5'][1][0]
    curves, ablations = [], []
    for fold, (a, b) in enumerate(folds(dev, 5, seed)):
        train, valid = dev.iloc[a].reset_index(drop=True), dev.iloc[b].reset_index(drop=True)
        inner_seed = seed * 10 + fold
        work = output / 'sensibilidade' / f'f{fold}'
        samples = {1.: train}
        for fraction in FRACTIONS[:-1]:
            splitter = StratifiedShuffleSplit(n_splits=1, train_size=fraction, random_state=inner_seed)
            subset, _ = next(splitter.split(train, train.y))
            samples[fraction] = train.iloc[np.sort(subset)].reset_index(drop=True)
        for name, profile in FIXED_PROFILES.items():
            params = original['candidates'][name][0]
            for fraction in FRACTIONS:
                subset = samples[fraction]
                setting = f'treino_{int(fraction * 100)}'
                info = fixed_evaluation(work / name / setting, setting, subset, valid, inner_seed,
                                        name, params, profile, n_jobs)
                curves.append(dict(fold=fold, model=name, profile=profile, fraction=fraction,
                                   n_train=len(subset), **info['metrics'],
                                   **{f'train_{k}': v for k, v in info['train_metrics'].items()}))
                if fraction == 1.:
                    ablations.append(dict(fold=fold, model=name, profile=profile, variant='completo',
                                          **info['metrics']))
            for variant in ABLATIONS[name]:
                info = fixed_evaluation(work / name / variant, variant, ablate(train, variant),
                                        ablate(valid, variant), inner_seed, name, params, profile, n_jobs)
                ablations.append(dict(fold=fold, model=name, profile=profile, variant=variant,
                                      **info['metrics']))
        save(pd.DataFrame(curves), output / 'curvas_aprendizado.csv')
        save(pd.DataFrame(ablations), output / 'ablacoes.csv')


def historical_metrics():
    external = pd.read_csv(HISTORICO / 'metricas_externas.csv')
    test = pd.read_csv(HISTORICO / 'metricas_teste.csv')
    return external.loc[external['mode'].eq('aprendido')], test.loc[test['mode'].eq('aprendido')]


def collect(output, design, design_rows, profile_rows):
    scope = output / design
    for folder in sorted(scope.glob('r*_f*')):
        repeat, fold = (int(token[1:]) for token in folder.name.split('_'))
        for label in ('base12', 'estendida16') if design == '5x2' else ('base12',):
            for name in MODELOS:
                models = folder / label / name
                infos = []
                for path in sorted(models.glob('*/concluido.json')):
                    info = read_json(path)
                    row = dict(design=design, budget=label, model=name, repeat=repeat, fold=fold,
                               profile=info['profile'], n_train=info['n_train'],
                               inner_ap=info['inner_ap'], candidate=info['candidate'],
                               threshold=info['threshold']['threshold'],
                               candidate_seconds=info['inner_candidate_seconds'],
                               search_seconds=info['shared_search_wall_seconds'],
                               refit_seconds=info['refit_seconds'],
                               path=path.parent.relative_to(output).as_posix(), **info['metrics'])
                    infos.append(row)
                if len(infos) != (1 if name == 'dummy' else 3):
                    continue
                profile_rows.extend(infos)
                maximum = max(row['inner_ap'] for row in infos)
                selected = min((row for row in infos if maximum - row['inner_ap'] <= 1e-6),
                               key=lambda row: REPRESENTATIONS.index(row['profile']))
                design_rows.append(selected)


def comparisons(external, output):
    results = []
    for budget, table in external.loc[external.design.eq('5x2')].groupby('budget'):
        scores = table.pivot(index=['repeat', 'fold'], columns='model', values='error').sort_index()
        if len(scores) != 10 or 'logistica' not in scores:
            continue
        for model in sorted(set(scores.columns) - {'logistica', 'dummy'}):
            difference = scores[model] - scores.logistica
            if difference.notna().all():
                results.append(dict(budget=budget, model=model, reference='logistica',
                                    **five_by_two(difference.to_numpy().reshape(5, 2))))
    for raw, corrected in [('f_p', 'f_p_holm'), ('t_p', 't_p_holm')]:
        for row, adjusted in zip(results, holm([row[raw] for row in results])):
            row[corrected] = adjusted
    write_json(output / 'testes_exploratorios_5x2.json', results)


def subgroup_analysis(output, external, dev):
    selected = external.loc[external.design.eq('2x5') & external.budget.eq('base12')]
    if selected.empty:
        return
    frame = dev[['ID', 'SEXO', 'FAIXA_ETARIA', 'PPA_CALCULADA', 'CLASSIFICACAO IMC']].copy()
    for col in ['SEXO', 'FAIXA_ETARIA']:
        frame[col] = frame[col].fillna('Ausente')
    for col in ['PPA_CALCULADA', 'CLASSIFICACAO IMC']:
        frame[col] = np.where(frame[col].notna(), 'Disponível', 'Ausente')
    rows, discordances = [], []
    for row in selected.itertuples():
        path = output / row.path / 'previsoes.csv'
        preds = pd.read_csv(path, dtype={'ID': str}).merge(frame, on='ID', validate='one_to_one')
        if row.model not in {'dummy', 'logistica'}:
            other = selected.loc[selected.model.eq('logistica') & selected.repeat.eq(row.repeat) &
                                 selected.fold.eq(row.fold)].iloc[0]
            reference = pd.read_csv(output / other.path / 'previsoes.csv', dtype={'ID': str})
            pair = preds.merge(reference[['ID', 'pred']], on='ID', validate='one_to_one',
                               suffixes=('', '_logistica'))
            for target, group in pair.groupby('y'):
                correct = group.pred.eq(target)
                baseline = group.pred_logistica.eq(target)
                discordances.append(dict(model=row.model, repeat=row.repeat, fold=row.fold, target=target,
                                         n=len(group), model_only=int((correct & ~baseline).sum()),
                                         logistic_only=int((~correct & baseline).sum())))
        for col in frame.columns.drop('ID'):
            for category, group in preds.groupby(col):
                for target, metric in [(0, 'specificity'), (1, 'recall')]:
                    labels = group.loc[group.y.eq(target), 'pred']
                    n, correct = len(labels), int(labels.eq(target).sum())
                    bounds = binomtest(correct, n).proportion_ci(method='wilson') if n else None
                    rows.append(dict(model=row.model, repeat=row.repeat, fold=row.fold, attribute=col,
                                     category=category, metric=metric, n=n, correct=correct,
                                     estimate=correct/n if n else None,
                                     lower=bounds.low if n else None, upper=bounds.high if n else None))
    save(pd.DataFrame(rows), output / 'subgrupos_por_fold.csv')
    save(pd.DataFrame(discordances), output / 'discordancias_por_fold.csv')


def md_table(frame):
    return '\n'.join([
        '| ' + ' | '.join(frame.columns) + ' |',
        '| ' + ' | '.join(['---'] * len(frame.columns)) + ' |',
        *['| ' + ' | '.join(f'{v:.4f}' if isinstance(v, float) else str(v) for v in row) + ' |'
          for row in frame.itertuples(index=False, name=None)],
    ])


def report(output, dev, complete):
    history, test = historical_metrics()
    save(test, output / 'referencia_teste_historico_v3.csv')
    design_rows, profile_rows = [], []
    for design in DESENHOS:
        collect(output, design, design_rows, profile_rows)
    if not design_rows:
        return
    new = pd.DataFrame(design_rows)
    save(pd.DataFrame(profile_rows), output / 'metricas_perfis_fixos.csv')
    base = history.rename(columns={'representation': 'profile'}).assign(design='5x2', budget='v3_4')
    external = pd.concat([base, new], ignore_index=True)
    save(external, output / 'metricas_por_fold.csv')
    summary = external.groupby(['design', 'budget', 'model']).agg(
        folds=('fold', 'size'), sensitivity_mean=('recall', 'mean'), sensitivity_sd=('recall', 'std'),
        specificity_mean=('specificity', 'mean'), folds_below_80=('specificity', lambda s: s.lt(.8).sum()),
        ap_mean=('ap', 'mean'), roc_auc_mean=('roc_auc', 'mean'), accuracy_mean=('accuracy', 'mean'),
        brier_mean=('brier', 'mean'),
    ).reset_index()
    save(summary, output / 'resumo_modelos.csv')
    aggregate = external.groupby(['design', 'budget', 'model', 'repeat']).agg(
        tp=('tp', 'sum'), tn=('tn', 'sum'), fp=('fp', 'sum'), fn=('fn', 'sum'),
        mean_fold_ap=('ap', 'mean'), mean_fold_roc_auc=('roc_auc', 'mean'), mean_fold_brier=('brier', 'mean'),
    ).reset_index()
    aggregate['recall'] = aggregate.tp / (aggregate.tp + aggregate.fn)
    aggregate['specificity'] = aggregate.tn / (aggregate.tn + aggregate.fp)
    save(aggregate, output / 'metricas_por_repeticao.csv')
    keys = ['model', 'repeat', 'fold']
    h = base[keys + METRICS]
    paired = new.loc[new.design.eq('5x2')].merge(h, on=keys, suffixes=('', '_v3'), validate='many_to_one')
    for metric in METRICS:
        paired[f'delta_{metric}'] = paired[metric] - paired[f'{metric}_v3']
    save(paired[['budget', *keys] + [f'delta_{m}' for m in METRICS]],
         output / 'diferencas_pareadas_orcamento.csv')
    comparisons(new, output)
    subgroup_analysis(output, new, dev)
    extra = ''
    if complete:
        learning = pd.read_csv(output / 'curvas_aprendizado.csv')
        curve = learning.groupby(['model', 'fraction'])[[
            'train_ap', 'ap', 'recall', 'specificity',
        ]].mean().reset_index()
        ablation = pd.read_csv(output / 'ablacoes.csv')
        comparator = ablation.loc[ablation.variant.eq('completo'), ['model', 'fold', 'ap', 'recall', 'specificity']]
        changes = ablation.loc[ablation.variant.ne('completo')].merge(
            comparator, on=['model', 'fold'], suffixes=('', '_completo'), validate='many_to_one',
        )
        deltas = []
        for metric in ['ap', 'recall', 'specificity']:
            key = f'delta_{metric}'
            changes[key] = changes[metric] - changes[f'{metric}_completo']
            deltas.append(key)
        save(changes[['model', 'fold', 'variant', *deltas]], output / 'diferencas_pareadas_ablacoes.csv')
        summarized = changes.groupby(['model', 'variant'])[deltas].mean().reset_index()
        extra = f"""
## Curvas de aprendizado e ablações

Médias de cinco folds com parâmetro fixo e limiares aprendidos dentro da fração de treino.

{md_table(curve)}

Diferenças externas médias em relação ao cenário completo. A ablação direcionada mascara motivos sensíveis e pode deixar um sinal de ausência. Clínica restrita omite todo o campo de motivos e HDA, além de B2 e pulsos.

{md_table(summarized)}
"""
    status = 'Concluída' if complete else 'Parcial'
    text = f"""# Extensão comparativa do UCMF

{status}. Foram usados {len(dev)} registros de desenvolvimento histórico. O teste histórico é apresentado com os resultados congelados da v3.

Os estimadores novos foram avaliados em folds externos com seleção de configuração e representação por AP interna. A política de limiar aprende sensibilidade máxima entre limiares com especificidade interna ≥80%. As medidas clínicas descrevem os registros, e essa meta é acadêmica.

{md_table(summary)}

As médias de AP, ROC-AUC e Brier foram calculadas entre folds. A tabela por repetição agrega as contagens de confusão. Desvios entre folds e diferenças pareadas descrevem estabilidade, pois os conjuntos de treino se sobrepõem. Os testes 5×2 de erro global são exploratórios. A família de hipóteses da extensão inclui floresta e boosting contra logística nos dois orçamentos 5×2, com correções Holm separadas para F e t.

O protocolo registra as grades e as sementes. O braço base12 contém os quatro candidatos da v3 e oito pontos adicionais da grade. Estendida16 adiciona quatro pontos externos à grade antiga. A calibração pode variar entre partições e a comparação por perfil mantém os mesmos registros.

Os intervalos dos subgrupos são Wilson por fold, condicionais aos modelos ajustados e à independência presumida dos registros naquele fold. A identidade do paciente não está disponível. Os conflitos de rótulos e as curvas de aprendizado investigam o erro observado. O erro de Bayes permanece desconhecido.

A confirmação externa requer uma nova coorte. As comparações prospectivas permanecem pendentes até que haja dados independentes com definição compatível de alvo, preditores e paciente.
{extra}

Métodos e referências no [plano de comparação](../referencias/plano_comparacao_modelos.md) e no [protocolo original](../referencias/protocolo_experimentos.md).
"""
    (output / 'relatorio_comparativo.md').write_text(text, encoding='utf-8')
