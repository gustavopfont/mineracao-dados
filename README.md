# Pré-processamento do conjunto UCMF

## Experimentos preditivos de NORMAL X ANORMAL

O repositório registra quatro rodadas de treinamento e uma preparação anterior da A1. A v3 avaliou os modelos no teste reservado. A rodada ampliada concluiu uma comparação exploratória nos mesmos dados de desenvolvimento.

| Rodada | Representações e orçamento | Execução comprovada | Resultados |
| --- | --- | --- | --- |
| A1 · `resultado_modelagem/` | Preparação com partições e transformador | Artefatos legados de preparação | [Resumo e artefatos da A1](resultado_modelagem/) |
| v1 · `resultado_experimentos/` | Perfil contínuo, 12 candidatos previstos por família | Interrompida antes do teste. Uma busca persistida, do Dummy no primeiro fold externo | [Configuração e buscas registradas](referencias/inventario_experimentos.json) |
| v2 · `resultado_experimentos_representacoes/` | Contínua, clínica e combinada, 12 candidatos por família/perfil | Interrompida antes do teste. 42 buscas persistidas em três folds externos, com o terceiro parcial | [Configuração e buscas registradas](referencias/inventario_experimentos.json) |
| v3 · `resultado_experimentos_reduzido/` | Três perfis, 4 candidatos por família/perfil | Concluída. 160 buscas externas e 16 buscas finais, incluindo o Dummy, com teste reservado avaliado | [Relatório técnico](resultado_experimentos_reduzido/relatorio_experimentos.md) |
| Extensão · `resultado_experimentos_ampliado_publicado/` | Três perfis, 12 e 16 candidatos no 5×2, 12 no 2×5 | Concluída. 200 avaliações no 5×2, 100 no 2×5 e 120 nas análises complementares | [Relatório comparativo](resultado_experimentos_ampliado_publicado/relatorio_comparativo.md) |

O [inventário de hiperparâmetros da v1 à v3](referencias/inventario_experimentos.json) reúne as combinações exatas dessas rodadas. Para verificar o que foi executado, consulte `buscas_registradas`: cada tentativa aponta pelo índice para a lista da família e informa quantos folds internos produziram AP. Candidatos sem busca persistida têm execução indeterminada. As grades, sementes e versões da extensão estão no [protocolo da rodada ampliada](resultado_experimentos_ampliado_publicado/protocolo.json).

Os [parâmetros e limiares congelados da v3](resultado_experimentos_reduzido/modelos_selecionados.json) incluem versões e hashes dos dados. A grade e os argumentos fixos, como 200 árvores na floresta, estão em [`scripts/modelos_ucmf.py`](scripts/modelos_ucmf.py).

| Modelo | Perfil final | Hiperparâmetros selecionados na v3 |
| --- | --- | --- |
| Dummy | Contínua (atributos ignorados) | `strategy=prior` |
| Regressão logística | Contínua | `C=1`, `class_weight=balanced` |
| Árvore de decisão | Clínica | `max_depth=None`, `min_samples_leaf=5`, `class_weight=None` |
| KNN | Contínua | `n_neighbors=41`, `weights=distance`, `p=2` |
| Random Forest | Clínica | `max_depth=None`, `min_samples_leaf=10`, `max_features=sqrt`, `class_weight=balanced_subsample` |
| HistGradientBoosting | Combinada | `max_iter=200`, `learning_rate=0.03`, `max_leaf_nodes=15`, `l2_regularization=1` |

### Comparação disponível e próximas etapas

A floresta clínica foi selecionada no desenvolvimento. No teste reservado, teve sensibilidade de **64,31%** e especificidade de **80,96%**. A diferença pareada de sensibilidade contra a logística foi **−0,31 ponto percentual** (IC95% **−1,95 a +1,44**; McNemar com Holm, **p = 0,828**). O F combinado 5×2 para erro global também não encontrou diferença entre esses modelos (**p ajustado = 0,645**). O estudo ainda tem incerteza sobre o ganho em detecção e sobre o desempenho em outros pacientes.

Consulte as [partições do desenvolvimento e teste](resultado_experimentos_reduzido/particao_principal.csv), as [métricas por fold](resultado_experimentos_reduzido/metricas_externas.csv), as [métricas por representação](resultado_experimentos_reduzido/metricas_por_representacao.csv), as [métricas do teste](resultado_experimentos_reduzido/metricas_teste.csv), o [F/t 5×2](resultado_experimentos_reduzido/testes_5x2.json), o [McNemar](resultado_experimentos_reduzido/mcnemar_teste.json) e os [IC95% bootstrap](resultado_experimentos_reduzido/bootstrap_ic95.csv).

O [plano da próxima comparação](referencias/plano_comparacao_modelos.md) prioriza auditar os erros, medir o que muda ao aumentar o tuning nos mesmos folds e avaliar a estabilidade em cinco folds externos repetidos. Curvas de aprendizado e revisão de rótulos investigam o erro residual. Uma nova coorte independente permitiria confirmar diferenças com modelos e limiares congelados. A comparação já concluída sustenta a redação da [A2](avaliacao2.md).

### Resultados da comparação ampliada

Nas mesmas partições 5×2 da v3, ampliar de quatro para 12 ou 16 configurações manteve as métricas médias próximas. Os testes F e t exploratórios do 5×2, com Holm, não encontraram diferença de erro global entre floresta ou boosting e logística. No 2×5, a floresta teve a maior sensibilidade média (**65,20%**, com **80,47%** de especificidade), e o boosting teve a maior AP média (**0,7641**). São resultados de desenvolvimento. O teste reservado da v3 continua sendo a referência para a comparação dos modelos congelados daquela rodada.

Na ablação que retira motivos, HDA, B2 e pulsos, a sensibilidade média caiu de **21,6 a 23,6 pontos percentuais**, conforme o modelo. A retirada isolada de PPA ou de uma representação de IMC apresentou efeitos médios pequenos nas configurações avaliadas. Consulte as [tabelas e a trilha de reprodução da extensão](resultado_experimentos_ampliado_publicado/README.md).

### Como executar a comparação ampliada

O [executor da extensão](scripts/comparar_modelos_ucmf.py) usa os 9.148 registros de desenvolvimento histórico. No **5×2**, ele repete cinco vezes a divisão em duas metades e alterna qual metade é usada para treino e qual para avaliação. Verifica as partições da v3, testa 12 candidatos por perfil com os quatro originais incluídos e avalia um braço de 16 candidatos com quatro combinações extras. Em seguida, executa o **2×5**, com duas repetições de cinco folds e 12 candidatos por perfil. Nos dois desenhos, o tuning usa três folds internos a cada treino externo. A rodada opcional de 10 folds externos foi retirada da execução. As comparações novas priorizam logística, floresta e boosting, com Dummy como referência.

O executor grava partições, buscas, previsões e análises em `resultado_experimentos_ampliado/`. Gera o relatório ao terminar cada desenho e o atualiza quando as análises complementares terminam. A publicação em `resultado_experimentos_ampliado_publicado/` contém os resultados agregados para consulta.

```powershell
.\.venv\Scripts\python.exe scripts/comparar_modelos_ucmf.py --status
Get-Content resultado_experimentos_ampliado/execucao_stdout.log -Tail 20
```

Para iniciar ou retomar a execução local, use `.\.venv\Scripts\python.exe -u scripts/comparar_modelos_ucmf.py`. Os checkpoints exigem entradas e código com os mesmos hashes. Use as versões do protocolo, incluindo scikit-learn 1.9.1, registrado na execução. Uma validação confirmatória com outro hold-out depende de obter uma coorte independente.

### Reprodução e acompanhamento

Os resultados finais publicados em `resultado_experimentos_reduzido/` são uma saída de consulta. Checkpoints, pipelines binários, logs e arquivos de controle da execução ficam locais. Para reproduzir os experimentos sem sobrescrever essa saída, use um diretório novo:

```powershell
python scripts/treinar_modelos.py --fase todos --saida resultado_experimentos_reproducao
```

O executor atual compara regressão logística, árvore, KNN, Random Forest e HistGradientBoosting, mais DummyClassifier. Cada família compara atributos contínuos, categorias clínicas e combinação dos dois, vinculando `atributos_complementares.csv` por ID à base supervisionada. Assim, IMC e sua classificação, PAS/PAD e PPA são comparados sem presumir superioridade. O perfil escolhido faz parte do tuning **interno**, não é escolhido olhando o teste.

```powershell
python scripts/treinar_modelos.py --fase desenvolvimento
python scripts/treinar_modelos.py --fase congelar
python scripts/treinar_modelos.py --fase teste
python scripts/treinar_modelos.py --fase relatorio
```

`--fase todos` executa a sequência com checkpoints. A saída válida é `resultado_experimentos_reduzido/`, com **quatro configurações por perfil**, mantendo três perfis e validação externa 5×2/interna de três folds. A busca de 12 configurações em `resultado_experimentos_representacoes/` foi encerrada por solicitação do usuário antes do teste: resultados, configuração e código original foram preservados. A execução ainda anterior está em `resultado_experimentos/`; não misturar seus resultados. A retomada exige hashes idênticos de código/dados/configuração/ambiente; mudanças exigem novo diretório. Depois de abrir o teste, não é permitido voltar ao desenvolvimento na mesma execução. Reexecutar teste lê as previsões já concluídas, sem nova predição. Relatório e bootstrap também podem ser retomados. Os modelos joblib devem ser carregados apenas de fontes confiáveis.

O [protocolo fundamentado](referencias/protocolo_experimentos.md) especifica 20% de teste aleatório estratificado, validação externa 5×2 e tuning interno de três folds. São quatro configurações por família/perfil (12/família), sorteadas da grade pré-especificada; fit ocorre exclusivamente nas partições de treino. O critério operacional é recall de Anormal sob especificidade interna ≥80%, uma escolha acadêmica, sem validação clínica. O teste não reajusta o limiar. AP seleciona hiperparâmetros e representação; p-valores não escolhem o vencedor. A redução do orçamento não garante encontrar o ótimo global.

Partições, buscas, previsões, métricas, testes F/t 5×2, Holm, McNemar, IC bootstrap, figuras e importâncias são salvos com os modelos congelados. `config_experimentos.json` fixa orçamento e sementes. A opção `--grupos caminho.csv` aceita ID/paciente_id confirmados, sem usar esses campos como preditores. Sem esse mapeamento, não é possível garantir separação por pessoa: o ID disponível identifica registro. Todos os perfis usam os mesmos registros, inclusive aqueles com faltantes; categorias não são recalculadas de valores imputados.

O relatório técnico e os resultados da v3 são fontes para o artigo solicitado em `avaliacao2.md`.

### Acompanhar a execução longa

`scripts/executar_experimentos_background.py` mantém a sequência completa com logs e estado final, usando os mesmos checkpoints. Nesta execução foi iniciado como processo local oculto, sem janela interativa. Para consultar:

```powershell
python scripts/status_experimentos.py
Get-Content resultado_experimentos_reduzido/execucao_stdout.log -Tail 20
```

O estado está em `estado_execucao.json`; erros/avisos em `execucao_stderr.log`; o relatório só está pronto quando `manifesto_resultados.json` existir. O wrapper registra concluída/falhou e usa lock para impedir dois wrappers simultâneos. Não iniciar outro executor direto enquanto esse trabalho estiver ativo. A execução depende de o computador permanecer ligado; se o processo for encerrado abruptamente, o estado pode permanecer antigo e um lock remanescente exige conferir o processo antes de qualquer retomada. O relatório final deve ser revisado depois da conclusão, sem interpretar resultados parciais como a comparação completa.

Projeto da Avaliação 1 de Mineração de Dados. O conjunto bruto registra atendimentos em cardiologia pediátrica. O objetivo desta etapa é examinar a qualidade dos dados, limpar inconsistências, criar atributos justificados e comparar as variáveis com NORMAL X ANORMAL.

## Base final para a próxima etapa

### Preparação supervisionada antes dos modelos

O fluxo atual consome a base final auditável e produz uma seleção supervisionada em diretório separado:

```powershell
python scripts/auditar_base_modelagem.py
python scripts/preparar_modelagem.py
python -m unittest discover -s tests -v
```

O primeiro comando valida valores e classificações, torna HDA contraditória indisponível, separa conflitos, deduplica perfis concordantes pelo menor ID e mantém a trilha de todos os registros. Gera `resultado_modelagem_preparo/UCMF_supervisionado.csv`, visão complementar de derivados, registros sem alvo, mapas, relatório e manifesto. O segundo apenas valida o contrato e declara o transformador; **não divide a base nem ajusta parâmetros**. O antigo `--momento` foi retirado e o comando não aceita mais SOPRO como preditor. As divisões e objetos já existentes em `resultado_modelagem/` são legados, não entram no fluxo novo e permanecem preservados.

Fontes e limites de **cada etapa** estão na [matriz metodológica](referencias/metodologia_preparo.md): OMS e SBC/SBN/SBH para critérios de saúde, literatura de predição clínica para métodos, scikit-learn para execução. Limites técnicos, deduplicação de perfis e escolha da mediana são identificados como decisões locais. A mediana é um baseline a comparar, não uma regra clínica OMS. Os scripts e testes são o código das alterações; mapas e correções permitem auditar o efeito em cada ID.

O KDD da A2 já inclui seleção, limpeza, adequação da base, comparação de modelos com pré-processamento ajustado nas partições e uma primeira interpretação dos erros e da importância dos atributos. O artigo IEEE e a apresentação previstos em `avaliacao2.md` consolidam essas evidências.

`resultado_analise/UCMF_base_final.csv` é a versão final do pré-processamento: 12.134 registros e 17 colunas. Preserva os 429 alvos desconhecidos, une motivos e HDA, acrescenta faixas etárias e classificação da medida de pressão e exclui SOPRO e convênio. ID é apenas metadado de rastreabilidade.

```powershell
python scripts/finalizar_dataset.py
```

Esse comando refaz a limpeza em memória a partir do bruto, confere a equivalência com `UCMF_limpo.csv` e gera os novos arquivos sem sobrescrever essas referências. Não executa divisão, imputação estatística ou treino, nem altera `resultado_modelagem/`. A geração funciona sem rede. Requer as dependências de `requirements.txt`; o ambiente local criado nesta etapa pode ser usado por `.\.venv\Scripts\python`.

A revisão de discretização mantém IMC, PAS e PAD contínuos e as categorias detalhadas OMS/DBHA. O relatório compara largura uniforme, quantis, k-means e cortes clínicos/supervisionados. Os CSVs `cobertura_discretizacao.csv`, `frequencias_discretizacao.csv` e `alvo_por_categoria_discretizacao.csv` mostram contagens e denominadores por referência etária e sexo. `continuas_por_alvo_discretizacao.csv` descreve as medidas nesses estratos; `diagnostico_quantis.csv` e `intervalos_quartis_descritivos.csv` descrevem empates sem criar atributos para o modelo. `auditoria_imc_final.csv` registra referência, idade e motivo de classificação por ID. A procedência e a fórmula de recuperação da altura constam nas auditorias de finalização e PPA.

Consulte `resultado_analise/relatorio_finalizacao.md` para resultados, fontes e limitações, `dataset.md` para o esquema e `referencias/README.md` para as tabelas de pressão. `auditoria_finalizacao.csv` registra uniões, idade e atributos retirados; `comparacao_ppa_final.csv` contém a PPA legada, classificação nova, limiares e impedimentos; `associacoes_final.csv` e `frequencias_associacoes_final.csv` documentam as relações, incluindo SOPRO antes de sua retirada. As auditorias `*_limpeza_reproduzida.csv` mantêm a trilha desde o bruto. `manifesto_base_final.json` guarda hashes de entradas e saídas.

As seções seguintes descrevem a etapa anterior e seu preparo opcional de modelagem. A PPA legada em `UCMF_limpo.csv` continua sem recálculo; a coluna validada por regras externas é `PPA_CALCULADA` na base final. Ela descreve a medida, sem confirmar diagnóstico clínico. A escolha de manter achados do exame e cardiopatia já conhecida corresponde ao exercício acadêmico, não à validação de um modelo prospectivo.

## Organização

| Local | Conteúdo |
| --- | --- |
| UCMF_raw.csv | Dados recebidos. Não é modificado pelo processamento. |
| scripts/analise_dataset.py | Leitura, limpeza, auditoria, análise e gráficos. |
| scripts/classificacao_imc.py | Classificação descritiva do IMC com referências da OMS. |
| referencias/ | Pontos de corte da OMS e indicação das fontes. |
| resultado_analise/UCMF_limpo.csv | Conjunto processado, com 21 colunas originais e CLASSIFICACAO IMC. |
| resultado_analise/alteracoes.csv | Valores originais e finais por ID e regra aplicada. |
| resultado_analise/pendencias.csv | Casos que não admitem correção segura apenas com o CSV. |
| resultado_analise/linhas_removidas.csv | Registros sem dados clínicos excluídos. |
| resultado_analise/registros_semelhantes.csv | Registros iguais nos demais campos, mantidos para revisão. |
| resultado_analise/qualidade_dados.csv | Ausências, limites e pendências por variável. |
| resultado_analise/resumo_*.csv | Resumos univariados numéricos, categóricos e de datas. |
| resultado_analise/bivariada_*.csv | Comparações com NORMAL X ANORMAL. |
| resultado_analise/graficos/ e graficos_bivariada/ | Visualizações correspondentes. |
| resultado_analise/relatorio_analise.md | Resumo interpretativo das saídas. |
| scripts/gerar_relatorio_a1.py | Geração do relatório paginado para a A1. |
| resultado_analise/relatorio_A1.pdf | Versão de cinco páginas, Arial 10, com gráfico inserido. |
| scripts/preparar_modelagem.py | Contrato atual e declaração de transformações; ajuste somente em partições futuras. |
| resultado_modelagem/ | IDs de treino e teste, conflitos de rótulo, transformador e resumo. |
| plano_modelagem.md | Decisão e justificativa para cada variável na próxima etapa. |
| docs.md | Registro da limpeza, justificativas e limites. |
| dataset.md | Dicionário de variáveis e regras de representação. |
| slides/ | Material das aulas. |

## Executar

Na raiz do projeto:

```powershell
python -m pip install -r requirements.txt
python scripts/analise_dataset.py
python scripts/gerar_relatorio_a1.py
```

O comando regenera os arquivos de resultado_analise/ e docs.md. O CSV bruto permanece intacto. Para verificar as regras principais:

```powershell
python -m unittest discover -s tests
```

Para verificar o contrato de entrada e declarar o transformador sem ajuste:

```powershell
python scripts/preparar_modelagem.py
```

Esse comando verifica o esquema supervisionado e declara o transformador. A separação e o ajuste fazem parte de `scripts/treinar_modelos.py`, conforme o histórico de experimentos.

## Critérios de interpretação

O arquivo limpo mantém valores ausentes quando não há informação suficiente para recuperar um valor confiável. PPA não é recalculada: Não Calculado passou a vazio e as classificações informadas na origem permanecem sem validação clínica. Os dados e gráficos não devem ser usados para diagnóstico. Consulte pendencias.csv antes de concluir que uma variável está completa.

O relatório em Markdown guarda o detalhamento técnico. O PDF aplica o limite de cinco páginas e Arial 10 da A1; o grupo deve revisar a redação e os resultados antes da submissão no SIGAA. A apresentação oral de 15 minutos é uma entrega separada.

## Uso de IA generativa

OpenAI Codex auxiliou a auditoria, a correção dos scripts, a organização das saídas e a redação inicial da documentação. O grupo deve revisar os resultados e registrar o uso da ferramenta na entrega.
