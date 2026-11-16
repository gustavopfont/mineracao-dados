"""Consulta checkpoints e estado, sem avaliar dados ou treinar modelos."""
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def status(output):
    path=output/'estado_execucao.json'
    state=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'status':'sem_monitor_background'}
    state['perfis_externos_concluidos']=len(list(output.glob('externo_*/*/*/concluido.json')))
    state['perfis_externos_previstos']=160
    state['perfis_finais_concluidos']=len(list(output.glob('finais/*/*/concluido.json')))
    state['perfis_finais_previstos']=16
    state['teste_aberto']=(output/'teste_aberto.json').exists()
    state['relatorio_pronto']=(output/'manifesto_resultados.json').exists()
    return state


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saida',type=Path,default=ROOT/'resultado_experimentos_reduzido')
    args=parser.parse_args()
    print(json.dumps(status(args.saida),ensure_ascii=False,indent=2))
