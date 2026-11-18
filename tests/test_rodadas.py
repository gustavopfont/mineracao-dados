"""Rodadas adicionais: candidatos, validação de configuração e consolidação; sem abrir o teste."""
import json
from pathlib import Path
import sys
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from rodadas_experimentos import (build_candidates, validate_round, load_rounds, v3_reference,
                                  md_table, V3_ID)
from modelos_ucmf import MODEL_ORDER, SPACES
from sklearn.model_selection import ParameterGrid


def round_config(**changes):
    base = dict(id='teste_rodada',descricao='x',outer_folds=5,outer_seeds=[1,2],inner_folds=3,
                candidates_per_family=12,incluir_candidatos_v3=True,candidate_seed=7,
                minimum_specificity=.8,n_jobs=2)
    base.update(changes)
    return base


class RodadasTest(unittest.TestCase):
    def test_config_versionada_valida(self):
        rounds = load_rounds(ROOT/'config_rodadas.json')
        self.assertTrue(rounds)
        self.assertEqual(len({r['id'] for r in rounds}),len(rounds))

    def test_validacao_rejeita_configuracoes_invalidas(self):
        for bad in [dict(id=V3_ID),dict(id='Maiuscula'),dict(outer_folds=1),dict(outer_seeds=[1,1]),
                    dict(candidates_per_family=0),dict(minimum_specificity=1),dict(n_jobs=0),
                    dict(espacos={'inexistente':{}})]:
            with self.assertRaises(ValueError,msg=bad):
                validate_round(round_config(**bad))

    def test_candidatos_incluem_v3_sem_repeticao(self):
        reference,_ = v3_reference()
        result,notes = build_candidates(round_config(),reference)
        self.assertEqual(result['dummy'],[{}])
        for name in MODEL_ORDER:
            grid = list(ParameterGrid(SPACES[name]))
            self.assertEqual(result[name][:4],reference[name])
            self.assertEqual(len(result[name]),min(12,len(grid)))
            self.assertEqual(len({json.dumps(p,sort_keys=True) for p in result[name]}),len(result[name]))
            self.assertTrue(all(p in grid for p in result[name]))
        self.assertTrue(notes['logistica']['grade_completa'])

    def test_candidatos_reprodutiveis_e_dependem_da_semente(self):
        reference,_ = v3_reference()
        a,_ = build_candidates(round_config(),reference)
        b,_ = build_candidates(round_config(),reference)
        c,_ = build_candidates(round_config(candidate_seed=8),reference)
        self.assertEqual(a,b)
        self.assertNotEqual(a['floresta'],c['floresta'])

    def test_sem_v3_sorteia_na_grade_inteira(self):
        reference,_ = v3_reference()
        result,notes = build_candidates(round_config(incluir_candidatos_v3=False,candidates_per_family=3),reference)
        self.assertTrue(all(len(result[n])==3 for n in MODEL_ORDER))
        self.assertEqual(notes['arvore']['candidatos'],3)

    def test_tabela_markdown_trata_ausentes(self):
        table = pd.DataFrame(dict(a=['x'],b=[None],c=[0.123456]))
        text = md_table(table,['a','b','c'])
        self.assertIn('| x | — | 0.1235 |',text)


if __name__=='__main__':
    unittest.main()
