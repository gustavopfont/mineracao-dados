"""Relato, bootstrap pareado e figuras de modelos já congelados (sem seleção)."""
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.calibration import calibration_curve
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_curve, precision_recall_curve, confusion_matrix
from threadpoolctl import threadpool_limits
import joblib

from modelos_ucmf import ALL_MODELS
from metricas_modelagem import metrics, mcnemar_exact, holm
from preparar_modelagem import ROOT, row_features, FEATURE_COLUMNS
from representacoes_ucmf import input_frame, ALL_FEATURES, columns
from treinar_modelos import read_json, write_json, sha, verify_frozen

BOOT_METRICS=['accuracy','recall','specificity','precision','f1','f2','balanced_accuracy','roc_auc','ap','brier']


def bootstrap_indices(y,groups,rng,patient_groups=False):
    y=np.asarray(y)
    if not patient_groups:
        return np.concatenate([rng.choice(np.flatnonzero(y==label),size=(y==label).sum(),replace=True) for label in [0,1]])
    # Estratos de grupos: apenas Normal, apenas Anormal ou ambos. Pessoas inteiras.
    groups=np.asarray(groups)
    members={g:np.flatnonzero(groups==g) for g in np.unique(groups)}
    strata={k:[] for k in [1,2,3]}
    for g,idx in members.items():
        pattern=int((y[idx]==0).any())+2*int((y[idx]==1).any())
        strata[pattern].append(g)
    return np.concatenate([members[g] for labels in strata.values() if labels
                           for g in rng.choice(labels,size=len(labels),replace=True)])


def bootstrap(output,state,tables,frozen):
    destination=output/'bootstrap_ic95.csv'
    if destination.exists(): return
    cfg=state['config'];rng=np.random.default_rng(cfg['seed']+9000)
    base=tables['logistica'];y=base.y.to_numpy()
    scores={name:{metric:[] for metric in BOOT_METRICS} for name in ALL_MODELS}
    winner=frozen['winner']
    differences={metric:[] for metric in BOOT_METRICS} if winner!='logistica' else {}
    for iteration in range(cfg['bootstrap_repetitions']):
        idx=bootstrap_indices(y,base.group_id,rng,state['grouping']=='paciente confirmado')
        results={}
        for name,table in tables.items():
            result=metrics(y[idx],table.p.to_numpy()[idx],prediction=table.pred.to_numpy()[idx])
            results[name]=result
            for metric in BOOT_METRICS:scores[name][metric].append(result[metric])
        for metric in differences:
            differences[metric].append(results[winner][metric]-results['logistica'][metric])
        if (iteration+1)%500==0:print(f'Bootstrap pareado: {iteration+1}/{cfg["bootstrap_repetitions"]}',flush=True)
    records=[]
    for name,values in scores.items():
        point=metrics(base.y,tables[name].p,prediction=tables[name].pred)
        for metric,draws in values.items():
            low,high=np.quantile(draws,[.025,.975])
            records.append(dict(model=name,metric=metric,estimate=point[metric],lower=float(low),upper=float(high),kind='modelo_fixo'))
    for metric,draws in differences.items():
        low,high=np.quantile(draws,[.025,.975])
        point=metrics(y,tables[winner].p,prediction=tables[winner].pred)[metric]-metrics(y,base.p,prediction=base.pred)[metric]
        records.append(dict(model=winner+' - logistica',metric=metric,estimate=point,lower=float(low),upper=float(high),kind='diferenca_pareada'))
    pd.DataFrame(records).to_csv(destination,index=False,encoding='utf-8-sig')


def hypothesis_holdout(output,tables,frozen):
    name=frozen['winner'];result=[]
    if name!='logistica':
        a,b=tables[name],tables['logistica']
        for target in [1,0]:result.append(mcnemar_exact(a.y,a.pred,b.pred,target))
        for i,p in enumerate(holm([r['p'] for r in result])):result[i]['p_holm']=p
    write_json(output/'mcnemar_teste.json',dict(winner=name,reference='logistica',comparisons=result,
                                             note='Sem comparação contra si própria' if not result else 'Alvos condicionados; modelos e limiares fixos'))


def plots(output,tables,frozen):
    colors=plt.get_cmap('tab10')
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    for i,(name,table) in enumerate(tables.items()):
        fpr,tpr,_=roc_curve(table.y,table.p)
        precision,recall,_=precision_recall_curve(table.y,table.p)
        point=metrics(table.y,table.p,prediction=table.pred)
        axes[0].plot(fpr,tpr,label=f'{name}: AUC={point["roc_auc"]:.3f}',color=colors(i))
        axes[1].step(recall,precision,where='post',label=f'{name}: AP={point["ap"]:.3f}',color=colors(i))
    axes[0].plot([0,1],[0,1],'k--',label='Referência aleatória')
    axes[1].axhline(tables['dummy'].y.mean(),ls='--',color='black',label='Prevalência de Anormal')
    for ax in axes:ax.set_xlim(0,1);ax.set_ylim(0,1.02);ax.legend(fontsize=8);ax.grid(alpha=.2)
    axes[0].set(xlabel='1 − especificidade',ylabel='Sensibilidade de Anormal',title='ROC — teste reservado')
    axes[1].set(xlabel='Recall de Anormal',ylabel='Precisão de Anormal',title='PR — teste reservado')
    fig.savefig(output/'curvas_roc_pr.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(12,7),layout='constrained')
    for ax,(name,table) in zip(axes.flat,tables.items()):
        matrix=confusion_matrix(table.y,table.pred,labels=[0,1])
        ax.imshow(matrix,cmap='Blues')
        for i in range(2):
            for j in range(2):ax.text(j,i,str(matrix[i,j]),ha='center',va='center',color='white' if matrix[i,j]>matrix.max()/2 else 'black')
        ax.set(xticks=[0,1],yticks=[0,1],xticklabels=['Normal','Anormal'],yticklabels=['Normal','Anormal'],
               xlabel='Predito',ylabel='Real',title=name+(' (selecionado)' if name==frozen['winner'] else ''))
    fig.suptitle('Matrizes de confusão — limiares congelados')
    fig.savefig(output/'matrizes_confusao.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,5),layout='constrained')
    for name,table in tables.items():
        observed,predicted=calibration_curve(table.y,table.p,n_bins=10,strategy='quantile')
        ax.plot(predicted,observed,'o-',label=name)
    ax.plot([0,1],[0,1],'k--');ax.set(xlim=(0,1),ylim=(0,1),xlabel='Probabilidade média prevista',
                                    ylabel='Fração observada de Anormal',title='Calibração descritiva — teste')
    ax.legend();ax.grid(alpha=.2);fig.savefig(output/'calibracao.png',dpi=160);plt.close(fig)


def importance(output,frame,state,frozen):
    destination=output/'importancia_permutacao.csv'
    if destination.exists():return
    identifiers=pd.read_csv(output/'particao_principal.csv',dtype={'ID':'string'})
    ids=set(identifiers.loc[identifiers.conjunto.eq('teste'),'ID'])
    test=frame.loc[frame.ID.isin(ids)]
    model=joblib.load(output/'finais'/frozen['winner']/'pipeline.joblib')
    with threadpool_limits(limits=1):
        result=permutation_importance(model,input_frame(test),test.y,scoring='average_precision',
            n_repeats=state['config']['permutation_repetitions'],random_state=state['config']['seed'],n_jobs=1)
    rows=[]
    numeric,categorical=columns(frozen['artifacts'][frozen['winner']]['representation'])
    included=set(numeric+categorical+['HDA_UNIFICADA'])
    for i,name in enumerate(ALL_FEATURES):
        if name not in included:continue
        for repeat,drop in enumerate(result.importances[i]):
            rows.append(dict(feature=name,repeat=repeat,ap_drop=float(drop)))
    pd.DataFrame(rows).to_csv(destination,index=False,encoding='utf-8-sig')


def markdown_table(table,columns):
    lines=['| '+' | '.join(columns)+' |','| '+' | '.join(['---']*len(columns))+' |']
    for row in table[columns].to_dict('records'):
        lines.append('| '+' | '.join('Indefinido' if pd.isna(row[c]) else
                     f'{row[c]:.4f}' if isinstance(row[c],float) else str(row[c]) for c in columns)+' |')
    return '\n'.join(lines)


def run_report(output,frame,state):
    frozen=verify_frozen(output)
    if not (output/'metricas_teste.csv').exists():raise ValueError('Teste não concluído')
    tables={}
    for name in ALL_MODELS:
        path=output/'finais'/name/'previsoes_teste.csv'
        if sha(path)!=read_json(path.parent/'teste_concluido.json')['prediction_sha256']:
            raise ValueError('Previsões de teste modificadas')
        tables[name]=pd.read_csv(path,float_precision='round_trip')
        if list(tables[name].ID)!=list(tables['dummy'].ID):raise ValueError('Bootstrap exige pareamento por ID')
    bootstrap(output,state,tables,frozen)
    hypothesis_holdout(output,tables,frozen)
    plots(output,tables,frozen)
    print('Importância por permutação do vencedor congelado...',flush=True)
    importance(output,frame,state,frozen)
    selection=read_json(output/'selecao_desenvolvimento.json')
    development=pd.DataFrame(selection['models'])
    test=pd.read_csv(output/'metricas_teste.csv')
    tuned=test.loc[test['mode'].eq('aprendido')]
    conventional=test.loc[test['mode'].eq('padrao_0.5')]
    winner=tuned.loc[tuned.model.eq(frozen['winner'])].iloc[0]
    representation_scores=pd.read_csv(output/'metricas_por_representacao.csv')
    representation_summary=representation_scores.loc[representation_scores['mode'].eq('aprendido')].groupby(
        ['model','representation'])[['recall','specificity','ap']].mean().reset_index()
    frozen_representation=frozen['artifacts'][frozen['winner']]['representation']
    statistical=pd.DataFrame(read_json(output/'testes_5x2.json'))
    statistical['rejeita_F_H0']=statistical.f_p_holm.map(lambda p:'Indefinido' if pd.isna(p) else
                                                       'Sim' if p<state['config']['alpha'] else 'Não')
    holdout=read_json(output/'mcnemar_teste.json')['comparisons']
    holdout_table=(markdown_table(pd.DataFrame(holdout),['target','n','winner_only_correct','logistic_only_correct','p','p_holm'])
                   if holdout else 'Logística selecionada: não há comparação contra si própria.')
    intervals=pd.read_csv(output/'bootstrap_ic95.csv')
    winner_intervals=intervals.loc[intervals.model.eq(frozen['winner'])]
    importances=pd.read_csv(output/'importancia_permutacao.csv').groupby('feature').ap_drop.agg(['mean','std']).reset_index().sort_values('mean',ascending=False)
    cols=['model','accuracy','precision','recall','specificity','f1','f2','roc_auc','ap','brier']
    text=f'''# Experimentos UCMF — resultado técnico

Classe positiva: **Anormal = 1**. Protocolo congelado antes da abertura do teste.
Vencedor escolhido exclusivamente no desenvolvimento: **{frozen['winner']}**, representação **{frozen_representation}**.
Meta de especificidade média ≥80% no desenvolvimento: **{'atingida' if frozen['target_met'] else 'não atingida; candidato exploratório'}**.
No teste, o vencedor obteve recall **{winner.recall:.4f}**, especificidade **{winner.specificity:.4f}** e AP **{winner.ap:.4f}**.
Meta de especificidade no teste: **{'atingida' if winner.specificity>=.8 else 'não reproduzida; nenhum limiar reajustado'}**.

## População e validade

Foram usados {len(frame)} perfis únicos concordantes na seleção principal. A visão complementar foi vinculada por ID para comparar 12 preditores contínuos/nominais, 9 clínicos e 15 combinados. Os grupos com rótulos conflitantes, repetições e alvos ausentes foram tratados antes desta execução conforme a auditoria. O desempenho é condicionado a essa seleção e não estima automaticamente a população completa de atendimentos. Agrupamento: **{state['grouping']}**. ID de atendimento não prova identidade de paciente. Não foi possível garantir independência por paciente sem ligação individual externa; a incerteza estatística depende dessa hipótese.

A base inteira já foi explorada anteriormente. O teste foi reservado antes dos novos ajustes, não é descrito como amostra historicamente intocada. B2, PULSOS e motivos próximos do diagnóstico continuam por decisão acadêmica. Não há validação clínica, temporal ou externa. Nem um p-valor pequeno transforma essas limitações em ausência de viés.

## Protocolo e seleção

20% para teste, estratificado e aleatório; desenvolvimento com cinco repetições de dois folds externos. Cada metade externa inclui busca interna de três folds, lista pré-especificada de {state['config']['candidates_per_family']} candidatos por família **por representação** e o Pipeline completo. AP média interna escolhe parâmetros e representação; OOF interno da configuração selecionada escolhe maior recall com especificidade ≥80%, depois precisão, especificidade e maior limiar. Essa reutilização interna pode favorecer pontuações internas; somente avaliações externas e teste estimam desempenho. Não houve SMOTE nem exclusão adicional de registros por representação. O Dummy é único, pois ignora os atributos. O orçamento menor restringe a exploração de hiperparâmetros: não se afirma encontrar o ótimo global nem superioridade entre famílias independente do orçamento.

### Comparação das representações no desenvolvimento

A contínua inclui IDADE, Peso, Altura, IMC, FC, PAS/PAD; a clínica substitui idade, antropometria e pressão por FAIXA_ETARIA, CLASSIFICACAO IMC e PPA_CALCULADA, mantendo FC. Ambas conservam SEXO, PULSOS, B2, motivos e HDA. A combinada une esses atributos. PPA/IMC categóricos usam regras clínicas externas, não são supostamente superiores por definição. Quantização perde detalhe e pode ajudar modelos simples; as conclusões aqui dependem da validação. Perfis iguais após reduzir para categorias podem pertencer a pessoas diferentes: não são tratados automaticamente como mesmo indivíduo. Registros idênticos na seleção principal já foram auditados.

{markdown_table(representation_summary,['model','representation','recall','specificity','ap'])}

Essas médias descrevem representações fixas avaliadas externamente, cada uma com tuning interno. A representação do procedimento de cada família é escolhida pela AP interna, nunca por essas pontuações externas; frequências de escolha estão em metricas_externas.csv. O teste usa somente a representação congelada de cada família. Não há novos testes de hipótese escolhidos após inspecionar esta tabela.

O mínimo de 80% é uma regra acadêmica, não meta clínica OMS. Probabilidades são convertidas por p ≥ limiar; a meta não é garantida em novas amostras. A configuração final pode ter um limiar diferente daqueles aprendidos nas metades externas. Os limiares do teste são exclusivamente os congelados no desenvolvimento inteiro. Nenhuma família foi escolhida pelo teste.

### Desenvolvimento: médias das cinco repetições externas

{markdown_table(development,['model','recall','specificity','ap','seconds','folds_below_target'])}

Detalhes dos dez folds e médias/desvios em metricas_externas.csv e resumo_externo_media_dp.csv. Desvios entre folds descrevem variabilidade; dez folds não são dez amostras independentes. As pontuações internas das buscas não são apresentadas como desempenho imparcial.

## Teste reservado — limiar aprendido

{markdown_table(tuned,cols)}

### Teste reservado — referência de limiar 0,5

{markdown_table(conventional,cols)}

Recall mede a fração de anormais detectados; FN representam anormais não sinalizados. Especificidade mede a fração de normais corretamente descartados. Precisão mostra quantos sinalizados realmente são anormais. F1 pondera precisão e recall igualmente; F2 aumenta o peso de recall. Acurácia e ROC-AUC não substituem o objetivo de detecção. AP é average_precision_score, não a área trapezoidal da PR. ROC e PR são complementares; a prevalência é a referência da PR. Brier e calibração descrevem probabilidades, não confirmam utilidade clínica. Nenhuma calibração foi ajustada usando o teste.

![Curvas ROC e PR](curvas_roc_pr.png)
![Matrizes de confusão](matrizes_confusao.png)
![Calibração](calibracao.png)

## Inferência e incerteza

testes_5x2.json apresenta quatro comparações pré-especificadas contra logística usando erro global no limiar aprendido: F combinado 5×2 principal (10,5 graus de liberdade), t original (5 graus de liberdade) como sensibilidade e Holm separado nas quatro comparações de cada análise. Esses testes são aproximados e não provam superioridade em recall. Variância nula é indefinida, sem p artificial. Não se escolhe o teste mais favorável. Não se aplicam t pareado comum, Friedman ou Nemenyi aos folds como se fossem datasets independentes.

Diferença de erro negativa favorece a família comparada; alfa={state['config']['alpha']}. Não rejeitar H0 não prova equivalência.

{markdown_table(statistical,['model','mean_difference','f_stat','f_p','f_p_holm','rejeita_F_H0','t_p_holm_sensibilidade'])}

mcnemar_teste.json compara vencedor pré-selecionado e logística, condicionando separadamente aos verdadeiros Anormal (detecção) e Normal (especificidade), com duas comparações corrigidas por Holm. A logística não é comparada contra si própria. ICs bootstrap de 95% estão em bootstrap_ic95.csv: 2000 reamostragens estratificadas e pareadas, sem refit ou novo limiar; representam incerteza do teste para modelos fixos, não toda a incerteza do procedimento de treinamento.

{holdout_table}

### Intervalos de 95% do vencedor no teste

{markdown_table(winner_intervals,['metric','estimate','lower','upper'])}

Os intervalos das diferenças pareadas contra logística estão no mesmo CSV, quando aplicável. Desvios dos folds externos e intervalos bootstrap do teste têm significados diferentes e não são intercambiáveis.

## Interpretação dos atributos

importancia_permutacao.csv contém 20 permutações por atributo original e queda em AP do vencedor. A análise é descritiva e posterior ao congelamento, sem nova seleção ou reajuste. Associações e importâncias não demonstram causalidade; atributos correlacionados podem dividir importância. HDA mede menção; não mencionado não equivale a negado. Imputações não são novas medidas clínicas.

{markdown_table(importances,['feature','mean','std'])}

## Reprodutibilidade e próximos passos

protocolo.json guarda hashes de dados, configuração, código e versões; os candidatos e todas as partições são persistidos. Buscas, avisos, parâmetros, limiares e tempos ficam nos diretórios por modelo. congelamento.json fixa artefatos, seleção e classe positiva. teste_aberto.json impede voltar ao desenvolvimento nesta execução. Retomar o teste lê previsões concluídas em vez de reavaliá-las. O cache só reutiliza operações aprendidas sobre a mesma partição; não ajusta transformações na base inteira.

As evidências apoiam a redação posterior do artigo IEEE e apresentação de avaliacao2.md; esta execução não cria/submete o artigo nem publica no GitHub. O protocolo e fontes completos estão a seguir.
'''
    text+='\n\n'+(ROOT/'referencias/protocolo_experimentos.md').read_text(encoding='utf-8')
    (output/'relatorio_experimentos.md').write_text(text,encoding='utf-8')
    paths=[p for p in output.rglob('*') if p.is_file() and '.cache' not in p.parts and p.name!='manifesto_resultados.json']
    write_json(output/'manifesto_resultados.json',dict(protocol_sha256=sha(output/'protocolo.json'),
               report_code_sha256=sha(Path(__file__)),outputs={str(p.relative_to(output)):sha(p) for p in paths}))
    print('Relatório e evidências finalizados.',flush=True)
