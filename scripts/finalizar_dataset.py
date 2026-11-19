"""Gera base clínica final, sem divisão, imputação estatística ou modelos."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import re
from pathlib import Path

import pandas as pd

from analise_dataset import (
    NUMERIC_COLUMNS, TARGET, clean_anthropometrics, clean_dates_and_age,
    clean_numbers, classify_bmi, normalize_categories, read_dataset,
    remove_placeholders, shown, unresolved_issues,
)
from classificacao_pa import ROOT, REFERENCE, age_context, classify_pressure
from analise_discretizacao import report_lines, summarize

FINAL_COLUMNS = ['ID', 'SEXO', 'IDADE', 'FAIXA_ETARIA', 'Peso', 'Altura', 'IMC',
                 'CLASSIFICACAO IMC', 'FC', 'PA SISTOLICA', 'PA DIASTOLICA',
                 'PPA_CALCULADA', 'PULSOS', 'B2', 'MOTIVO_UNIFICADO',
                 'HDA_UNIFICADA', TARGET]
REMOVED = ['SOPRO', 'Convenio', 'Atendimento', 'DN', 'MOTIVO1', 'MOTIVO2',
           'HDA 1', 'HDA2', 'PPA']
# Mapeamento fechado: não infere equivalência clínica a partir de semelhança textual.
SPELLING = {'Palpitacao': 'Palpitação', '6 - Dispnéia': '6 - Dispneia',
            '1 - Cardiopatia congenica': '1 - Cardiopatia congênita',
            '6 - Cardiopatia na familia': '6 - Cardiopatia na família',
            '6 - Cianose e dispnéia': '6 - Cianose e dispneia'}
HDA_ORDER = ['Assintomático', 'Palpitação', 'Dispneia', 'Dor precordial',
             'Desmaio/tontura', 'Cianose', 'Ganho de peso', 'Outro']
LEGACY_PPA = {'Normal': 'Normal', 'Pre-Hipertensão PAS': 'Pré-hipertensão',
              'Pre-Hipertensão PAD': 'Pré-hipertensão', 'HAS-1 PAS': 'HA estágio 1',
              'HAS-1 PAD': 'HA estágio 1', 'HAS-2 PAS': 'HA estágio 2',
              'HAS-2 PAD': 'HA estágio 2'}


def canonical(value: object) -> str:
    text = shown(value)
    return SPELLING.get(text, text)


def merge_reasons(first: object, second: object) -> tuple[str | None, bool]:
    a, b = canonical(first), canonical(second)
    prefixes = [re.match(r'^(\d+)\s*-', x) for x in (a, b)]
    conflict = bool(all(prefixes) and prefixes[0][1] != prefixes[1][1])
    return (' → '.join(x for x in (a, b) if x) or None), conflict


def merge_history(first: object, second: object) -> tuple[str | None, bool]:
    values = {canonical(x) for x in (first, second)} - {''}
    ordered = sorted(values, key=lambda x: (HDA_ORDER.index(x) if x in HDA_ORDER else len(HDA_ORDER), x))
    return (' | '.join(ordered) or None), ('Assintomático' in values and len(values) > 1)


def regenerate(raw_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Reexecuta regras existentes em memória, sem chamar main nem sobrescrever saídas."""
    frame = read_dataset(raw_path)
    events, issues = [], []
    normalize_categories(frame, events)
    frame, removed = remove_placeholders(frame)
    clean_numbers(frame, events, issues)
    _, days = clean_dates_and_age(frame, events, issues)
    clean_anthropometrics(frame, events, issues)
    frame['CLASSIFICACAO IMC'] = pd.Series(pd.NA, index=frame.index, dtype=object)
    bmi_audit = classify_bmi(frame, days)
    issues = unresolved_issues(frame, issues)
    return frame, pd.DataFrame(events), pd.DataFrame(issues), removed, bmi_audit


def validate_baseline(frame: pd.DataFrame, baseline: pd.DataFrame) -> None:
    if not frame.ID.is_unique or not baseline.ID.is_unique or list(frame.ID) != list(baseline.ID):
        raise ValueError('IDs ou ordem divergem entre limpeza reproduzida e referência')
    for column in baseline:
        a, b = frame[column].map(shown), baseline[column].map(shown)
        if column in NUMERIC_COLUMNS:
            a = pd.to_numeric(a, errors='coerce')
            b = pd.to_numeric(b, errors='coerce')
            equal = (a.isna() & b.isna()) | ((a-b).abs() < 1e-9)
        else:
            equal = a == b
        if not equal.all():
            raise ValueError(f'Limpeza reproduzida diverge em {column}: {int((~equal).sum())} registros')


def transform(frame: pd.DataFrame, events: pd.DataFrame | None = None
              ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    final = frame.copy()
    audits, comparisons = [], []
    recovered = {}
    if events is not None and not events.empty:
        changes = events.loc[events.variavel.eq('Altura') &
                             events.regra.str.startswith('sqrt(Peso / IMC)', na=False)]
        recovered = dict(zip(changes.ID.map(str), changes.regra))
    for index, row in frame.iterrows():
        context = age_context(row.to_dict())
        pressure = classify_pressure(context['idade_anos_completos'], shown(row['SEXO']),
                                     row['Altura'], row['PA SISTOLICA'], row['PA DIASTOLICA'])
        reason, mismatch = merge_reasons(row['MOTIVO1'], row['MOTIVO2'])
        history, contradiction = merge_history(row['HDA 1'], row['HDA2'])
        height_origin = ('ausente' if pd.isna(row.Altura) else
                         'recuperada por relação antropométrica' if str(row.ID) in recovered else
                         'informada na origem' if events is not None else 'origem não auditada')
        height_provenance = {'origem_altura': height_origin,
                             'formula_altura': recovered.get(str(row.ID), '')}
        values = {'FAIXA_ETARIA': context['faixa_etaria'], 'PPA_CALCULADA': pressure['classificacao'],
                  'MOTIVO_UNIFICADO': reason, 'HDA_UNIFICADA': history}
        for column, value in values.items():
            if column not in final:
                final[column] = pd.Series(pd.NA, index=final.index, dtype=object)
            final.at[index, column] = value
        audits.append({'ID': shown(row.ID), 'linha_origem': row['_LINHA_ORIGEM'],
                       **context, **values, **height_provenance, 'MOTIVO1_original': shown(row['MOTIVO1']),
                       'MOTIVO2_original': shown(row['MOTIVO2']),
                       'HDA1_original': shown(row['HDA 1']), 'HDA2_original': shown(row['HDA2']),
                       'prefixos_motivo_divergentes': mismatch, 'hda_contraditoria': contradiction,
                       **{f'{c}_original': shown(row[c]) for c in ['SOPRO', 'Convenio', 'Atendimento', 'DN']}})
        old = LEGACY_PPA.get(shown(row['PPA']))
        new = pressure['classificacao']
        if old and new:
            status = 'concordante' if old == new else 'divergente'
        elif new:
            status = 'nova classificação'
        else:
            status = 'não verificável'
        comparisons.append({'ID': shown(row.ID), **context, **height_provenance, 'SEXO': shown(row.SEXO),
                            'Altura': row.Altura, 'PAS': row['PA SISTOLICA'], 'PAD': row['PA DIASTOLICA'],
                            'PPA_original': shown(row.PPA), 'PPA_original_harmonizada': old,
                            'situacao': status, **pressure})
    return final[FINAL_COLUMNS], pd.DataFrame(audits), pd.DataFrame(comparisons)


def association(frame: pd.DataFrame, a: str, b: str, method: str,
                stratum: str = 'Todos') -> dict:
    pair = frame[[a, b]].dropna()
    n = len(pair)
    value = float('nan')
    if method == 'Spearman':
        pair = pair.apply(pd.to_numeric, errors='coerce').dropna()
        n = len(pair)
        if n > 1 and pair[a].nunique() > 1 and pair[b].nunique() > 1:
            value = pair[a].rank().corr(pair[b].rank())
    elif n:
        table = pd.crosstab(pair[a], pair[b])
        k = min(table.shape)-1
        if k > 0:
            expected = table.sum(axis=1).to_numpy()[:, None] * table.sum(axis=0).to_numpy()[None, :] / n
            chi2 = (((table.to_numpy()-expected)**2)/expected).sum()
            value = math.sqrt(chi2/(n*k))
    return dict(variavel_a=a, variavel_b=b, metodo=method, estrato=stratum,
                n_total=len(frame), n_pares=n, n_sem_par=len(frame)-n,
                ausentes_a=int(frame[a].isna().sum()), ausentes_b=int(frame[b].isna().sum()),
                coeficiente=value)


def analyze(frame: pd.DataFrame, final: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = frame.copy()
    for c in ['FAIXA_ETARIA', 'MOTIVO_UNIFICADO', 'HDA_UNIFICADA', 'PPA_CALCULADA']:
        data[c] = final[c]
    numeric = ['IDADE', 'Peso', 'Altura', 'IMC', 'FC', 'PA SISTOLICA', 'PA DIASTOLICA']
    results = [association(data, a, b, 'Spearman') for a, b in itertools.combinations(numeric, 2)]
    for (band, sex), group in data.groupby(['FAIXA_ETARIA', 'SEXO'], dropna=False, observed=True):
        for a in ['Peso', 'Altura', 'IMC']:
            for b in ['PA SISTOLICA', 'PA DIASTOLICA']:
                results.append(association(group, a, b, 'Spearman', f'{band}; {sex}'))
    cats = ['SEXO', 'B2', 'PULSOS', 'MOTIVO_UNIFICADO', 'HDA_UNIFICADA',
            'MOTIVO1', 'MOTIVO2', 'HDA 1', 'HDA2', 'PPA_CALCULADA', 'CLASSIFICACAO IMC']
    pairs = list(dict.fromkeys([(c, TARGET) for c in cats+['SOPRO']] +
                              [('SOPRO', c) for c in cats] +
                              [('MOTIVO_UNIFICADO', 'HDA_UNIFICADA')]))
    frequencies = []
    for a, b in pairs:
        results.append(association(data, a, b, 'V de Cramér'))
        counts = data.groupby([a, b], dropna=False, observed=True).size()
        for (x, y), count in counts.items():
            frequencies.append(dict(variavel_a=a, categoria_a=x, variavel_b=b, categoria_b=y,
                                    quantidade=int(count), n_total=len(data)))
    return pd.DataFrame(results), pd.DataFrame(frequencies)


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report(output: Path, final: pd.DataFrame, audit: pd.DataFrame,
           comparison: pd.DataFrame, associations: pd.DataFrame, issues: pd.DataFrame,
           discretization: dict[str, pd.DataFrame]) -> None:
    n = len(final)
    old_count = comparison.PPA_original.ne('').sum()
    calculated = comparison.classificacao.notna().sum()
    new_count = comparison.situacao.eq('nova classificação').sum()
    old_only = (comparison.PPA_original.ne('') & comparison.classificacao.isna()).sum()
    sopr = associations.loc[(associations.variavel_a == 'SOPRO') &
                            (associations.variavel_b == TARGET)].iloc[0]
    lines = ['# Finalização do pré-processamento UCMF', '',
             f'Base final: **{n} registros e {len(final.columns)} colunas**, com '
             f'**{final[TARGET].isna().sum()} alvos ausentes**. IDs, ordem e alvo preservados.', '',
             '## Auditoria e cobertura', '',
             'A limpeza foi reproduzida em memória a partir do bruto e comparada célula a célula '
             'com a base limpa de referência (tolerância numérica 1e-9). Nenhum dos dois CSVs foi sobrescrito. '
             'Auditorias anteriores foram regeneradas em arquivos separados, incluindo linhas removidas e pendências.', '',
             f'- PPA legada preenchida: {old_count} ({100*old_count/n:.2f}%).',
             f'- PPA calculada: {calculated} ({100*calculated/n:.2f}%).',
             f'- Novas classificações onde a PPA era vazia: {new_count}.',
             f'- PPA legada preenchida, mas sem requisitos para recálculo: {old_only}.',
             f'- Variação líquida da cobertura validável: {calculated-old_count:+d} registros.',
             f'- Motivos com prefixos divergentes, preservados: {audit.prefixos_motivo_divergentes.sum()}.',
             f'- Contradições em HDA: {audit.hda_contraditoria.sum()}.',
             f'- Pendências herdadas da limpeza: {len(issues)}.', '',
             '### Comparação da PPA', '', '| Situação | Registros |', '| --- | ---: |']
    lines += [f'| {status} | {count} |' for status, count in comparison.situacao.value_counts().items()]
    lines += ['', '### Impedimentos para classificação', '', '| Motivo | Registros |', '| --- | ---: |']
    lines += [f'| {reason} | {count} |' for reason, count in comparison.loc[
        comparison.classificacao.isna(), 'motivo'].value_counts().items()]
    lines += ['', '## SOPRO e relações entre variáveis', '',
              f'SOPRO × alvo: V de Cramér = **{sopr.coeficiente:.4f}**, '
              f'n = {sopr.n_pares}; {sopr.n_sem_par} registros sem par completo. '
              'SOPRO foi analisado antes de ser excluído por escolha pedagógica. '
              'A associação não comprova vazamento. O motivo de encaminhamento “Sopro” permanece.', '',
              'As tabelas de associações informam pares válidos, ausências e estratos de idade/sexo; '
              'as frequências incluem os faltantes. V de Cramér é descritivo, sem correção por viés, '
              'e pode ser instável em tabelas esparsas. Spearman nos estratos não elimina todo o '
              'efeito de idade. HDA unificada é um conjunto de sintomas, não uma escala ordinal.', '',
              '## Regras e limites', '',
              'Faixas etárias usam aniversários quando as datas são coerentes. IDADE contínua foi preservada; '
              'o detalhe dos anos completos e sua origem ficam na auditoria. Sem datas coerentes, usa-se '
              'a idade disponível, cuja precisão pode ser limitada pelo arredondamento prévio.', '',
              'PPA_CALCULADA descreve uma medida. Para 1–12 anos, os percentis são interpolados '
              'linearmente em centímetros entre alturas tabuladas, sem extrapolação e sem arredondar '
              'os limiares. Essa interpolação é uma aproximação computacional do projeto. '
              'O limite de maior gravidade entre PAS/PAD prevalece, com os tetos absolutos da diretriz. '
              'Menores de um ano não são classificados. Aos 18 anos passam a valer os cortes brasileiros '
              'para adultos, que diferem dos cortes de adolescentes.', '',
              'A PPA legada só é harmonizada para comparação de categoria; seu componente PAS/PAD '
              'permanece no texto original. Uma concordância não valida retroativamente o diagnóstico.', '',
              'ID é metadado, nunca preditor. B2, PULSOS e histórico de cardiopatia conhecida permanecem '
              'por decisão do exercício: o momento de disponibilidade precisa ser revisto antes de '
              'uma aplicação prospectiva. Peso, altura, IMC e sua classificação são redundantes em parte; '
              'sua seleção fica para a modelagem. Faltantes continuam vazios e alvos não foram inferidos.', '',
              'Não houve divisão de dados, imputação estatística, normalização aprendida, balanceamento '
              'ou treino. Ganhos de cobertura e organização não demonstram ganho preditivo.', '',
              '## Fontes', '',
              '- [DBHA 2025, tabelas 9.1–9.3 e quadro 3.2](https://www.scielo.br/j/abc/a/BXT7Vk4B9VKQnJFsJhgJ4Hn/?lang=pt): classificação, idade, sexo e altura; diagnóstico exige confirmação.',
              '- [AAP 2017](https://publications.aap.org/pediatrics/article/140/3/e20171904/38358): tabelas completas e diferença entre triagem e classificação.',
              '- [RCH: dor torácica](https://www.rch.org.au/clinicalguide/guideline_index/Chest_Pain/): sintomas não são diagnósticos; história e exame importam em conjunto.',
              '- [RCH: variáveis fisiológicas](https://www.rch.org.au/clinicalguide/guideline_index/normal_ranges_for_physiological_variables/): FC e pressão variam com idade e contexto.',
              '- [AHA: sopros](https://www.heart.org/en/health-topics/heart-murmurs): sopros inocentes são comuns.', '',
              'Os valores de referência e seu hash estão em referencias/pa_dbha_2025.csv e .json. '
              'Consulta em 07/11/2026. O gerador funciona sem rede.', '']
    lines += report_lines(discretization, comparison)
    (output/'relatorio_finalizacao.md').write_text('\n'.join(lines), encoding='utf-8')


def run(raw: Path, baseline_path: Path, output: Path) -> None:
    # Uma saída nunca pode substituir uma fonte, inclusive por --saida personalizado.
    if output.resolve() in {raw.resolve(), baseline_path.resolve()}:
        raise ValueError('Diretório de saída não pode ser arquivo de entrada')
    reference_paths = [REFERENCE, REFERENCE.with_suffix('.json'),
                       ROOT/'referencias/imc_oms_0_5.csv', ROOT/'referencias/imc_oms_5_19.csv']
    protected_paths = [raw, baseline_path] + reference_paths
    before = {str(path): checksum(path) for path in protected_paths}
    baseline = pd.read_csv(baseline_path, dtype='string', encoding='utf-8-sig')
    frame, events, issues, removed, bmi_audit = regenerate(raw)
    validate_baseline(frame, baseline)
    final, audit, comparison = transform(frame, events)
    if list(final.ID) != list(baseline.ID) or list(final[TARGET].map(shown)) != list(baseline[TARGET].map(shown)):
        raise AssertionError('IDs ou alvo alterados')
    associations, frequencies = analyze(frame, final)
    discretization = summarize(final, bmi_audit, comparison)
    output.mkdir(parents=True, exist_ok=True)
    tables = {'UCMF_base_final.csv': final, 'auditoria_finalizacao.csv': audit,
              'comparacao_ppa_final.csv': comparison, 'associacoes_final.csv': associations,
              'frequencias_associacoes_final.csv': frequencies,
              'alteracoes_limpeza_reproduzida.csv': events, 'pendencias_limpeza_reproduzida.csv': issues,
              'linhas_removidas_limpeza_reproduzida.csv': removed}
    tables.update(discretization)
    tables['auditoria_imc_final.csv'] = bmi_audit
    for name, table in tables.items():
        destination = output/name
        if destination.resolve() in {raw.resolve(), baseline_path.resolve()}:
            raise ValueError('Saída sobrescreveria fonte')
        table.to_csv(destination, index=False, encoding='utf-8-sig')
    quality = pd.DataFrame([dict(variavel=c, ausentes=int(final[c].isna().sum()),
                                 percentual_ausente=round(100*final[c].isna().mean(), 3),
                                 categorias_ou_valores=int(final[c].nunique())) for c in final])
    quality.to_csv(output/'qualidade_base_final.csv', index=False, encoding='utf-8-sig')
    report(output, final, audit, comparison, associations, issues, discretization)
    manifest = dict(entradas_sha256=before, referencia_sha256=checksum(REFERENCE),
                    linhas=len(final), colunas=list(final), excluidas=REMOVED,
                    alvos_ausentes=int(final[TARGET].isna().sum()),
                    saidas_sha256={name: checksum(output/name) for name in
                                   list(tables)+['qualidade_base_final.csv', 'relatorio_finalizacao.md']})
    if before != {str(path): checksum(path) for path in protected_paths}:
        raise AssertionError('Arquivo de referência alterado')
    (output/'manifesto_base_final.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'Base final: {len(final)} registros; {len(final.columns)} colunas')
    print(f'PPA calculada: {comparison.classificacao.notna().sum()}; alvos ausentes: {final[TARGET].isna().sum()}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bruto', type=Path, default=ROOT/'dados/UCMF_raw.csv')
    parser.add_argument('--limpo', type=Path, default=ROOT/'resultados/analise/UCMF_limpo.csv')
    parser.add_argument('--saida', type=Path, default=ROOT/'resultados/analise')
    args = parser.parse_args()
    run(args.bruto, args.limpo, args.saida)
