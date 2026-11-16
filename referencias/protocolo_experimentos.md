# Protocolo de treinamento e comparação — versão 3 (orçamento reduzido)

Fixado antes da avaliação de teste. Consulta metodológica: 15/11/2026. A versão 2 incorporou três representações e 12 configurações por perfil. Em 15/11/2026, por solicitação do usuário devido ao custo observado, a versão 3 reduz para **quatro configurações por perfil**, mantendo cinco repetições externas de dois folds, três folds internos, os três perfis e todos os demais critérios. A execução válida passa a ser resultado_experimentos_reduzido/. A versão 2 em resultado_experimentos_representacoes/ foi encerrada antes da abertura do teste, com configuração/código arquivados e resultados parciais preservados. A execução ainda anterior está em resultado_experimentos/. Não misturar métricas dessas execuções nem escolher os quatro candidatos por resultados já observados.

## Decisões, fontes e implementação

| Etapa | Decisão | Fonte e limite | Código / evidência |
| --- | --- | --- | --- |
| População | Perfis supervisionados únicos concordantes; seleção anterior preservada | Matriz de preparação e OMS [S1]; não representa automaticamente todos os atendimentos | manifesto_adequacao.json e protocolo.json |
| Identidade e grupos | ID de registro não prova paciente; grupos reais só com mapeamento externo | TRIPOD+AI [S2] e scikit-learn [S3]; independência individual não garantida na base disponível | load_frame, assert_partition, folds |
| Aleatoriedade e estratificação | 20% teste, semente 42; desenvolvimento 5×2 com sementes 101,202,303,404,505 | [S3]; com grupos verdadeiros, grupos prevalecem e estratificação é aproximada | particao_principal.csv e partições externas/internas |
| Validação aninhada | Três folds internos em cada metade; avaliar procedimento completo fora do tuning | [S4]; escores internos são otimistas por seleção | search_and_fit, develop |
| Representação contínua | IDADE, peso, altura, IMC, FC, PAS, PAD + sexo, pulsos, B2, motivo e HDA | [S5–S7]; incluir IMC permite a comparação direta solicitada com seu atributo categórico; redundância não demonstra inutilidade | representacoes_ucmf.py, perfil continua |
| Representação clínica | FC + sexo, pulsos, B2, motivo, HDA, faixa etária, classificação IMC e PPA | OMS [S5], DBHA [S6]; categorias descrevem nutrição/pressão, não o alvo cardíaco | perfil clinica, referências clínicas versionadas |
| Combinada | União dos dois perfis, 15 preditores | [S7]; conveniência preditiva precisa ser avaliada, sem supor superioridade de qualquer representação | perfil combinada |
| Tuning | 4 configurações/família/perfil, 12 por família; mesmas listas nos três perfis; Dummy único | [S4,S8]; orçamento igual entre famílias não garante custo computacional idêntico; redução restringe a exploração | candidatos no protocolo.json; busca.json por perfil |
| Seleção de perfil | Escolher configuração de cada perfil por AP interna, depois perfil pela maior AP interna; empate 1e-6 favorece a ordem continua, clinica, combinada | [S4]; jamais escolher representação pela avaliação externa ou teste | fit_representations |
| Faltantes/codificação | Pipeline ajustado só dentro dos treinos; regras de preparação mantidas | [S9] e referencias/metodologia_preparo.md; mediana é baseline, sem recalcular categoria clínica depois da imputação | preprocessor, oof_interno.csv |
| Limiar | Máximo recall com especificidade interna ≥80%; desempate precisão, especificidade, maior limiar | [S10]; 80% é escolha acadêmica, sem recomendação clínica universal | choose_threshold e threshold_info |
| Métricas | Recall principal operacional, especificidade como restrição; AP para tuning; acurácia, precisão, F1/F2, balanced accuracy, ROC-AUC, Brier e curvas | [S8,S11,S12]; AP não é área trapezoidal PR; ROC é complementar e não inválida por desbalanceamento | metricas_modelagem.py e figuras |
| Inferência no desenvolvimento | F combinado 5×2 sobre diferenças de erro global; t original como sensibilidade, quatro comparações vs logística, Holm em cada família | [S13–S15]; testes aproximados, não prova de melhora em recall; tuning e representação repetidos dentro de cada metade | five_by_two, testes_5x2.json |
| Teste reservado | Seleção por desenvolvimento; pipelines e limiares congelados antes de prever o teste | [S2,S4]; teste já foi explorado em etapas anteriores e só está reservado para estes novos ajustes | congelamento.json, teste_aberto.json |
| Inferência no teste | McNemar exato nos verdadeiros positivos e negativos; duas comparações pareadas vs logística com Holm | [S15–S16]; somente vencedor previamente selecionado, nenhuma comparação consigo mesmo | mcnemar_teste.json |
| Intervalos | 2000 bootstrap estratificados pareados, sem refit; caso haja pacientes, amostragem por grupos inteiros estratificados por composição de classe | [S2,S17]; intervalos de modelos fixos, não toda a incerteza de treinamento; hipótese de independência limitada | bootstrap_ic95.csv |
| Interpretação | 20 permutações por atributo original usado no vencedor; queda em AP, sem nova seleção | [S18]; importância não é causalidade e correlação pode dividir contribuição | importancia_permutacao.csv |
| Relato e código | Configuração, parâmetros, índices, avisos, tempos, pipelines, limiares, versões, hashes e figuras | OMS [S1] e TRIPOD+AI [S2] | relatório técnico e manifesto_resultados.json |

## Escopo científico e orçamento

O resultado principal compara **procedimentos por família**, incluindo escolha interna da representação. As avaliações dos três perfis fixos também são reportadas, mas não originam testes de hipótese adicionais selecionados após olhar os resultados. As cinco famílias são regressão logística, árvore, KNN, Random Forest e HistGradientBoosting. DummyClassifier é referência ingênua e não compete pelo vencedor.

Grades exatas estão em modelos_ucmf.py e permanecem iguais às anteriores. Em todas as cinco famílias, incluindo logística, sorteiam-se quatro configurações sem reposição com sementes fixas; a lista é repetida nos três perfis e nos folds. Não se usam escores antigos para escolher esses candidatos. O protocolo v3 custa aproximadamente **1800 fits internos externos**, contra 5400 no v2, além dos refits e ajustes finais; a OOF do candidato escolhido é reutilizada de sua busca, sem refit redundante. Quatro processos no máximo, um único nível de paralelismo, estimadores internos com uma thread. Cache só reutiliza transformações ajustadas exatamente nos mesmos dados/partição. Não aplica SMOTE. A busca menor é uma comparação condicionada ao orçamento e não demonstra ótimo global dos hiperparâmetros.

Observações que se tornam iguais ao reduzir para categorias não são necessariamente duplicatas ou a mesma pessoa. Não se retiram linhas por perfil: as comparações usam os mesmos IDs e folds. A deduplicação anterior se baseou no contrato principal de 11 preditores; sua seleção e a exclusão de conflitos limitam a população alvo deste estudo.

Um candidato com aviso ConvergenceWarning é inelegível; erros de ajuste interrompem a execução. A busca completa e os avisos são mantidos. Se todos falharem, exige correção documentada e nova execução, sem atribuir score artificial. Não se muda o código de treinamento de uma execução já iniciada e a retoma como se fosse o mesmo protocolo: mudanças exigem um novo diretório.

## Métricas e seleção operacional

Anormal é 1. Recall = TP/(TP+FN), especificidade = TN/(TN+FP), precisão = TP/(TP+FP), acurácia = (TP+TN)/n, F1 = 2TP/(2TP+FP+FN), F2 = 5TP/(5TP+4FN+FP). Balanced accuracy é a média de recall e especificidade. Predição positiva usa p ≥ limiar; o limiar acima do máximo permite prever nenhum positivo, sem forçar um recall mínimo não aprovado.

Selecionar famílias elegíveis com especificidade média ≥80% nas cinco repetições externas, por maior recall médio, depois maior AP, menor tempo total e ordem fixa logística/árvore/KNN/floresta/boosting. Sem elegíveis, registrar meta não atingida e escolher apenas candidato exploratório por AP. O teste não muda essa decisão. Reportar falhas em reproduzir a meta nos folds e no teste. Especificidade abaixo da meta em dados novos não autoriza reajustar o limiar ali.

F combinado: d_ij é erro da família menos erro da logística, s_i² é a soma dos desvios das duas diferenças em relação à média da repetição. F = soma(d_ij²)/(2 soma(s_i²)), referência aproximada F(10,5). t = d_11/sqrt(soma(s_i²)/5), referência t(5) bilateral. Variância zero é resultado indefinido. Não aplicar t pareado comum aos dez resultados, nem Friedman/Nemenyi tratando folds como datasets independentes. Um p não significativo não prova equivalência.

## Referências

- **S1 — OMS (2023).** [Considerações regulatórias sobre IA em saúde](https://www.who.int/publications/i/item/9789240078871): qualidade, documentação, validação e uso pretendido; não certifica este estudo.
- **S2 — Collins et al. (2024).** [TRIPOD+AI](https://www.bmj.com/content/385/bmj-2023-078378), DOI 10.1136/bmj-2023-078378.
- **S3 — scikit-learn.** [Cross-validation e grupos](https://scikit-learn.org/stable/modules/cross_validation.html).
- **S4 — scikit-learn.** [Nested versus non-nested cross-validation](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html).
- **S5 — OMS.** [Padrões infantis](https://www.who.int/news-room/questions-and-answers/item/child-growth-standards) e [IMC por idade 5–19 anos](https://www.who.int/tools/growth-reference-data-for-5to19-years/indicators/bmi-for-age). Fontes e tabelas locais em referencias/README.md.
- **S6 — SBC/SBN/SBH (2025).** [Diretriz Brasileira de Hipertensão Arterial](https://www.scielo.br/j/abc/a/BXT7Vk4B9VKQnJFsJhgJ4Hn/?lang=pt), DOI 10.36660/abc.20250624.
- **S7 — BMJ (2025).** [Continuous variables and non-linear associations in healthcare data](https://www.bmj.com/content/390/bmj-2024-082440.short), DOI 10.1136/bmj-2024-082440.
- **S8 — scikit-learn.** [Métricas](https://scikit-learn.org/stable/modules/model_evaluation.html), [modelos supervisionados](https://scikit-learn.org/stable/supervised_learning.html), [busca de hiperparâmetros](https://scikit-learn.org/stable/modules/grid_search.html).
- **S9 — Sisk et al. (2023).** [Imputation and missing indicators: simulation study](https://pmc.ncbi.nlm.nih.gov/articles/PMC10515473/). Métodos podem comportar-se diferentemente conforme mecanismo de ausência e implantação.
- **S10 — scikit-learn.** [Tuning the decision threshold](https://scikit-learn.org/stable/modules/classification_threshold.html).
- **S11 — Saito e Rehmsmeier (2015).** [Precision-recall plot](https://doi.org/10.1371/journal.pone.0118432).
- **S12 — scikit-learn.** [Calibration](https://scikit-learn.org/stable/modules/calibration.html).
- **S13 — Dietterich (1998).** [Approximate Statistical Tests](https://doi.org/10.1162/089976698300017197).
- **S14 — Alpaydin (1999).** [Combined 5×2cv F test](https://pubmed.ncbi.nlm.nih.gov/10578036/), DOI 10.1162/089976699300016007.
- **S15 — Holm (1979).** [Sequentially rejective multiple test procedure](https://www.ime.usp.br/~abe/lista/pdf4R8xPVzCnX.pdf).
- **S16 — McNemar (1947).** [Correlated proportions](https://doi.org/10.1007/BF02295996).
- **S17 — Efthimiou et al. (2024).** [Developing clinical prediction models](https://www.bmj.com/content/386/bmj-2023-078276). Relatar validação, incerteza e limitação populacional.
- **S18 — scikit-learn.** [Permutation feature importance](https://scikit-learn.org/stable/modules/permutation_importance.html).

O resultado técnico apoiará o artigo IEEE e a apresentação exigidos em avaliacao2.md após os experimentos. Nenhum resultado de validação interna será descrito como validação clínica externa. Não há publicação ou submissão automática.
