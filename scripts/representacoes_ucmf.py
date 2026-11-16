"""Representações comparadas somente dentro do desenvolvimento aninhado."""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import MissingIndicator, SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from preparar_modelagem import NUMERIC_COLUMNS, CATEGORICAL_COLUMNS, HISTORY_COLUMN, HistoryEncoder, MISSING_CATEGORY

REPRESENTATIONS=['continua','clinica','combinada']
ALL_NUMERIC=NUMERIC_COLUMNS+['IMC']
ALL_CATEGORICAL=CATEGORICAL_COLUMNS+['FAIXA_ETARIA','CLASSIFICACAO IMC','PPA_CALCULADA']
ALL_FEATURES=ALL_NUMERIC+ALL_CATEGORICAL+[HISTORY_COLUMN]


def columns(name):
    if name not in REPRESENTATIONS:raise ValueError('Representação desconhecida')
    numeric=['FC'] if name=='clinica' else ALL_NUMERIC.copy()
    categorical=CATEGORICAL_COLUMNS.copy() if name=='continua' else ALL_CATEGORICAL.copy()
    return numeric,categorical


def input_frame(frame):
    data=frame[ALL_FEATURES].copy()
    for c in ALL_NUMERIC:data[c]=pd.to_numeric(data[c],errors='coerce').astype(float)
    for c in ALL_CATEGORICAL+[HISTORY_COLUMN]:data[c]=data[c].astype(object).where(data[c].notna(),np.nan)
    return data


def preprocessor(name):
    numeric,categorical=columns(name)
    return ColumnTransformer([
        ('numericas',Pipeline([('imputar',SimpleImputer(strategy='median',keep_empty_features=True)),
                              ('padronizar',StandardScaler())]),numeric),
        ('ausencias_numericas',MissingIndicator(features='all'),numeric),
        ('categoricas',Pipeline([('ausente',SimpleImputer(strategy='constant',fill_value=MISSING_CATEGORY,keep_empty_features=True)),
                                 ('codificar',OneHotEncoder(handle_unknown='ignore',sparse_output=False))]),categorical),
        ('hda',HistoryEncoder(),[HISTORY_COLUMN]),
    ],remainder='drop')
