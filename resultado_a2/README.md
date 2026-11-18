# Dados de apoio ao artigo da A2

Este material reúne tabelas e figuras para o [enunciado da A2](../avaliacao2.md). O artigo usa o [template de conferências IEEE](https://www.ieee.org/conferences/publishing/templates), duas colunas, até cinco páginas, resumo de 100–150 palavras e link para [o repositório público](https://github.com/gustavopfont/mineracao-dados) no rodapé da primeira página.

O resultado principal é a comparação da **Random Forest com a regressão logística no teste reservado da v3**. A floresta com perfil clínico foi selecionada no desenvolvimento e atingiu **64,31% de sensibilidade** e **80,96% de especificidade** no teste. A logística atingiu **64,62%** e **81,87%**, respectivamente. A diferença pareada de sensibilidade foi **−0,31 ponto percentual** (IC95% nominal **−1,95 a +1,44**, **p Holm = 0,828**). O teste não demonstrou superioridade da floresta na detecção de Anormal.

| Parte do artigo | Evidência para usar |
| --- | --- |
| Resumo e introdução | Prever o rótulo registrado `NORMAL X ANORMAL` em atendimentos de cardiologia pediátrica. Apresentar a comparação entre baseline simples e modelo complexo e a sensibilidade no teste reservado. |
| Dados e análise exploratória | [Relatório de finalização](../resultado_analise/relatorio_finalizacao.md), [auditoria do preparo](../resultado_modelagem_preparo/relatorio_adequacao.md), [contagens por partição](contagens_por_particao.csv), [gráfico de SOPRO e alvo](figura_sopro_alvo.png) e seus [denominadores](sopro_alvo_contagens.csv). |
| Metodologia | [Protocolo v3](../referencias/protocolo_experimentos.md), [configuração e sementes](../config_experimentos.json), [modelos e limiares congelados](../resultado_experimentos_reduzido/modelos_selecionados.json) e [fontes do preparo](../referencias/metodologia_preparo.md). |
| Resultados e discussão | [Tabela do teste da v3](desempenho_teste_v3.csv), [matrizes de confusão](figura_matrizes_teste_v3.png), [IC95% e diferenças pareadas](../resultado_experimentos_reduzido/bootstrap_ic95.csv), [McNemar planejado](../resultado_experimentos_reduzido/mcnemar_teste.json) e [importância por permutação da floresta](importancia_floresta_v3.csv). |
| Robustez e limitações | [Médias por desenho de validação](desempenho_desenvolvimento.csv), [testes exploratórios da r01](../resultado_experimentos_rodadas/r01_5folds_2rep_12cand/inferencia_exploratoria/relatorio.md), [extensão com ablações e curvas de aprendizado](../resultado_experimentos_ampliado_publicado/relatorio_comparativo.md) e [análise pós-hoc no teste histórico da v3](teste_exploratorio_floresta_knn_v3.json). |

## Dados e figuras

A base bruta registra **12.873 atendimentos**. A base auditável final tem **12.134 registros e 17 colunas**, incluindo ID e alvo. Para a modelagem ficaram **11.436** registros. A preparação separou **429 sem alvo**, **142** em grupos com rótulos conflitantes e **127** duplicatas concordantes. A divisão estratificada da v3, com semente 42, deixou **9.148** para desenvolvimento e **2.288** para teste. No teste, **975** eram Anormal e **1.313**, Normal. O ID identifica o registro e a independência por paciente é desconhecida.

**Legenda para a figura exploratória.** Proporção de registros rotulados como Anormal entre atendimentos com SOPRO preenchido e alvo conhecido, antes da seleção de preditores. Nos **11.682** pares válidos, foram **720/7.260 (9,9%)** quando SOPRO indicava ausência do achado e **4.233/4.422 (95,7%)** quando havia tipo de sopro registrado. A tabela original por categoria teve **V de Cramér = 0,842**. A exclusão de SOPRO do treinamento seguiu a decisão pedagógica da A2. A associação, por si só, não estabelece vazamento. O motivo de encaminhamento por sopro continuou disponível.

**Legenda para a figura de resultados.** Matrizes de confusão da logística e da floresta no mesmo teste reservado da v3, com limiares aprendidos no desenvolvimento. A floresta deixou de sinalizar **348 dos 975** registros Anormal e sinalizou **250 dos 1.313** registros Normal. A logística registrou **345 falsos negativos** e **238 falsos positivos**. As [curvas ROC e PR originais](../resultado_experimentos_reduzido/curvas_roc_pr.png) também estão disponíveis.

## Números que cabem na tabela principal

Métricas no teste reservado da v3 com limiar aprendido. AP é *average precision*.
Para uma tabela em uma coluna, priorize sensibilidade, especificidade, AP e F1. A tabela completa também serve como referência para a apresentação.

| Modelo | Acurácia | Sensibilidade | Especificidade | Precisão | F1 | ROC-AUC | AP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Dummy | 0,574 | 0,000 | 1,000 | 0,000 | 0,000 | 0,500 | 0,426 |
| Logística | 0,745 | 0,646 | 0,819 | 0,726 | 0,684 | 0,789 | 0,763 |
| Árvore | 0,699 | 0,557 | 0,805 | 0,680 | 0,612 | 0,743 | 0,695 |
| KNN | 0,708 | 0,581 | 0,802 | 0,685 | 0,629 | 0,760 | 0,712 |
| Random Forest | 0,739 | 0,643 | 0,810 | 0,715 | 0,677 | 0,802 | 0,775 |
| HistGradientBoosting | 0,740 | 0,650 | 0,807 | 0,715 | 0,681 | 0,804 | 0,775 |

O Dummy evidencia por que acurácia isolada é insuficiente: alcança **57,4%** mesmo sem detectar nenhum Anormal no limiar avaliado. A sensibilidade foi a medida operacional principal, lida junto da especificidade. O mínimo de **80%** foi uma escolha acadêmica para aprender o limiar no desenvolvimento e pode falhar em alguns folds. Na floresta, `MOTIVO_UNIFICADO` e `B2` foram os campos de maior queda média em AP quando permutados. A interpretação depende de quando esses campos estariam disponíveis no atendimento.

## Separação das evidências

- **v3, teste reservado:** a comparação planejada por McNemar é floresta × logística. A validação aninhada no desenvolvimento usou cinco repetições de dois folds externos, três folds internos e quatro configurações por família e perfil. A seleção e o limiar precederam a avaliação do teste.
- **r01 e extensão, desenvolvimento:** ampliar a grade no mesmo 5×2 mudou pouco as médias. Nas rodadas 2×5, a floresta liderou em sensibilidade média entre os modelos em comum, e o boosting, em AP. O contraste exploratório da r01 encontrou **+5,49 pontos percentuais** de sensibilidade para floresta sobre KNN (Holm **p = 0,0222**). Esse p-valor se refere à validação cruzada repetida da r01.
- **v3, contraste pós-hoc floresta × KNN:** entre os 975 registros Anormal, 106 foram detectados só pela floresta e 45 só pelo KNN. A diferença de sensibilidade foi **+6,26 pontos percentuais** (IC95% bootstrap nominal **+3,90 a +8,72**, Holm **p = 0,00000150**). A diferença de especificidade foi **+0,76 ponto percentual** (Holm **p = 0,468**). O McNemar usa exclusivamente as previsões congeladas da v3 no teste já avaliado, com Holm para os dois contrastes por classe. Confirmar um ganho da r01 exigiria avaliar seus modelos congelados em dados independentes.

As ablações com retirada conjunta de motivos, HDA, B2 e pulsos reduziram a sensibilidade média em **21,6–23,6 pontos percentuais**. Isso sustenta discutir a dependência do desempenho em informações clínicas próximas do alvo. Para fechar as limitações, registre a seleção dos perfis concordantes, a ausência de identificação por paciente, a dependência entre folds e a necessidade de validação externa. A base inteira já havia passado por exploração histórica. A reserva do teste valeu para os ajustes da v3.

## Fontes e reprodução

As fontes clínicas são as referências de [crescimento e IMC da OMS](../referencias/README.md) e a [Diretriz Brasileira de Hipertensão de 2025](https://www.scielo.br/j/abc/a/BXT7Vk4B9VKQnJFsJhgJ4Hn/?lang=pt). As decisões de preparo e modelagem estão documentadas na [matriz metodológica](../referencias/metodologia_preparo.md) e no [protocolo v3](../referencias/protocolo_experimentos.md). Para relato, consulte [TRIPOD+AI](https://pmc.ncbi.nlm.nih.gov/articles/PMC11019967/).

Para regenerar as tabelas e figuras a partir dos artefatos versionados, execute `python scripts/preparar_evidencias_a2.py` na raiz do repositório. O argumento opcional `--incluir-teste-exploratorio` recalcula o McNemar pós-hoc quando as previsões locais congeladas da v3 estão disponíveis. O código confere os hashes das previsões, os IDs do teste, os limiares e as matrizes publicadas antes de gravar somente resultados agregados.
