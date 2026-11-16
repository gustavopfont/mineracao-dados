"""Protocolos estatísticos, partições e bloqueios; sem usar o teste UCMF."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from scipy.stats import f,t

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from metricas_modelagem import choose_threshold, metrics, five_by_two, holm, mcnemar_exact
from modelos_ucmf import candidates, MODEL_ORDER
from treinar_modelos import (assert_partition, folds, load_frame, initialize, test_once,
                             _candidate_job, search_and_fit, write_json, sha)
from preparar_modelagem import FEATURE_COLUMNS, NUMERIC_COLUMNS, CATEGORICAL_COLUMNS, TARGET
from representacoes_ucmf import input_frame, preprocessor, REPRESENTATIONS, ALL_FEATURES


def synthetic(n=100):
    frame = pd.DataFrame({c:np.arange(n,dtype=float)+10 for c in NUMERIC_COLUMNS})
    frame['ID'] = [str(i) for i in range(n)]
    for c in CATEGORICAL_COLUMNS: frame[c]='Categoria'
    frame['HDA_UNIFICADA']='Dispneia'
    frame[TARGET]=['Normal','Anormal']*(n//2)
    frame['y']=np.tile([0,1],n//2)
    frame['group_id']=frame.ID
    frame['IMC']=20.
    frame['FAIXA_ETARIA']='6–12 anos'
    frame['CLASSIFICACAO IMC']='Eutrofia'
    frame['PPA_CALCULADA']='Normal'
    return frame


class MetricTest(unittest.TestCase):
    def test_manual_metrics(self):
        m=metrics([0,0,1,1],[.1,.7,.4,.9])
        for c in ['accuracy','precision','recall','specificity','f1','balanced_accuracy']:
            self.assertEqual(m[c],.5)
        self.assertEqual([m[c] for c in ['tn','fp','fn','tp']],[1]*4)

    def test_threshold_constant_and_ties(self):
        y=np.array([0,0,0,0,1,1])
        for p in [np.ones(6)*.4,np.array([.1,.2,.8,.8,.8,.9])]:
            result=choose_threshold(y,p,.8)
            m=metrics(y,p,result['threshold'])
            self.assertGreaterEqual(m['specificity'],.8)
            possibilities=[metrics(y,p,x)['recall'] for x in np.r_[np.nextafter(max(p),np.inf),np.unique(p)]
                           if metrics(y,p,x)['specificity']>=.8]
            self.assertEqual(m['recall'],max(possibilities))
        self.assertEqual(choose_threshold(y,np.ones(6)*.4)['recall'],0)

    def test_statistic_formulas_and_degeneracy(self):
        d=np.arange(10).reshape(5,2)/100
        variance=((d-d.mean(axis=1)[:,None])**2).sum()
        result=five_by_two(d)
        self.assertAlmostEqual(result['f_stat'],(d*d).sum()/(2*variance))
        self.assertAlmostEqual(result['f_p'],f.sf(result['f_stat'],10,5))
        self.assertAlmostEqual(result['t_p'],2*t.sf(abs(d[0,0]/np.sqrt(variance/5)),5))
        self.assertIsNone(five_by_two(np.ones((5,2)))['f_p'])
        with self.assertRaises(ValueError): five_by_two(np.ones((10,)))

    def test_holm_and_mcnemar(self):
        np.testing.assert_allclose(holm([.01,.04,.03]),[.03,.06,.06])
        self.assertEqual(holm([None,.01]),[None,.02])
        m=mcnemar_exact([1]*10,[1]*10,[0]*10,1)
        self.assertAlmostEqual(m['p'],2*(.5**10))
        self.assertEqual(mcnemar_exact([1,0],[1,0],[1,0],1)['p'],1)

    def test_invalid_predictions_fail(self):
        with self.assertRaises(ValueError): metrics([0,1],[.1,float('nan')])


class ProtocolTest(unittest.TestCase):
    def test_candidate_budget_reproducible(self):
        for count in [4,12]:
            a=candidates(count=count);self.assertEqual(a,candidates(count=count))
            for name in MODEL_ORDER:
                self.assertEqual(len(a[name]),count)
                self.assertEqual(len({json.dumps(p,sort_keys=True) for p in a[name]}),count)
        self.assertEqual(len(candidates()['logistica']),4)
        for count in [0,13,True]:
            with self.assertRaises(ValueError):candidates(count=count)

    def test_random_stratified_folds_and_group_lock(self):
        frame=synthetic()
        a=folds(frame,2,101); b=folds(frame,2,101); c=folds(frame,2,202)
        np.testing.assert_array_equal(a[0][0],b[0][0])
        self.assertFalse(np.array_equal(a[0][0],c[0][0]))
        self.assertEqual(frame.iloc[a[0][0]].y.mean(),.5)
        grouped=frame.copy(); grouped.group_id=[str(i//4) for i in range(len(frame))]
        for train,valid in folds(grouped,3,1):
            assert_partition(grouped,train,valid)
        with self.assertRaises(ValueError): assert_partition(frame,[0,1],[1,2])

    def test_tuning_uses_only_passed_training_ids(self):
        frame=synthetic(60)
        splits=folds(frame,3,42)
        seen=[]
        from preparar_modelagem import row_features
        from modelos_ucmf import pipeline
        actual=pipeline('logistica',{},42)
        original=actual.fit
        def fit_spy(X,y):
            seen.append(set(X.index)); return original(X,y)
        with patch('treinar_modelos.pipeline',return_value=actual),patch.object(actual,'fit',side_effect=fit_spy):
            trial=_candidate_job('logistica',0,{},input_frame(frame),frame.y.to_numpy(),splits,42,None)
        for ids,(train,valid) in zip(seen,splits):
            self.assertEqual(ids,set(train)); self.assertFalse(ids & set(valid))
        self.assertTrue(trial['eligible'])

    def test_resume_and_final_test_requires_freeze(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);source=path/'input.csv';cfg=path/'config.json';out=path/'run'
            data=synthetic()
            derived=['IMC','CLASSIFICACAO IMC','FAIXA_ETARIA','PPA_CALCULADA']
            data[['ID']+derived].to_csv(path/'atributos_complementares.csv',index=False)
            data.drop(columns=['y','group_id']+derived).to_csv(source,index=False)
            config=json.loads((ROOT/'config_experimentos.json').read_text());config['n_jobs']=1
            write_json(cfg,config)
            out.mkdir()
            (out/'execucao_stdout.log').touch()
            (out/'execucao_stderr.log').touch()
            (out/'execucao_background.lock').touch()
            write_json(out/'estado_execucao.json',{'status':'em_execucao'})
            state,frame=initialize(source,cfg,out)
            for name in MODEL_ORDER:self.assertEqual(len(state['candidates'][name]),config['candidates_per_family'])
            resumed,_=initialize(source,cfg,out);self.assertEqual(state,resumed)
            with self.assertRaises(FileNotFoundError): test_once(state,frame,out)
            config['seed']=9;write_json(cfg,config)
            with self.assertRaises(ValueError): initialize(source,cfg,out)

    def test_three_representations_keep_same_rows_and_distinct_attributes(self):
        frame=synthetic(20)
        for representation in REPRESENTATIONS:
            transform=preprocessor(representation)
            result=transform.fit_transform(input_frame(frame),frame.y)
            self.assertEqual(len(result),len(frame))
            names=transform.get_feature_names_out()
            if representation=='clinica':
                self.assertTrue(any('PPA_CALCULADA' in x for x in names))
                self.assertFalse(any(x=='numericas__IMC' for x in names))
            elif representation=='continua':
                self.assertTrue(any(x=='numericas__IMC' for x in names))
                self.assertFalse(any('PPA_CALCULADA' in x for x in names))
            else:
                self.assertTrue(any('PPA_CALCULADA' in x for x in names))
                self.assertTrue(any(x=='numericas__IMC' for x in names))

    def test_final_test_is_never_repredicted_on_resume(self):
        from modelos_ucmf import ALL_MODELS
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);frame=synthetic(20)
            write_json(out/'protocolo.json',{'fixed':True})
            write_json(out/'selecao_desenvolvimento.json',{'winner':'logistica'})
            frame[['ID']].assign(conjunto='teste').to_csv(out/'particao_principal.csv',index=False)
            artifacts={}
            for name in ALL_MODELS:
                folder=out/'finais'/name;folder.mkdir(parents=True)
                (folder/'pipeline.joblib').write_bytes(b'fixture, never loaded')
                write_json(folder/'concluido.json',{'threshold':.5})
                artifacts[name]=dict(pipeline_sha256=sha(folder/'pipeline.joblib'),info_sha256=sha(folder/'concluido.json'),threshold=.5)
            write_json(out/'congelamento.json',dict(protocol_sha256=sha(out/'protocolo.json'),selection_sha256=sha(out/'selecao_desenvolvimento.json'),
                artifacts=artifacts,winner='logistica',development_ids=['not-in-test']))
            predictions=frame[['ID','group_id','y']].assign(p=np.where(frame.y==1,.8,.2),pred=frame.y,pred_default=frame.y)
            with patch('treinar_modelos.joblib.load',return_value=object()) as loader,patch('treinar_modelos.prediction_table',return_value=predictions) as predict:
                test_once({},frame,out)
                self.assertEqual(predict.call_count,6)
                test_once({},frame,out)
                self.assertEqual(predict.call_count,6)
                self.assertEqual(loader.call_count,6)
            altered=frame.copy();altered.loc[0,'ID']='not-in-test'
            with self.assertRaises(ValueError):test_once({},altered,out)

    def test_bootstrap_paired_and_patient_groups(self):
        from relatorio_modelos import bootstrap_indices
        y=np.tile([0,0,1,1],5);groups=np.repeat(np.arange(5),4)
        indices=bootstrap_indices(y,groups,np.random.default_rng(42))
        self.assertEqual((y[indices]==1).sum(),10)
        grouped=bootstrap_indices(y,groups,np.random.default_rng(42),True)
        for group in np.unique(groups[grouped]):
            counts=[(grouped==i).sum() for i in np.flatnonzero(groups==group)]
            self.assertEqual(len(set(counts)),1)

    def test_report_contract_with_synthetic_frozen_predictions(self):
        from modelos_ucmf import ALL_MODELS
        from metricas_modelagem import metrics
        from relatorio_modelos import run_report
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);frame=synthetic(20)
            y=frame.y.to_numpy();p=np.where(y==1,.8,.2)
            rows=[]
            for name in ALL_MODELS:
                folder=out/'finais'/name;folder.mkdir(parents=True)
                table=frame[['ID','group_id','y']].assign(p=p,pred=y,pred_default=y)
                table.to_csv(folder/'previsoes_teste.csv',index=False)
                write_json(folder/'teste_concluido.json',dict(prediction_sha256=sha(folder/'previsoes_teste.csv')))
                for mode in ['aprendido','padrao_0.5']:rows.append(dict(model=name,mode=mode,**metrics(y,p)))
            pd.DataFrame(rows).to_csv(out/'metricas_teste.csv',index=False)
            write_json(out/'selecao_desenvolvimento.json',dict(models=[dict(model='logistica',recall=1.,specificity=1.,ap=1.,seconds=1.,folds_below_target=0)]))
            pd.DataFrame([dict(model='logistica',representation='continua',mode='aprendido',recall=1.,specificity=1.,ap=1.)]).to_csv(out/'metricas_por_representacao.csv',index=False)
            write_json(out/'testes_5x2.json',[dict(model='arvore',**five_by_two(np.ones((5,2))),f_p_holm=None,t_p_holm_sensibilidade=None)])
            pd.DataFrame([dict(feature='IDADE',repeat=i,ap_drop=.1) for i in range(2)]).to_csv(out/'importancia_permutacao.csv',index=False)
            write_json(out/'protocolo.json',{})
            config=read_config=json.loads((ROOT/'config_experimentos.json').read_text());config['bootstrap_repetitions']=10
            state=dict(config=config,grouping='registro; independência por paciente desconhecida')
            frozen=dict(winner='logistica',target_met=True,artifacts={'logistica':{'representation':'continua'}})
            with patch('relatorio_modelos.verify_frozen',return_value=frozen):run_report(out,frame,state)
            self.assertTrue((out/'curvas_roc_pr.png').exists())
            self.assertTrue((out/'manifesto_resultados.json').exists())
            self.assertIn('Indefinido',(out/'relatorio_experimentos.md').read_text(encoding='utf-8'))


if __name__=='__main__': unittest.main()
