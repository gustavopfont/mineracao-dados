"""Experimentos UCMF: init → desenvolvimento → congelar → teste → relatorio.

O protocolo da v3 consta no relatório publicado. Retomada nunca faz
nova avaliação de teste; carrega as previsões originais depois da abertura.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import time
import warnings

import joblib
from joblib import Parallel, delayed, parallel_config
import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import average_precision_score
from sklearn.model_selection import StratifiedKFold, StratifiedGroupKFold, train_test_split
from threadpoolctl import threadpool_limits

from preparar_modelagem import ROOT, TARGET, FEATURE_COLUMNS, row_features, profile_keys
from modelos_ucmf import ALL_MODELS, MODEL_ORDER, candidates, pipeline
from metricas_modelagem import choose_threshold, metrics, five_by_two, holm
from representacoes_ucmf import REPRESENTATIONS, ALL_FEATURES, input_frame


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    tmp.replace(path)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def versions():
    return dict(python=platform.python_version(), **{p:importlib.metadata.version(p)
                for p in ['numpy','pandas','scipy','scikit-learn','joblib','threadpoolctl']})


def assert_partition(frame, train, valid):
    if set(train)&set(valid) or not len(train) or not len(valid):
        raise ValueError('Partição inválida ou sobreposta')
    a,b = frame.iloc[train],frame.iloc[valid]
    if set(a.ID)&set(b.ID) or set(a.group_id)&set(b.group_id):
        raise ValueError('ID/grupo atravessou partições')
    for part in [a,b]:
        if set(part.y) != {0,1}:
            raise ValueError('Classe ausente na partição')


def folds(frame, k, seed):
    if frame.group_id.duplicated().any():
        splitter = StratifiedGroupKFold(n_splits=k,shuffle=True,random_state=seed)
        result = list(splitter.split(frame,frame.y,frame.group_id))
    else:
        result = list(StratifiedKFold(n_splits=k,shuffle=True,random_state=seed).split(frame,frame.y))
    for a,b in result:
        assert_partition(frame,a,b)
    return result


def protocol_inputs(source, config_path, groups_path=None):
    code = ['treinar_modelos.py','modelos_ucmf.py','metricas_modelagem.py','preparar_modelagem.py','representacoes_ucmf.py']
    return dict(data_sha256=sha(source), complementary_sha256=sha(Path(source).with_name('atributos_complementares.csv')), config_sha256=sha(config_path),
                groups_sha256=sha(groups_path) if groups_path else None,
                code_sha256={p:sha(ROOT/'scripts'/p) for p in code}, versions=versions())


def load_frame(source, groups_path=None):
    frame = pd.read_csv(source,dtype='string',encoding='utf-8-sig')
    if frame.ID.isna().any() or frame.ID.duplicated().any() or not frame[TARGET].isin(['Normal','Anormal']).all():
        raise ValueError('Exige IDs únicos e alvos conhecidos')
    X = row_features(frame)
    if len(set(profile_keys(X,FEATURE_COLUMNS))) != len(frame):
        raise ValueError('Perfis repetidos: reexecutar auditoria antes do treino')
    complementary = pd.read_csv(Path(source).with_name('atributos_complementares.csv'),dtype='string')
    if complementary.ID.duplicated().any() or set(complementary.ID)!=set(frame.ID):
        raise ValueError('Atributos complementares não correspondem à base supervisionada')
    frame = frame.merge(complementary,on='ID',how='left',validate='one_to_one',sort=False)
    input_frame(frame)
    frame['y'] = frame[TARGET].map({'Normal':0,'Anormal':1}).astype(int)
    if groups_path:
        mapping = pd.read_csv(groups_path,dtype='string')
        if set(mapping) != {'ID','paciente_id'} or mapping.ID.duplicated().any() or mapping.isna().any().any():
            raise ValueError('Mapeamento exige ID único e paciente_id preenchido')
        frame['group_id'] = frame.ID.map(mapping.set_index('ID').paciente_id)
        if frame.group_id.isna().any():
            raise ValueError('Mapeamento de pacientes incompleto')
    else:
        frame['group_id'] = frame.ID  # grupo de registro; NÃO afirma identidade de paciente
    return frame


def initialize(source, config_path, output, groups_path=None):
    cfg = read_json(config_path)
    if cfg.get('representations') != REPRESENTATIONS:
        raise ValueError('Esta execução exige as três representações pré-especificadas')
    if cfg['positive_class'] != 'Anormal' or len(set(cfg['outer_seeds'])) != 5 or cfg['inner_folds'] != 3:
        raise ValueError('Protocolo exige Anormal positiva e validação 5×2 / 3 interna')
    if cfg['candidates_per_family'] not in [4,12] or not 1 <= cfg['n_jobs'] <= 4:
        raise ValueError('Orçamento exige 4 ou 12 candidatos por perfil e 1–4 processos')
    if not 0 < cfg['minimum_specificity'] < 1 or cfg['test_size'] != .2:
        raise ValueError('Restrição de especificidade inválida ou teste diferente de 20%')
    signature = protocol_inputs(source,config_path,groups_path)
    output.mkdir(parents=True,exist_ok=True)
    state_path = output/'protocolo.json'
    if state_path.exists():
        state = read_json(state_path)
        if state['inputs'] != signature:
            raise ValueError('Dados/código/configuração/ambiente mudaram: usar novo diretório de execução')
        return state,load_frame(source,groups_path)
    bootstrap_files={'execucao_background.lock','estado_execucao.json','execucao_stdout.log','execucao_stderr.log'}
    if any(p.name not in bootstrap_files for p in output.iterdir()):
        raise ValueError('Diretório não vazio sem protocolo; exige revisão manual')
    frame = load_frame(source,groups_path)
    if groups_path:
        train,test = folds(frame,5,cfg['seed'])[0]  # 4/5 grupos para desenvolvimento
    else:
        train,test = train_test_split(np.arange(len(frame)),test_size=.2,stratify=frame.y,random_state=cfg['seed'],shuffle=True)
    assert_partition(frame,train,test)
    assignment = frame[['ID','group_id','y']].copy()
    assignment['conjunto'] = 'desenvolvimento'
    assignment.loc[test,'conjunto'] = 'teste'
    assignment.to_csv(output/'particao_principal.csv',index=False,encoding='utf-8-sig')
    state = dict(inputs=signature,config=cfg,candidates=candidates(cfg['seed'],cfg['candidates_per_family']),
                 partition_sha256=sha(output/'particao_principal.csv'),
                 grouping='paciente confirmado' if groups_path else 'registro; independência por paciente desconhecida')
    write_json(state_path,state)
    print(f'Partições salvas: desenvolvimento={len(train)}, teste={len(test)}',flush=True)
    return state,frame


def verify_partition(state,frame,output):
    path = output/'particao_principal.csv'
    if sha(path) != state['partition_sha256']:
        raise ValueError('Partição principal modificada')
    assignment = pd.read_csv(path,dtype={'ID':'string','group_id':'string'})
    if list(assignment.ID) != list(frame.ID):
        raise ValueError('IDs/ordem da partição divergentes')
    a = np.flatnonzero(assignment.conjunto.eq('desenvolvimento'))
    b = np.flatnonzero(assignment.conjunto.eq('teste'))
    assert_partition(frame,a,b)
    return frame.iloc[a].reset_index(drop=True), frame.iloc[b].reset_index(drop=True)


def save_folds(frame, splits, path, seed):
    records = []
    for fold,(_,valid) in enumerate(splits):
        records.append(frame.iloc[valid][['ID','group_id','y']].assign(fold=fold,seed=int(seed)))
    table = pd.concat(records,ignore_index=True)
    if path.exists():
        old = pd.read_csv(path,dtype={'ID':'string','group_id':'string'})
        if old.to_csv(index=False) != table.to_csv(index=False):
            raise ValueError(f'Partições alteradas: {path}')
    else:
        table.to_csv(path,index=False,encoding='utf-8-sig')


def _candidate_job(name,index,params,X,y,splits,seed,cache,representation='continua'):
    start = time.perf_counter()
    scores, log, oof = [],[],np.full(len(y),np.nan)
    for fold,(train,valid) in enumerate(splits):
        model = pipeline(name,params,seed,cache,representation)
        with threadpool_limits(limits=1), warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            model.fit(X.iloc[train],y[train])
            p = model.predict_proba(X.iloc[valid])[:,list(model.classes_).index(1)]
        messages = [dict(category=w.category.__name__,message=str(w.message)) for w in caught]
        log += [dict(fold=fold,**m) for m in messages]
        if any(issubclass(w.category,ConvergenceWarning) for w in caught):
            return dict(candidate=index,params=params,eligible=False,fold_ap=scores,warnings=log,
                        seconds=time.perf_counter()-start,oof=None)
        scores.append(float(average_precision_score(y[valid],p)))
        oof[valid] = p
    if not np.isfinite(oof).all():
        raise ValueError('OOF incompleto')
    return dict(candidate=index,params=params,eligible=True,fold_ap=scores,mean_ap=float(np.mean(scores)),
                warnings=log,seconds=time.perf_counter()-start,oof=oof)


def search_and_fit(name,frame,splits,state,folder,seed,representation='continua'):
    cfg = state['config']
    # Os IDs externos/teste nunca são passados a esta função.
    X,y = input_frame(frame),frame.y.to_numpy()
    folder.mkdir(parents=True,exist_ok=True)
    cache = next((p/'.cache' for p in folder.parents if (p/'protocolo.json').exists()),None)
    candidates_path = folder/'busca.json'
    if candidates_path.exists():
        search = read_json(candidates_path)
        best = search['selected_candidate']
        params = search['trials'][best]['params']
        oof = pd.read_csv(folder/'oof_interno.csv',float_precision='round_trip')
        if list(oof.ID.astype(str)) != list(frame.ID.astype(str)):
            raise ValueError('OOF retomado possui IDs divergentes')
        threshold = choose_threshold(y,oof.p.to_numpy(),cfg['minimum_specificity'])
    else:
        with parallel_config(backend='loky',inner_max_num_threads=1):
            trials = Parallel(n_jobs=cfg['n_jobs'])(delayed(_candidate_job)(
                name,i,params,X,y,splits,seed,cache,representation)
                for i,params in enumerate(state['candidates'][name]))
        eligible = [t for t in trials if t['eligible']]
        if not eligible:
            write_json(folder/'falha_busca.json',[{k:v for k,v in t.items() if k!='oof'} for t in trials])
            raise ValueError(f'Nenhum candidato convergente em {name}')
        maximum = max(t['mean_ap'] for t in eligible)
        chosen = min((t for t in eligible if maximum-t['mean_ap'] <= 1e-6),key=lambda t:t['candidate'])
        best,params = chosen['candidate'],chosen['params']
        threshold = choose_threshold(y,chosen['oof'],cfg['minimum_specificity'])
        pd.DataFrame(dict(ID=frame.ID,y=y,p=chosen['oof'])).to_csv(folder/'oof_interno.csv',index=False,encoding='utf-8-sig')
        search = dict(selected_candidate=best,trials=[{k:v for k,v in t.items() if k!='oof'} for t in trials])
        write_json(candidates_path,search)
    model = pipeline(name,params,seed,cache,representation)
    with threadpool_limits(limits=1), warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        model.fit(X,y)
    if any(issubclass(w.category,ConvergenceWarning) for w in caught):
        raise ValueError(f'Refit não convergiu: {name}')
    return model,dict(params=params,selected_candidate=best,representation=representation,
                      inner_ap=search['trials'][best]['mean_ap'],threshold_info=threshold,
                      refit_warnings=[str(w.message) for w in caught])


def prediction_table(model,frame,threshold):
    with threadpool_limits(limits=1):
        p = model.predict_proba(input_frame(frame))[:,list(model.classes_).index(1)]
    return pd.DataFrame(dict(ID=frame.ID,group_id=frame.group_id,y=frame.y,p=p,
                             pred=(p>=threshold).astype(int),pred_default=(p>=.5).astype(int)))


def table_metrics(table,mode='aprendido'):
    return metrics(table.y,table.p,prediction=table.pred if mode=='aprendido' else table.pred_default)


def fit_representations(name,train_frame,inner,state,folder,seed,valid_frame=None):
    """Escolhe representação exclusivamente pela AP interna; salva todas as avaliações."""
    folder.mkdir(parents=True,exist_ok=True)
    records=[]
    for representation in (['continua'] if name=='dummy' else REPRESENTATIONS):
        sub=folder/representation
        done=sub/'concluido.json'
        if not done.exists():
            print(f'  {name} / {representation}',flush=True)
            start=time.perf_counter()
            model,info=search_and_fit(name,train_frame,inner,state,sub,seed,representation)
            if valid_frame is not None:
                table=prediction_table(model,valid_frame,info['threshold_info']['threshold'])
                table.to_csv(sub/'previsoes_externas.csv',index=False,encoding='utf-8-sig')
                info['prediction_sha256']=sha(sub/'previsoes_externas.csv')
            else:
                model.memory=None
                joblib.dump(model,sub/'pipeline.joblib')
                info['pipeline_sha256']=sha(sub/'pipeline.joblib')
            info['seconds']=time.perf_counter()-start
            write_json(done,info)
        info=read_json(done)
        artifact=sub/('previsoes_externas.csv' if valid_frame is not None else 'pipeline.joblib')
        key='prediction_sha256' if valid_frame is not None else 'pipeline_sha256'
        if sha(artifact)!=info[key]:raise ValueError('Artefato de representação modificado')
        records.append(info)
    best_ap=max(i['inner_ap'] for i in records)
    selected=min((i for i in records if best_ap-i['inner_ap']<=1e-6),key=lambda i:REPRESENTATIONS.index(i['representation']))
    chosen=selected.copy()
    chosen['seconds']=sum(i['seconds'] for i in records)
    representation=chosen['representation']
    filename='previsoes_externas.csv' if valid_frame is not None else 'pipeline.joblib'
    if not (folder/filename).exists():
        (folder/filename).write_bytes((folder/representation/filename).read_bytes())
    if sha(folder/filename)!=chosen[key]:raise ValueError('Seleção de representação modificada')
    write_json(folder/'concluido.json',chosen)
    return chosen,records


def develop(state,dev,output):
    if (output/'teste_aberto.json').exists():
        raise ValueError('Teste já aberto: desenvolvimento não pode ser alterado nesta execução')
    cfg = state['config']
    outer,representation_scores = [],[]
    for repeat,seed in enumerate(cfg['outer_seeds']):
        splits = folds(dev,2,seed)
        save_folds(dev,splits,output/f'particao_externa_r{repeat}.csv',seed)
        for orientation,(train,valid) in enumerate(splits):
            train_frame,valid_frame = dev.iloc[train].reset_index(drop=True),dev.iloc[valid].reset_index(drop=True)
            inner_seed = seed*10+orientation
            inner = folds(train_frame,3,inner_seed)
            outer_folder = output/f'externo_r{repeat}_f{orientation}'
            outer_folder.mkdir(exist_ok=True)
            save_folds(train_frame,inner,outer_folder/'particoes_internas.csv',inner_seed)
            for name in ALL_MODELS:
                folder = outer_folder/name
                print(f'Desenvolvimento r{repeat+1}/5 metade {orientation+1}/2: {name}',flush=True)
                info,records=fit_representations(name,train_frame,inner,state,folder,inner_seed,valid_frame)
                for record in records:
                    rep=record['representation']
                    rep_table=pd.read_csv(folder/rep/'previsoes_externas.csv',float_precision='round_trip')
                    for mode in ['aprendido','padrao_0.5']:
                        representation_scores.append(dict(model=name,representation=rep,repeat=repeat,fold=orientation,mode=mode,
                                                           **table_metrics(rep_table,mode)))
                if sha(folder/'previsoes_externas.csv') != info['prediction_sha256']:
                    raise ValueError('Previsões externas modificadas')
                table = pd.read_csv(folder/'previsoes_externas.csv',float_precision='round_trip')
                if set(table.ID.astype(str)) != set(valid_frame.ID):
                    raise ValueError('IDs externos incorretos')
                for mode in ['aprendido','padrao_0.5']:
                    outer.append(dict(model=name,representation=info['representation'],repeat=repeat,fold=orientation,mode=mode,
                                      seconds=info['seconds'],threshold=info['threshold_info']['threshold'],
                                      **table_metrics(table,mode)))
    pd.DataFrame(outer).to_csv(output/'metricas_externas.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(representation_scores).to_csv(output/'metricas_por_representacao.csv',index=False,encoding='utf-8-sig')
    summarize_development(output)


def summarize_development(output):
    external = pd.read_csv(output/'metricas_externas.csv')
    per_repeat = []
    for name in ALL_MODELS:
        for repeat in range(5):
            tables = [pd.read_csv(output/f'externo_r{repeat}_f{fold}'/name/'previsoes_externas.csv',float_precision='round_trip') for fold in range(2)]
            table = pd.concat(tables,ignore_index=True)
            if table.ID.duplicated().any():
                raise ValueError('Uma repetição externa não é OOF')
            for mode in ['aprendido','padrao_0.5']:
                per_repeat.append(dict(model=name,repeat=repeat,mode=mode,**table_metrics(table,mode)))
    rep = pd.DataFrame(per_repeat)
    rep.to_csv(output/'metricas_repeticoes.csv',index=False,encoding='utf-8-sig')
    numeric = ['accuracy','recall','specificity','precision','f1','f2','balanced_accuracy','roc_auc','ap','brier','error']
    external.groupby(['model','mode'])[numeric].agg(['mean','std']).to_csv(output/'resumo_externo_media_dp.csv',encoding='utf-8-sig')
    summary = []
    for name in MODEL_ORDER:
        scores = rep.loc[rep.model.eq(name)&rep['mode'].eq('aprendido')]
        times = external.loc[external.model.eq(name)&external['mode'].eq('aprendido'),'seconds']
        summary.append(dict(model=name,recall=float(scores.recall.mean()),specificity=float(scores.specificity.mean()),
                            ap=float(scores.ap.mean()),seconds=float(times.mean()),
                            folds_below_target=int((external.loc[external.model.eq(name)&external['mode'].eq('aprendido'),'specificity']<.8).sum())))
    cfg = read_json(output/'protocolo.json')['config']
    eligible = [s for s in summary if s['specificity'] >= cfg['minimum_specificity']]
    if eligible:
        winner = sorted(eligible,key=lambda s:(-s['recall'],-s['ap'],s['seconds'],MODEL_ORDER.index(s['model'])))[0]['model']
    else:
        winner = sorted(summary,key=lambda s:(-s['ap'],MODEL_ORDER.index(s['model'])))[0]['model']
    write_json(output/'selecao_desenvolvimento.json',dict(winner=winner,target_met=bool(eligible),models=summary))
    comparisons = []
    scores = external.loc[external['mode'].eq('aprendido')].sort_values(['repeat','fold'])
    base = scores.loc[scores.model.eq('logistica'),'error'].to_numpy()
    for name in MODEL_ORDER:
        if name != 'logistica':
            diff = scores.loc[scores.model.eq(name),'error'].to_numpy()-base
            comparisons.append(dict(model=name,reference='logistica',metric='error_aprendido',**five_by_two(diff.reshape(5,2))))
    for i,p in enumerate(holm([c['f_p'] for c in comparisons])):
        comparisons[i]['f_p_holm'] = p
    for i,p in enumerate(holm([c['t_p'] for c in comparisons])):
        comparisons[i]['t_p_holm_sensibilidade'] = p
    write_json(output/'testes_5x2.json',comparisons)


def freeze(state,dev,output):
    if (output/'teste_aberto.json').exists():
        raise ValueError('Teste aberto: não se permite congelar novos modelos')
    selection = read_json(output/'selecao_desenvolvimento.json')
    inner = folds(dev,3,4201)
    save_folds(dev,inner,output/'particoes_internas_finais.csv',4201)
    artifacts = {}
    for name in ALL_MODELS:
        folder = output/'finais'/name
        done = folder/'concluido.json'
        print(f'Ajuste final no desenvolvimento: {name}',flush=True)
        info,_=fit_representations(name,dev,inner,state,folder,4201)
        if sha(folder/'pipeline.joblib') != info['pipeline_sha256']:
            raise ValueError('Pipeline final modificado')
        artifacts[name] = dict(pipeline_sha256=info['pipeline_sha256'],info_sha256=sha(done),
                               threshold=info['threshold_info']['threshold'],representation=info['representation'])
    frozen = dict(protocol_sha256=sha(output/'protocolo.json'),selection_sha256=sha(output/'selecao_desenvolvimento.json'),
                  winner=selection['winner'],target_met=selection['target_met'],artifacts=artifacts,
                  development_ids=list(dev.ID),positive_class='Anormal',prediction_rule='p >= threshold')
    write_json(output/'congelamento.json',frozen)


def verify_frozen(output):
    frozen = read_json(output/'congelamento.json')
    if sha(output/'protocolo.json') != frozen['protocol_sha256'] or sha(output/'selecao_desenvolvimento.json') != frozen['selection_sha256']:
        raise ValueError('Protocolo/seleção alterados após congelamento')
    for name,record in frozen['artifacts'].items():
        folder = output/'finais'/name
        if sha(folder/'pipeline.joblib') != record['pipeline_sha256'] or sha(folder/'concluido.json') != record['info_sha256']:
            raise ValueError('Modelo/limiar alterado após congelamento')
    return frozen


def test_once(state,test,output):
    frozen = verify_frozen(output)
    if set(test.ID)&set(frozen['development_ids']):
        raise ValueError('Desenvolvimento passado como teste')
    assignment=pd.read_csv(output/'particao_principal.csv',dtype={'ID':'string'})
    if set(test.ID)!=set(assignment.loc[assignment.conjunto.eq('teste'),'ID']):
        raise ValueError('Teste difere da partição congelada')
    opened = output/'teste_aberto.json'
    if opened.exists():
        prior = read_json(opened)
        if prior['freeze_sha256'] != sha(output/'congelamento.json'):
            raise ValueError('Congelamento divergente do teste já aberto')
    else:
        write_json(opened,dict(freeze_sha256=sha(output/'congelamento.json'),policy='retomada somente dos mesmos artefatos congelados'))
    rows = []
    for name in ALL_MODELS:
        folder = output/'finais'/name
        prediction_path = folder/'previsoes_teste.csv'
        done = folder/'teste_concluido.json'
        if not done.exists():
            if prediction_path.exists():
                raise ValueError('Previsões sem marcador de conclusão: revisar interrupção antes de retomar')
            model = joblib.load(folder/'pipeline.joblib')
            table = prediction_table(model,test,frozen['artifacts'][name]['threshold'])
            table.to_csv(prediction_path,index=False,encoding='utf-8-sig')
            write_json(done,dict(prediction_sha256=sha(prediction_path)))
        if sha(prediction_path) != read_json(done)['prediction_sha256']:
            raise ValueError('Previsões finais alteradas')
        table = pd.read_csv(prediction_path,float_precision='round_trip')
        if list(table.ID.astype(str)) != list(test.ID):
            raise ValueError('IDs de teste não correspondem à partição')
        for mode in ['aprendido','padrao_0.5']:
            rows.append(dict(model=name,mode=mode,**table_metrics(table,mode)))
    pd.DataFrame(rows).to_csv(output/'metricas_teste.csv',index=False,encoding='utf-8-sig')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fase',choices=['init','desenvolvimento','congelar','teste','relatorio','todos'],default='desenvolvimento')
    parser.add_argument('--entrada',type=Path,default=ROOT/'resultados/preparo/UCMF_supervisionado.csv')
    parser.add_argument('--config',type=Path,default=ROOT/'config/config_experimentos.json')
    parser.add_argument('--grupos',type=Path)
    parser.add_argument('--saida',type=Path,default=ROOT/'resultados/experimentos/v3')
    args = parser.parse_args()
    args.saida.mkdir(parents=True,exist_ok=True)
    state,frame = initialize(args.entrada,args.config,args.saida,args.grupos)
    dev,test = verify_partition(state,frame,args.saida)
    phases = ['desenvolvimento','congelar','teste','relatorio'] if args.fase=='todos' else [args.fase]
    for phase in phases:
        if args.fase=='todos' and phase in ['desenvolvimento','congelar'] and (args.saida/'teste_aberto.json').exists():
            verify_frozen(args.saida)
            continue
        if phase=='desenvolvimento': develop(state,dev,args.saida)
        elif phase=='congelar': freeze(state,dev,args.saida)
        elif phase=='teste': test_once(state,test,args.saida)
        elif phase=='relatorio':
            from relatorio_modelos import run_report
            run_report(args.saida,frame,state)


if __name__=='__main__':
    main()
