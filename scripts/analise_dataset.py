# -*- coding: utf-8 -*-
"""Auditoria e análise univariada do arquivo UCMF_raw.csv."""

from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from classificacao_imc import classificar_imc_pediatrico


NUMERIC_COLUMNS = [
    "Peso",
    "Altura",
    "IMC",
    "IDADE",
    "FC",
    "PA SISTOLICA",
    "PA DIASTOLICA",
]

CATEGORICAL_COLUMNS = [
    "Convenio",
    "PULSOS",
    "PPA",
    "NORMAL X ANORMAL",
    "B2",
    "SOPRO",
    "HDA 1",
    "HDA2",
    "SEXO",
    "MOTIVO1",
    "MOTIVO2",
    "CLASSIFICACAO IMC",
]

DATE_COLUMNS = ["Atendimento", "DN"]
REFERENCE_ID = "65"


def clean_column_name(name: object) -> str:
    """Remove espaços externos e normaliza espaços internos do cabeçalho."""
    return re.sub(r"\s+", " ", str(name).replace("\ufeff", "")).strip()


def read_dataset(path: Path) -> pd.DataFrame:
    """Lê o CSV preservando valores inválidos para que sejam contabilizados."""
    def repair_bad_line(fields: list[str]) -> list[str]:
        # Alguns motivos possuem virgula sem aspas; mantem esses textos nos dois ultimos campos.
        if len(fields) > 21:
            return fields[:19] + [", ".join(fields[19:-1]), fields[-1]]
        return fields + [""] * (21 - len(fields))

    last_error = None
    for encoding in ("utf-8-sig", "latin1"):
        try:
            frame = pd.read_csv(
                path,
                sep=",",
                encoding=encoding,
                dtype=str,
                keep_default_na=False,
                na_filter=False,
                engine="python",
                on_bad_lines=repair_bad_line,
            )
            break
        except UnicodeDecodeError as error:
            last_error = error
    else:
        raise last_error

    frame.columns = [clean_column_name(column) for column in frame.columns]
    frame = frame.rename(columns={"Peso (kg)": "Peso", "Altura (cm)": "Altura"})
    for column in frame.columns:
        frame[column] = frame[column].astype(str).str.strip()
        frame[column] = frame[column].replace({"": pd.NA, "#VALUE!": pd.NA})
    return frame


def replace_anthropometric_zeroes(frame: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Converte zeros de Peso e Altura em valores ausentes."""
    cleaned = frame.copy()
    changed = 0
    for column in ("Peso", "Altura"):
        numeric = pd.to_numeric(cleaned[column], errors="coerce")
        zero_mask = numeric.eq(0)
        changed += int(zero_mask.sum())
        cleaned.loc[zero_mask, column] = pd.NA
    return cleaned, changed


def remove_rows_matching_reference(
    frame: pd.DataFrame, reference_id: str = REFERENCE_ID
) -> tuple[pd.DataFrame, dict]:
    """Remove linhas com os mesmos valores do registro de referência, exceto o ID."""
    id_values = frame["ID"].astype("string").str.strip()
    reference_rows = frame.loc[id_values == reference_id]
    if reference_rows.empty:
        raise ValueError(f"ID de referencia {reference_id} nao foi encontrado")

    reference = reference_rows.iloc[0]
    comparison_columns = [column for column in frame.columns if column != "ID"]
    matches = pd.Series(True, index=frame.index)
    for column in comparison_columns:
        reference_value = reference[column]
        if pd.isna(reference_value):
            matches &= frame[column].isna()
        else:
            matches &= frame[column].eq(reference_value)

    # O ID de referência sempre é removido, mesmo se houver alguma diferença de formatação.
    matches |= id_values.eq(reference_id)
    matched_ids = frame.loc[matches, "ID"].astype("string").fillna("<ausente>").tolist()
    matched_positions = (frame.index[matches] + 2).tolist()
    cleaned = frame.loc[~matches].reset_index(drop=True)
    details = {
        "reference_id": reference_id,
        "comparison_columns": comparison_columns,
        "removed_count": int(matches.sum()),
        "removed_ids": matched_ids,
        "original_csv_lines": matched_positions,
    }
    return cleaned, details


def move_sexo_after_id(frame: pd.DataFrame) -> pd.DataFrame:
    """Coloca a coluna SEXO imediatamente depois de ID."""
    columns = [column for column in frame.columns if column not in {"ID", "SEXO"}]
    return frame[["ID", "SEXO", *columns]]


def write_cleaning_log(log_path: Path, details: dict, input_path: Path, output_path: Path) -> None:
    """Registra no docs.md o critério e o resultado da limpeza."""
    removed_ids = ", ".join(details["removed_ids"]) or "nenhum"
    section = "\n".join([
        "## Limpeza de linhas do ID 65",
        f"- Arquivo de entrada: `{input_path.name}`",
        f"- Arquivo limpo gerado: `{output_path.name}`",
        f"- Critério: mesmos valores em todas as colunas, exceto `ID`, comparados com o primeiro registro cujo `ID` e `{details['reference_id']}`.",
        f"- Linhas removidas: **{details['removed_count']}** (o próprio ID 65 está incluído).",
        f"- IDs removidos: `{removed_ids}`",
        f"- Linhas originais do CSV removidas: `{details['original_csv_lines']}`",
        "",
    ])
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    marker = "## Limpeza de linhas do ID 65"
    prefix = existing.split(marker, 1)[0].rstrip() if marker in existing else existing.rstrip()
    content = f"{prefix}\n\n{section}" if prefix else section
    log_path.write_text(content, encoding="utf-8")


def to_number(series: pd.Series) -> pd.Series:
    values = series.astype("string").str.replace(",", ".", regex=False)
    return pd.to_numeric(values, errors="coerce")


def parse_mixed_date(series: pd.Series) -> pd.Series:
    """Converte datas textuais e números seriais do Excel."""
    result = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    text_values = series.astype("string").str.strip()
    numeric_values = pd.to_numeric(text_values, errors="coerce")
    serial_mask = numeric_values.between(1, 60000)
    result.loc[serial_mask] = pd.to_datetime(
        numeric_values.loc[serial_mask], unit="D", origin="1899-12-30", errors="coerce"
    )
    text_mask = ~serial_mask & text_values.notna()
    result.loc[text_mask] = pd.to_datetime(
        text_values.loc[text_mask], dayfirst=True, errors="coerce"
    )
    return result


def normalized_text(value: object) -> str:
    text = "" if pd.isna(value) else str(value).strip().lower()
    return "".join(
        char for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )


EXPLICIT_CATEGORY_MAPS = {
    "SEXO": {
        "m": "Masculino",
        "masculino": "Masculino",
        "f": "Feminino",
        "feminino": "Feminino",
        "indeterminado": "Indeterminado",
    },
    "NORMAL X ANORMAL": {
        "normal": "Normal",
        "normais": "Normal",
        "anormal": "Anormal",
    },
    "PULSOS": {
        "normais": "Normais",
        "amplos": "Amplos",
        "femorais diminuidos": "Femorais diminuídos",
        "diminuídos": "Diminuídos",
    },
    "SOPRO": {
        "ausente": "Ausente",
        "sistolico": "Sistólico",
        "continuo": "Contínuo",
        "diastolico": "Diastólico",
        "sistolico e diastolico": "Sistólico e diastólico",
        "normal": "Normal",
    },
    "B2": {
        "normal": "Normal",
        "hiperfonetica": "Hiperfonética",
        "desdob fixo": "Desdob fixo",
        "unica": "Única",
        "outro": "Outro",
        "anormal": "Anormal",
    },
}


def normalize_categorical_columns(frame: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Consolida grafias equivalentes sem alterar valores ausentes."""
    normalized = frame.copy()
    changed = 0
    for column in CATEGORICAL_COLUMNS:
        if column not in normalized:
            continue
        values = normalized[column]
        present = values.notna()
        generic = {}
        counts = values[present].map(normalized_text).value_counts()
        for key in counts.index:
            variants = values[present & values.map(normalized_text).eq(key)]
            generic[key] = variants.value_counts().index[0]
        explicit = EXPLICIT_CATEGORY_MAPS.get(column, {})
        for index in values.index[present]:
            key = normalized_text(values.at[index])
            replacement = explicit.get(key, generic.get(key, values.at[index]))
            if values.at[index] != replacement:
                normalized.at[index, column] = replacement
                changed += 1
    return normalized, changed


def write_normalization_log(log_path: Path, changed: int) -> None:
    section = "\n".join([
        "## Normalização das categorias",
        "As colunas categóricas foram normalizadas antes da análise.",
        "Foram consolidadas diferenças de maiúsculas/minúsculas, acentos, espaços e grafias equivalentes conhecidas.",
        f"Total de células alteradas: **{changed}**.",
        "",
    ])
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    marker = "## Normalização das categorias"
    prefix = existing.split(marker, 1)[0].rstrip() if marker in existing else existing.rstrip()
    log_path.write_text(f"{prefix}\n\n{section}" if prefix else section, encoding="utf-8")


def write_zero_replacement_log(log_path: Path, changed: int) -> None:
    section = "\n".join([
        "## Conversão de zeros antropométricos",
        "Os valores zero das colunas `Peso` e `Altura` foram substituídos por valores nulos antes da análise.",
        f"- Células alteradas: **{changed}**.",
        "",
    ])
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    marker = "## Conversão de zeros antropométricos"
    prefix = existing.split(marker, 1)[0].rstrip() if marker in existing else existing.rstrip()
    log_path.write_text(f"{prefix}\n\n{section}" if prefix else section, encoding="utf-8")


def calculate_missing_anthropometrics(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calcula Peso, Altura ou IMC quando os outros dois valores estão disponíveis."""
    calculated = frame.copy()
    weight = to_number(calculated["Peso"]).where(lambda values: values > 0)
    height = to_number(calculated["Altura"]).where(lambda values: values > 0)
    bmi = to_number(calculated["IMC"]).where(lambda values: values > 0)
    records = []

    def record(index: object, field: str, value: float, formula: str) -> None:
        calculated.at[index, field] = round(value, 2)
        records.append({
            "ID": calculated.at[index, "ID"],
            "campo_calculado": field,
            "valor_calculado": round(value, 2),
            "formula": formula,
        })

    for index in calculated.index:
        if pd.isna(bmi.at[index]) and pd.notna(weight.at[index]) and pd.notna(height.at[index]):
            record(index, "IMC", weight.at[index] / (height.at[index] / 100) ** 2, "Peso / (Altura / 100)^2")
        elif pd.isna(height.at[index]) and pd.notna(weight.at[index]) and pd.notna(bmi.at[index]):
            record(index, "Altura", (weight.at[index] / bmi.at[index]) ** 0.5 * 100, "sqrt(Peso / IMC) * 100")
        elif pd.isna(weight.at[index]) and pd.notna(height.at[index]) and pd.notna(bmi.at[index]):
            record(index, "Peso", bmi.at[index] * (height.at[index] / 100) ** 2, "IMC * (Altura / 100)^2")

    return calculated, pd.DataFrame(records, columns=["ID", "campo_calculado", "valor_calculado", "formula"])


def write_anthropometric_log(log_path: Path, calculations: pd.DataFrame, frame: pd.DataFrame) -> None:
    numeric = {column: to_number(frame[column]).where(lambda values: values > 0) for column in ("Peso", "Altura", "IMC")}
    complete = sum(values.notna() for values in numeric.values())
    complete_count = int((complete == 3).sum())
    exactly_one_missing = int((complete == 2).sum())
    one_valid_count = int((complete == 1).sum())
    none_valid_count = int((complete == 0).sum())
    section = "\n".join([
        "## Cálculo de Peso, Altura e IMC",
        "Foi aplicado cálculo determinístico somente quando exatamente um dos três campos estava ausente ou zero e os outros dois eram válidos.",
        f"- Células preenchidas: **{len(calculations)}**.",
        f"- Registros com os três valores válidos: **{complete_count}**.",
        f"- Registros com exatamente dois valores válidos, que permitiriam cálculo: **{exactly_one_missing}**.",
        f"- Registros com apenas um valor válido: **{one_valid_count}**.",
        f"- Registros sem valores válidos: **{none_valid_count}**.",
        "- Os detalhes estão em `resultado_analise/calculos_peso_altura_imc.csv`.",
        "",
    ])
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    marker = "## Cálculo de Peso, Altura e IMC"
    prefix = existing.split(marker, 1)[0].rstrip() if marker in existing else existing.rstrip()
    log_path.write_text(f"{prefix}\n\n{section}" if prefix else section, encoding="utf-8")


def calculate_missing_age(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Recalcula idades negativas ou ausentes quando as datas permitem."""
    calculated = frame.copy()
    attendance = parse_mixed_date(calculated["Atendimento"])
    birth = parse_mixed_date(calculated["DN"])
    age = to_number(calculated["IDADE"])
    both_dates = attendance.notna() & birth.notna()
    valid_dates = both_dates & (attendance >= birth)
    expected_age = (attendance - birth).dt.days / 365.25
    records = []

    for index in calculated.index:
        current = age.at[index]
        if pd.notna(current) and current >= 0:
            if valid_dates.at[index] and abs(current - round(expected_age.at[index], 2)) > 0.10:
                records.append({
                    "ID": calculated.at[index, "ID"],
                    "tipo": "inconsistencia",
                    "idade_original": current,
                    "idade_calculada": round(expected_age.at[index], 2),
                    "diferença": round(current - expected_age.at[index], 2),
                    "motivo": "idade preenchida diverge das datas",
                })
            continue

        if valid_dates.at[index]:
            expected = round(expected_age.at[index], 2)
            calculated.at[index, "IDADE"] = expected
            records.append({
                "ID": calculated.at[index, "ID"],
                "tipo": "idade negativa/ausente corrigida",
                "idade_original": current,
                "idade_calculada": expected,
                "diferença": pd.NA,
                "motivo": "Atendimento - DN",
            })
        elif pd.notna(current) and current < 0:
            calculated.at[index, "IDADE"] = pd.NA
            records.append({
                "ID": calculated.at[index, "ID"],
                "tipo": "idade negativa removida",
                "idade_original": current,
                "idade_calculada": pd.NA,
                "diferença": pd.NA,
                "motivo": "datas ausentes ou DN posterior ao Atendimento",
            })

    return calculated, pd.DataFrame(
        records,
        columns=["ID", "tipo", "idade_original", "idade_calculada", "diferença", "motivo"],
    )


def write_age_log(log_path: Path, report: pd.DataFrame, frame: pd.DataFrame) -> None:
    attendance = parse_mixed_date(frame["Atendimento"])
    birth = parse_mixed_date(frame["DN"])
    valid_dates = attendance.notna() & birth.notna() & (attendance >= birth)
    corrected = int((report["tipo"] == "idade negativa/ausente corrigida").sum()) if not report.empty else 0
    removed = int((report["tipo"] == "idade negativa removida").sum()) if not report.empty else 0
    inconsistencies = int((report["tipo"] == "inconsistencia").sum()) if not report.empty else 0
    section = "\n".join([
        "## Cálculo de Atendimento menos DN igual a Idade",
        "A idade foi calculada em anos como a diferença entre `Atendimento` e `DN`, dividida por 365,25.",
        f"- Registros com datas válidas e coerentes: **{int(valid_dates.sum())}**.",
        f"- Idades negativas/ausentes corrigidas pelas datas: **{corrected}**.",
        f"- Idades negativas sem datas confiáveis, convertidas em ausentes: **{removed}**.",
        f"- Idades existentes inconsistentes por mais de 0,10 ano: **{inconsistencies}**.",
        "- Os detalhes estão em `resultado_analise/calculos_atendimento_dn_idade.csv`.",
        "",
    ])
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    marker = "## Cálculo de Atendimento menos DN igual a Idade"
    prefix = existing.split(marker, 1)[0].rstrip() if marker in existing else existing.rstrip()
    log_path.write_text(f"{prefix}\n\n{section}" if prefix else section, encoding="utf-8")


def classify_bmi(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Classifica o IMC pediátrico usando idade e sexo, sem forçar dados inválidos."""
    classified = frame.copy()
    results = []
    age_values = to_number(classified["IDADE"])
    bmi_values = to_number(classified["IMC"])
    sex_values = classified["SEXO"].map({"Masculino": "M", "Feminino": "F"})

    for index in classified.index:
        age = age_values.at[index]
        bmi = bmi_values.at[index]
        sex = sex_values.at[index]
        classification = "Não classificável"
        reason = "idade, sexo ou IMC ausente/inválido"
        if pd.notna(age) and pd.notna(bmi) and pd.notna(sex) and 0 <= age <= 19 and bmi > 0:
            total_months = int(round(age * 12))
            years, months = divmod(total_months, 12)
            try:
                classification = classificar_imc_pediatrico(years, months, sex, float(bmi))["classificacao"]
                reason = "classificação aplicada"
            except ValueError:
                reason = "idade fora do intervalo de 0 a 19 anos"
        classified.at[index, "CLASSIFICACAO IMC"] = classification
        results.append({
            "ID": classified.at[index, "ID"],
            "classificacao": classification,
            "motivo": reason,
        })

    return classified, pd.DataFrame(results, columns=["ID", "classificacao", "motivo"])


def move_bmi_classification_to_sixth_column(frame: pd.DataFrame) -> pd.DataFrame:
    """Coloca CLASSIFICACAO IMC na sexta posição do arquivo final."""
    columns = [column for column in frame.columns if column != "CLASSIFICACAO IMC"]
    return frame[columns[:5] + ["CLASSIFICACAO IMC"] + columns[5:]]


def write_bmi_log(log_path: Path, report: pd.DataFrame) -> None:
    valid = int((report["motivo"] == "classificação aplicada").sum())
    unavailable = int((report["motivo"] != "classificação aplicada").sum())
    section = "\n".join([
        "## Classificação pediátrica do IMC",
        "A coluna `CLASSIFICACAO IMC` foi criada usando `SEXO`, `IDADE` e `IMC`, conforme `classificacao_imc.py`.",
        f"- Registros classificados: **{valid}**.",
        f"- Registros não classificáveis: **{unavailable}**.",
        "- O detalhamento está em `resultado_analise/classificacoes_imc.csv`.",
        "",
    ])
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    marker = "## Classificação pediátrica do IMC"
    prefix = existing.split(marker, 1)[0].rstrip() if marker in existing else existing.rstrip()
    log_path.write_text(f"{prefix}\n\n{section}" if prefix else section, encoding="utf-8")


def add_issue(issues: list[dict], check: str, count: int, examples: object = "") -> None:
    if count:
        issues.append({"verificacao": check, "quantidade": int(count), "exemplos": examples})


def quality_checks(frame: pd.DataFrame) -> pd.DataFrame:
    issues: list[dict] = []
    add_issue(issues, "IDs ausentes", frame["ID"].isna().sum())
    duplicate_ids = frame.loc[frame["ID"].duplicated(keep=False), "ID"].dropna().unique()
    add_issue(issues, "IDs duplicados", len(duplicate_ids), ", ".join(map(str, duplicate_ids[:10])))

    numeric = {column: to_number(frame[column]) for column in NUMERIC_COLUMNS}
    for column, values in numeric.items():
        add_issue(issues, f"{column}: valores ausentes ou nao numericos", values.isna().sum())

    for column in ("Peso", "Altura", "IMC"):
        values = numeric[column]
        add_issue(issues, f"{column}: valores zero", (values == 0).sum())
    add_issue(issues, "IDADE: valores negativos", (numeric["IDADE"] < 0).sum())
    add_issue(issues, "FC: fora do intervalo plausivel (30-250)", ((numeric["FC"] < 30) | (numeric["FC"] > 250)).sum())
    add_issue(issues, "PA SISTOLICA: fora do intervalo plausivel (40-250)", ((numeric["PA SISTOLICA"] < 40) | (numeric["PA SISTOLICA"] > 250)).sum())
    add_issue(issues, "PA DIASTOLICA: fora do intervalo plausivel (20-150)", ((numeric["PA DIASTOLICA"] < 20) | (numeric["PA DIASTOLICA"] > 150)).sum())

    expected_bmi = numeric["Peso"] / (numeric["Altura"] / 100) ** 2
    bmi_mismatch = expected_bmi.notna() & numeric["IMC"].notna() & ((expected_bmi - numeric["IMC"]).abs() > 1)
    add_issue(issues, "IMC inconsistente com Peso e Altura", bmi_mismatch.sum())

    dates = {column: parse_mixed_date(frame[column]) for column in DATE_COLUMNS}
    for column in DATE_COLUMNS:
        raw_present = frame[column].notna()
        add_issue(issues, f"{column}: data invalida", (raw_present & dates[column].isna()).sum())
        add_issue(issues, f"{column}: data ausente", frame[column].isna().sum())
    both_dates = dates["DN"].notna() & dates["Atendimento"].notna()
    add_issue(issues, "DN posterior ao Atendimento", (both_dates & (dates["DN"] > dates["Atendimento"])).sum())

    pas = numeric["PA SISTOLICA"].notna()
    pad = numeric["PA DIASTOLICA"].notna()
    ppa_present = frame["PPA"].notna()
    add_issue(issues, "PPA ausente com PAS e PAD preenchidas", (pas & pad & ~ppa_present).sum())
    add_issue(issues, "PPA preenchida sem PAS ou PAD", (ppa_present & ~(pas & pad)).sum())

    expected_categories = {
        "NORMAL X ANORMAL": {"normal", "anormal"},
        "SEXO": {"m", "f", "indeterminado"},
    }
    for column, allowed in expected_categories.items():
        invalid = frame[column].notna() & ~frame[column].map(normalized_text).isin(allowed)
        add_issue(issues, f"{column}: categorias invalidas", invalid.sum())

    for column in CATEGORICAL_COLUMNS:
        missing = frame[column].isna().sum()
        add_issue(issues, f"{column}: valores ausentes", missing)
        normalized_counts = frame.loc[frame[column].notna(), column].map(normalized_text).value_counts()
        variants = normalized_counts[normalized_counts > 1]
        if len(variants):
            add_issue(issues, f"{column}: possiveis variacoes de grafia", len(variants), "; ".join(variants.index[:10]))

    return pd.DataFrame(issues, columns=["verificacao", "quantidade", "exemplos"])


def numeric_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in NUMERIC_COLUMNS:
        values = to_number(frame[column])
        valid = values.dropna()
        rows.append({
            "variavel": column,
            "validos": valid.size,
            "ausentes": values.isna().sum(),
            "media": valid.mean(),
            "mediana": valid.median(),
            "desvio_padrao": valid.std(),
            "minimo": valid.min(),
            "Q1": valid.quantile(0.25),
            "Q3": valid.quantile(0.75),
            "maximo": valid.max(),
        })
    return pd.DataFrame(rows)


def categorical_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    total = len(frame)
    for column in CATEGORICAL_COLUMNS:
        values = frame[column].dropna()
        counts = values.value_counts(dropna=False)
        for category, count in counts.items():
            rows.append({
                "variavel": column,
                "categoria": category,
                "frequencia": count,
                "porcentagem_total": 100 * count / total if total else 0,
                "ausentes": frame[column].isna().sum(),
                "numero_categorias": values.nunique(),
            })
    return pd.DataFrame(rows)


def save_plots(frame: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for column in NUMERIC_COLUMNS:
        values = to_number(frame[column]).dropna()
        if values.empty:
            continue
        figure, axes = plt.subplots(1, 2, figsize=(12, 4))
        axes[0].hist(values, bins="auto", color="#1976a3", edgecolor="white")
        axes[0].set_title(f"Histograma - {column}")
        axes[0].set_xlabel(column)
        axes[0].set_ylabel("Frequencia")
        axes[1].boxplot(values, orientation="horizontal", patch_artist=True, boxprops={"facecolor": "#f28e2b"})
        axes[1].set_title(f"Boxplot - {column}")
        axes[1].set_xlabel(column)
        figure.tight_layout()
        figure.savefig(output_dir / f"numerica_{normalized_text(column).replace(' ', '_')}.png", dpi=150)
        plt.close(figure)

    for column in CATEGORICAL_COLUMNS:
        counts = frame[column].value_counts(dropna=False).head(20).rename(index={pd.NA: "Ausente"})
        if counts.empty:
            continue
        figure, axis = plt.subplots(figsize=(10, 5))
        counts.sort_values().plot.barh(ax=axis, color="#59a14f")
        axis.set_title(f"Categorias - {column} (top 20)")
        axis.set_xlabel("Frequencia")
        figure.tight_layout()
        figure.savefig(output_dir / f"categorica_{normalized_text(column).replace(' ', '_')}.png", dpi=150)
        plt.close(figure)


def bivariate_numeric_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    target = frame["NORMAL X ANORMAL"].fillna("Ausente")
    for column in NUMERIC_COLUMNS:
        values = to_number(frame[column])
        for target_value in target.unique():
            group = values[target == target_value]
            valid = group.dropna()
            rows.append({
                "variavel": column,
                "classe_alvo": target_value,
                "n_grupo": len(group),
                "validos": len(valid),
                "ausentes": int(group.isna().sum()),
                "media": valid.mean(),
                "mediana": valid.median(),
                "desvio_padrao": valid.std(),
                "minimo": valid.min(),
                "Q1": valid.quantile(0.25),
                "Q3": valid.quantile(0.75),
                "maximo": valid.max(),
            })
    return pd.DataFrame(rows)


def bivariate_categorical_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    target = frame["NORMAL X ANORMAL"].fillna("Ausente")
    columns = [column for column in CATEGORICAL_COLUMNS if column != "NORMAL X ANORMAL"]
    for column in columns:
        values = frame[column].fillna("Ausente")
        cross = pd.crosstab(values, target)
        for category, counts in cross.iterrows():
            for target_value, count in counts.items():
                target_total = int((target == target_value).sum())
                rows.append({
                    "variavel": column,
                    "categoria": category,
                    "classe_alvo": target_value,
                    "frequencia": int(count),
                    "porcentagem_na_classe": 100 * count / target_total if target_total else 0,
                    "porcentagem_na_categoria": 100 * count / counts.sum() if counts.sum() else 0,
                })
    return pd.DataFrame(rows)


def save_bivariate_plots(frame: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = frame["NORMAL X ANORMAL"].fillna("Ausente")
    for column in NUMERIC_COLUMNS:
        values = to_number(frame[column])
        figure, axis = plt.subplots(figsize=(8, 5))
        plotted = False
        for target_value, color in (("Normal", "#59a14f"), ("Anormal", "#e15759")):
            group = values[target == target_value].dropna()
            if not group.empty:
                axis.boxplot(group, positions=[1 if target_value == "Normal" else 2], tick_labels=[target_value], patch_artist=True, boxprops={"facecolor": color})
                plotted = True
        if plotted:
            axis.set_title(f"{column} por NORMAL X ANORMAL")
            axis.set_ylabel(column)
            figure.tight_layout()
            figure.savefig(output_dir / f"bivariada_numerica_{normalized_text(column).replace(' ', '_')}.png", dpi=150)
        plt.close(figure)

    for column in [column for column in CATEGORICAL_COLUMNS if column != "NORMAL X ANORMAL"]:
        cross = pd.crosstab(frame[column].fillna("Ausente"), target)
        if cross.empty:
            continue
        cross = cross.loc[cross.sum(axis=1).sort_values(ascending=False).head(15).index]
        axis = cross.plot.bar(figsize=(12, 5), color=["#59a14f", "#e15759", "#9c9c9c"])
        axis.set_title(f"{column} por NORMAL X ANORMAL (top 15)")
        axis.set_ylabel("Frequencia")
        axis.tick_params(axis="x", rotation=45)
        axis.figure.tight_layout()
        axis.figure.savefig(output_dir / f"bivariada_categorica_{normalized_text(column).replace(' ', '_')}.png", dpi=150)
        plt.close(axis.figure)


def write_bivariate_log(log_path: Path, numeric: pd.DataFrame, categorical: pd.DataFrame) -> None:
    section = "\n".join([
        "## Análise bivariada com NORMAL X ANORMAL",
        "Foram comparadas todas as variáveis numéricas e categóricas com a variável-alvo `NORMAL X ANORMAL`. O identificador `ID` não foi usado como variável explicativa.",
        f"- Linhas numéricas no relatório: **{len(numeric)}**.",
        f"- Linhas categóricas no relatório: **{len(categorical)}**.",
        "- Relatórios: `resultado_analise/bivariada_numericas.csv` e `resultado_analise/bivariada_categoricas.csv`.",
        "- Gráficos: `resultado_analise/graficos_bivariada/`.",
        "",
    ])
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    marker = "## Análise bivariada com NORMAL X ANORMAL"
    prefix = existing.split(marker, 1)[0].rstrip() if marker in existing else existing.rstrip()
    log_path.write_text(f"{prefix}\n\n{section}" if prefix else section, encoding="utf-8")

def main() -> None:
    parser = argparse.ArgumentParser(description="Analisa e audita UCMF_raw.csv")
    parser.add_argument("csv", nargs="?", type=Path, default=Path("UCMF_raw.csv"))
    parser.add_argument("--saida", type=Path, default=Path("resultado_analise"))
    args = parser.parse_args()

    frame = read_dataset(args.csv)
    frame, zero_replacements = replace_anthropometric_zeroes(frame)
    frame, normalization_changes = normalize_categorical_columns(frame)
    args.saida.mkdir(parents=True, exist_ok=True)
    cleaned_frame, cleaning_details = remove_rows_matching_reference(frame)
    cleaned_frame = move_sexo_after_id(cleaned_frame)
    cleaned_frame, anthropometric_calculations = calculate_missing_anthropometrics(cleaned_frame)
    cleaned_frame, age_calculations = calculate_missing_age(cleaned_frame)
    cleaned_frame, bmi_classifications = classify_bmi(cleaned_frame)
    cleaned_frame = move_bmi_classification_to_sixth_column(cleaned_frame)
    cleaned_path = args.saida / "UCMF_limpo.csv"
    cleaned_frame.to_csv(cleaned_path, index=False, encoding="utf-8-sig")
    write_cleaning_log(Path("docs.md"), cleaning_details, args.csv, cleaned_path)
    write_normalization_log(Path("docs.md"), normalization_changes)
    write_zero_replacement_log(Path("docs.md"), zero_replacements)
    anthropometric_calculations.to_csv(args.saida / "calculos_peso_altura_imc.csv", index=False, encoding="utf-8-sig")
    write_anthropometric_log(Path("docs.md"), anthropometric_calculations, cleaned_frame)
    age_calculations.to_csv(args.saida / "calculos_atendimento_dn_idade.csv", index=False, encoding="utf-8-sig")
    write_age_log(Path("docs.md"), age_calculations, cleaned_frame)
    bmi_classifications.to_csv(args.saida / "classificacoes_imc.csv", index=False, encoding="utf-8-sig")
    write_bmi_log(Path("docs.md"), bmi_classifications)

    quality_checks(cleaned_frame).to_csv(args.saida / "qualidade_dados.csv", index=False, encoding="utf-8-sig")
    numeric_summary(cleaned_frame).to_csv(args.saida / "resumo_numericas.csv", index=False, encoding="utf-8-sig", float_format="%.4f")
    categorical_summary(cleaned_frame).to_csv(args.saida / "resumo_categoricas.csv", index=False, encoding="utf-8-sig")
    save_plots(cleaned_frame, args.saida / "graficos")
    bivariate_numeric = bivariate_numeric_summary(cleaned_frame)
    bivariate_categorical = bivariate_categorical_summary(cleaned_frame)
    bivariate_numeric.to_csv(args.saida / "bivariada_numericas.csv", index=False, encoding="utf-8-sig", float_format="%.4f")
    bivariate_categorical.to_csv(args.saida / "bivariada_categoricas.csv", index=False, encoding="utf-8-sig")
    save_bivariate_plots(cleaned_frame, args.saida / "graficos_bivariada")
    write_bivariate_log(Path("docs.md"), bivariate_numeric, bivariate_categorical)

    print(f"Linhas originais: {len(frame)}")
    print(f"Linhas removidas: {cleaning_details['removed_count']}")
    print(f"Linhas analisadas apos limpeza: {len(cleaned_frame)}")
    print(f"Resultados salvos em: {args.saida.resolve()}")
    print(f"Problemas encontrados: {len(quality_checks(cleaned_frame))}")


if __name__ == "__main__":
    main()