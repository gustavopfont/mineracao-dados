# Testes de hipótese exploratórios da r01_5folds_2rep_12cand

Foram comparados os cinco modelos treinados em 2 repetições de 5 folds externos. A fonte é o commit publicado `9ee9172509fbadd493e07f39c613dd9cb3b4e469`. Cada comparação usa os mesmos folds com limiar aprendido no treino. As contagens de classe foram conferidas contra as partições publicadas dos 9148 registros de desenvolvimento. Dummy permanece como referência descritiva.

O teste t bilateral para validação cruzada repetida usa as diferenças A − B em cada fold. H₀ é diferença média igual a zero. Com m diferenças, a variância estimada da média é `(1/m + n_val/n_treino) × s²`. Usamos a média da razão entre tamanhos dos folds porque há pequenas diferenças de tamanho entre eles. A referência t usa m − 1 graus de liberdade. Diferença positiva favorece A em sensibilidade e especificidade, e negativa favorece A em erro. [Bouckaert e Frank](https://ml.cms.waikato.ac.nz/publications/2004/bouckaert-frank.pdf)

Holm a α = 0,05 ajusta a família inteira de 30 contrastes (dez pares × três métricas). Os IC95% são nominais e individuais. Houve **1 de 30 rejeições** após o ajuste. Variância nula torna o teste indefinido. [Holm](https://www.ime.usp.br/~abe/lista/pdf4R8xPVzCnX.pdf)

| Métrica | Modelo A | Modelo B | Δ (p.p.) | IC95% nominal (p.p.) | p bruto | p Holm | Rejeita H₀ |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| Sensibilidade | floresta | boosting | +0.51 | -0.46 a +1.49 | 0.2657 | 1 | Não |
| Sensibilidade | floresta | arvore | +3.39 | -0.20 a +6.98 | 0.0617 | 1 | Não |
| Sensibilidade | floresta | knn | +5.49 | +3.01 a +7.97 | 0.0007401 | 0.0222 | Sim |
| Sensibilidade | floresta | logistica | +0.96 | -0.51 a +2.43 | 0.1737 | 1 | Não |
| Sensibilidade | boosting | arvore | +2.87 | -0.96 a +6.71 | 0.1241 | 1 | Não |
| Sensibilidade | boosting | knn | +4.98 | +2.34 a +7.62 | 0.002105 | 0.06105 | Não |
| Sensibilidade | boosting | logistica | +0.45 | -0.86 a +1.76 | 0.4574 | 1 | Não |
| Sensibilidade | arvore | knn | +2.10 | -1.14 a +5.34 | 0.1762 | 1 | Não |
| Sensibilidade | arvore | logistica | -2.42 | -5.87 a +1.02 | 0.1454 | 1 | Não |
| Sensibilidade | knn | logistica | -4.53 | -7.18 a -1.87 | 0.003874 | 0.1085 | Não |
| Especificidade | floresta | boosting | -0.17 | -1.47 a +1.13 | 0.7726 | 1 | Não |
| Especificidade | floresta | arvore | -0.10 | -4.21 a +4.00 | 0.9552 | 1 | Não |
| Especificidade | floresta | knn | -1.13 | -2.25 a -0.01 | 0.04758 | 0.9993 | Não |
| Especificidade | floresta | logistica | +0.30 | -0.61 a +1.22 | 0.4712 | 1 | Não |
| Especificidade | boosting | arvore | +0.07 | -3.62 a +3.75 | 0.9683 | 1 | Não |
| Especificidade | boosting | knn | -0.96 | -2.18 a +0.25 | 0.1067 | 1 | Não |
| Especificidade | boosting | logistica | +0.48 | -0.81 a +1.76 | 0.4224 | 1 | Não |
| Especificidade | arvore | knn | -1.03 | -4.66 a +2.60 | 0.5377 | 1 | Não |
| Especificidade | arvore | logistica | +0.41 | -3.35 a +4.17 | 0.8109 | 1 | Não |
| Especificidade | knn | logistica | +1.44 | +0.35 a +2.53 | 0.01549 | 0.3872 | Não |
| Erro global | floresta | boosting | -0.12 | -0.85 a +0.61 | 0.718 | 1 | Não |
| Erro global | floresta | arvore | -1.38 | -2.76 a -0.00 | 0.04967 | 0.9993 | Não |
| Erro global | floresta | knn | -1.69 | -2.71 a -0.67 | 0.004589 | 0.1239 | Não |
| Erro global | floresta | logistica | -0.58 | -1.05 a -0.12 | 0.02001 | 0.4802 | Não |
| Erro global | boosting | arvore | -1.26 | -2.47 a -0.05 | 0.04281 | 0.9714 | Não |
| Erro global | boosting | knn | -1.57 | -2.72 a -0.42 | 0.01292 | 0.3359 | Não |
| Erro global | boosting | logistica | -0.46 | -1.18 a +0.25 | 0.1735 | 1 | Não |
| Erro global | arvore | knn | -0.31 | -2.24 a +1.63 | 0.7284 | 1 | Não |
| Erro global | arvore | logistica | +0.80 | -0.33 a +1.93 | 0.1445 | 1 | Não |
| Erro global | knn | logistica | +1.10 | +0.05 a +2.16 | 0.04224 | 0.9714 | Não |

A análise é pós-hoc. A correção é aproximada para folds dependentes. Sua aplicação às taxas por classe é exploratória. Os folds usam os mesmos registros em repetições diferentes e a identidade dos pacientes não está disponível. Um resultado não significativo mantém a incerteza sobre a diferença e não demonstra equivalência. A análise usa somente previsões resumidas nos folds externos. O teste reservado segue como evidência histórica da v3.

Decompusemos cada contraste em [diferenças por fold](diferencas_por_fold.csv). Os valores completos estão em [resultados.csv](resultados.csv), com a [proveniência dos dados](analise.json).
