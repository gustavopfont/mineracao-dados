"""Contrato atual e transformações ajustadas só em dados sintéticos de treino."""
import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.base import clone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from preparar_modelagem import (NUMERIC_COLUMNS, CATEGORICAL_COLUMNS, FEATURE_COLUMNS,
    HistoryEncoder, SYMPTOMS, build_preprocessor, duplicate_groups, fit_on_train, row_features)


def records(ages):
    f = pd.DataFrame({c: [10.0]*len(ages) for c in NUMERIC_COLUMNS})
    f['IDADE'] = ages
    for c in CATEGORICAL_COLUMNS:
        f[c] = 'Categoria clínica'
    f['HDA_UNIFICADA'] = 'Dispneia'
    return f


class PreparoModelagemTest(unittest.TestCase):
    def test_fit_apenas_no_treino_e_categorias_ineditas(self):
        train, test = records([2, 4, np.nan]), records([100])
        test['MOTIVO_UNIFICADO'] = 'Categoria inédita'
        transformer, a, b = fit_on_train(train, test)
        median = transformer.named_transformers_['numericas'].named_steps['imputar'].statistics_[0]
        self.assertEqual(median, 3)
        self.assertEqual(a.shape[1], b.shape[1])
        self.assertTrue(np.isfinite(b).all())

    def test_colunas_vazias_e_faltante_novo_tem_dimensao_estavel(self):
        train, test = records([2, 4]), records([np.nan])
        train['Peso'] = np.nan
        test['Peso'] = 20.0
        train['B2'] = np.nan
        test['B2'] = 'Normal'
        transformer, a, b = fit_on_train(train, test)
        self.assertEqual(a.shape[1], b.shape[1])
        self.assertTrue(np.isfinite(a).all())
        self.assertTrue(np.isfinite(b).all())
        indicator = transformer.named_transformers_['ausencias_numericas'].transform(row_features(test)[NUMERIC_COLUMNS])
        self.assertEqual(indicator[0, 0], 1)
        self.assertIn('numericas__Peso', transformer.get_feature_names_out())

    def test_pipeline_clonavel_e_contrato_sem_identificador_alvo_sopro(self):
        transformer = clone(build_preprocessor())
        self.assertFalse(hasattr(transformer, 'transformers_'))
        f = records([2, 4]); f['ID'] = ['1', '2']; f['NORMAL X ANORMAL'] = 'Normal'; f['SOPRO'] = 'Sistólico'
        self.assertEqual(list(row_features(f)), FEATURE_COLUMNS)
        with self.assertRaises(ValueError):
            build_preprocessor([], ['SOPRO'])
        with self.assertRaises(ValueError):
            build_preprocessor(['ID'], [])

    def test_hda_multiplas_mencoes_ausente_outro_e_inedito(self):
        encoder = HistoryEncoder().fit([['Dispneia']])
        a = encoder.transform([['Palpitação | Dispneia'], [np.nan], ['Outro'], ['Sintoma novo'], ['Assintomático']])
        self.assertEqual(a[0, SYMPTOMS.index('Palpitação')], 1)
        self.assertEqual(a[0, SYMPTOMS.index('Dispneia')], 1)
        self.assertEqual(a[1, -2], 1)
        self.assertEqual(a[3, -1], 1)
        self.assertFalse(np.array_equal(a[1], a[2]))
        self.assertEqual(a[4, SYMPTOMS.index('Assintomático')], 1)

    def test_grupos_comparam_valores_completos_sem_id_alvo(self):
        f = pd.DataFrame({'ID': ['1','2','3'], 'X': [np.nan,np.nan,'<ausente>'],
                          'NORMAL X ANORMAL': ['Normal','Anormal','Normal']})
        g = duplicate_groups(f)
        self.assertEqual(g[0], g[1])
        self.assertNotEqual(g[0], g[2])

    def test_indeterminado_e_faltante_permanecem_distintos(self):
        train = records([1, 2, 3])
        train['SEXO'] = ['Indeterminado', np.nan, 'Outro']
        transformer, a, _ = fit_on_train(train, train)
        self.assertFalse(np.array_equal(a[0], a[1]))
        names = transformer.get_feature_names_out()
        self.assertTrue(any('SEXO___SEM_INFORMACAO__' in name for name in names))
        self.assertTrue(any('SEXO_Indeterminado' in name for name in names))


if __name__ == '__main__':
    unittest.main()
