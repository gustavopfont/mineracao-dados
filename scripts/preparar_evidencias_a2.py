"""Gera tabelas e figuras de apoio à A2 a partir das saídas agregadas."""
import argparse
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np
import pandas as pd

from metricas_modelagem import holm, mcnemar_exact
from treinar_modelos import ROOT, read_json, sha, write_json

EDA = ROOT / 'resultado_analise'
V3 = ROOT / 'resultado_experimentos_reduzido'
EXT = ROOT / 'resultado_experimentos_ampliado_publicado'
R01 = ROOT / 'resultado_experimentos_rodadas/r01_5folds_2rep_12cand'
DEFAULT_OUT = ROOT / 'resultado_a2'
MODEL_NAMES = {
    'dummy': 'Dummy', 'logistica': 'Regressão logística', 'arvore': 'Árvore',
    'knn': 'KNN', 'floresta': 'Random Forest', 'boosting': 'HistGradientBoosting',
}


def save(table, path):
    table.to_csv(path, index=False, encoding='utf-8', lineterminator='\n')


def prepare_tables(out):
    comparison = pd.read_csv(V3 / 'metricas_teste.csv')
    comparison = comparison.loc[comparison['mode'].eq('aprendido')].drop(columns='mode').copy()
    frozen = read_json(V3 / 'modelos_selecionados.json')['models']
    comparison.insert(1, 'representation', comparison.model.map(lambda m: frozen[m]['representation']))
    comparison.insert(2, 'threshold', comparison.model.map(lambda m: frozen[m]['threshold_info']['threshold']))
    save(comparison, out / 'desempenho_teste_v3.csv')

    assignment = pd.read_csv(V3 / 'particao_principal.csv', dtype={'ID': str})
    if assignment.ID.duplicated().any() or set(assignment.y) != {0, 1}:
        raise ValueError('Partição principal inconsistente')
    population = assignment.groupby(['conjunto', 'y']).size().unstack(fill_value=0)
    population = population.rename(columns={0: 'Normal', 1: 'Anormal'}).reset_index()
    population['total'] = population.Normal + population.Anormal
    save(population, out / 'contagens_por_particao.csv')

    r01 = pd.read_csv(R01 / 'metricas_externas.csv')
    r01 = r01.loc[r01['mode'].eq('aprendido')].assign(rodada='r01', design='2x5', budget='base12')
    ext = pd.read_csv(EXT / 'metricas_por_fold.csv')
    ext = ext.assign(rodada=np.where(ext.budget.eq('v3_4'), 'v3', 'extensao'))
    development = pd.concat([r01, ext], ignore_index=True)
    groups = development.groupby(['rodada', 'design', 'budget', 'model'])
    result = groups.agg(
        folds=('fold', 'size'), sensibilidade=('recall', 'mean'),
        especificidade=('specificity', 'mean'), ap=('ap', 'mean'), roc_auc=('roc_auc', 'mean'),
        f1=('f1', 'mean'), brier=('brier', 'mean'),
        folds_especificidade_abaixo_80=('specificity', lambda x: x.lt(.8).sum()),
    ).reset_index()
    if not result.folds.eq(10).all():
        raise ValueError('A tabela de A2 exige dez avaliações externas por grupo')
    save(result, out / 'desempenho_desenvolvimento.csv')

    permutation = pd.read_csv(V3 / 'importancia_permutacao.csv')
    ordered = permutation.groupby('feature')['ap_drop'].agg(['mean', 'std', 'count'])
    ordered = ordered.rename(columns={'mean': 'queda_ap_media', 'std': 'queda_ap_dp', 'count': 'permutacoes'})
    save(ordered.sort_values('queda_ap_media', ascending=False).reset_index(),
         out / 'importancia_floresta_v3.csv')
    return comparison.set_index('model'), assignment, frozen


def figure_sopro(out):
    pairs = pd.read_csv(EDA / 'frequencias_associacoes_final.csv', keep_default_na=False)
    rows = pairs.loc[pairs.variavel_a.eq('SOPRO') & pairs.variavel_b.eq('NORMAL X ANORMAL') &
                     pairs.categoria_a.ne('') & pairs.categoria_b.isin(['Normal', 'Anormal'])].copy()
    rows['grupo'] = np.where(rows.categoria_a.eq('Ausente'), 'Sopro ausente', 'Sopro registrado')
    counts = rows.pivot_table(index='grupo', columns='categoria_b', values='quantidade', aggfunc='sum')
    counts = counts.reindex(['Sopro ausente', 'Sopro registrado'])
    counts['total'] = counts.Normal + counts.Anormal
    counts['proporcao_anormal'] = counts.Anormal / counts.total
    if counts.total.sum() != 11682:
        raise ValueError('A figura exige os 11.682 pares válidos da auditoria')
    save(counts.reset_index(), out / 'sopro_alvo_contagens.csv')
    fig, ax = plt.subplots(figsize=(3.5, 2.22), layout='constrained')
    bars = ax.barh(counts.index, counts.proporcao_anormal, color=['#3F7298', '#00604F'], height=.54)
    for bar, row in zip(bars, counts.itertuples()):
        ratio = f'{row.proporcao_anormal:.1%}'.replace('.', ',')
        ax.text(bar.get_width() + .025, bar.get_y() + bar.get_height()/2,
                f'{ratio}\n{row.Anormal}/{row.total}', va='center', fontsize=8)
    ax.invert_yaxis()
    ax.set(xlim=(0, 1.22), xticks=[0, .25, .5, .75, 1], xlabel='Proporção de registros Anormal')
    ax.xaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax.tick_params(labelsize=8, length=0)
    ax.grid(axis='x', alpha=.2)
    ax.set_axisbelow(True)
    ax.spines[['top', 'right', 'left']].set_visible(False)
    fig.savefig(out / 'figura_sopro_alvo.png', dpi=350)
    plt.close(fig)


def figure_confusion(out, comparison):
    fig, axes = plt.subplots(1, 2, figsize=(3.5, 2.1), layout='constrained')
    for ax, model in zip(axes, ['logistica', 'floresta']):
        row = comparison.loc[model]
        matrix = np.array([[row.tn, row.fp], [row.fn, row.tp]], dtype=int)
        ax.imshow(matrix, cmap='Blues', vmin=0, vmax=1313)
        ax.set_xticks([0, 1], labels=['Normal', 'Anormal'], fontsize=7)
        ax.set_yticks([0, 1], labels=['Normal', 'Anormal'], fontsize=7)
        ax.set_title('Logística' if model == 'logistica' else 'Random Forest', fontsize=9)
        ax.tick_params(length=0)
        for (i, j), value in np.ndenumerate(matrix):
            ax.text(j, i, str(value), ha='center', va='center', weight='bold',
                    color='white' if value >= 650 else '#12304B', fontsize=10)
    fig.supxlabel('Classe prevista', fontsize=8)
    fig.supylabel('Classe observada', fontsize=8)
    fig.savefig(out / 'figura_matrizes_teste_v3.png', dpi=350)
    plt.close(fig)


def frozen_predictions(name, reference, truth, model_info, test_hash):
    directories = V3 / 'finais' / name
    path = directories / 'previsoes_teste.csv'
    marker = read_json(directories / 'teste_concluido.json')
    if sha(path) != marker['prediction_sha256']:
        raise ValueError(f'Predições alteradas em {name}')
    table = pd.read_csv(path, dtype={'ID': str, 'p': str}).set_index('ID')
    if not table.index.is_unique or set(table.index) != set(truth.index):
        raise ValueError(f'IDs inesperados nas previsões de {name}')
    table = table.reindex(truth.index)
    threshold = model_info['threshold_info']['threshold']
    implied_label = table.p.map(float).ge(threshold).astype(int)
    if not table.y.eq(truth).all() or not table.pred.eq(implied_label).all():
        raise ValueError(f'Alvo ou limiar congelado incoerente em {name}')
    counts = Counter(zip(truth, table.pred))
    for key, pair in {'tn': (0, 0), 'fp': (0, 1), 'fn': (1, 0), 'tp': (1, 1)}.items():
        if counts[pair] != int(reference[key]):
            raise ValueError(f'Matriz local difere do resultado publicado: {name}')
    test_hash[name] = marker['prediction_sha256']
    return table.pred.to_numpy()


def exploratory_test(out, comparison, assignment, frozen):
    test = assignment.loc[assignment.conjunto.eq('teste'), ['ID', 'y']]
    truth = test.set_index('ID').y
    hashes = {}
    a, b = [frozen_predictions(name, comparison.loc[name], truth, frozen[name], hashes)
            for name in ('floresta', 'knn')]
    rng = np.random.default_rng(1830)
    results = []
    for target, metric in [(1, 'recall'), (0, 'specificity')]:
        exact = mcnemar_exact(truth.to_numpy(), a, b, target)
        n = exact['n']
        only_a, only_b = exact['winner_only_correct'], exact['logistic_only_correct']
        simulated = rng.multinomial(n, [only_a/n, only_b/n, 1-(only_a+only_b)/n], size=2000)
        interval = np.quantile((simulated[:, 0] - simulated[:, 1])/n, [.025, .975])
        results.append(dict(metric=metric, n=n, somente_floresta_correta=only_a, somente_knn_correto=only_b,
                            diferenca_floresta_menos_knn=(only_a-only_b)/n, p=exact['p'],
                            ic95_bootstrap_nominal=[float(v) for v in interval]))
    for entry, p in zip(results, holm([row['p'] for row in results])):
        entry['p_holm'] = p
    write_json(out / 'teste_exploratorio_floresta_knn_v3.json', dict(
        tipo='pos_hoc_testes_de_mcnemar_pareados_por_classe',
        origem='Modelos e limiares congelados v3; teste histórico já avaliado',
        modelo_a=MODEL_NAMES['floresta'], modelo_b=MODEL_NAMES['knn'],
        previsoes_locais_sha256=hashes, bootstrap_seed=1830, bootstrap_repeticoes=2000,
        comparacoes=results,
    ))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saida', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--incluir-teste-exploratorio', action='store_true',
                        help='Exige checkpoints locais das previsões do teste da v3.')
    args = parser.parse_args()
    args.saida.mkdir(parents=True, exist_ok=True)
    comparison, assignment, frozen = prepare_tables(args.saida)
    figure_sopro(args.saida)
    figure_confusion(args.saida, comparison)
    if args.incluir_teste_exploratorio:
        exploratory_test(args.saida, comparison, assignment, frozen)
    print(f'Evidências da A2 em {args.saida}')


if __name__ == '__main__':
    main()
