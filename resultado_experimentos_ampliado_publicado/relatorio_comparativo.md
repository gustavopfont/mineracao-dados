# Extensão comparativa do UCMF

Concluída. Foram usados 9148 registros de desenvolvimento histórico. O teste histórico é apresentado com os resultados congelados da v3.

Os estimadores novos foram avaliados em folds externos com seleção de configuração e representação por AP interna. A política de limiar aprende sensibilidade máxima entre limiares com especificidade interna ≥80%. As medidas clínicas descrevem os registros, e essa meta é acadêmica.

| design | budget | model | folds | sensitivity_mean | sensitivity_sd | specificity_mean | folds_below_80 | ap_mean | roc_auc_mean | accuracy_mean | brier_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2x5 | base12 | boosting | 10 | 0.6426 | 0.0176 | 0.8089 | 1 | 0.7641 | 0.7956 | 0.7380 | 0.1779 |
| 2x5 | base12 | dummy | 10 | 0.0000 | 0.0000 | 1.0000 | 0 | 0.4261 | 0.5000 | 0.5739 | 0.2445 |
| 2x5 | base12 | floresta | 10 | 0.6520 | 0.0158 | 0.8047 | 4 | 0.7609 | 0.7928 | 0.7396 | 0.1837 |
| 2x5 | base12 | logistica | 10 | 0.6406 | 0.0142 | 0.8043 | 4 | 0.7539 | 0.7846 | 0.7345 | 0.1817 |
| 5x2 | base12 | boosting | 10 | 0.6403 | 0.0096 | 0.8078 | 3 | 0.7596 | 0.7907 | 0.7364 | 0.1796 |
| 5x2 | base12 | dummy | 10 | 0.0000 | 0.0000 | 1.0000 | 0 | 0.4261 | 0.5000 | 0.5739 | 0.2445 |
| 5x2 | base12 | floresta | 10 | 0.6442 | 0.0070 | 0.8016 | 3 | 0.7565 | 0.7861 | 0.7345 | 0.1899 |
| 5x2 | base12 | logistica | 10 | 0.6374 | 0.0072 | 0.8037 | 5 | 0.7518 | 0.7829 | 0.7329 | 0.1826 |
| 5x2 | estendida16 | boosting | 10 | 0.6409 | 0.0102 | 0.8077 | 3 | 0.7595 | 0.7909 | 0.7366 | 0.1795 |
| 5x2 | estendida16 | dummy | 10 | 0.0000 | 0.0000 | 1.0000 | 0 | 0.4261 | 0.5000 | 0.5739 | 0.2445 |
| 5x2 | estendida16 | floresta | 10 | 0.6442 | 0.0070 | 0.8016 | 3 | 0.7565 | 0.7861 | 0.7345 | 0.1899 |
| 5x2 | estendida16 | logistica | 10 | 0.6382 | 0.0061 | 0.8024 | 5 | 0.7517 | 0.7830 | 0.7324 | 0.1824 |
| 5x2 | v3_4 | arvore | 10 | 0.5345 | 0.0210 | 0.8338 | 1 | 0.6626 | 0.7278 | 0.7062 | 0.2152 |
| 5x2 | v3_4 | boosting | 10 | 0.6419 | 0.0101 | 0.8067 | 4 | 0.7604 | 0.7911 | 0.7365 | 0.1794 |
| 5x2 | v3_4 | dummy | 10 | 0.0000 | 0.0000 | 1.0000 | 0 | 0.4261 | 0.5000 | 0.5739 | 0.2445 |
| 5x2 | v3_4 | floresta | 10 | 0.6439 | 0.0072 | 0.8023 | 4 | 0.7569 | 0.7864 | 0.7348 | 0.1914 |
| 5x2 | v3_4 | knn | 10 | 0.5713 | 0.0136 | 0.8050 | 3 | 0.6957 | 0.7489 | 0.7054 | 0.1989 |
| 5x2 | v3_4 | logistica | 10 | 0.6382 | 0.0079 | 0.8026 | 5 | 0.7515 | 0.7829 | 0.7325 | 0.1857 |

As médias de AP, ROC-AUC e Brier foram calculadas entre folds. A tabela por repetição agrega as contagens de confusão. Desvios entre folds e diferenças pareadas descrevem estabilidade, pois os conjuntos de treino se sobrepõem. Os testes 5×2 de erro global são exploratórios. A família de hipóteses da extensão inclui floresta e boosting contra logística nos dois orçamentos 5×2, com correções Holm separadas para F e t.

O protocolo registra as grades e as sementes. O braço base12 contém os quatro candidatos da v3 e oito pontos adicionais da grade. Estendida16 adiciona quatro pontos externos à grade antiga. A calibração pode variar entre partições e a comparação por perfil mantém os mesmos registros.

Os intervalos dos subgrupos são Wilson por fold, condicionais aos modelos ajustados e à independência presumida dos registros naquele fold. A identidade do paciente não está disponível. Os conflitos de rótulos e as curvas de aprendizado investigam o erro observado. O erro de Bayes permanece desconhecido.

A confirmação externa requer uma nova coorte. As comparações prospectivas permanecem pendentes até que haja dados independentes com definição compatível de alvo, preditores e paciente.

## Curvas de aprendizado e ablações

Médias de cinco folds com parâmetro fixo e limiares aprendidos dentro da fração de treino.

| model | fraction | train_ap | ap | recall | specificity |
| --- | --- | --- | --- | --- | --- |
| boosting | 0.2500 | 0.8221 | 0.7534 | 0.6280 | 0.8120 |
| boosting | 0.5000 | 0.8027 | 0.7578 | 0.6401 | 0.8080 |
| boosting | 0.7500 | 0.7917 | 0.7647 | 0.6380 | 0.8082 |
| boosting | 1.0000 | 0.7875 | 0.7660 | 0.6408 | 0.8103 |
| floresta | 0.2500 | 0.7883 | 0.7467 | 0.6262 | 0.8078 |
| floresta | 0.5000 | 0.7902 | 0.7556 | 0.6426 | 0.8034 |
| floresta | 0.7500 | 0.7872 | 0.7579 | 0.6457 | 0.8032 |
| floresta | 1.0000 | 0.7865 | 0.7614 | 0.6465 | 0.8055 |
| logistica | 0.2500 | 0.7586 | 0.7434 | 0.6272 | 0.8059 |
| logistica | 0.5000 | 0.7615 | 0.7504 | 0.6416 | 0.8025 |
| logistica | 0.7500 | 0.7589 | 0.7535 | 0.6444 | 0.8017 |
| logistica | 1.0000 | 0.7597 | 0.7534 | 0.6378 | 0.8040 |

Diferenças externas médias em relação ao cenário completo. A ablação direcionada mascara motivos sensíveis e pode deixar um sinal de ausência. Clínica restrita omite todo o campo de motivos e HDA, além de B2 e pulsos.

| model | variant | delta_ap | delta_recall | delta_specificity |
| --- | --- | --- | --- | --- |
| boosting | clinica_restrita | -0.1627 | -0.2158 | -0.0101 |
| boosting | sem_classificacao_imc | 0.0000 | 0.0021 | 0.0040 |
| boosting | sem_exame_motivos | -0.0426 | -0.0303 | -0.0032 |
| boosting | sem_imc_continuo | -0.0003 | -0.0015 | 0.0015 |
| boosting | sem_ppa | -0.0009 | -0.0018 | -0.0010 |
| floresta | clinica_restrita | -0.1813 | -0.2358 | -0.0101 |
| floresta | sem_classificacao_imc | -0.0002 | 0.0005 | -0.0010 |
| floresta | sem_exame_motivos | -0.0469 | -0.0344 | -0.0023 |
| floresta | sem_ppa | -0.0018 | -0.0038 | 0.0017 |
| logistica | clinica_restrita | -0.1822 | -0.2342 | -0.0044 |
| logistica | sem_exame_motivos | -0.0469 | -0.0292 | -0.0030 |
| logistica | sem_imc_continuo | 0.0000 | -0.0008 | 0.0011 |


Métodos e referências no [plano de comparação](../referencias/plano_comparacao_modelos.md) e no [protocolo original](../referencias/protocolo_experimentos.md).
