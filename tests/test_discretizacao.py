"""Fronteiras OMS e denominadores das descrições contínuas/categóricas."""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from analise_discretizacao import bmi_age_reference, summarize
from classificacao_imc import carregar_referencias, classificar_imc_pediatrico
from classificacao_pa import age_context, classify_pressure, reference
from finalizar_dataset import transform


class BmiBoundaryTest(unittest.TestCase):
    def test_each_cut_both_sexes_both_references(self):
        daily, monthly = carregar_referencias()
        for sex in ['Feminino', 'Masculino']:
            for days in [0, 730, 731, 1856, 1857, math.ceil(228*30.4375)]:
                initial = days <= 1856
                cut = daily.loc[(sex, days)] if initial else monthly.loc[(sex, math.floor(days/30.4375))]
                cases = {
                    'z_menos_3': ['Magreza acentuada', 'Magreza', 'Magreza'],
                    'z_menos_2': ['Magreza', 'Eutrofia', 'Eutrofia'],
                    'z_mais_1': ['Eutrofia', 'Eutrofia', 'Risco de sobrepeso' if initial else 'Sobrepeso'],
                    'z_mais_2': (['Risco de sobrepeso', 'Risco de sobrepeso', 'Sobrepeso'] if initial
                                 else ['Sobrepeso', 'Sobrepeso', 'Obesidade']),
                    'z_mais_3': (['Sobrepeso', 'Sobrepeso', 'Obesidade'] if initial
                                 else ['Obesidade']*3),
                }
                for key, expected in cases.items():
                    for delta, category in zip([-1e-6, 0, 1e-6], expected):
                        with self.subTest(sex=sex, days=days, key=key, delta=delta):
                            result = classificar_imc_pediatrico(days, sex, cut[key]+delta)
                            self.assertEqual(result['classificacao'], category)
                            self.assertIn('2006' if initial else '2007', result['referencia'])

    def test_reference_transitions_and_upper_limit(self):
        self.assertIn('2006', classificar_imc_pediatrico(1856, 'Feminino', 17)['referencia'])
        self.assertIn('2007', classificar_imc_pediatrico(1857, 'Feminino', 17)['referencia'])
        last = math.ceil(229*30.4375)-1
        self.assertEqual(classificar_imc_pediatrico(last, 'Masculino', 20)['idade_referencia'], 228)
        self.assertIsNone(classificar_imc_pediatrico(last+1, 'Masculino', 20)['classificacao'])
        self.assertIn('Fora', bmi_age_reference(last+1))
        for days, sex, value in [(-1, 'Feminino', 17), (10, '', 17),
                                  (10, 'Feminino', float('nan')), (10, 'Feminino', 0)]:
            self.assertIsNone(classificar_imc_pediatrico(days, sex, value)['classificacao'])

    def test_sex_selects_separate_table(self):
        daily, _ = carregar_referencias()
        female = daily.loc[('Feminino', 0), 'z_mais_1']
        male = daily.loc[('Masculino', 0), 'z_mais_1']
        self.assertNotEqual(female, male)
        midpoint = (female+male)/2
        results = {classificar_imc_pediatrico(0, sex, midpoint)['classificacao']
                   for sex in ['Feminino', 'Masculino']}
        self.assertEqual(results, {'Eutrofia', 'Risco de sobrepeso'})


class PressureRevisionTest(unittest.TestCase):
    def test_female_reference_boundary_and_no_extrapolation(self):
        point = reference()[('Feminino', 1)][0]
        for delta, expected in [(-1e-6, 'Pré-hipertensão'), (0, 'HA estágio 1'), (1e-6, 'HA estágio 1')]:
            result = classify_pressure(1, 'Feminino', point['altura_cm'],
                                       point['pas_p95']+delta, 30)
            self.assertEqual(result['classificacao'], expected)
        self.assertIsNone(classify_pressure(1, 'Feminino', point['altura_cm']-.01, 100, 60)['classificacao'])

    def test_anniversaries_change_pressure_reference(self):
        expected = [('2001-05-19', 0), ('2001-05-20', 1),
                    ('2013-05-19', 12), ('2013-05-20', 13),
                    ('2018-05-19', 17), ('2018-05-20', 18)]
        for visit, years in expected:
            context = age_context({'DN': '2000-05-20', 'Atendimento': visit, 'IDADE': 0})
            self.assertEqual(context['idade_anos_completos'], years)
        self.assertEqual(classify_pressure(17, '', None, 135, 85)['classificacao'], 'HA estágio 1')
        self.assertEqual(classify_pressure(18, '', None, 135, 85)['classificacao'], 'Pré-hipertensão')

    def test_height_provenance_does_not_change_classification(self):
        frame = pd.read_csv(ROOT/'resultado_analise/UCMF_limpo.csv', dtype='string').head(4)
        frame['_LINHA_ORIGEM'] = range(len(frame))
        frame['Altura'] = '82.4'
        frame['Atendimento'] = '2005-06-01'
        frame['DN'] = '2004-06-01'
        frame['PA SISTOLICA'] = '100'
        frame['PA DIASTOLICA'] = '50'
        events = pd.DataFrame([{'ID': frame.iloc[0].ID, 'variavel': 'Altura', 'regra': 'sqrt(Peso / IMC) * 100'}])
        original, _, _ = transform(frame)
        final, audit, comparison = transform(frame, events)
        pd.testing.assert_frame_equal(original, final)
        self.assertEqual(comparison.iloc[0].origem_altura, 'recuperada por relação antropométrica')
        self.assertEqual(audit.iloc[1].origem_altura, 'informada na origem')
        self.assertEqual(comparison.iloc[0].formula_altura, 'sqrt(Peso / IMC) * 100')


class SummaryTest(unittest.TestCase):
    def test_missing_denominators_and_ties(self):
        final = pd.DataFrame({
            'ID': ['1', '2', '3', '4'], 'SEXO': ['Feminino']*3+[None],
            'CLASSIFICACAO IMC': ['Eutrofia', 'Sobrepeso', None, None],
            'PPA_CALCULADA': ['Normal', None, 'HA estágio 1', None],
            'IMC': [15, 20, 15, None], 'PA SISTOLICA': [100, 100, 110, None],
            'PA DIASTOLICA': [60, 60, 60, None],
            'NORMAL X ANORMAL': ['Normal', 'Anormal', None, None]})
        bmi = pd.DataFrame({'ID': final.ID, 'idade_dias': [2000]*3+[None]})
        pressure = pd.DataFrame({'ID': final.ID, 'idade_anos_completos': [5]*3+[None]})
        before = final.copy(deep=True)
        tables = summarize(final, bmi, pressure)
        pd.testing.assert_frame_equal(final, before)
        coverage = tables['cobertura_discretizacao.csv']
        for _, groups in coverage.groupby('variavel'):
            self.assertEqual(groups.n_total.sum(), 4)
            self.assertEqual(groups.n_classificados.sum(), 2)
            self.assertEqual(groups.n_ausentes.sum(), 2)
        freq = tables['frequencias_discretizacao.csv']
        for _, group in freq.groupby(['variavel', 'referencia_etaria', 'sexo']):
            self.assertEqual(group.quantidade.sum(), group.n_total_estrato.iloc[0])
            self.assertAlmostEqual(group.percentual_estrato.sum(), 100)
            self.assertAlmostEqual(group.percentual_classificados.sum(),
                                   100 if group.n_classificados_estrato.iloc[0] else 0)
        outcome = tables['alvo_por_categoria_discretizacao.csv']
        self.assertTrue((outcome.n_normal+outcome.n_anormal+outcome.n_alvo_ausente == outcome.n_categoria).all())
        zero = outcome.loc[outcome.n_alvo_conhecido.eq(0)]
        self.assertTrue(zero.percentual_anormal_alvo_conhecido.isna().all())
        quartiles = tables['diagnostico_quantis.csv'].set_index('variavel')
        self.assertEqual(quartiles.loc['PA DIASTOLICA', 'n_intervalos_efetivos'], 0)


if __name__ == '__main__':
    unittest.main()
