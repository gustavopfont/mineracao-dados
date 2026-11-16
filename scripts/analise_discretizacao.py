"""Resumos descritivos de discretização; não aprende cortes para a base clínica."""
from __future__ import annotations

import math

import pandas as pd

TARGET = 'NORMAL X ANORMAL'
IMC_CATEGORIES = ['Magreza acentuada', 'Magreza', 'Eutrofia', 'Risco de sobrepeso',
                  'Sobrepeso', 'Obesidade']
PA_CATEGORIES = ['Normal', 'Pré-hipertensão', 'HA estágio 1', 'HA estágio 2', 'HA estágio 3']
MISSING = 'Sem informação'


def bmi_age_reference(days: object) -> str:
    if pd.isna(days):
        return 'Idade indisponível'
    months = math.floor(float(days) / 30.4375)
    if 0 <= float(days) <= 1856:
        return 'OMS 2006: 0–60 meses completos'
    if 61 <= months <= 228:
        return 'OMS 2007: 61–228 meses completos'
    return 'Fora da referência OMS'


def pressure_age_reference(years: object) -> str:
    if pd.isna(years):
        return 'Idade indisponível'
    if years < 1:
        return 'Menor de 1 ano: não classificável'
    if years < 13:
        return 'DBHA: 1–12 anos'
    if years < 18:
        return 'DBHA: 13–17 anos'
    return 'DBHA: 18–19 anos'


def summarize(final: pd.DataFrame, bmi_audit: pd.DataFrame,
              pressure_audit: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Denominadores explícitos; inclui estratos sem classificação e categorias vazias."""
    data = final.copy()
    bmi = bmi_audit.set_index('ID')
    pa = pressure_audit.set_index('ID')
    data['ref_imc'] = data.ID.map(bmi.idade_dias).map(bmi_age_reference)
    data['ref_pa'] = data.ID.map(pa.idade_anos_completos).map(pressure_age_reference)
    data['sexo_resumo'] = data.SEXO.fillna(MISSING)
    coverage, frequencies, outcomes = [], [], []
    for variable, ref, categories in [('CLASSIFICACAO IMC', 'ref_imc', IMC_CATEGORIES),
                                       ('PPA_CALCULADA', 'ref_pa', PA_CATEGORIES)]:
        for (reference, sex), group in data.groupby([ref, 'sexo_resumo'], sort=True):
            total, classified = len(group), int(group[variable].notna().sum())
            coverage.append(dict(variavel=variable, referencia_etaria=reference, sexo=sex,
                                 n_total=total, n_classificados=classified, n_ausentes=total-classified,
                                 cobertura_percentual=100*classified/total))
            for category in categories + [MISSING]:
                subset = group.loc[group[variable].isna() if category == MISSING else group[variable].eq(category)]
                count = len(subset)
                frequencies.append(dict(variavel=variable, referencia_etaria=reference, sexo=sex,
                                        categoria=category, quantidade=count, n_total_estrato=total,
                                        percentual_estrato=100*count/total, n_classificados_estrato=classified,
                                        percentual_classificados=(100*count/classified
                                            if classified and category != MISSING else float('nan'))))
                normal = int(subset[TARGET].eq('Normal').sum())
                abnormal = int(subset[TARGET].eq('Anormal').sum())
                labeled = normal+abnormal
                outcomes.append(dict(variavel=variable, referencia_etaria=reference, sexo=sex,
                                     categoria=category, n_categoria=count, n_alvo_conhecido=labeled,
                                     n_normal=normal, n_anormal=abnormal, n_alvo_ausente=count-labeled,
                                     percentual_anormal_alvo_conhecido=(100*abnormal/labeled
                                         if labeled else float('nan'))))
    continuous = []
    # Mesmos estratos clínicos das categorias; alvo ausente também é exibido.
    for variable, ref in [('IMC', 'ref_imc'), ('PA SISTOLICA', 'ref_pa'), ('PA DIASTOLICA', 'ref_pa')]:
        for (reference, sex, target), group in data.groupby([ref, 'sexo_resumo', TARGET], dropna=False, sort=True):
            values = pd.to_numeric(group[variable], errors='coerce').dropna()
            continuous.append(dict(variavel=variable, referencia_etaria=reference, sexo=sex,
                                   alvo=target if pd.notna(target) else MISSING,
                                   n_total=len(group), n_validos=len(values), n_ausentes=len(group)-len(values),
                                   minimo=values.min(), q1=values.quantile(.25), mediana=values.median(),
                                   q3=values.quantile(.75), maximo=values.max()))
    quantiles, bins = [], []
    for variable in ['IMC', 'PA SISTOLICA', 'PA DIASTOLICA']:
        values = pd.to_numeric(data[variable], errors='coerce').dropna()
        limits = values.quantile([0, .25, .5, .75, 1])
        # Empates não são desfeitos por ordenação arbitrária nem por ruído.
        categorized = pd.qcut(values, 4, duplicates='drop') if len(values) else pd.Series(dtype='category')
        counts = categorized.value_counts(sort=False)
        quantiles.append(dict(variavel=variable, n_total=len(data), n_validos=len(values),
                              n_ausentes=len(data)-len(values), n_valores_distintos=values.nunique(),
                              minimo=limits.iloc[0], q1=limits.iloc[1], mediana=limits.iloc[2],
                              q3=limits.iloc[3], maximo=limits.iloc[4],
                              n_intervalos_efetivos=len(counts), metodo_quantil='linear (pandas)',
                              uso='somente descrição; não exportado como atributo'))
        for interval, count in counts.items():
            bins.append(dict(variavel=variable, intervalo=str(interval), quantidade=int(count),
                             n_validos=len(values), percentual_validos=100*count/len(values)))
    return {'cobertura_discretizacao.csv': pd.DataFrame(coverage),
            'frequencias_discretizacao.csv': pd.DataFrame(frequencies),
            'alvo_por_categoria_discretizacao.csv': pd.DataFrame(outcomes),
            'continuas_por_alvo_discretizacao.csv': pd.DataFrame(continuous),
            'diagnostico_quantis.csv': pd.DataFrame(quantiles),
            'intervalos_quartis_descritivos.csv': pd.DataFrame(bins)}


def report_lines(tables: dict[str, pd.DataFrame], comparison: pd.DataFrame) -> list[str]:
    quantiles = tables['diagnostico_quantis.csv']
    lines = ['', '## Revisão da discretização de IMC e pressão', '',
             'IMC, PAS e PAD contínuos e suas categorias clínicas são preservados. '
             'CLASSIFICACAO IMC e PPA_CALCULADA já são discretizações clínicas. '
             'Converter rótulos em números seria codificação; unir categorias seria agrupamento adicional. '
             'Não foram criadas versões binárias, cortes supervisionados nem uma segunda classificação de pressão.', '',
             '| Método | Avaliação e decisão |', '| --- | --- |',
             '| Mesma largura | Sensível a extremos; apenas para histogramas, sem rótulos clínicos. |',
             '| Quantis | Descrição relativa da amostra; empates e mistura de idades limitam interpretação. Não entram na base. |',
             '| K-means | Grupos de proximidade numérica não equivalem a condições médicas; reservado para estudo futuro. |',
             '| Cortes clínicos externos | Mantidos: OMS para IMC e DBHA 2025 para pressão. |',
             '| Entropia/MDL supervisionado | Depende do alvo e exigiria ajuste dentro do treino; fora desta etapa. |', '',
             'A [documentação do scikit-learn](https://sklearn.org/stable/modules/generated/sklearn.preprocessing.KBinsDiscretizer.html) '
             'descreve largura uniforme, quantis e k-means. [Fayyad e Irani](https://ijcai.org/proceedings/1993/141) '
             'descrevem discretização por entropia/MDL. A perda de informação ao categorizar preditores '
             'é discutida no [BMJ, 2025](https://www.bmj.com/content/390/bmj-2024-082440.short). '
             'Não se conclui superioridade preditiva de uma representação sem avaliar modelos.', '',
             '### Precisão e quartis observados', '',
             '| Medida | Válidos | Distintos | Q1 | Mediana | Q3 | Intervalos efetivos |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for row in quantiles.itertuples():
        lines.append(f'| {row.variavel} | {row.n_validos} | {row.n_valores_distintos} | '
                     f'{row.q1:g} | {row.mediana:g} | {row.q3:g} | {row.n_intervalos_efetivos} |')
    lines += ['', 'Os valores iguais permanecem juntos; os grupos podem ter tamanhos diferentes e '
              'limites repetidos são descartados. Esses intervalos não são chamados de normalidade ou hipertensão. '
              'O IMC disponível tem precisão limitada: poucos valores distintos não autorizam inventar casas decimais. '
              'Fronteiras de classificação precisam ser lidas considerando essa precisão.', '',
              '### IMC por idade e sexo — OMS mantida', '',
              '| Referência | Cortes em escore-z |', '| --- | --- |',
              '| Ambas | Magreza acentuada z < −3; magreza −3 ≤ z < −2; eutrofia −2 ≤ z ≤ +1. |',
              '| OMS 2006, 0–60 meses completos | Risco de sobrepeso +1 < z ≤ +2; sobrepeso +2 < z ≤ +3; obesidade z > +3. |',
              '| OMS 2007, 61–228 meses completos | Sobrepeso +1 < z ≤ +2; obesidade z > +2. |', '',
              'Mantêm-se as [categorias OMS infantis](https://www.who.int/news-room/questions-and-answers/item/child-growth-standards) '
              'e [posteriores](https://www.who.int/tools/growth-reference-data-for-5to19-years/indicators/bmi-for-age), '
              'sem acrescentar obesidade grave ou fundir grupos pequenos. A tabela inicial usa dias até 1856; '
              'a posterior usa meses completos por floor(dias/30,4375). A extensão inicial até o dia anterior '
              'a 61 meses completos está nas [notas oficiais da OMS](https://www.who.int/docs/default-source/child-growth/child-growth-standards/indicators/body-mass-index-for-age/readme-bfa-exp.pdf). '
              'Aniversários de 5 anos e as faixas gerais da base não substituem essa escala. '
              'Idades fora da referência continuam sem classificação, sem extrapolação para completar 19 anos. '
              'Nenhum escore-z individual é estimado apenas pelos pontos de corte.', '',
              '### Cobertura por referência etária e sexo', '',
              '| Variável | Referência etária | Sexo | Total | Classificados | Ausentes | Cobertura % |',
              '| --- | --- | --- | ---: | ---: | ---: | ---: |']
    for row in tables['cobertura_discretizacao.csv'].itertuples():
        lines.append(f'| {row.variavel} | {row.referencia_etaria} | {row.sexo} | {row.n_total} | '
                     f'{row.n_classificados} | {row.n_ausentes} | {row.cobertura_percentual:.2f} |')
    recovered = comparison.origem_altura.eq('recuperada por relação antropométrica')
    lines += ['', 'As referências etárias são atribuídas mesmo quando sexo ou medida estão ausentes; '
              'isso mantém todos os registros nos denominadores. Cobertura = classificados/total do estrato. '
              'As frequências em frequencias_discretizacao.csv mostram percentuais sobre todo o estrato '
              'e sobre os classificados; o percentual dos classificados fica vazio para a categoria técnica de ausência.', '',
              '### Pressão, procedência da altura e significado da PPA', '',
              'Menores de 1 ano não são classificados; 1–12 anos usam idade, sexo e altura; '
              '13–17 usam cortes de adolescentes; 18–19 usam os cortes brasileiros de adultos. '
              'Os limiares e a referência de cada registro estão na auditoria. A categoria mais elevada '
              'entre PAS e PAD prevalece; PPA normal não avalia hipotensão nem exclui cardiopatia. '
              'Uma única medida não confirma diagnóstico de hipertensão. [DBHA 2025](https://www.scielo.br/j/abc/a/BXT7Vk4B9VKQnJFsJhgJ4Hn/?lang=pt).', '',
              f'Alturas recuperadas por relação antropométrica: **{int(recovered.sum())}**; '
              f'PPA calculada nesses registros: **{int((recovered & comparison.classificacao.notna()).sum())}**. '
              'A auditoria distingue altura informada na origem, recuperada, ausente e origem não auditada. '
              'Recuperação algébrica não equivale a uma nova medição direta. Não houve imputação estatística; '
              'a aproximação por interpolação entre alturas continua explícita e sem extrapolação.', '',
              '### Relações com o alvo e comparação das representações', '',
              'alvo_por_categoria_discretizacao.csv apresenta contagens Normal/Anormal/alvo ausente '
              'por categoria, referência e sexo; percentual Anormal usa apenas alvos conhecidos da categoria. '
              'Categorias com zero registros e grupos pequenos permanecem identificáveis. '
              'continuas_por_alvo_discretizacao.csv apresenta n, ausências, mínimo, quartis e máximo '
              'de IMC/PAS/PAD nos mesmos estratos e por alvo, inclusive alvo desconhecido. '
              'As tabelas permitem descrição paralela; não constituem comparação de desempenho ou causalidade. '
              'As associações com o alvo continuam em associacoes_final.csv. Não há comparação direta '
              'de magnitude entre Spearman e V de Cramér como medida de qualidade preditiva.', '']
    lines += ['Resumo global por categoria (mistura idades e sexos; detalhes estratificados no CSV):', '',
              '| Variável | Categoria | Total | Normal | Anormal | Alvo ausente | % Anormal entre alvos conhecidos |',
              '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    outcomes = tables['alvo_por_categoria_discretizacao.csv']
    totals = outcomes.groupby(['variavel', 'categoria'], sort=False)[
        ['n_categoria', 'n_normal', 'n_anormal', 'n_alvo_ausente']].sum()
    for (variable, category), row in totals.iterrows():
        labeled = row.n_normal+row.n_anormal
        share = f'{100*row.n_anormal/labeled:.2f}' if labeled else '—'
        lines.append(f'| {variable} | {category} | {int(row.n_categoria)} | {int(row.n_normal)} | '
                     f'{int(row.n_anormal)} | {int(row.n_alvo_ausente)} | {share} |')
    lines += ['', 'Uma categoria nutricional ou pressórica não determina NORMAL X ANORMAL. '
              'Diferenças nestas proporções podem refletir a composição dos atendimentos e '
              'o padrão de dados ausentes; não justificam mudar pontos de corte ou preencher o alvo.', '']
    return lines
