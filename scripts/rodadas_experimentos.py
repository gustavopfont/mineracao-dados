"""Rodadas adicionais de comparação UCMF, somente no desenvolvimento.

Cada rodada (config/config_rodadas.json) usa outros folds externos e/ou outro orçamento de
hiperparâmetros, reaproveita a população de desenvolvimento da v3 e NUNCA abre o teste
reservado. Os resultados são gravados fold a fold (retomável) e consolidados junto
com a v3 em resultados/experimentos/rodadas/consolidado/.
As configurações efetivas e os limites constam no relatório de cada rodada.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd
from sklearn.model_selection import ParameterGrid

from preparar_modelagem import ROOT
from modelos_ucmf import ALL_MODELS, MODEL_ORDER, SPACES, candidates
from metricas_modelagem import five_by_two, holm
from representacoes_ucmf import REPRESENTATIONS
from treinar_modelos import (load_frame, folds, save_folds, fit_representations, table_metrics,
                             read_json, write_json, sha, versions)

RODADAS_DIR = ROOT/'resultados/experimentos/rodadas'
V3_DIR = ROOT/'resultados/experimentos/v3'
V3_ID = 'v3_5x2_4cand'
INVENTARIO = ROOT/'referencias/inventario_experimentos.json'
CODE = ['rodadas_experimentos.py','treinar_modelos.py','modelos_ucmf.py','metricas_modelagem.py',
        'preparar_modelagem.py','representacoes_ucmf.py']
MODES = ['aprendido','padrao_0.5']
NUMERIC = ['accuracy','recall','specificity','precision','f1','f2','balanced_accuracy','roc_auc','ap','brier','error']


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def validate_round(rc):
    required = ['id','descricao','outer_folds','outer_seeds','inner_folds','candidates_per_family',
                'incluir_candidatos_v3','candidate_seed','minimum_specificity','n_jobs']
    missing = [k for k in required if k not in rc]
    if missing:
        raise ValueError(f'Rodada sem campos: {missing}')
    if not re.fullmatch(r'[a-z0-9_]+',rc['id']) or rc['id']==V3_ID or rc['id']=='consolidado':
        raise ValueError('Identificador inválido ou reservado (use letras minúsculas, dígitos e _)')
    ints = lambda v,low:isinstance(v,int) and not isinstance(v,bool) and v>=low
    if not ints(rc['outer_folds'],2) or not ints(rc['inner_folds'],2) or not ints(rc['candidates_per_family'],1):
        raise ValueError('Folds externos/internos (≥2) e candidatos (≥1) devem ser inteiros')
    seeds = rc['outer_seeds']
    if not isinstance(seeds,list) or not seeds or len(set(seeds))!=len(seeds) or not all(ints(s,0) for s in seeds):
        raise ValueError('outer_seeds exige lista não vazia de inteiros distintos')
    if not 0 < rc['minimum_specificity'] < 1 or not ints(rc['n_jobs'],1) or rc['n_jobs']>12:
        raise ValueError('Especificidade mínima em (0,1) e n_jobs entre 1 e 12')
    unknown = set(rc.get('espacos',{}))-set(MODEL_ORDER)
    if unknown:
        raise ValueError(f'Famílias desconhecidas em espacos: {sorted(unknown)}')
    return rc


def load_rounds(path):
    rounds = [validate_round(r) for r in read_json(path)['rodadas']]
    if len({r['id'] for r in rounds}) != len(rounds):
        raise ValueError('Identificadores de rodada repetidos')
    return rounds


def v3_reference():
    """Candidatos e hash da partição da v3, conferidos contra o código atual."""
    run = next(e for e in read_json(INVENTARIO)['execucoes'] if e['diretorio_local']=='resultado_experimentos_reduzido')
    reference = run['candidatos_por_familia']
    if reference != json.loads(json.dumps(candidates(42,4))):
        raise ValueError('Grade atual não reproduz os candidatos da v3: inventário e código divergem')
    return reference, run['sha256_particao']


def build_candidates(rc, reference):
    """Candidatos da rodada: (opcional) os da v3 primeiro, depois sorteio sem reposição na grade."""
    spaces = {**SPACES, **rc.get('espacos',{})}
    result = {'dummy':[{}]}
    notes = {}
    for i,name in enumerate(MODEL_ORDER):
        grid = list(ParameterGrid(spaces[name]))
        want = min(rc['candidates_per_family'],len(grid))
        chosen = [p for p in reference[name] if p in grid][:want] if rc['incluir_candidatos_v3'] else []
        remaining = [p for p in grid if p not in chosen]
        need = want-len(chosen)
        if need > 0:
            picks = np.random.default_rng(rc['candidate_seed']+i).choice(len(remaining),need,replace=False)
            chosen += [remaining[int(j)] for j in picks]
        if len({json.dumps(p,sort_keys=True) for p in chosen}) != len(chosen):
            raise ValueError(f'Candidatos repetidos em {name}')
        result[name] = chosen
        notes[name] = dict(grade=len(grid),candidatos=len(chosen),
                           grade_completa=len(chosen)==len(grid),
                           da_v3=sum(p in reference[name] for p in chosen))
    return result, notes


def load_development(source, partition_sha):
    """População de desenvolvimento da v3; as linhas de teste são descartadas aqui."""
    path = V3_DIR/'particao_principal.csv'
    if sha(path) != partition_sha:
        raise ValueError('particao_principal.csv da v3 difere do inventário')
    frame = load_frame(source)
    assignment = pd.read_csv(path,dtype={'ID':'string','group_id':'string'})
    if list(assignment.ID) != list(frame.ID):
        raise ValueError('IDs da base supervisionada divergem da partição da v3')
    return frame.loc[assignment.conjunto.eq('desenvolvimento').to_numpy()].reset_index(drop=True)


def initialize_round(rc, source, folder, reference, partition_sha):
    candidate_lists, notes = build_candidates(rc,reference)
    signature = dict(data_sha256=sha(source),complementary_sha256=sha(Path(source).with_name('atributos_complementares.csv')),
                     partition_sha256=partition_sha,round=rc,code_sha256={p:sha(ROOT/'scripts'/p) for p in CODE},
                     versions=versions())
    folder.mkdir(parents=True,exist_ok=True)
    path = folder/'protocolo.json'
    if path.exists():
        state = read_json(path)
        if state['inputs'] != signature:
            raise ValueError('Dados/código/configuração/ambiente mudaram: criar uma nova rodada com outro id')
        return state
    allowed = {'rodada.lock','estado_rodada.json','execucao_stdout.log','execucao_stderr.log'}
    if any(p.name not in allowed for p in folder.iterdir()):
        raise ValueError('Diretório da rodada não vazio e sem protocolo; exige revisão manual')
    state = dict(inputs=signature,config=dict(n_jobs=rc['n_jobs'],minimum_specificity=rc['minimum_specificity']),
                 candidates=candidate_lists,candidates_notes=notes,criado_em=now(),
                 observacao='Somente desenvolvimento da v3; teste reservado não é carregado nem avaliado.')
    write_json(path,state)
    return state


def fold_done(fold_dir):
    return all((fold_dir/m/'concluido.json').exists() for m in ALL_MODELS)


def collect(folder, rc):
    """Lê somente folds externos completos e monta as tabelas da rodada."""
    external,by_rep,hyper,done = [],[],[],[]
    for repeat in range(len(rc['outer_seeds'])):
        for fold in range(rc['outer_folds']):
            fold_dir = folder/f'externo_r{repeat}_f{fold}'
            if not fold_done(fold_dir):
                continue
            done.append((repeat,fold))
            for name in ALL_MODELS:
                chosen = read_json(fold_dir/name/'concluido.json')
                for representation in (['continua'] if name=='dummy' else REPRESENTATIONS):
                    sub = fold_dir/name/representation
                    info = read_json(sub/'concluido.json')
                    if sha(sub/'previsoes_externas.csv') != info['prediction_sha256']:
                        raise ValueError(f'Previsões modificadas: {sub}')
                    table = pd.read_csv(sub/'previsoes_externas.csv',float_precision='round_trip')
                    for mode in MODES:
                        by_rep.append(dict(rodada=rc['id'],model=name,representation=representation,repeat=repeat,
                                           fold=fold,mode=mode,**table_metrics(table,mode)))
                    hyper.append(dict(rodada=rc['id'],model=name,representation=representation,repeat=repeat,fold=fold,
                                      escolhida_no_procedimento=representation==chosen['representation'],
                                      candidato=info['selected_candidate'],
                                      parametros=json.dumps(info['params'],ensure_ascii=False,sort_keys=True),
                                      ap_interna=info['inner_ap'],limiar=info['threshold_info']['threshold'],
                                      recall_interno=info['threshold_info']['recall'],
                                      especificidade_interna=info['threshold_info']['specificity'],segundos=info['seconds']))
                table = pd.read_csv(fold_dir/name/'previsoes_externas.csv',float_precision='round_trip')
                if sha(fold_dir/name/'previsoes_externas.csv') != chosen['prediction_sha256']:
                    raise ValueError('Previsões externas modificadas')
                for mode in MODES:
                    external.append(dict(rodada=rc['id'],model=name,representation=chosen['representation'],repeat=repeat,
                                         fold=fold,mode=mode,seconds=chosen['seconds'],threshold=chosen['threshold_info']['threshold'],
                                         **table_metrics(table,mode)))
    return pd.DataFrame(external),pd.DataFrame(by_rep),pd.DataFrame(hyper),done


def pooled_repeats(folder, rc, done):
    """Métricas por repetição, agregando as previsões fora do treino dos k folds."""
    rows = []
    for repeat in range(len(rc['outer_seeds'])):
        if not all((repeat,f) in done for f in range(rc['outer_folds'])):
            continue
        for name in ALL_MODELS:
            table = pd.concat([pd.read_csv(folder/f'externo_r{repeat}_f{f}'/name/'previsoes_externas.csv',
                                           float_precision='round_trip') for f in range(rc['outer_folds'])],ignore_index=True)
            if table.ID.duplicated().any():
                raise ValueError('Uma repetição externa não é OOF')
            for mode in MODES:
                rows.append(dict(rodada=rc['id'],model=name,repeat=repeat,mode=mode,**table_metrics(table,mode)))
    return pd.DataFrame(rows)


def summarize(external, pooled, rc):
    rows = []
    for name in ALL_MODELS:
        e = external.loc[external.model.eq(name)&external['mode'].eq('aprendido')]
        p = pooled.loc[pooled.model.eq(name)&pooled['mode'].eq('aprendido')] if len(pooled) else pooled
        rows.append(dict(rodada=rc['id'],model=name,folds=len(e),
                         recall_media=e.recall.mean(),recall_dp=e.recall.std(),
                         especificidade_media=e.specificity.mean(),especificidade_dp=e.specificity.std(),
                         ap_media=e.ap.mean(),brier_media=e.brier.mean(),segundos_medios=e.seconds.mean(),
                         folds_abaixo_da_meta=int((e.specificity<rc['minimum_specificity']).sum()),
                         repeticoes_agregadas=len(p),
                         recall_agregado=p.recall.mean() if len(p) else np.nan,
                         especificidade_agregada=p.specificity.mean() if len(p) else np.nan,
                         ap_agregada=p.ap.mean() if len(p) else np.nan))
    return pd.DataFrame(rows)


def md_table(table, columns, digits=4):
    head = '| '+' | '.join(columns)+' |\n| '+' | '.join('---' for _ in columns)+' |'
    body = []
    for _,row in table.iterrows():
        cells = [f'{row[c]:.{digits}f}' if isinstance(row[c],(float,np.floating)) and pd.notna(row[c])
                 else ('—' if pd.isna(row[c]) else str(row[c])) for c in columns]
        body.append('| '+' | '.join(cells)+' |')
    return '\n'.join([head]+body)


def round_report(folder, rc, state, summary, hyper, by_rep, done):
    total = len(rc['outer_seeds'])*rc['outer_folds']
    complete = len(done)==total
    notes = pd.DataFrame([dict(familia=k,grade=v['grade'],candidatos=v['candidatos'],da_v3=v['da_v3'],
                               grade_completa='sim' if v['grade_completa'] else 'não') for k,v in state['candidates_notes'].items()])
    rep = (by_rep.loc[by_rep['mode'].eq('aprendido')].groupby(['model','representation'])[['recall','specificity','ap']]
           .mean().reset_index())
    chosen = hyper.loc[hyper.escolhida_no_procedimento].groupby(['model','representation']).size().reset_index(name='folds_em_que_foi_escolhida')
    params = (hyper.loc[hyper.escolhida_no_procedimento].groupby(['model','parametros']).size()
              .reset_index(name='folds').sort_values(['model','folds'],ascending=[True,False]))
    text = f"""# Rodada {rc['id']} — resultado técnico

{rc['descricao']}

Estado: **{'concluída' if complete else 'parcial'}** — {len(done)} de {total} folds externos completos. Classe positiva: **Anormal = 1**. Gerado em {now()}.

## Desenho

| Item | Valor |
| --- | --- |
| População | Desenvolvimento da v3 (9.148 registros). O teste reservado não é carregado, avaliado nem usado para escolher nada. |
| Validação externa | {rc['outer_folds']} folds × {len(rc['outer_seeds'])} repetições (sementes {rc['outer_seeds']}) |
| Tuning interno | {rc['inner_folds']} folds; semente interna = semente externa × 10 + índice do fold |
| Candidatos por família/perfil | {rc['candidates_per_family']} (sorteio sem reposição, semente {rc['candidate_seed']}; v3 incluídos primeiro: {'sim' if rc['incluir_candidatos_v3'] else 'não'}) |
| Seleção | AP interna escolhe candidato e perfil; limiar de maior recall com especificidade interna ≥ {rc['minimum_specificity']:.0%} |
| Execução | {rc['n_jobs']} processos; pipelines, cache e previsões por fold ficam locais |

{md_table(notes,['familia','grade','candidatos','da_v3','grade_completa'])}

## Desenvolvimento: média dos folds externos (limiar aprendido)

{md_table(summary,['model','folds','recall_media','recall_dp','especificidade_media','especificidade_dp','ap_media','brier_media','segundos_medios','folds_abaixo_da_meta'])}

## Agregado por repetição (previsões fora do treino de todos os folds)

{md_table(summary,['model','repeticoes_agregadas','recall_agregado','especificidade_agregada','ap_agregada'])}

## Perfis fixos (média dos folds, limiar aprendido)

{md_table(rep,['model','representation','recall','specificity','ap'])}

## Perfil escolhido pelo procedimento

{md_table(chosen,['model','representation','folds_em_que_foi_escolhida'])}

## Hiperparâmetros escolhidos (perfil do procedimento)

{md_table(params,['model','parametros','folds'])}

## Limites

Os folds de uma repetição não são amostras independentes e as repetições reaproveitam os mesmos registros: médias e desvios são descritivos, sem t pareado comum nem IC por desvio/√n. Treinos externos de {1-1/rc['outer_folds']:.0%} do desenvolvimento diferem dos 50% da v3, então diferenças em relação a ela misturam efeito de orçamento, de folds e de quantidade de dados. Escores internos de busca não são desempenho imparcial. A meta de 80% de especificidade é uma escolha acadêmica, sem validação clínica. Agrupamento: registro; independência por paciente desconhecida. Nenhum resultado desta rodada substitui o teste da v3 nem autoriza reajustar limiares no teste.
"""
    (folder/'relatorio_rodada.md').write_text(text,encoding='utf-8')


def consolidate_round(folder, rc, state):
    external,by_rep,hyper,done = collect(folder,rc)
    if not len(external):
        return None
    pooled = pooled_repeats(folder,rc,done)
    summary = summarize(external,pooled,rc)
    out = lambda df,name:df.to_csv(folder/name,index=False,encoding='utf-8-sig')
    out(external,'metricas_externas.csv')
    out(by_rep,'metricas_por_representacao.csv')
    out(pooled,'metricas_repeticoes.csv')
    out(hyper,'hiperparametros_selecionados.csv')
    out(summary,'resumo_desenvolvimento.csv')
    total = len(rc['outer_seeds'])*rc['outer_folds']
    if len(done)==total and rc['outer_folds']==2 and len(rc['outer_seeds'])==5:
        scores = external.loc[external['mode'].eq('aprendido')].sort_values(['repeat','fold'])
        base = scores.loc[scores.model.eq('logistica'),'error'].to_numpy()
        tests = [dict(model=n,reference='logistica',metric='error_aprendido',
                      **five_by_two((scores.loc[scores.model.eq(n),'error'].to_numpy()-base).reshape(5,2)))
                 for n in MODEL_ORDER if n!='logistica']
        for t,p in zip(tests,holm([t['f_p'] for t in tests])):
            t['f_p_holm'] = p
        write_json(folder/'testes_5x2.json',tests)
    round_report(folder,rc,state,summary,hyper,by_rep,done)
    return dict(folds_completos=len(done),folds_total=total)


def save_state(folder, rc, status, completed, total, **extra):
    write_json(folder/'estado_rodada.json',dict(rodada=rc['id'],status=status,folds_completos=completed,
                                                 folds_total=total,atualizado_em=now(),**extra))


def run_round(rc, source, root=RODADAS_DIR, max_folds=None):
    reference,partition_sha = v3_reference()
    folder = root/rc['id']
    state = initialize_round(rc,source,folder,reference,partition_sha)
    dev = load_development(source,partition_sha)
    total = len(rc['outer_seeds'])*rc['outer_folds']
    lock = folder/'rodada.lock'
    try:
        os.close(os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY))
    except FileExistsError:
        raise SystemExit(f'Rodada em execução ou interrompida (lock {lock}). Confira o processo antes de retomar.')
    ran = 0
    try:
        for repeat,seed in enumerate(rc['outer_seeds']):
            splits = folds(dev,rc['outer_folds'],seed)
            save_folds(dev,splits,folder/f'particao_externa_r{repeat}.csv',seed)
            for fold,(train,valid) in enumerate(splits):
                fold_dir = folder/f'externo_r{repeat}_f{fold}'
                if fold_done(fold_dir):
                    continue
                if max_folds is not None and ran >= max_folds:
                    raise StopIteration
                train_frame,valid_frame = dev.iloc[train].reset_index(drop=True),dev.iloc[valid].reset_index(drop=True)
                inner_seed = seed*10+fold
                inner = folds(train_frame,rc['inner_folds'],inner_seed)
                fold_dir.mkdir(exist_ok=True)
                save_folds(train_frame,inner,fold_dir/'particoes_internas.csv',inner_seed)
                completed = sum(fold_done(folder/f'externo_r{r}_f{f}') for r in range(len(rc['outer_seeds'])) for f in range(rc['outer_folds']))
                save_state(folder,rc,'em_execucao',completed,total,fold_atual=f'r{repeat}_f{fold}')
                for name in ALL_MODELS:
                    print(f'[{rc["id"]}] repetição {repeat+1}/{len(rc["outer_seeds"])} fold {fold+1}/{rc["outer_folds"]}: {name}',flush=True)
                    fit_representations(name,train_frame,inner,state,fold_dir/name,inner_seed,valid_frame)
                ran += 1
                consolidate_round(folder,rc,state)
                consolidate_all(root)
    except StopIteration:
        pass
    finally:
        lock.unlink(missing_ok=True)
    completed = sum(fold_done(folder/f'externo_r{r}_f{f}') for r in range(len(rc['outer_seeds'])) for f in range(rc['outer_folds']))
    save_state(folder,rc,'concluida' if completed==total else 'parcial',completed,total)
    consolidate_round(folder,rc,state)
    consolidate_all(root)
    return completed,total


def v3_tables():
    frames = {}
    for key,name in [('externas','metricas_externas.csv'),('representacao','metricas_por_representacao.csv'),
                     ('repeticoes','metricas_repeticoes.csv')]:
        df = pd.read_csv(V3_DIR/name,encoding='utf-8-sig')
        df.insert(0,'rodada',V3_ID)
        frames[key] = df
    return frames


def consolidate_all(root=RODADAS_DIR, config_path=ROOT/'config/config_rodadas.json'):
    """Reúne v3 e rodadas novas, sem alterar nenhum arquivo de origem."""
    out = root/'consolidado'
    out.mkdir(parents=True,exist_ok=True)
    v3 = v3_tables()
    ext,rep,per,hyp,registry = [v3['externas']],[v3['representacao']],[v3['repeticoes']],[],[]
    registry.append(dict(rodada=V3_ID,pasta=V3_DIR.relative_to(ROOT).as_posix(),folds_externos='2',repeticoes=5,folds_internos=3,
                         candidatos_por_perfil=4,estado='concluida (teste avaliado)',folds_completos=10,folds_total=10,
                         observacao='Referência da A2; teste reservado já aberto.'))
    summaries = []
    for rc in load_rounds(config_path):
        folder = root/rc['id']
        if not (folder/'metricas_externas.csv').exists():
            continue
        e = pd.read_csv(folder/'metricas_externas.csv',encoding='utf-8-sig')
        ext.append(e)
        rep.append(pd.read_csv(folder/'metricas_por_representacao.csv',encoding='utf-8-sig'))
        try:
            per.append(pd.read_csv(folder/'metricas_repeticoes.csv',encoding='utf-8-sig'))
        except pd.errors.EmptyDataError:
            pass  # nenhuma repetição completa ainda
        hyp.append(pd.read_csv(folder/'hiperparametros_selecionados.csv',encoding='utf-8-sig'))
        summaries.append(pd.read_csv(folder/'resumo_desenvolvimento.csv',encoding='utf-8-sig'))
        st = read_json(folder/'estado_rodada.json') if (folder/'estado_rodada.json').exists() else {}
        location = folder.resolve()
        if location.is_relative_to(ROOT):
            location = location.relative_to(ROOT)
        registry.append(dict(rodada=rc['id'],pasta=location.as_posix(),
                             folds_externos=str(rc['outer_folds']),repeticoes=len(rc['outer_seeds']),
                             folds_internos=rc['inner_folds'],candidatos_por_perfil=rc['candidates_per_family'],
                             estado=st.get('status','desconhecido'),folds_completos=st.get('folds_completos'),
                             folds_total=st.get('folds_total'),observacao=rc['descricao']))
    ext,rep,per = (pd.concat(x,ignore_index=True) for x in (ext,rep,per))
    ext.to_csv(out/'metricas_externas_todas_rodadas.csv',index=False,encoding='utf-8-sig')
    rep.to_csv(out/'metricas_por_representacao_todas_rodadas.csv',index=False,encoding='utf-8-sig')
    per.to_csv(out/'metricas_repeticoes_todas_rodadas.csv',index=False,encoding='utf-8-sig')
    if hyp:
        pd.concat(hyp,ignore_index=True).to_csv(out/'hiperparametros_selecionados_todas_rodadas.csv',index=False,encoding='utf-8-sig')
    registry = pd.DataFrame(registry)
    registry.to_csv(out/'registro_rodadas.csv',index=False,encoding='utf-8-sig')
    write_json(out/'registro_rodadas.json',registry.astype(object).where(registry.notna(),None).to_dict('records'))
    comparison(out,per,ext,registry)


def comparison(out, per, ext, registry):
    """Tabela comparativa descritiva: média das repetições agregadas, por modelo e rodada."""
    learned = per.loc[per['mode'].eq('aprendido')]
    blocks = []
    for column,label in [('recall','Sensibilidade (recall de Anormal)'),('specificity','Especificidade'),('ap','AP')]:
        wide = learned.groupby(['model','rodada'])[column].mean().unstack('rodada')
        wide = wide.reindex(index=ALL_MODELS,columns=list(registry.rodada)).reset_index()
        blocks.append(f'### {label}\n\n'+md_table(wide,['model']+[c for c in wide.columns if c!='model']))
    below = ext.loc[ext['mode'].eq('aprendido')].assign(abaixo=lambda d:d.specificity<.8)
    folds = below.groupby(['model','rodada']).abaixo.agg(['sum','count']).reset_index()
    folds['texto'] = folds['sum'].astype(int).astype(str)+'/'+folds['count'].astype(str)
    wide = folds.pivot(index='model',columns='rodada',values='texto').reindex(index=ALL_MODELS,columns=list(registry.rodada)).reset_index()
    blocks.append('### Folds com especificidade abaixo de 80%\n\n'+md_table(wide,['model']+[c for c in wide.columns if c!='model']))
    text = f"""# Comparação consolidada das rodadas de desenvolvimento

Atualizado em {now()}. Médias, por modelo, das métricas agregadas por repetição (previsões fora do treino, limiar aprendido dentro do treino). Todas as rodadas usam a mesma população de desenvolvimento; o teste reservado não entra aqui.

{md_table(registry,['rodada','folds_externos','repeticoes','folds_internos','candidatos_por_perfil','estado','folds_completos','folds_total'])}

{(chr(10)*2).join(blocks)}

Diferenças entre rodadas misturam o tamanho do treino externo (50% na v3, 80% com cinco folds), o orçamento de hiperparâmetros e a semente dos folds; não são testes de hipótese e não substituem a avaliação no teste da v3. Repetições e folds reaproveitam os mesmos registros, então desvios não são erros-padrão. Detalhes por fold em metricas_externas_todas_rodadas.csv.
"""
    (out/'comparacao_rodadas.md').write_text(text,encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=ROOT/'config/config_rodadas.json')
    parser.add_argument('--entrada',type=Path,default=ROOT/'resultados/preparo/UCMF_supervisionado.csv')
    parser.add_argument('--saida',type=Path,default=RODADAS_DIR)
    parser.add_argument('--rodada',help='id da rodada a executar/retomar; "todas" executa as pendentes')
    parser.add_argument('--max-folds',type=int,help='para após concluir N folds externos novos (retomável)')
    parser.add_argument('--consolidar',action='store_true',help='apenas regenera os consolidados')
    parser.add_argument('--listar',action='store_true')
    args = parser.parse_args()
    rounds = load_rounds(args.config)
    if args.listar:
        for rc in rounds:
            path = args.saida/rc['id']/'estado_rodada.json'
            status = read_json(path) if path.exists() else dict(status='nao_iniciada')
            print(rc['id'],status['status'],f"{status.get('folds_completos','-')}/{status.get('folds_total','-')}",sep='\t')
        return
    if args.consolidar:
        consolidate_all(args.saida,args.config)
        return
    if not args.rodada:
        parser.error('informe --rodada, --consolidar ou --listar')
    chosen = rounds if args.rodada=='todas' else [r for r in rounds if r['id']==args.rodada]
    if not chosen:
        parser.error(f'rodada desconhecida: {args.rodada}')
    for rc in chosen:
        completed,total = run_round(rc,args.entrada,args.saida,args.max_folds)
        print(f"{rc['id']}: {completed}/{total} folds externos completos",flush=True)


if __name__=='__main__':
    main()
