"""Deduplicação, quarentena e rastreabilidade antes da modelagem."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from finalizar_dataset import FINAL_COLUMNS
from preparar_modelagem import TARGET, FEATURE_COLUMNS
from auditar_base_modelagem import normalize, prepare, run, digest


def fixture():
    row = dict.fromkeys(FINAL_COLUMNS, pd.NA)
    row.update({'ID': '1', 'SEXO': 'Feminino', 'IDADE': 5, 'Peso': 20, 'Altura': 110,
                'IMC': 16.53, 'FC': 90, 'PA SISTOLICA': 100, 'PA DIASTOLICA': 60,
                'PULSOS': 'Normais', 'B2': 'Normal', 'HDA_UNIFICADA': 'Dispneia',
                'MOTIVO_UNIFICADO': 'Check-up', TARGET: 'Normal'})
    return row


class AdequacaoTest(unittest.TestCase):
    def test_dedup_menor_id_conflitos_integrais_e_sem_alvo(self):
        rows = []
        for identifier, weight, target in [('10',20,'Normal'), ('2',20,'Normal'),
                                           ('3',21,'Normal'), ('4',21,'Anormal'),
                                           ('5',22,None), ('6',23,'Anormal')]:
            row = fixture(); row.update(ID=identifier, Peso=weight); row[TARGET] = target
            rows.append(row)
        result = prepare(pd.DataFrame(rows))
        self.assertEqual(set(result['supervised'].ID), {'2', '6'})
        self.assertEqual(set(result['conflicts'].ID), {'3', '4'})
        self.assertEqual(list(result['unlabeled'].ID), ['5'])
        m = result['mapping'].set_index('ID')
        self.assertEqual(m.at['10', 'ID_representante'], '2')
        self.assertEqual(m.at['10', 'destino'], 'duplicata')
        self.assertEqual(len(m), len(rows))
        self.assertEqual(list(result['complementary'].ID), list(result['supervised'].ID))

    def test_inconsistencias_nao_excluem_linha_e_preservam_original(self):
        a = fixture(); a.update({'HDA_UNIFICADA': 'Assintomático | Palpitação', 'FC': float('inf'), 'B2': 'inexistente'})
        frame = pd.DataFrame([a]); before = frame.copy(deep=True)
        clean, events = normalize(frame)
        pd.testing.assert_frame_equal(frame, before)
        for column in ['HDA_UNIFICADA', 'FC', 'B2']:
            self.assertTrue(pd.isna(clean.at[0, column]))
        self.assertEqual(len(events), 3)
        self.assertEqual(clean.at[0, TARGET], 'Normal')

    def test_duplicatas_reavaliadas_apos_correcoes(self):
        a, b, c = fixture(), fixture(), fixture()
        a.update(ID='1', FC=0); b.update(ID='2', FC=None)
        c['ID'] = '3'; c[TARGET] = 'Anormal'
        result = prepare(pd.DataFrame([a,b,c]))
        self.assertEqual(set(result['supervised'].ID), {'1','3'})

    def test_ids_e_alvo_invalidos_falham_sem_inferencia(self):
        a = fixture(); a[TARGET] = 'Talvez'
        with self.assertRaises(ValueError):
            prepare(pd.DataFrame([a]))
        a = fixture()
        with self.assertRaises(ValueError):
            prepare(pd.DataFrame([a,a]))

    def test_integracao_real_preserva_fontes_e_reproduz(self):
        source = ROOT/'resultados/analise/UCMF_base_final.csv'
        paths = [source, ROOT/'dados/UCMF_raw.csv', ROOT/'resultados/analise/UCMF_limpo.csv']
        paths += [p for folder in ['referencias','resultados/modelagem_legada'] for p in (ROOT/folder).iterdir() if p.is_file()]
        before = {str(p): digest(p) for p in paths}
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            run(source, out)
            first = json.loads((out/'manifesto_adequacao.json').read_text(encoding='utf-8'))
            frame = pd.read_csv(out/'UCMF_supervisionado.csv')
            mapping = pd.read_csv(out/'rastreabilidade.csv')
            self.assertEqual(len(mapping), 12134)
            self.assertTrue(mapping.ID.is_unique)
            self.assertEqual(sum(first['destinos'].values()), 12134)
            self.assertFalse(frame[FEATURE_COLUMNS].duplicated().any())
            self.assertFalse(set(frame.ID) & set(pd.read_csv(out/'conflitos_alvo.csv').ID))
            self.assertEqual(first['destinos']['sem_alvo'], 429)
            self.assertEqual(first['destinos']['conflito'], 142)
            self.assertEqual(first['destinos']['duplicata'], 127)
            self.assertEqual(len(frame), 11436)
            run(source, out)
            second = json.loads((out/'manifesto_adequacao.json').read_text(encoding='utf-8'))
            self.assertEqual(first['saidas_sha256'], second['saidas_sha256'])
            self.assertFalse(any(out.glob('*.joblib')))
            self.assertFalse((out/'divisao_treino_teste.csv').exists())
        self.assertEqual(before, {str(p): digest(p) for p in paths})


if __name__ == '__main__':
    unittest.main()
