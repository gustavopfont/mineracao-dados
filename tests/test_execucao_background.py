import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from subprocess import CompletedProcess

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from executar_experimentos_background import execute
from status_experimentos import status


class BackgroundTest(unittest.TestCase):
    def test_state_logs_and_no_duplicate_launcher(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            with patch('executar_experimentos_background.subprocess.run',return_value=CompletedProcess([],0)) as run:
                self.assertEqual(execute(out,ROOT/'config/config_experimentos.json',ROOT/'dummy.csv'),0)
                self.assertEqual(run.call_args.kwargs['env']['PYTHONIOENCODING'],'utf-8')
            self.assertEqual(status(out)['status'],'concluida')
            self.assertFalse((out/'execucao_background.lock').exists())
            (out/'execucao_background.lock').touch()
            with self.assertRaises(FileExistsError):execute(out,'config.json','source.csv')

    def test_failure_is_reported_without_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            with patch('executar_experimentos_background.subprocess.run',return_value=CompletedProcess([],1)):
                self.assertEqual(execute(out,'config.json','source.csv'),1)
            self.assertEqual(status(out)['status'],'falhou')
            self.assertFalse(status(out)['relatorio_pronto'])
            self.assertFalse(status(out)['teste_aberto'])


if __name__=='__main__':unittest.main()
