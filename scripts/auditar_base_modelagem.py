"""Audita e reduz a base supervisionada, sem imputar, dividir ou treinar."""
from __future__ import annotations

# Regras R1–R12 e fontes clínicas/metodológicas: referencias/metodologia_preparo.md.
# Deduplicação/quarentena são políticas locais; não são prescrições da OMS.

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from analise_dataset import LIMITS
from finalizar_dataset import FINAL_COLUMNS
from preparar_modelagem import (ROOT, TARGET, FEATURE_COLUMNS, DERIVED_COLUMNS,
                               SYMPTOMS, duplicate_groups, build_preprocessor)

DOMAINS = {
    'SEXO': {'Masculino', 'Feminino', 'Indeterminado'},
    'PULSOS': {'Normais', 'Amplos', 'Femorais diminuídos', 'Diminuídos', 'Outro'},
    'B2': {'Normal', 'Outro', 'Hiperfonética', 'Desdob fixo', 'Única'},
    'CLASSIFICACAO IMC': {'Magreza acentuada', 'Magreza', 'Eutrofia', 'Risco de sobrepeso', 'Sobrepeso', 'Obesidade'},
    'PPA_CALCULADA': {'Normal', 'Pré-hipertensão', 'HA estágio 1', 'HA estágio 2', 'HA estágio 3'},
    'FAIXA_ETARIA': {'Menor de 1 ano', '1–2 anos', '3–5 anos', '6–12 anos', '13–17 anos', '18–19 anos'},
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(frame):
    if set(frame) != set(FINAL_COLUMNS):
        raise ValueError('Esquema de entrada diferente da base final de 17 colunas')
    data = frame[FINAL_COLUMNS].copy().astype(object)
    for c in data:
        data[c] = data[c].map(lambda x: x.strip() if isinstance(x, str) else x)
        data[c] = data[c].replace('', pd.NA)
    if data.ID.isna().any() or data.ID.duplicated().any() or not data.ID.astype(str).str.fullmatch(r'\d+').all():
        raise ValueError('IDs devem ser inteiros únicos e preenchidos')
    if not data[TARGET].dropna().isin(['Normal', 'Anormal']).all():
        raise ValueError('Alvo inválido: não será corrigido por inferência')
    events = []

    def clear(index, column, reason):
        value = data.at[index, column]
        if pd.notna(value):
            events.append(dict(ID=str(data.at[index, 'ID']), variavel=column,
                               valor_anterior=str(value), valor_final='', motivo=reason))
            data.at[index, column] = pd.NA

    for c, (low, high) in LIMITS.items():
        values = pd.to_numeric(data[c], errors='coerce')
        valid = values.ge(0) & values.lt(high) if c == 'IDADE' else values.gt(low) & values.le(high)
        for i in data.index[data[c].notna() & ~valid]:
            clear(i, c, 'valor não numérico, não finito ou fora dos limites técnicos')
        data[c] = pd.to_numeric(data[c], errors='coerce').astype(float)
    for c, domain in DOMAINS.items():
        for i in data.index[data[c].notna() & ~data[c].isin(domain)]:
            clear(i, c, 'categoria fora do domínio documentado')
    for i, row in data.iterrows():
        if pd.notna(row['PA SISTOLICA']) and pd.notna(row['PA DIASTOLICA']) and row['PA SISTOLICA'] <= row['PA DIASTOLICA']:
            for c in ['PA SISTOLICA', 'PA DIASTOLICA']:
                clear(i, c, 'PAS menor ou igual à PAD')
        if all(pd.notna(data.at[i, c]) for c in ['Peso', 'Altura', 'IMC']):
            expected = data.at[i, 'Peso']/(data.at[i, 'Altura']/100)**2
            if not 8 < expected <= 70 or abs(data.at[i, 'IMC']-round(expected, 2)) > 1:
                clear(i, 'IMC', 'incompatível com peso/altura; sem escolher qual medida corrigir')
                clear(i, 'CLASSIFICACAO IMC', 'IMC inconsistente')
        if pd.notna(row.HDA_UNIFICADA):
            tokens = {s.strip() for s in row.HDA_UNIFICADA.split('|') if s.strip()}
            if 'Assintomático' in tokens and len(tokens) > 1:
                clear(i, 'HDA_UNIFICADA', 'Assintomático combinado com sintomas: informação indisponível')
            else:
                data.at[i, 'HDA_UNIFICADA'] = ' | '.join(sorted(tokens, key=lambda x: (SYMPTOMS.index(x) if x in SYMPTOMS else len(SYMPTOMS), x))) or pd.NA
        if pd.isna(data.at[i, 'IDADE']):
            for c in ['FAIXA_ETARIA', 'CLASSIFICACAO IMC', 'PPA_CALCULADA']:
                clear(i, c, 'idade indisponível')
        if pd.isna(data.at[i, 'IMC']):
            clear(i, 'CLASSIFICACAO IMC', 'IMC indisponível')
        if any(pd.isna(data.at[i, c]) for c in ['PA SISTOLICA', 'PA DIASTOLICA']):
            clear(i, 'PPA_CALCULADA', 'pressão indisponível')
    return data, pd.DataFrame(events, columns=['ID', 'variavel', 'valor_anterior', 'valor_final', 'motivo'])


def prepare(frame):
    data, corrections = normalize(frame)
    labeled = data.loc[data[TARGET].notna()].copy()
    labeled['grupo'] = duplicate_groups(labeled[['ID']+FEATURE_COLUMNS+[TARGET]])
    cardinality = labeled.groupby('grupo')[TARGET].nunique()
    conflicts = labeled.loc[labeled.grupo.isin(cardinality.index[cardinality.gt(1)])].copy()
    candidates = labeled.loc[~labeled.grupo.isin(conflicts.grupo)].copy()
    # IDs inteiros, não ordenação lexicográfica; ordenação estável em empates.
    candidates['_id_order'] = candidates.ID.map(int)
    kept = candidates.sort_values('_id_order', kind='stable').drop_duplicates('grupo')
    representatives = kept.set_index('grupo').ID.to_dict()
    mapping = []
    lookup = labeled.set_index('ID')
    conflict_groups = set(conflicts.grupo)
    for identifier in data.ID:
        if identifier not in lookup.index:
            mapping.append(dict(ID=identifier, destino='sem_alvo', grupo='', ID_representante=''))
            continue
        group = lookup.at[identifier, 'grupo']
        status = ('conflito' if group in conflict_groups else
                  'mantido' if representatives[group] == identifier else 'duplicata')
        mapping.append(dict(ID=identifier, destino=status, grupo=group,
                            ID_representante=representatives.get(group, '')))
    mapping = pd.DataFrame(mapping)
    ids = set(kept.ID)
    selected = data.loc[data.ID.isin(ids)]
    if selected[FEATURE_COLUMNS].duplicated().any():
        raise AssertionError('Duplicatas remanescentes nos preditores')
    if set(selected[TARGET]) != {'Normal', 'Anormal'}:
        raise ValueError('Uma classe ficou ausente')
    supervised = selected[['ID']+FEATURE_COLUMNS+[TARGET]].copy()
    complementary = selected[['ID']+DERIVED_COLUMNS].copy()
    if supervised[FEATURE_COLUMNS].isna().all(axis=1).any():
        raise ValueError('Registro sem qualquer preditor; exige revisão explícita')
    return dict(data=data, supervised=supervised, complementary=complementary,
                corrections=corrections, mapping=mapping, conflicts=conflicts.drop(columns='grupo').assign(
                    grupo=conflicts.grupo), unlabeled=data.loc[data[TARGET].isna()].copy())


def validate_context(frame, folder):
    """Confere classificações contra as trilhas existentes, sem estimar medidas."""
    from classificacao_imc import classificar_imc_pediatrico
    from classificacao_pa import age_context, classify_pressure
    bmi = pd.read_csv(folder/'auditoria_imc_final.csv', dtype='string').set_index('ID')
    audit = pd.read_csv(folder/'auditoria_finalizacao.csv', dtype='string').set_index('ID')
    if set(frame.ID) != set(bmi.index) or set(frame.ID) != set(audit.index):
        raise ValueError('Auditorias não correspondem aos IDs de entrada')
    issues = []
    for _, row in frame.iterrows():
        ctx = audit.loc[row.ID]
        age = age_context({'Atendimento': ctx.Atendimento_original, 'DN': ctx.DN_original, 'IDADE': row.IDADE})
        checks = {'FAIXA_ETARIA': age['faixa_etaria']}
        pressure = classify_pressure(age['idade_anos_completos'], row.SEXO, row.Altura,
                                     row['PA SISTOLICA'], row['PA DIASTOLICA'])
        checks['PPA_CALCULADA'] = pressure['classificacao']
        days = pd.to_numeric(bmi.at[row.ID, 'idade_dias'], errors='coerce')
        value = pd.to_numeric(row.IMC, errors='coerce')
        checks['CLASSIFICACAO IMC'] = (classificar_imc_pediatrico(int(days), row.SEXO, value)['classificacao']
                                        if pd.notna(days) and pd.notna(value) else None)
        for column, expected in checks.items():
            actual = row[column]
            if ('' if pd.isna(actual) else str(actual)) != ('' if expected is None else str(expected)):
                issues.append(dict(ID=row.ID, variavel=column, valor_anterior=actual,
                                   valor_final='', motivo='diverge da referência e dos dados auditados'))
    return pd.DataFrame(issues, columns=['ID', 'variavel', 'valor_anterior', 'valor_final', 'motivo'])


def run(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output == source.parent or output == (ROOT/'resultado_modelagem').resolve():
        raise ValueError('Use diretório separado para preservar resultados anteriores')
    protected = [ROOT/'UCMF_raw.csv', source, ROOT/'resultado_analise/UCMF_limpo.csv']
    protected += [p for folder in [ROOT/'referencias', ROOT/'resultado_modelagem', source.parent]
                  for p in folder.iterdir() if p.is_file()]
    before = {str(p): digest(p) for p in protected}
    frame = pd.read_csv(source, dtype='string', encoding='utf-8-sig')
    # Corrigir apenas as categorias divergentes na cópia supervisionada.
    normalized, numeric_corrections = normalize(frame)
    consistency = validate_context(normalized, source.parent)
    for event in consistency.to_dict('records'):
        normalized.loc[normalized.ID.eq(event['ID']), event['variavel']] = pd.NA
    result = prepare(normalized)
    result['corrections'] = pd.concat([numeric_corrections, consistency, result['corrections']], ignore_index=True)
    output.mkdir(parents=True, exist_ok=True)
    files = {
        'UCMF_supervisionado.csv': result['supervised'],
        'atributos_complementares.csv': result['complementary'],
        'rastreabilidade.csv': result['mapping'],
        'duplicatas.csv': result['mapping'].loc[result['mapping'].destino.eq('duplicata')],
        'conflitos_alvo.csv': result['conflicts'], 'registros_sem_alvo.csv': result['unlabeled'],
        'correcoes.csv': result['corrections'],
    }
    quality = []
    for stage, data in [('entrada', frame), ('supervisionado', result['supervised'])]:
        for label, group in [('Todos', data)]+list(data.groupby(TARGET, dropna=False)):
            for c in FEATURE_COLUMNS:
                quality.append(dict(etapa=stage, classe='Sem alvo' if pd.isna(label) else label,
                                    variavel=c, n_total=len(group), n_ausentes=int(group[c].isna().sum()),
                                    percentual_ausente=100*group[c].isna().mean(), n_distintos=group[c].nunique()))
    files['faltantes_por_classe.csv'] = pd.DataFrame(quality)
    cats = []
    for c in FEATURE_COLUMNS:
        if c not in LIMITS:
            for value, count in result['supervised'][c].value_counts(dropna=False).items():
                cats.append(dict(variavel=c, categoria=value, quantidade=count))
    files['categorias.csv'] = pd.DataFrame(cats)
    for name, data in files.items():
        data.to_csv(output/name, index=False, encoding='utf-8-sig')
    build_preprocessor()  # Sem fit, serialização ajustada ou divisão.
    counts = result['mapping'].destino.value_counts().to_dict()
    report = f'''# Adequação da base supervisionada

Base apta ao preparo computacional; não constitui validação clínica ou desempenho de modelo.

| Destino | Registros |
| --- | ---: |
''' + '\n'.join(f'| {name} | {counts.get(name, 0)} |' for name in ['mantido', 'duplicata', 'conflito', 'sem_alvo']) + f'''

Total de entrada: {len(frame)}; soma dos destinos: {sum(counts.values())}.
Correções de campos auditadas: {len(result['corrections'])}. Grupos conflitantes: {result['conflicts'].grupo.nunique()}.
Os {len(result['supervised'])} perfis supervisionados são únicos nos 11 preditores selecionados.
Cada ID de entrada possui exatamente um destino em rastreabilidade.csv. O menor ID numérico representa duplicatas concordantes.

## Seleção e faltantes

ID é metadado. IMC, CLASSIFICACAO IMC, FAIXA_ETARIA e PPA_CALCULADA ficam na visão complementar alinhada por ID, por sua derivação parcial de outros campos. SOPRO, convênio e datas brutas não entram nos preditores. Sintomas contraditórios ficam indisponíveis na cópia supervisionada; originais e correções são preservados.

O CSV mantém faltantes. O transformador declara mediana do treino e indicadores para todos os campos numéricos. Se uma coluna for inteiramente ausente no treino, o imputador mantém sua dimensão com zero técnico e indicador; isso não é uma medição clínica. Escala, medianas e vocabulários serão ajustados exclusivamente dentro de cada treino da validação cruzada futura. Categorias ausentes usam __SEM_INFORMACAO__, diferente de Indeterminado e Outro. Categorias inéditas não alteram o vocabulário e geram zeros no bloco one-hot. Não se agrupam categorias clínicas raras automaticamente.

HDA usa menções de sintomas separadas, indicador de informação ausente e indicador de categoria inédita. Sintoma não mencionado não significa negação clínica confirmada. Não se recalculam diagnósticos ou categorias a partir de medidas imputadas.

## Limitações e próxima etapa do KDD

Perfil idêntico não comprova mesmo paciente: a deduplicação reduz multiplicidade e muda a distribuição empírica. multiplicidade e IDs continuam rastreáveis. Grupos com alvos conflitantes são separados integralmente, sem escolher por maioria. Não se excluem categorias raras ou extremos válidos por associação ao alvo. As ausências variam entre classes e podem refletir a rotina de registro.

B2, PULSOS, HDA, motivo de sopro e cardiopatia já conhecida permanecem para o exercício acadêmico; podem conter informação próxima à definição do alvo. Não se declara validade para triagem prospectiva. Há exploração anterior da base inteira; a avaliação futura será interna, com essa limitação documentada.

Nenhum classificador foi treinado, nenhuma divisão real nova foi feita e nenhum parâmetro foi aprendido da base inteira. As saídas em resultado_modelagem/ são legadas e não devem ser usadas como avaliação do esquema atual. A próxima etapa definirá a validação, comparação dos modelos e o compromisso entre sensibilidade de Anormal e especificidade. Colocar o pré-processamento e o classificador no mesmo Pipeline por partição. Fontes metodológicas: [scikit-learn: prevenção de vazamento](https://scikit-learn.org/stable/common_pitfalls.html), [imputação e colunas vazias](https://scikit-learn.org/stable/modules/impute.html).
'''
    report += '\n\n---\n\n'+(ROOT/'referencias/metodologia_preparo.md').read_text(encoding='utf-8')
    (output/'relatorio_adequacao.md').write_text(report, encoding='utf-8')
    manifest = dict(entradas_sha256=before, linhas_entrada=len(frame), destinos=counts,
                    preditores=FEATURE_COLUMNS, derivados=DERIVED_COLUMNS, alvo=TARGET,
                    esquema_supervisionado=list(result['supervised']),
                    regras=dict(duplicatas='menor ID; igualdade dos preditores', conflitos='quarentena integral',
                                faltantes='preservados; fit apenas no treino futuro'),
                    saidas_sha256={name: digest(output/name) for name in list(files)+['relatorio_adequacao.md']})
    if before != {str(p): digest(p) for p in protected}:
        raise AssertionError('Uma referência ou saída legada foi modificada')
    (output/'manifesto_adequacao.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(counts, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--entrada', type=Path, default=ROOT/'resultado_analise/UCMF_base_final.csv')
    parser.add_argument('--saida', type=Path, default=ROOT/'resultado_modelagem_preparo')
    args = parser.parse_args()
    run(args.entrada, args.saida)
