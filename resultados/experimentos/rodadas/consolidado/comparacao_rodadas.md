# Comparação consolidada das rodadas de desenvolvimento

Atualizado em 2026-11-18T03:01:20+00:00. Médias, por modelo, das métricas agregadas por repetição (previsões fora do treino, limiar aprendido dentro do treino). Todas as rodadas usam a mesma população de desenvolvimento; o teste reservado não entra aqui.

| rodada | folds_externos | repeticoes | folds_internos | candidatos_por_perfil | estado | folds_completos | folds_total |
| --- | --- | --- | --- | --- | --- | --- | --- |
| v3_5x2_4cand | 2 | 5 | 3 | 4 | concluida (teste avaliado) | 10 | 10 |
| r01_5folds_2rep_12cand | 5 | 2 | 3 | 12 | concluida | 10 | 10 |

### Sensibilidade (recall de Anormal)

| model | v3_5x2_4cand | r01_5folds_2rep_12cand |
| --- | --- | --- |
| dummy | 0.0000 | 0.0000 |
| logistica | 0.6382 | 0.6397 |
| arvore | 0.5345 | 0.6154 |
| knn | 0.5713 | 0.5944 |
| floresta | 0.6439 | 0.6493 |
| boosting | 0.6419 | 0.6442 |

### Especificidade

| model | v3_5x2_4cand | r01_5folds_2rep_12cand |
| --- | --- | --- |
| dummy | 1.0000 | 1.0000 |
| logistica | 0.8026 | 0.8035 |
| arvore | 0.8338 | 0.8076 |
| knn | 0.8050 | 0.8179 |
| floresta | 0.8023 | 0.8066 |
| boosting | 0.8067 | 0.8083 |

### AP

| model | v3_5x2_4cand | r01_5folds_2rep_12cand |
| --- | --- | --- |
| dummy | 0.4261 | 0.4260 |
| logistica | 0.7505 | 0.7540 |
| arvore | 0.6677 | 0.7345 |
| knn | 0.6947 | 0.7071 |
| floresta | 0.7563 | 0.7637 |
| boosting | 0.7593 | 0.7637 |

### Folds com especificidade abaixo de 80%

| model | v3_5x2_4cand | r01_5folds_2rep_12cand |
| --- | --- | --- |
| dummy | 0/10 | 0/10 |
| logistica | 5/10 | 3/10 |
| arvore | 1/10 | 5/10 |
| knn | 3/10 | 2/10 |
| floresta | 4/10 | 4/10 |
| boosting | 4/10 | 3/10 |

Diferenças entre rodadas misturam o tamanho do treino externo (50% na v3, 80% com cinco folds), o orçamento de hiperparâmetros e a semente dos folds; não são testes de hipótese e não substituem a avaliação no teste da v3. Repetições e folds reaproveitam os mesmos registros, então desvios não são erros-padrão. Detalhes por fold em metricas_externas_todas_rodadas.csv.
