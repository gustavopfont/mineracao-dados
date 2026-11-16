"""Execução completa local, com logs, exclusão mútua e estado final."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def save(path,value):
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(path)


def execute(output,config,source,groups=None):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    lock=output/'execucao_background.lock'
    descriptor=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(descriptor)
    state=dict(status='em_execucao',pid=os.getpid(),inicio_utc=datetime.now(timezone.utc).isoformat())
    command=[sys.executable,'-u',str(ROOT/'scripts/treinar_modelos.py'),'--fase','todos',
             '--saida',str(output),'--config',str(config),'--entrada',str(source)]
    if groups:command+=['--grupos',str(groups)]
    state['command']=command;destination=output/'estado_execucao.json'
    try:
        save(destination,state)
        environment=os.environ.copy();environment['PYTHONIOENCODING']='utf-8'
        with (output/'execucao_stdout.log').open('a',encoding='utf-8') as stdout, (output/'execucao_stderr.log').open('a',encoding='utf-8') as stderr:
            result=subprocess.run(command,cwd=ROOT,stdout=stdout,stderr=stderr,
                                  env=environment,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        state.update(status='concluida' if result.returncode==0 else 'falhou',returncode=result.returncode,
                     fim_utc=datetime.now(timezone.utc).isoformat())
        save(destination,state)
        return result.returncode
    except BaseException as error:
        state.update(status='interrompida',error=str(error),fim_utc=datetime.now(timezone.utc).isoformat())
        save(destination,state)
        raise
    finally:lock.unlink()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saida',type=Path,default=ROOT/'resultado_experimentos_reduzido')
    parser.add_argument('--config',type=Path,default=ROOT/'config_experimentos.json')
    parser.add_argument('--entrada',type=Path,default=ROOT/'resultado_modelagem_preparo/UCMF_supervisionado.csv')
    parser.add_argument('--grupos',type=Path)
    args=parser.parse_args()
    raise SystemExit(execute(args.saida,args.config,args.entrada,args.grupos))
