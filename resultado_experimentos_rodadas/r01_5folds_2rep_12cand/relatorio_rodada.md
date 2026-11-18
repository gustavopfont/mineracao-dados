# Rodada r01_5folds_2rep_12cand — resultado técnico

Cinco folds externos repetidos duas vezes, três folds internos e 12 candidatos por família/perfil: os quatro da v3 mais oito inéditos da mesma grade (logística percorre a grade inteira).

Estado: **concluída** — 10 de 10 folds externos completos. Classe positiva: **Anormal = 1**. Gerado em 2026-11-18T03:00:36+00:00.

## Desenho

| Item | Valor |
| --- | --- |
| População | Desenvolvimento da v3 (9.148 registros). O teste reservado não é carregado, avaliado nem usado para escolher nada. |
| Validação externa | 5 folds × 2 repetições (sementes [606, 707]) |
| Tuning interno | 3 folds; semente interna = semente externa × 10 + índice do fold |
| Candidatos por família/perfil | 12 (sorteio sem reposição, semente 4242; v3 incluídos primeiro: sim) |
| Seleção | AP interna escolhe candidato e perfil; limiar de maior recall com especificidade interna ≥ 80% |
| Execução | 6 processos; pipelines, cache e previsões por fold ficam locais |

| familia | grade | candidatos | da_v3 | grade_completa |
| --- | --- | --- | --- | --- |
| logistica | 12 | 12 | 4 | sim |
| arvore | 24 | 12 | 4 | não |
| knn | 20 | 12 | 4 | não |
| floresta | 54 | 12 | 4 | não |
| boosting | 36 | 12 | 4 | não |

## Desenvolvimento: média dos folds externos (limiar aprendido)

| model | folds | recall_media | recall_dp | especificidade_media | especificidade_dp | ap_media | brier_media | segundos_medios | folds_abaixo_da_meta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dummy | 10 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | 0.4261 | 0.2445 | 2.0521 | 0 |
| logistica | 10 | 0.6397 | 0.0196 | 0.8035 | 0.0154 | 0.7547 | 0.1814 | 15.5786 | 3 |
| arvore | 10 | 0.6154 | 0.0269 | 0.8076 | 0.0330 | 0.7341 | 0.1920 | 8.7771 | 5 |
| knn | 10 | 0.5944 | 0.0173 | 0.8179 | 0.0175 | 0.7061 | 0.1933 | 30.0264 | 2 |
| floresta | 10 | 0.6493 | 0.0175 | 0.8066 | 0.0179 | 0.7647 | 0.1796 | 128.4763 | 4 |
| boosting | 10 | 0.6442 | 0.0144 | 0.8083 | 0.0141 | 0.7653 | 0.1773 | 68.5610 | 3 |

## Agregado por repetição (previsões fora do treino de todos os folds)

| model | repeticoes_agregadas | recall_agregado | especificidade_agregada | ap_agregada |
| --- | --- | --- | --- | --- |
| dummy | 2 | 0.0000 | 1.0000 | 0.4260 |
| logistica | 2 | 0.6397 | 0.8035 | 0.7540 |
| arvore | 2 | 0.6154 | 0.8076 | 0.7345 |
| knn | 2 | 0.5944 | 0.8179 | 0.7071 |
| floresta | 2 | 0.6493 | 0.8066 | 0.7637 |
| boosting | 2 | 0.6442 | 0.8083 | 0.7637 |

## Perfis fixos (média dos folds, limiar aprendido)

| model | representation | recall | specificity | ap |
| --- | --- | --- | --- | --- |
| arvore | clinica | 0.6154 | 0.8076 | 0.7341 |
| arvore | combinada | 0.6075 | 0.8058 | 0.7201 |
| arvore | continua | 0.6126 | 0.8070 | 0.7264 |
| boosting | clinica | 0.6485 | 0.8069 | 0.7643 |
| boosting | combinada | 0.6449 | 0.8071 | 0.7654 |
| boosting | continua | 0.6443 | 0.8097 | 0.7658 |
| dummy | continua | 0.0000 | 1.0000 | 0.4261 |
| floresta | clinica | 0.6469 | 0.8081 | 0.7642 |
| floresta | combinada | 0.6506 | 0.8070 | 0.7619 |
| floresta | continua | 0.6525 | 0.8033 | 0.7656 |
| knn | clinica | 0.5956 | 0.8181 | 0.7088 |
| knn | combinada | 0.5581 | 0.8112 | 0.6824 |
| knn | continua | 0.5749 | 0.8210 | 0.7053 |
| logistica | clinica | 0.6401 | 0.8046 | 0.7531 |
| logistica | combinada | 0.6383 | 0.8057 | 0.7546 |
| logistica | continua | 0.6394 | 0.8045 | 0.7551 |

## Perfil escolhido pelo procedimento

| model | representation | folds_em_que_foi_escolhida |
| --- | --- | --- |
| arvore | clinica | 10 |
| boosting | clinica | 1 |
| boosting | combinada | 5 |
| boosting | continua | 4 |
| dummy | continua | 10 |
| floresta | clinica | 6 |
| floresta | continua | 4 |
| knn | clinica | 9 |
| knn | continua | 1 |
| logistica | clinica | 1 |
| logistica | combinada | 1 |
| logistica | continua | 8 |

## Hiperparâmetros escolhidos (perfil do procedimento)

| model | parametros | folds |
| --- | --- | --- |
| arvore | {"class_weight": "balanced", "max_depth": 12, "min_samples_leaf": 20} | 8 |
| arvore | {"class_weight": null, "max_depth": 12, "min_samples_leaf": 20} | 2 |
| boosting | {"l2_regularization": 1, "learning_rate": 0.03, "max_iter": 200, "max_leaf_nodes": 15} | 4 |
| boosting | {"l2_regularization": 10, "learning_rate": 0.1, "max_iter": 200, "max_leaf_nodes": 7} | 3 |
| boosting | {"l2_regularization": 1, "learning_rate": 0.1, "max_iter": 100, "max_leaf_nodes": 7} | 1 |
| boosting | {"l2_regularization": 10, "learning_rate": 0.03, "max_iter": 200, "max_leaf_nodes": 7} | 1 |
| boosting | {"l2_regularization": 10, "learning_rate": 0.1, "max_iter": 100, "max_leaf_nodes": 7} | 1 |
| dummy | {} | 10 |
| floresta | {"class_weight": null, "max_depth": 16, "max_features": "sqrt", "min_samples_leaf": 3} | 10 |
| knn | {"n_neighbors": 41, "p": 1, "weights": "uniform"} | 7 |
| knn | {"n_neighbors": 81, "p": 2, "weights": "uniform"} | 2 |
| knn | {"n_neighbors": 21, "p": 1, "weights": "distance"} | 1 |
| logistica | {"C": 1, "class_weight": null} | 10 |

## Limites

Os folds de uma repetição não são amostras independentes e as repetições reaproveitam os mesmos registros: médias e desvios são descritivos, sem t pareado comum nem IC por desvio/√n. Treinos externos de 80% do desenvolvimento diferem dos 50% da v3, então diferenças em relação a ela misturam efeito de orçamento, de folds e de quantidade de dados. Escores internos de busca não são desempenho imparcial. A meta de 80% de especificidade é uma escolha acadêmica, sem validação clínica. Agrupamento: registro; independência por paciente desconhecida. Nenhum resultado desta rodada substitui o teste da v3 nem autoriza reajustar limiares no teste.
