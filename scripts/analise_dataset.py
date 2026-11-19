"""Limpeza auditável e exploração do conjunto UCMF."""

from __future__ import annotations

import argparse
import io
import math
import re
import time
import unicodedata
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from classificacao_imc import classificar_imc_pediatrico

ROOT = Path(__file__).resolve().parents[1]
NUMERIC_COLUMNS = ["Peso", "Altura", "IMC", "IDADE", "FC", "PA SISTOLICA", "PA DIASTOLICA"]
DATE_COLUMNS = ["Atendimento", "DN"]
CATEGORICAL_COLUMNS = [
    "Convenio", "PULSOS", "PPA", "NORMAL X ANORMAL", "B2", "SOPRO",
    "HDA 1", "HDA2", "SEXO", "MOTIVO1", "MOTIVO2", "CLASSIFICACAO IMC",
]
TARGET = "NORMAL X ANORMAL"
TARGET_CLASSES = ["Normal", "Anormal"]
COLORS = {"Normal": "#59a14f", "Anormal": "#e15759"}
EXPECTED_COLUMNS = [
    "ID", "Peso", "Altura", "IMC", "Atendimento", "DN", "IDADE",
    "Convenio", "PULSOS", "PA SISTOLICA", "PA DIASTOLICA", "PPA",
    "NORMAL X ANORMAL", "B2", "SOPRO", "FC", "HDA 1", "HDA2",
    "SEXO", "MOTIVO1", "MOTIVO2",
]
# Limites técnicos amplos para detectar erros de registro, não cortes diagnósticos.
LIMITS = {
    "Peso": (0, 200), "Altura": (30, 220), "IMC": (8, 70),
    "IDADE": (0, 20), "FC": (30, 250),
    "PA SISTOLICA": (40, 250), "PA DIASTOLICA": (20, 150),
}
EXPLICIT = {
    "SEXO": {"m": "Masculino", "masculino": "Masculino",
             "f": "Feminino", "feminino": "Feminino",
             "indeterminado": "Indeterminado"},
    TARGET: {"normal": "Normal", "normais": "Normal", "anormal": "Anormal"},
    "PULSOS": {"normais": "Normais", "amplos": "Amplos",
               "femorais diminuidos": "Femorais diminuídos",
               "diminuidos": "Diminuídos"},
    "SOPRO": {"ausente": "Ausente", "sistolico": "Sistólico",
              "continuo": "Contínuo", "diastolico": "Diastólico",
              "sistolico e diastolico": "Sistólico e diastólico",
              "normal": "Normal"},
    "B2": {"normal": "Normal", "hiperfonetica": "Hiperfonética",
           "desdob fixo": "Desdob fixo", "unica": "Única",
           "outro": "Outro", "anormal": "Anormal"},
}
PPA_CATEGORIES = {
    "Normal", "Pre-Hipertensão PAS", "Pre-Hipertensão PAD",
    "HAS-1 PAS", "HAS-1 PAD", "HAS-2 PAS", "HAS-2 PAD",
}


def missing(value: object) -> bool:
    return bool(pd.isna(value))


def shown(value: object) -> str:
    return "" if missing(value) else str(value)


def key(value: object) -> str:
    value = re.sub(r"\s+", " ", shown(value).strip().lower())
    return "".join(c for c in unicodedata.normalize("NFKD", value)
                   if not unicodedata.combining(c))


def filename(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", key(value)).strip("_")


def change(events: list[dict], row: pd.Series, field: str,
           before: object, after: object, rule: str) -> None:
    if shown(before) == shown(after):
        return
    events.append({
        "ID": shown(row["ID"]), "linha_origem": int(row["_LINHA_ORIGEM"]),
        "variavel": field, "valor_original": shown(before),
        "valor_final": shown(after), "regra": rule,
    })


def pending(rows: list[dict], row: pd.Series, field: str, reason: str) -> None:
    rows.append({
        "ID": shown(row["ID"]), "linha_origem": int(row["_LINHA_ORIGEM"]),
        "variavel": field, "motivo": reason,
    })


def read_dataset(path: Path) -> pd.DataFrame:
    """Lê aspas após espaços; falha se alguma linha tiver campos deslocados."""
    last_error = None
    for encoding in ("utf-8-sig", "latin1"):
        try:
            frame = pd.read_csv(
                path, sep=",", encoding=encoding, dtype="string",
                keep_default_na=False, na_filter=False, skipinitialspace=True,
                engine="c",
            )
            break
        except UnicodeDecodeError as error:
            last_error = error
    else:
        raise last_error
    frame.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in frame.columns]
    frame = frame.rename(columns={"Peso (kg)": "Peso", "Altura (cm)": "Altura"})
    if list(frame.columns) != EXPECTED_COLUMNS:
        raise ValueError(f"Esquema inesperado: {list(frame.columns)}")
    for column in frame:
        frame[column] = frame[column].str.strip().replace({"": pd.NA, "#VALUE!": pd.NA})
    frame["_LINHA_ORIGEM"] = range(2, len(frame) + 2)
    frame = frame.astype(object)
    if frame["ID"].isna().any() or frame["ID"].duplicated().any():
        raise ValueError("IDs ausentes ou repetidos no arquivo bruto")
    return frame


def canonical_category(column: str, value: object) -> object:
    """Padroniza uma célula por regras fixas, sem aprender com outras linhas."""
    if missing(value):
        return pd.NA
    old = str(value)
    normalized = key(old)
    if column == "Convenio":
        return normalized.upper()
    if column == "PPA" and normalized == "nao calculado":
        return pd.NA
    new = EXPLICIT.get(column, {}).get(normalized, old)
    if column == "PPA" and new not in PPA_CATEGORIES:
        return pd.NA
    if column == TARGET and new not in TARGET_CLASSES:
        return pd.NA
    if column == "SEXO" and new not in {"Masculino", "Feminino", "Indeterminado"}:
        return pd.NA
    return new


def normalize_categories(frame: pd.DataFrame, events: list[dict]) -> None:
    for column in [c for c in CATEGORICAL_COLUMNS if c in frame]:
        for index in frame.index[frame[column].notna()]:
            old = frame.at[index, column]
            new = canonical_category(column, old)
            if shown(old) != shown(new):
                change(events, frame.loc[index], column, old, new, "padronização categórica")
                frame.at[index, column] = new


def remove_placeholders(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Remove registros sem dados clínicos, equivalentes ao padrão do ID 65."""
    other = [c for c in EXPECTED_COLUMNS if c not in {"ID", "SEXO"}]
    empty = frame[other].isna()
    for column in ("Peso", "Altura"):
        empty[column] |= frame[column].astype("string").str.fullmatch(
            r"0+(?:[.,]0+)?", na=False
        )
    mask = frame["SEXO"].eq("Indeterminado").fillna(False) & empty.all(axis=1)
    removed = frame.loc[mask, ["ID", "_LINHA_ORIGEM"]].rename(
        columns={"_LINHA_ORIGEM": "linha_origem"}
    ).copy()
    removed["motivo"] = "registro sem dados clínicos (padrão ID 65)"
    return frame.loc[~mask].copy().reset_index(drop=True), removed


def number(value: object) -> float | None:
    if missing(value):
        return None
    try:
        result = float(str(value).replace(",", "."))
        return result if math.isfinite(result) else None
    except ValueError:
        return None


def clean_numbers(frame: pd.DataFrame, events: list[dict],
                  issues: list[dict]) -> None:
    for index in frame.index:
        row = frame.loc[index]
        for column in NUMERIC_COLUMNS:
            old = row[column]
            value = number(old)
            low, high = LIMITS[column]
            valid = value is not None and low < value <= high
            if column == "IDADE":
                valid = value is not None and 0 <= value < high
            if not valid and not missing(old):
                change(events, row, column, old, pd.NA, "valor ausente ou fora do limite técnico")
                sentinel = column in {"Peso", "Altura", "IMC"} and value == 0
                if not sentinel:
                    pending(issues, row, column, f"valor original fora do limite técnico: {shown(old)}")
            frame.at[index, column] = value if valid else pd.NA
    pas = pd.to_numeric(frame["PA SISTOLICA"], errors="coerce")
    pad = pd.to_numeric(frame["PA DIASTOLICA"], errors="coerce")
    for index in frame.index[pas.notna() & pad.notna() & (pas <= pad)]:
        row = frame.loc[index]
        pending(issues, row, "PA SISTOLICA/PA DIASTOLICA", "sistólica menor ou igual à diastólica")
        for column in ("PA SISTOLICA", "PA DIASTOLICA"):
            change(events, row, column, row[column], pd.NA, "pressões contraditórias")
            frame.at[index, column] = pd.NA


def parse_date(value: object) -> tuple[date | None, str]:
    if missing(value):
        return None, "ausente"
    original = str(value).strip()
    if re.fullmatch(r"\d+(?:\.\d+)?", original):
        serial = float(original)
        if 1 <= serial <= 60000:
            result = date(1899, 12, 30) + timedelta(days=serial)
            return result, "serial Excel"
    text = original.replace("\\", "/")
    text = re.sub(r"^(\d{1,2}/\d{1,2}),([12]\d{3})$", r"\1/\2", text)
    match = re.fullmatch(r"(?i)(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)/(\d{1,2}),?/(\d{4})", text)
    if match:
        months = "jan fev mar abr mai jun jul ago set out nov dez".split()
        text = f"{int(match[2]):02d}/{months.index(match[1].lower()) + 1:02d}/{match[3]}"
    for pattern in ("%d/%m/%y", "%d/%m/%Y"):
        try:
            result = datetime.strptime(text, pattern).date()
            if 1900 <= result.year <= 2026:
                return result, "texto" if text == original else "pontuação normalizada"
        except ValueError:
            pass
    return None, "data inválida"


def clean_dates_and_age(frame: pd.DataFrame, events: list[dict],
                        issues: list[dict]) -> tuple[pd.DataFrame, dict[int, int]]:
    dates: dict[str, dict[int, date | None]] = {c: {} for c in DATE_COLUMNS}
    age_days: dict[int, int] = {}
    age_records = []
    for index in frame.index:
        row = frame.loc[index]
        for column in DATE_COLUMNS:
            old = row[column]
            parsed, status = parse_date(old)
            dates[column][index] = parsed
            new = parsed.isoformat() if parsed else pd.NA
            if shown(old) != shown(new):
                change(events, row, column, old, new, f"conversão de data: {status}")
                if status == "data inválida":
                    pending(issues, row, column, f"data original inválida: {shown(old)}")
            if parsed and column == "Atendimento" and not 2000 <= parsed.year <= 2010:
                pending(issues, row, column, "ano de atendimento fora da concentração 2000–2010")
            if parsed and column == "DN" and parsed.year > 2010:
                pending(issues, row, column, "nascimento posterior a 2010")
            frame.at[index, column] = new
        attendance, birth = dates["Atendimento"][index], dates["DN"][index]
        old_age = frame.at[index, "IDADE"]
        if attendance is not None and birth is not None:
            days = (attendance - birth).days
            calculated = round(days / 365.25, 2)
            if 0 <= calculated < 20:
                age_days[index] = days
                if missing(old_age) or abs(float(old_age) - calculated) > 0.01:
                    change(events, row, "IDADE", old_age, calculated, "Atendimento menos DN / 365,25")
                    frame.at[index, "IDADE"] = calculated
                    age_records.append({
                        "ID": shown(row["ID"]), "idade_original": shown(old_age),
                        "idade_calculada": calculated, "diferenca": (
                            round(float(old_age) - calculated, 2) if not missing(old_age) else ""
                        ), "decisao": "idade recalculada pelas datas",
                    })
            else:
                pending(issues, row, "Atendimento/DN", "datas incompatíveis com a faixa de 0 a 19 anos")
        elif not missing(old_age):
            pending(issues, row, "IDADE", "idade mantida sem dois documentos de data válidos")
    return pd.DataFrame(age_records, columns=[
        "ID", "idade_original", "idade_calculada", "diferenca", "decisao"
    ]), age_days


def clean_anthropometrics(frame: pd.DataFrame, events: list[dict],
                         issues: list[dict]) -> pd.DataFrame:
    calculations = []
    for index in frame.index:
        row = frame.loc[index]
        weight = number(row["Peso"])
        height = number(row["Altura"])
        bmi = number(row["IMC"])
        field = None
        formula = ""
        result = None
        if weight is not None and height is not None:
            expected = round(weight / (height / 100) ** 2, 2)
            if not 8 < expected <= 70:
                pending(issues, row, "Peso/Altura/IMC", "medidas produzem IMC fora do limite técnico")
                if bmi is not None:
                    change(events, row, "IMC", bmi, pd.NA, "medidas antropométricas contraditórias")
                    frame.at[index, "IMC"] = pd.NA
                continue
            if bmi is None or abs(bmi - expected) > 1:
                field, result, formula = "IMC", expected, "Peso / (Altura / 100)^2"
        elif weight is None and height is not None and bmi is not None:
            candidate = round(bmi * (height / 100) ** 2, 2)
            if 0 < candidate <= 200:
                field, result, formula = "Peso", candidate, "IMC * (Altura / 100)^2"
        elif height is None and weight is not None and bmi is not None:
            candidate = round(math.sqrt(weight / bmi) * 100, 2)
            if 30 < candidate <= 220:
                field, result, formula = "Altura", candidate, "sqrt(Peso / IMC) * 100"
        if field is not None:
            before = frame.at[index, field]
            change(events, row, field, before, result, formula)
            frame.at[index, field] = result
            calculations.append({
                "ID": shown(row["ID"]), "campo_calculado": field,
                "valor_original": shown(before), "valor_calculado": result,
                "formula": formula,
            })
    return pd.DataFrame(calculations, columns=[
        "ID", "campo_calculado", "valor_original", "valor_calculado", "formula"
    ])


def classify_bmi(frame: pd.DataFrame, age_days: dict[int, int]) -> pd.DataFrame:
    records = []
    for index in frame.index:
        row = frame.loc[index]
        age = number(row["IDADE"])
        bmi = number(row["IMC"])
        if age is None:
            result = {"classificacao": None, "motivo": "idade ausente"}
            days = None
        elif bmi is None:
            result = {"classificacao": None, "motivo": "IMC ausente"}
            days = age_days.get(index, round(age * 365.25))
        else:
            days = age_days.get(index, round(age * 365.25))
            result = classificar_imc_pediatrico(days, shown(row["SEXO"]), bmi)
        frame.at[index, "CLASSIFICACAO IMC"] = (
            result["classificacao"] if result["classificacao"] is not None else pd.NA
        )
        records.append({
            "ID": shown(row["ID"]), "idade_dias": days, "SEXO": shown(row["SEXO"]),
            "IMC": bmi, "classificacao": result["classificacao"],
            "referencia": result.get("referencia", ""),
            "idade_referencia": result.get("idade_referencia", ""),
            "motivo": result["motivo"],
        })
    return pd.DataFrame(records)


def similar_records(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [c for c in EXPECTED_COLUMNS if c != "ID"]
    duplicated = frame.duplicated(subset=columns, keep=False)
    if not duplicated.any():
        return pd.DataFrame(columns=["grupo", "ID", "linha_origem", "registros_no_grupo"])
    groups = frame.loc[duplicated, columns].fillna("<ausente>").astype(str)
    codes = pd.util.hash_pandas_object(groups, index=False)
    counts = codes.value_counts()
    group_numbers = {code: n for n, code in enumerate(sorted(counts.index), 1)}
    selected = frame.loc[duplicated, ["ID", "_LINHA_ORIGEM"]].copy()
    selected.insert(0, "grupo", codes.map(group_numbers).to_numpy())
    selected["registros_no_grupo"] = codes.map(counts).to_numpy()
    return selected.rename(columns={"_LINHA_ORIGEM": "linha_origem"}).sort_values(
        ["grupo", "ID"]
    )


def unresolved_issues(frame: pd.DataFrame, issues: list[dict]) -> list[dict]:
    by_id = frame.set_index("ID")
    remaining = []
    for issue in issues:
        field = issue["variavel"]
        if issue["motivo"].startswith("valor original fora do limite técnico"):
            if field in NUMERIC_COLUMNS and not missing(by_id.at[issue["ID"], field]):
                continue
        remaining.append(issue)
    return remaining


def quality_summary(frame: pd.DataFrame, similar: pd.DataFrame,
                    issues: list[dict]) -> pd.DataFrame:
    rows = []
    for column in EXPECTED_COLUMNS + ["CLASSIFICACAO IMC"]:
        rows.append({
            "variavel": column, "verificacao": "valores ausentes",
            "quantidade": int(frame[column].isna().sum()), "observacao": "",
        })
    rows.extend([
        {"variavel": "ID", "verificacao": "IDs duplicados",
         "quantidade": int(frame["ID"].duplicated().sum()), "observacao": ""},
        {"variavel": "registro", "verificacao": "registros semelhantes sem considerar ID",
         "quantidade": len(similar), "observacao": "revisão, sem exclusão automática"},
        {"variavel": TARGET, "verificacao": "categoria fora de Normal/Anormal",
         "quantidade": int((frame[TARGET].notna() &
                          ~frame[TARGET].isin(TARGET_CLASSES)).sum()), "observacao": ""},
        {"variavel": "SEXO", "verificacao": "categoria fora do domínio",
         "quantidade": int((frame["SEXO"].notna() &
                          ~frame["SEXO"].isin(["Masculino", "Feminino", "Indeterminado"])).sum()),
         "observacao": ""},
    ])
    for column in NUMERIC_COLUMNS:
        values = pd.to_numeric(frame[column], errors="coerce")
        low, high = LIMITS[column]
        bad = values.notna() & ((values <= low) | (values > high))
        if column == "IDADE":
            bad = values.notna() & ((values < 0) | (values >= high))
        rows.append({
            "variavel": column, "verificacao": "fora do limite técnico",
            "quantidade": int(bad.sum()), "observacao": f"limites: {low} a {high}",
        })
    for column in DATE_COLUMNS:
        converted = pd.to_datetime(frame[column], errors="coerce")
        rows.append({
            "variavel": column, "verificacao": "data preenchida inválida",
            "quantidade": int((frame[column].notna() & converted.isna()).sum()),
            "observacao": "",
        })
    def issue_type(reason: str) -> str:
        if reason.startswith("valor original fora do limite técnico"):
            return "valor original fora do limite técnico"
        if reason.startswith("data original inválida"):
            return "data original inválida"
        return reason

    counts = Counter((r["variavel"], issue_type(r["motivo"])) for r in issues)
    for (column, reason), count in sorted(counts.items()):
        rows.append({
            "variavel": column, "verificacao": "pendência para revisão",
            "quantidade": count, "observacao": reason,
        })
    return pd.DataFrame(rows)


def numeric_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in NUMERIC_COLUMNS:
        series = pd.to_numeric(frame[column], errors="coerce")
        valid = series.dropna()
        rows.append({
            "variavel": column, "validos": len(valid), "ausentes": int(series.isna().sum()),
            "media": valid.mean(), "mediana": valid.median(),
            "desvio_padrao": valid.std(), "minimo": valid.min(),
            "Q1": valid.quantile(0.25), "Q3": valid.quantile(0.75),
            "maximo": valid.max(),
        })
    return pd.DataFrame(rows)


def date_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in DATE_COLUMNS:
        values = pd.to_datetime(frame[column], errors="coerce").dropna()
        rows.append({
            "variavel": column, "validos": len(values),
            "ausentes": int(frame[column].isna().sum()),
            "data_inicial": values.min().date().isoformat() if len(values) else "",
            "data_final": values.max().date().isoformat() if len(values) else "",
        })
    return pd.DataFrame(rows)


def categorical_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in CATEGORICAL_COLUMNS:
        counts = frame[column].fillna("Ausente").value_counts()
        for category, count in counts.items():
            rows.append({
                "variavel": column, "categoria": category, "frequencia": int(count),
                "porcentagem_total": round(100 * count / len(frame), 2),
                "numero_categorias_validas": int(frame[column].nunique()),
            })
    return pd.DataFrame(rows)


def bivariate_numeric(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in NUMERIC_COLUMNS:
        for target in TARGET_CLASSES:
            group = pd.to_numeric(
                frame.loc[frame[TARGET].eq(target), column], errors="coerce"
            )
            valid = group.dropna()
            rows.append({
                "variavel": column, "classe_alvo": target, "n_grupo": len(group),
                "validos": len(valid), "ausentes": int(group.isna().sum()),
                "media": valid.mean(), "mediana": valid.median(),
                "desvio_padrao": valid.std(), "minimo": valid.min(),
                "Q1": valid.quantile(0.25), "Q3": valid.quantile(0.75),
                "maximo": valid.max(),
            })
    return pd.DataFrame(rows)


def bivariate_categorical(frame: pd.DataFrame) -> pd.DataFrame:
    valid = frame.loc[frame[TARGET].isin(TARGET_CLASSES)]
    totals = valid[TARGET].value_counts()
    rows = []
    for column in [c for c in CATEGORICAL_COLUMNS if c != TARGET]:
        cross = pd.crosstab(valid[column].fillna("Ausente"), valid[TARGET])
        cross = cross.reindex(columns=TARGET_CLASSES, fill_value=0)
        for category, frequencies in cross.iterrows():
            for target in TARGET_CLASSES:
                count = int(frequencies[target])
                rows.append({
                    "variavel": column, "categoria": category, "classe_alvo": target,
                    "frequencia": count,
                    "porcentagem_na_classe": round(100 * count / totals[target], 2),
                    "porcentagem_na_categoria": round(
                        100 * count / frequencies.sum(), 2
                    ) if frequencies.sum() else 0,
                })
    return pd.DataFrame(rows)


def save_figure(figure: plt.Figure, path: Path) -> None:
    """Grava o PNG com nova tentativa quando o OneDrive bloqueia o destino."""
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=150)
    for attempt in range(4):
        try:
            path.write_bytes(buffer.getvalue())
            return
        except OSError:
            if attempt == 3:
                raise
            time.sleep(0.25 * (attempt + 1))


def save_plots(frame: pd.DataFrame, output: Path) -> None:
    uni = output / "graficos"
    bi = output / "graficos_bivariada"
    uni.mkdir(parents=True, exist_ok=True)
    bi.mkdir(parents=True, exist_ok=True)
    for column in NUMERIC_COLUMNS:
        series = pd.to_numeric(frame[column], errors="coerce").dropna()
        if series.empty:
            continue
        low, high = series.quantile([0.01, 0.99])
        central = series.between(low, high)
        figure, axes = plt.subplots(1, 2, figsize=(12, 4))
        axes[0].hist(series.loc[central], bins=30, color="#1976a3", edgecolor="white")
        axes[0].set_title(f"Histograma - {column}")
        axes[0].set_xlabel(column)
        axes[0].set_ylabel("Frequência")
        axes[1].boxplot(series, vert=False, showfliers=False,
                        patch_artist=True, boxprops={"facecolor": "#f28e2b"})
        axes[1].set_title(f"Boxplot - {column}")
        axes[1].set_xlabel(column)
        figure.suptitle(f"Escala central (1º–99º percentil); {int((~central).sum())} valores fora")
        figure.tight_layout()
        save_figure(figure, uni / f"numerica_{filename(column)}.png")
        plt.close(figure)

    for column in CATEGORICAL_COLUMNS:
        counts = frame[column].fillna("Ausente").value_counts().head(20).sort_values()
        if counts.empty:
            continue
        figure, axis = plt.subplots(figsize=(10, 5))
        counts.plot.barh(ax=axis, color="#4e79a7")
        axis.set_title(f"Categorias - {column} (20 mais frequentes)")
        axis.set_xlabel("Frequência")
        figure.tight_layout()
        save_figure(figure, uni / f"categorica_{filename(column)}.png")
        plt.close(figure)

    valid = frame.loc[frame[TARGET].isin(TARGET_CLASSES)]
    for column in NUMERIC_COLUMNS:
        groups = [
            pd.to_numeric(valid.loc[valid[TARGET].eq(target), column], errors="coerce").dropna()
            for target in TARGET_CLASSES
        ]
        if not any(len(group) for group in groups):
            continue
        figure, axis = plt.subplots(figsize=(8, 5))
        boxes = axis.boxplot(groups, patch_artist=True, showfliers=False)
        axis.set_xticks([1, 2], TARGET_CLASSES)
        for patch, target in zip(boxes["boxes"], TARGET_CLASSES):
            patch.set_facecolor(COLORS[target])
        axis.set_title(f"{column} por {TARGET}\nPontos extremos omitidos do desenho")
        axis.set_ylabel(column)
        figure.tight_layout()
        save_figure(figure, bi / f"bivariada_numerica_{filename(column)}.png")
        plt.close(figure)

    for column in [c for c in CATEGORICAL_COLUMNS if c != TARGET]:
        cross = pd.crosstab(valid[column].fillna("Ausente"), valid[TARGET])
        cross = cross.reindex(columns=TARGET_CLASSES, fill_value=0)
        cross = cross.loc[cross.sum(axis=1).sort_values(ascending=False).head(12).index]
        if cross.empty:
            continue
        for target in TARGET_CLASSES:
            total = int(valid[TARGET].eq(target).sum())
            cross[target] = cross[target] * 100 / total if total else 0
        axis = cross.plot.barh(figsize=(11, 6), color=[COLORS[t] for t in TARGET_CLASSES])
        axis.set_title(f"{column} por {TARGET} (12 categorias mais frequentes)")
        axis.set_xlabel("Percentual dentro da classe (%)")
        axis.invert_yaxis()
        axis.legend(loc="lower right")
        axis.figure.tight_layout()
        save_figure(axis.figure, bi / f"bivariada_categorica_{filename(column)}.png")
        plt.close(axis.figure)


def write_report(
    frame: pd.DataFrame, removed: pd.DataFrame, issues: pd.DataFrame,
    numeric: pd.DataFrame, date_stats: pd.DataFrame, categorical: pd.DataFrame,
    bivariate: pd.DataFrame, age_report: pd.DataFrame, output: Path,
) -> None:
    n = len(frame)
    raw_count = n + len(removed)
    target_counts = frame[TARGET].value_counts()
    age_normal = bivariate.loc[
        (bivariate["variavel"] == "IDADE") & (bivariate["classe_alvo"] == "Normal")
    ].iloc[0]
    age_abnormal = bivariate.loc[
        (bivariate["variavel"] == "IDADE") & (bivariate["classe_alvo"] == "Anormal")
    ].iloc[0]
    age_divergences = int(
        pd.to_numeric(age_report["diferenca"], errors="coerce").abs().gt(0.1).sum()
    )
    pending_ids = int(issues["ID"].nunique())
    male_share = {
        target: round(
            100 * int((frame["SEXO"].eq("Masculino") & frame[TARGET].eq(target)).sum())
            / int(frame[TARGET].eq(target).sum()), 1
        )
        for target in TARGET_CLASSES
    }

    numeric_lines = "\n".join(
        f"| {r.variavel} | {int(r.validos)} | {int(r.ausentes)} | {r.mediana:.2f} | {r.minimo:.2f} | {r.maximo:.2f} |"
        for r in numeric.itertuples(index=False)
    )
    date_lines = "\n".join(
        f"| {r.variavel} | {int(r.validos)} | {int(r.ausentes)} | {r.data_inicial} | {r.data_final} |"
        for r in date_stats.itertuples(index=False)
    )
    category_lines = []
    for column in CATEGORICAL_COLUMNS:
        present = frame[column].dropna()
        main_category = str(present.value_counts().index[0]) if len(present) else "—"
        category_lines.append(
            f"| {column} | {int(frame[column].isna().sum())} | "
            f"{100 * frame[column].isna().mean():.1f}% | {main_category} |"
        )
    category_table = "\n".join(category_lines)
    treatments = {
        "ID": "conferir unicidade; manter como identificador",
        "Atendimento": "converter para ISO; invalidar data ilegível",
        "DN": "converter para ISO; invalidar data ilegível",
        "IDADE": "recalcular com as duas datas coerentes",
        "Peso": "retirar sentinelas e valores fora do limite",
        "Altura": "retirar sentinelas e valores fora do limite",
        "IMC": "conferir com peso e altura; corrigir quando possível",
        "FC": "retirar valores fora do limite técnico",
        "PA SISTOLICA": "conferir limite e coerência com diastólica",
        "PA DIASTOLICA": "conferir limite e coerência com sistólica",
        "PPA": "converter Não Calculado em ausente; não recalcular",
        TARGET: "padronizar Normal/Anormal; manter ausentes",
        "SEXO": "padronizar M/F; manter ausentes",
        "CLASSIFICACAO IMC": "derivar com tabelas OMS se entradas válidas",
    }
    for column in CATEGORICAL_COLUMNS:
        treatments.setdefault(column, "unificar grafias equivalentes; manter ausentes")
    quality_lines = []
    for column in EXPECTED_COLUMNS + ["CLASSIFICACAO IMC"]:
        issue_count = int(issues["variavel"].eq(column).sum())
        quality_lines.append(
            f"| {column} | {int(frame[column].isna().sum())} | {issue_count} | "
            f"{treatments[column]} |"
        )
    quality_table = "\n".join(quality_lines)
    numeric_bivariate_lines = []
    for column in NUMERIC_COLUMNS:
        normal = bivariate.loc[
            bivariate["variavel"].eq(column) & bivariate["classe_alvo"].eq("Normal")
        ].iloc[0]
        abnormal = bivariate.loc[
            bivariate["variavel"].eq(column) & bivariate["classe_alvo"].eq("Anormal")
        ].iloc[0]
        numeric_bivariate_lines.append(
            f"| {column} | {int(normal['validos'])} | {normal['mediana']:.2f} | "
            f"{int(abnormal['validos'])} | {abnormal['mediana']:.2f} |"
        )
    numeric_bivariate_table = "\n".join(numeric_bivariate_lines)
    labeled = frame.loc[frame[TARGET].isin(TARGET_CLASSES)]
    categorical_bivariate_lines = []
    for column in [c for c in CATEGORICAL_COLUMNS if c != TARGET]:
        present = labeled[column].dropna()
        if present.empty:
            category, count = "—", 0
            shares = {target: 0.0 for target in TARGET_CLASSES}
        else:
            category = str(present.value_counts().index[0])
            count = int(present.eq(category).sum())
            shares = {
                target: 100 * labeled.loc[labeled[TARGET].eq(target), column].eq(category).mean()
                for target in TARGET_CLASSES
            }
        categorical_bivariate_lines.append(
            f"| {column} | {category} (n={count}) | "
            f"{shares['Normal']:.1f}% | {shares['Anormal']:.1f}% |"
        )
    categorical_bivariate_table = "\n".join(categorical_bivariate_lines)
    report = f"""# Relatório de análise do conjunto UCMF

## Conjunto e objetivo

O arquivo bruto contém {raw_count} registros e 21 variáveis de atendimento em cardiologia pediátrica. A variável-alvo é {TARGET}, que indica presença ou ausência de patologia cardíaca. Após a exclusão de {len(removed)} registros sem dados clínicos, o conjunto analisado tem {n} registros. O dicionário de variáveis do projeto está em dados/dicionario.md.

## Análise univariada após a limpeza

| Variável numérica | Válidos | Ausentes | Mediana | Mínimo | Máximo |
| --- | ---: | ---: | ---: | ---: | ---: |
{numeric_lines}

| Data | Válidas | Ausentes | Primeira | Última |
| --- | ---: | ---: | --- | --- |
{date_lines}

| Variável categórica | Ausentes | Percentual ausente | Categoria mais frequente entre os válidos |
| --- | ---: | ---: | --- |
{category_table}

As frequências completas de cada categoria, incluindo Ausente, estão em resumo_categoricas.csv. O alvo apresenta {int(target_counts.get("Normal", 0))} registros Normal e {int(target_counts.get("Anormal", 0))} Anormal; {int(frame[TARGET].isna().sum())} não têm rótulo. ID identifica registros e não deve ser interpretado como medida clínica. HDA2 e PPA exigem cautela devido à alta proporção de ausências.

## Qualidade e soluções

A leitura do CSV foi corrigida para preservar campos entre aspas. Valores vazios, #VALUE! e marcadores que não são medidas foram convertidos em ausentes. Categorias equivalentes foram padronizadas. Idades foram recalculadas a partir de datas coerentes; {age_divergences} idades originais divergiam em mais de 0,10 ano. Os demais casos permanecem auditáveis. Valores fora dos limites técnicos foram retirados da análise, sem imputação por média. Restam {len(issues)} verificações em {pending_ids} IDs que não podem ser resolvidas com segurança apenas pelo CSV. Registros semelhantes com IDs diferentes ficaram para revisão, pois não há evidência suficiente para excluí-los. Os quantitativos por variável estão em qualidade_dados.csv e as decisões por ID em alteracoes.csv e pendencias.csv.

| Variável | Ausentes finais | Pendências diretas | Solução aplicada ou critério |
| --- | ---: | ---: | --- |
{quality_table}

Pendências de relações entre Atendimento/DN, Peso/Altura/IMC e PAS/PAD aparecem como linhas próprias em qualidade_dados.csv. Contagens de ausentes não significam que todos os valores possam ser recuperados.

## Comparação de duas variáveis

IDADE e {TARGET} foram comparadas após a limpeza. A mediana de idade é {age_normal["mediana"]:.2f} anos entre os registros Normal e {age_abnormal["mediana"]:.2f} anos entre os Anormal. O boxplot em graficos_bivariada/bivariada_numerica_idade.png mostra as distribuições; a tabela bivariada_numericas.csv informa os tamanhos de amostra e dispersões. O gráfico mostra a parte central da distribuição para preservar legibilidade; os valores válidos extremos permanecem nas estatísticas. A associação observada não implica relação causal.

## Análise bivariada com o alvo

As sete variáveis numéricas e as variáveis categóricas foram comparadas com {TARGET}. As categorias de alvo ausente ficaram fora desta etapa. As medianas abaixo descrevem apenas registros com a medida preenchida:

| Variável numérica | n Normal | Mediana Normal | n Anormal | Mediana Anormal |
| --- | ---: | ---: | ---: | ---: |
{numeric_bivariate_table}

Para cada variável categórica, a tabela mostra sua categoria mais frequente e a proporção dela em cada classe. Ela permite ver a direção e o tamanho das diferenças sem confundir frequência absoluta com percentual. As tabelas CSV e os gráficos mostram todas as categorias, inclusive Ausente.

| Variável categórica | Categoria de referência | % Normal | % Anormal |
| --- | --- | ---: | ---: |
{categorical_bivariate_table}

As medianas de IDADE diferem entre as classes ({age_normal["mediana"]:.2f} e {age_abnormal["mediana"]:.2f} anos). A ausência de SOPRO é muito mais frequente no grupo Normal, enquanto as medianas de PAS e PAD são iguais nos dois grupos. Na variável SEXO, Masculino representa {male_share["Normal"]:.1f}% do grupo Normal e {male_share["Anormal"]:.1f}% do grupo Anormal, diferença pequena. As outras diferenças nas tabelas também são descritivas: faltantes, composição da amostra e categorias raras podem mudar a comparação. PPA e CLASSIFICACAO IMC têm restrições descritas abaixo. Gráficos usam verde para Normal e vermelho para Anormal; não há inferência causal ou teste de significância nesta etapa.

## Transformações e limites

O processamento criou IDADE, IMC e CLASSIFICACAO IMC somente quando os dados necessários eram consistentes. CLASSIFICACAO IMC usa as referências oficiais da OMS por idade e sexo. PPA não foi recalculada: a implementação anterior empregava cortes simplificados e faltam dados para conferir todas as situações. Por isso, Não Calculado passou a ausente e os valores informados na origem continuam identificáveis. A ausência de alguns campos pode ser informativa; não foi preenchida por estimativa estatística.

A seleção supervisionada é gerada em uma etapa posterior por scripts/auditar_base_modelagem.py. O dicionário em dados/dicionario.md descreve os preditores, e resultados/preparo/relatorio_adequacao.md detalha as regras de preparo. O ajuste dos transformadores ocorre dentro das partições de treino em scripts/treinar_modelos.py.

Este relatório em Markdown conserva o detalhamento técnico dos arquivos reproduzíveis em resultados/analise/. A versão paginada para submissão é gerada por scripts/gerar_relatorio_a1.py em relatorio_A1.pdf; o grupo deve conferir o texto e os resultados antes do envio.

## Uso de IA generativa

OpenAI Codex auxiliou a revisão dos dados, a correção dos scripts, a geração das tabelas e gráficos e a redação inicial deste relatório. O grupo deve conferir os resultados e assumir a interpretação final.
"""
    (output / "relatorio_analise.md").write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Limpa e analisa dados/UCMF_raw.csv")
    parser.add_argument("csv", nargs="?", type=Path, default=ROOT / "dados/UCMF_raw.csv")
    parser.add_argument("--saida", type=Path, default=ROOT / "resultados/analise")
    args = parser.parse_args()
    output = args.saida.resolve()
    output.mkdir(parents=True, exist_ok=True)

    frame = read_dataset(args.csv)
    raw_count = len(frame)
    events: list[dict] = []
    issues: list[dict] = []
    normalize_categories(frame, events)
    frame, removed = remove_placeholders(frame)
    clean_numbers(frame, events, issues)
    age_report, age_days = clean_dates_and_age(frame, events, issues)
    anthropometric = clean_anthropometrics(frame, events, issues)
    classifications = classify_bmi(frame, age_days)
    issues = unresolved_issues(frame, issues)
    similar = similar_records(frame)
    numeric = numeric_summary(frame)
    dates = date_summary(frame)
    categorical = categorical_summary(frame)
    bi_numeric = bivariate_numeric(frame)
    bi_categorical = bivariate_categorical(frame)
    issue_report = pd.DataFrame(issues, columns=["ID", "linha_origem", "variavel", "motivo"])
    change_report = pd.DataFrame(events, columns=[
        "ID", "linha_origem", "variavel", "valor_original", "valor_final", "regra"
    ])
    quality = quality_summary(frame, similar, issues)

    ordered = ["ID", "SEXO", "Peso", "Altura", "IMC", "CLASSIFICACAO IMC"] + [
        c for c in EXPECTED_COLUMNS if c not in {"ID", "SEXO", "Peso", "Altura", "IMC"}
    ]
    frame[ordered].to_csv(output / "UCMF_limpo.csv", index=False, encoding="utf-8-sig")
    files = {
        "alteracoes.csv": change_report, "pendencias.csv": issue_report,
        "linhas_removidas.csv": removed, "registros_semelhantes.csv": similar,
        "qualidade_dados.csv": quality, "resumo_numericas.csv": numeric,
        "resumo_datas.csv": dates, "resumo_categoricas.csv": categorical,
        "bivariada_numericas.csv": bi_numeric,
        "bivariada_categoricas.csv": bi_categorical,
        "calculos_atendimento_dn_idade.csv": age_report,
        "calculos_peso_altura_imc.csv": anthropometric,
        "classificacoes_imc.csv": classifications,
    }
    for name, table in files.items():
        table.to_csv(output / name, index=False, encoding="utf-8-sig")
    ppa = pd.DataFrame([
        {"situacao": "ausente ou Não Calculado na origem",
         "quantidade": int(frame["PPA"].isna().sum())},
        {"situacao": "informado na origem, sem validação clínica",
         "quantidade": int(frame["PPA"].notna().sum())},
    ])
    ppa.to_csv(output / "situacao_ppa.csv", index=False, encoding="utf-8-sig")
    stale = output / "calculos_ppa.csv"
    if stale.exists():
        stale.unlink()
    save_plots(frame, output)
    write_report(frame, removed, issue_report, numeric, dates, categorical, bi_numeric, age_report, output)
    print(f"Linhas brutas: {raw_count}")
    print(f"Linhas excluídas: {len(removed)}")
    print(f"Linhas limpas: {len(frame)}")
    print(f"Alterações auditadas: {len(change_report)}")
    print(f"Pendências: {len(issue_report)}")
    print(f"Resultados: {output}")


if __name__ == "__main__":
    main()
