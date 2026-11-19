"""Declara o preparo atual. Nenhum fit ou split ocorre ao executar este script."""
from pathlib import Path
# Fundamentação R8–R11 no relatório de adequação publicado.
# Mediana/indicadores são baseline metodológico, não recomendação clínica OMS.
import argparse
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import MissingIndicator, SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.utils.validation import check_is_fitted

ROOT = Path(__file__).resolve().parents[1]
TARGET = 'NORMAL X ANORMAL'
NUMERIC_COLUMNS = ['IDADE', 'Peso', 'Altura', 'FC', 'PA SISTOLICA', 'PA DIASTOLICA']
CATEGORICAL_COLUMNS = ['SEXO', 'PULSOS', 'B2', 'MOTIVO_UNIFICADO']
HISTORY_COLUMN = 'HDA_UNIFICADA'
FEATURE_COLUMNS = NUMERIC_COLUMNS + CATEGORICAL_COLUMNS + [HISTORY_COLUMN]
DERIVED_COLUMNS = ['IMC', 'CLASSIFICACAO IMC', 'FAIXA_ETARIA', 'PPA_CALCULADA']
MISSING_CATEGORY = '__SEM_INFORMACAO__'
SYMPTOMS = ['Assintomático', 'Palpitação', 'Dispneia', 'Dor precordial', 'Desmaio/tontura', 'Cianose', 'Ganho de peso', 'Outro']


def select_features():
    return NUMERIC_COLUMNS.copy(), CATEGORICAL_COLUMNS.copy()


def profile_keys(frame, columns):
    """Compara valores completos, com ausentes distintos de textos literais."""
    return [tuple((0,) if pd.isna(v) else (1, v) for v in row)
            for row in frame[columns].itertuples(index=False, name=None)]


def duplicate_groups(frame):
    columns = [c for c in frame if c not in {'ID', TARGET}]
    mapping, groups = {}, []
    for key in profile_keys(frame, columns):
        if key not in mapping:
            mapping[key] = f'g{len(mapping)+1:06d}'
        groups.append(mapping[key])
    return pd.Series(groups, index=frame.index)


def _validate_selection(numeric, categorical):
    if not set(numeric) <= set(NUMERIC_COLUMNS) or not set(categorical) <= set(CATEGORICAL_COLUMNS):
        raise ValueError('Somente atributos do contrato supervisionado são permitidos')
    if len(set(numeric+categorical)) != len(numeric+categorical):
        raise ValueError('Atributos repetidos na seleção')


def row_features(frame, numeric=None, categorical=None):
    numeric = NUMERIC_COLUMNS if numeric is None else numeric
    categorical = CATEGORICAL_COLUMNS if categorical is None else categorical
    _validate_selection(numeric, categorical)
    data = frame[numeric+categorical+[HISTORY_COLUMN]].copy()
    for c in numeric:
        data[c] = pd.to_numeric(data[c], errors='coerce').astype(float)
    for c in categorical+[HISTORY_COLUMN]:
        data[c] = data[c].astype(object).where(data[c].notna(), np.nan)
    return data


class HistoryEncoder(TransformerMixin, BaseEstimator):
    """Codifica menções de sintomas, não nega sintomas não citados."""
    def fit(self, X, y=None):
        self.n_features_in_ = 1
        return self

    def transform(self, X):
        check_is_fitted(self)
        values = np.asarray(X, dtype=object).reshape(-1)
        result = np.zeros((len(values), len(SYMPTOMS)+2), dtype=float)
        for i, value in enumerate(values):
            if pd.isna(value) or not str(value).strip():
                result[i, -2] = 1
                continue
            tokens = {s.strip() for s in str(value).split('|') if s.strip()}
            for j, symptom in enumerate(SYMPTOMS):
                result[i, j] = symptom in tokens
            result[i, -1] = bool(tokens-set(SYMPTOMS))
        return result

    def get_feature_names_out(self, input_features=None):
        return np.asarray([f'HDA_mencao_{s}' for s in SYMPTOMS]+['HDA_sem_informacao', 'HDA_categoria_inedita'], dtype=object)


def build_preprocessor(numeric=None, categorical=None):
    numeric = NUMERIC_COLUMNS.copy() if numeric is None else numeric
    categorical = CATEGORICAL_COLUMNS.copy() if categorical is None else categorical
    _validate_selection(numeric, categorical)
    return ColumnTransformer([
        ('numericas', Pipeline([
            ('imputar', SimpleImputer(strategy='median', keep_empty_features=True)),
            ('padronizar', StandardScaler()),
        ]), numeric),
        ('ausencias_numericas', MissingIndicator(features='all'), numeric),
        ('categoricas', Pipeline([
            ('ausente', SimpleImputer(strategy='constant', fill_value=MISSING_CATEGORY, keep_empty_features=True)),
            ('codificar', OneHotEncoder(handle_unknown='ignore', sparse_output=False)),
        ]), categorical),
        ('hda', HistoryEncoder(), [HISTORY_COLUMN]),
    ], remainder='drop', verbose_feature_names_out=True)


def fit_on_train(train, test, numeric=None, categorical=None):
    """Auxiliar: na validação cruzada futura, usar o Pipeline completo por fold."""
    preprocessor = build_preprocessor(numeric, categorical)
    a = preprocessor.fit_transform(row_features(train, numeric, categorical))
    b = preprocessor.transform(row_features(test, numeric, categorical))
    return preprocessor, a, b


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--entrada', type=Path, default=ROOT/'resultados/preparo/UCMF_supervisionado.csv')
    args = parser.parse_args()
    frame = pd.read_csv(args.entrada, dtype='string', encoding='utf-8-sig')
    row_features(frame)
    build_preprocessor()
    print(f'Contrato validado: {len(frame)} registros; {len(FEATURE_COLUMNS)} preditores. Transformador não ajustado.')


if __name__ == '__main__':
    main()
