# Pré-processamento do conjunto UCMF

## Experimentos preditivos — protocolo com três representações

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

O relatório técnico gerado será a fonte para a redação posterior do artigo solicitado em `avaliacao2.md`. Não há publicação no GitHub nem submissão automática.

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

Etapas do KDD para a A2: (1) seleção e limpeza documentadas; (2) adequação da base e declaração de transformadores, nesta entrega; (3) comparação futura de baseline e modelo complexo com pré-processamento ajustado dentro das partições, prioridade para Anormal e definição do limiar sem consultar teste; (4) interpretação dos erros, limitações e importância dos atributos; (5) artigo IEEE e apresentação previstos em `avaliacao2.md`. O enunciado é preservado. Não há resultados de modelos nesta fase.

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

Esse comando agora apenas verifica o esquema supervisionado e declara o transformador sem ajuste. A separação e o ajuste ocorrerão na etapa futura de experimentos. As saídas antigas descritas abaixo são da A1; não representam o esquema supervisionado novo.

## Critérios de interpretação

O arquivo limpo mantém valores ausentes quando não há informação suficiente para recuperar um valor confiável. PPA não é recalculada: Não Calculado passou a vazio e as classificações informadas na origem permanecem sem validação clínica. Os dados e gráficos não devem ser usados para diagnóstico. Consulte pendencias.csv antes de concluir que uma variável está completa.

O relatório em Markdown guarda o detalhamento técnico. O PDF aplica o limite de cinco páginas e Arial 10 da A1; o grupo deve revisar a redação e os resultados antes da submissão no SIGAA. A apresentação oral de 15 minutos é uma entrega separada.

## Uso de IA generativa

OpenAI Codex auxiliou a auditoria, a correção dos scripts, a organização das saídas e a redação inicial da documentação. O grupo deve revisar os resultados e registrar o uso da ferramenta na entrega.
