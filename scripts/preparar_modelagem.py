"""Separa dados rotulados e ajusta o pré-processamento somente no treino.

Este script prepara atributos para a próxima etapa. Não treina nem avalia um
classificador; o conjunto de teste fica reservado para essa avaliação.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
TARGET = "NORMAL X ANORMAL"
NUMERIC_COLUMNS = ["IDADE", "Peso", "Altura", "FC", "PA SISTOLICA", "PA DIASTOLICA"]
BEFORE_EXAM = ["SEXO", "MOTIVO1"]
AFTER_EXAM = BEFORE_EXAM + ["PULSOS", "B2", "SOPRO", "HDA 1"]
MISSING_CATEGORY = "__SEM_INFORMACAO__"


def select_features(moment: str) -> tuple[list[str], list[str]]:
    """Retorna a seleção clínica provisória para o momento da previsão."""
    if moment == "antes_exame":
        return NUMERIC_COLUMNS.copy(), BEFORE_EXAM.copy()
    if moment == "apos_exame":
        return NUMERIC_COLUMNS.copy(), AFTER_EXAM.copy()
    raise ValueError(f"Momento desconhecido: {moment}")


def row_features(frame: pd.DataFrame, numeric: list[str],
                 categorical: list[str]) -> pd.DataFrame:
    """Converte tipos por linha, sem estimar parâmetros da população."""
    data = frame[numeric + categorical].copy()
    for column in numeric:
        data[column] = pd.to_numeric(data[column], errors="coerce").astype(float)
    for column in categorical:
        data[column] = data[column].astype(object).where(data[column].notna(), np.nan)
    return data


def duplicate_groups(frame: pd.DataFrame) -> pd.Series:
    """Agrupa linhas idênticas sem consultar ID ou o rótulo."""
    columns = [column for column in frame if column not in {"ID", TARGET}]
    values = frame[columns].fillna("<ausente>").astype(str)
    return pd.util.hash_pandas_object(values, index=False).map(lambda value: f"{value:016x}")


def split_labeled(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """Reserva um dos cinco blocos estratificados, mantendo grupos juntos."""
    labeled = frame.loc[frame[TARGET].isin(["Normal", "Anormal"])].copy()
    if labeled["ID"].duplicated().any():
        raise ValueError("IDs repetidos impedem a divisão auditável")
    groups = duplicate_groups(labeled)
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    train_idx, test_idx = next(splitter.split(labeled, labeled[TARGET], groups))
    train = labeled.iloc[train_idx].copy()
    test = labeled.iloc[test_idx].copy()
    if set(groups.iloc[train_idx]) & set(groups.iloc[test_idx]):
        raise AssertionError("Um grupo semelhante caiu em treino e teste")
    if set(train[TARGET]) != {"Normal", "Anormal"} or set(test[TARGET]) != {
        "Normal", "Anormal"
    }:
        raise ValueError("Uma classe ficou ausente em treino ou teste")
    return train, test, groups


def build_preprocessor(numeric: list[str], categorical: list[str]) -> ColumnTransformer:
    """Cria transformações ajustáveis; nenhuma é ajustada nesta função."""
    numeric_pipe = Pipeline([
        ("imputar", SimpleImputer(strategy="median", add_indicator=True)),
        ("padronizar", StandardScaler()),
    ])
    categorical_pipe = Pipeline([
        ("ausente", SimpleImputer(strategy="constant", fill_value=MISSING_CATEGORY)),
        ("codificar", OneHotEncoder(
            handle_unknown="infrequent_if_exist", min_frequency=10,
            sparse_output=False,
        )),
    ])
    return ColumnTransformer([
        ("numericas", numeric_pipe, numeric),
        ("categoricas", categorical_pipe, categorical),
    ], remainder="drop", verbose_feature_names_out=False)


def fit_on_train(train: pd.DataFrame, test: pd.DataFrame,
                 numeric: list[str], categorical: list[str]
                 ) -> tuple[ColumnTransformer, np.ndarray, np.ndarray]:
    """Ajusta no treino e somente transforma o teste reservado."""
    x_train = row_features(train, numeric, categorical)
    x_test = row_features(test, numeric, categorical)
    preprocessor = build_preprocessor(numeric, categorical)
    transformed_train = preprocessor.fit_transform(x_train)
    transformed_test = preprocessor.transform(x_test)
    if transformed_train.shape[1] != transformed_test.shape[1]:
        raise AssertionError("Número de atributos diferente entre treino e teste")
    return preprocessor, transformed_train, transformed_test


def write_results(output: Path, frame: pd.DataFrame, train: pd.DataFrame,
                  test: pd.DataFrame, groups: pd.Series, moment: str,
                  numeric: list[str], categorical: list[str],
                  preprocessor: ColumnTransformer,
                  transformed_train: np.ndarray,
                  transformed_test: np.ndarray) -> None:
    output.mkdir(parents=True, exist_ok=True)
    assignment = pd.DataFrame({
        "ID": pd.concat([train["ID"], test["ID"]]),
        "conjunto": ["treino"] * len(train) + ["teste"] * len(test),
        "grupo_sem_id_alvo": pd.concat([
            groups.loc[train.index], groups.loc[test.index]
        ]),
        TARGET: pd.concat([train[TARGET], test[TARGET]]),
    })
    assignment.to_csv(output / "divisao_treino_teste.csv", index=False, encoding="utf-8-sig")

    labeled = frame.loc[frame[TARGET].isin(["Normal", "Anormal"])]
    conflicting = labeled.groupby(groups)[TARGET].nunique()
    conflict_groups = set(conflicting.index[conflicting > 1])
    conflicts = assignment.loc[
        assignment["grupo_sem_id_alvo"].isin(conflict_groups),
        ["grupo_sem_id_alvo", "ID", "conjunto", TARGET],
    ].sort_values(["grupo_sem_id_alvo", "ID"])
    conflicts.to_csv(output / "rotulos_conflitantes.csv", index=False, encoding="utf-8-sig")

    joblib.dump({
        "preprocessador": preprocessor, "numericas": numeric,
        "categoricas": categorical, "momento": moment,
    }, output / "preprocessador_treino.joblib")

    def counts(data: pd.DataFrame) -> str:
        values = data[TARGET].value_counts()
        return f"{len(data)} registros; {values.get('Normal', 0)} Normal; {values.get('Anormal', 0)} Anormal"

    report = f"""# Preparo para modelagem

Esta saída usa UCMF_limpo.csv, gerado pela limpeza determinística da A1. O momento provisório da previsão é **{moment}**. Nenhum classificador foi treinado e o teste não foi usado para escolher atributos nem para ajustar transformações.

| Conjunto | Distribuição |
| --- | --- |
| Treino | {counts(train)} |
| Teste reservado | {counts(test)} |
| Sem rótulo, fora da divisão | {len(frame) - len(labeled)} registros |

Os grupos de registros idênticos sem ID e alvo foram mantidos no mesmo conjunto. Há **{len(conflict_groups)} grupos** com rótulos conflitantes, listados em rotulos_conflitantes.csv. Não há IDs repetidos; ainda assim, não é possível provar apenas com estes campos que uma pessoa não tenha recebido IDs diferentes em atendimentos distintos.

## Atributos e funções

- Numéricos: {', '.join(numeric)}.
- Categóricos: {', '.join(categorical)}.
- `select_features` define as colunas; `row_features` converte tipos sem aprender com outras linhas; `split_labeled` separa grupos; `build_preprocessor` declara as operações ajustáveis; `fit_on_train` executa `fit_transform` somente no treino e `transform` no teste.
- Numéricos: mediana do treino para ausências, indicador de ausência e padronização com média e desvio do treino.
- Categóricos: categoria técnica Sem informação, distinta de valores clínicos como SOPRO = Ausente; agrupamento de níveis com menos de 10 ocorrências no treino e codificação one-hot. Categorias inéditas no teste não alteram o vocabulário aprendido.
- A matriz resultante tem {transformed_train.shape[1]} atributos, com {transformed_train.shape[0]} linhas no treino e {transformed_test.shape[0]} no teste. Ela não é duplicada em CSV: o objeto ajustado está em preprocessador_treino.joblib e os IDs em divisao_treino_teste.csv.

As escolhas de variáveis e o momento da previsão precisam ser confirmados antes de treinar um modelo. Seleção supervisionada, PCA e eventual reamostragem são decisões da próxima etapa e deverão ocorrer dentro de cada treino da validação cruzada. O teste reservado só poderá ser usado na avaliação final.
"""
    (output / "resumo_preparo.md").write_text(report, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepara treino e teste sem vazamento")
    parser.add_argument("--entrada", type=Path,
                        default=ROOT / "resultado_analise" / "UCMF_limpo.csv")
    parser.add_argument("--saida", type=Path, default=ROOT / "resultado_modelagem")
    parser.add_argument("--momento", choices=["antes_exame", "apos_exame"],
                        default="antes_exame")
    args = parser.parse_args()
    frame = pd.read_csv(args.entrada, dtype="string", encoding="utf-8-sig")
    numeric, categorical = select_features(args.momento)
    train, test, groups = split_labeled(frame)
    preprocessor, transformed_train, transformed_test = fit_on_train(
        train, test, numeric, categorical
    )
    write_results(args.saida, frame, train, test, groups, args.momento,
                  numeric, categorical, preprocessor,
                  transformed_train, transformed_test)
    print(f"Treino: {len(train)}; teste: {len(test)}; atributos: {transformed_train.shape[1]}")


if __name__ == "__main__":
    main()
