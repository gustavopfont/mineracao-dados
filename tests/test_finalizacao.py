"""Limites clínicos, preservação da referência e transformações sem alvo."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from classificacao_pa import age_context, classify_pressure, pediatric_thresholds, reference
from finalizar_dataset import (FINAL_COLUMNS, TARGET, checksum, merge_history,
                              merge_reasons, run, transform)


class PressureTest(unittest.TestCase):
    def test_anniversaries_override_rounded_age(self):
        for year, before_band, after_band in [(2001, 'Menor de 1 ano', '1–2 anos'),
                                              (2013, '6–12 anos', '13–17 anos'),
                                              (2018, '13–17 anos', '18–19 anos')]:
            row = {'DN': '2000-05-20', 'Atendimento': f'{year}-05-19', 'IDADE': year-2000}
            self.assertEqual(age_context(row)['faixa_etaria'], before_band)
            row['Atendimento'] = f'{year}-05-20'
            self.assertEqual(age_context(row)['faixa_etaria'], after_band)

    def test_fallback_and_invalid_dates(self):
        self.assertEqual(age_context({'DN': 'inválida', 'IDADE': '12.99'})['idade_anos_completos'], 12)
        self.assertEqual(age_context({'DN': '2020-01-01', 'Atendimento': '2010-01-01',
                                      'IDADE': 3})['origem_idade'], 'IDADE disponível')
        self.assertIsNone(age_context({'IDADE': 20})['faixa_etaria'])

    def test_reference_and_interpolation(self):
        self.assertEqual(len(reference()), 24)
        point = pediatric_thresholds(1, 'Masculino', 77.2)
        self.assertEqual(point, dict(pas_p90=98, pas_p95=102, pad_p90=52, pad_p95=54))
        self.assertAlmostEqual(pediatric_thresholds(1, 'Masculino', 77.75)['pas_p90'], 98.5)
        self.assertIsNone(pediatric_thresholds(1, 'Masculino', 77.19))
        self.assertIsNone(pediatric_thresholds(1, 'Masculino', 87.91))

    def test_pediatric_boundaries_and_worst_component(self):
        for pas, pad, expected in [(97, 51, 'Normal'), (98, 51, 'Pré-hipertensão'),
                                    (101.99, 51, 'Pré-hipertensão'), (102, 51, 'HA estágio 1'),
                                    (113.99, 51, 'HA estágio 1'), (114, 51, 'HA estágio 2'),
                                    (97, 54, 'HA estágio 1'), (97, 66, 'HA estágio 2')]:
            with self.subTest(pas=pas, pad=pad):
                self.assertEqual(classify_pressure(1, 'Masculino', 77.2, pas, pad)['classificacao'], expected)

    def test_absolute_caps(self):
        points = reference()[('Masculino', 12)]
        result = classify_pressure(12, 'Masculino', points[-1]['altura_cm'], 130, 79)
        self.assertLessEqual(result['pas_estagio1'], 130)
        self.assertLessEqual(result['pad_estagio1'], 80)
        self.assertEqual(result['classificacao'], 'HA estágio 1')

    def test_adolescent_boundaries(self):
        for pas, pad, expected in [(119, 79, 'Normal'), (120, 79, 'Pré-hipertensão'),
                                    (129.99, 79, 'Pré-hipertensão'), (130, 79, 'HA estágio 1'),
                                    (110, 80, 'HA estágio 1'), (139.99, 89.99, 'HA estágio 1'),
                                    (140, 79, 'HA estágio 2'), (110, 90, 'HA estágio 2')]:
            with self.subTest(pas=pas, pad=pad):
                self.assertEqual(classify_pressure(13, '', None, pas, pad)['classificacao'], expected)

    def test_adult_transition_and_boundaries(self):
        for pas, pad, expected in [(119, 79, 'Normal'), (120, 79, 'Pré-hipertensão'),
                                    (130, 80, 'Pré-hipertensão'), (140, 79, 'HA estágio 1'),
                                    (110, 90, 'HA estágio 1'), (160, 79, 'HA estágio 2'),
                                    (120, 100, 'HA estágio 2'), (180, 79, 'HA estágio 3'),
                                    (120, 110, 'HA estágio 3')]:
            with self.subTest(pas=pas, pad=pad):
                self.assertEqual(classify_pressure(18, '', None, pas, pad)['classificacao'], expected)

    def test_insufficient_or_contradictory_inputs(self):
        for args in [(None, '', None, 100, 60), (0, 'Masculino', 60, 100, 60),
                     (1, '', 77.2, 100, 60), (1, 'Masculino', None, 100, 60),
                     (1, 'Masculino', 30, 100, 60), (13, '', None, None, 60),
                     (13, '', None, 100, None), (13, '', None, 100, 100),
                     (13, '', None, 260, 60)]:
            with self.subTest(args=args):
                self.assertIsNone(classify_pressure(*args)['classificacao'])


class MergeTest(unittest.TestCase):
    def test_reasons_preserve_conflicting_prefixes_and_murmur(self):
        merged, conflict = merge_reasons('5 - Parecer cardiológico', '6 - Sopro')
        self.assertEqual(merged, '5 - Parecer cardiológico → 6 - Sopro')
        self.assertTrue(conflict)
        self.assertEqual(merge_reasons('2 - Check-up', pd.NA), ('2 - Check-up', False))
        self.assertEqual(merge_reasons(pd.NA, pd.NA), (None, False))

    def test_history_symptoms_duplicates_and_missing(self):
        self.assertEqual(merge_history(pd.NA, 'Dispneia'), ('Dispneia', False))
        self.assertEqual(merge_history('Palpitacao', 'Palpitacao'), ('Palpitação', False))
        self.assertEqual(merge_history('Dispneia', 'Palpitacao'), ('Palpitação | Dispneia', False))
        self.assertEqual(merge_history('Assintomático', 'Cianose'), ('Assintomático | Cianose', True))
        self.assertEqual(merge_history(pd.NA, pd.NA), (None, False))


class FinalBaseTest(unittest.TestCase):
    def test_final_preserves_ids_target_and_clinical_fields(self):
        original = pd.read_csv(ROOT/'resultados/analise/UCMF_limpo.csv', dtype='string')
        frame = original.copy()
        frame['_LINHA_ORIGEM'] = range(len(frame))
        result, audit, comparison = transform(frame)
        self.assertEqual(list(result), FINAL_COLUMNS)
        self.assertEqual(list(result.ID), list(original.ID))
        pd.testing.assert_series_equal(result[TARGET], original[TARGET])
        for c in ['Peso', 'Altura', 'IMC', 'IDADE', 'FC', 'B2', 'PULSOS',
                  'PA SISTOLICA', 'PA DIASTOLICA', 'CLASSIFICACAO IMC']:
            pd.testing.assert_series_equal(result[c], original[c])
        self.assertEqual(len(result), 12134)
        self.assertEqual(result[TARGET].isna().sum(), 429)
        self.assertEqual(audit.prefixos_motivo_divergentes.sum(), 230)
        self.assertTrue(result.MOTIVO_UNIFICADO.str.contains('Sopro', na=False).any())
        self.assertEqual(len(comparison), len(result))

    def test_derivations_do_not_consult_target_or_murmur(self):
        frame = pd.read_csv(ROOT/'resultados/analise/UCMF_limpo.csv', dtype='string').head(40)
        frame['_LINHA_ORIGEM'] = range(len(frame))
        before, _, _ = transform(frame)
        frame[TARGET] = 'Normal'
        frame['SOPRO'] = pd.NA
        after, _, _ = transform(frame)
        pd.testing.assert_frame_equal(before.drop(columns=TARGET), after.drop(columns=TARGET))

    def test_reproducible_generation_preserves_sources(self):
        paths = [ROOT/'dados/UCMF_raw.csv', ROOT/'resultados/analise/UCMF_limpo.csv']
        paths += sorted(p for p in (ROOT/'resultados/modelagem_legada').iterdir() if p.is_file())
        paths += sorted((ROOT/'referencias').glob('*.csv'))
        current_final = ROOT/'resultados/analise/UCMF_base_final.csv'
        original_final_hash = checksum(current_final)
        before = {str(p): checksum(p) for p in paths}
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            run(paths[0], paths[1], output)
            manifest = json.loads((output/'manifesto_base_final.json').read_text(encoding='utf-8'))
            first = manifest['saidas_sha256']
            self.assertEqual(first['UCMF_base_final.csv'], original_final_hash)
            coverage = pd.read_csv(output/'cobertura_discretizacao.csv')
            for _, groups in coverage.groupby('variavel'):
                self.assertEqual(groups.n_total.sum(), 12134)
            run(paths[0], paths[1], output)
            second = json.loads((output/'manifesto_base_final.json').read_text(encoding='utf-8'))
            self.assertEqual(first, second['saidas_sha256'])
        self.assertEqual(before, {str(p): checksum(p) for p in paths})


if __name__ == '__main__':
    unittest.main()
