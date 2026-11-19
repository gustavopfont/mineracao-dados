# Finalização do pré-processamento UCMF

Base final: **12134 registros e 17 colunas**, com **429 alvos ausentes**. IDs, ordem e alvo preservados.

## Auditoria e cobertura

A limpeza foi reproduzida em memória a partir do bruto e comparada célula a célula com a base limpa de referência (tolerância numérica 1e-9). Nenhum dos dois CSVs foi sobrescrito. Auditorias anteriores foram regeneradas em arquivos separados, incluindo linhas removidas e pendências.

- PPA legada preenchida: 2079 (17.13%).
- PPA calculada: 2489 (20.51%).
- Novas classificações onde a PPA era vazia: 673.
- PPA legada preenchida, mas sem requisitos para recálculo: 263.
- Variação líquida da cobertura validável: +410 registros.
- Motivos com prefixos divergentes, preservados: 230.
- Contradições em HDA: 1.
- Pendências herdadas da limpeza: 537.

### Comparação da PPA

| Situação | Registros |
| --- | ---: |
| não verificável | 9645 |
| concordante | 1545 |
| nova classificação | 673 |
| divergente | 271 |

### Impedimentos para classificação

| Motivo | Registros |
| --- | ---: |
| PAS ou PAD ausente/inválida | 3854 |
| menor de 1 ano: fora da referência adotada | 2822 |
| altura ausente/inválida | 1588 |
| idade ausente ou inválida | 938 |
| altura fora da grade: sem extrapolação | 344 |
| sexo ausente ou sem referência | 99 |

## SOPRO e relações entre variáveis

SOPRO × alvo: V de Cramér = **0.8424**, n = 11682; 452 registros sem par completo. SOPRO foi analisado antes de ser excluído por escolha pedagógica. A associação não comprova vazamento. O motivo de encaminhamento “Sopro” permanece.

As tabelas de associações informam pares válidos, ausências e estratos de idade/sexo; as frequências incluem os faltantes. V de Cramér é descritivo, sem correção por viés, e pode ser instável em tabelas esparsas. Spearman nos estratos não elimina todo o efeito de idade. HDA unificada é um conjunto de sintomas, não uma escala ordinal.

## Regras e limites

Faixas etárias usam aniversários quando as datas são coerentes. IDADE contínua foi preservada; o detalhe dos anos completos e sua origem ficam na auditoria. Sem datas coerentes, usa-se a idade disponível, cuja precisão pode ser limitada pelo arredondamento prévio.

PPA_CALCULADA descreve uma medida. Para 1–12 anos, os percentis são interpolados linearmente em centímetros entre alturas tabuladas, sem extrapolação e sem arredondar os limiares. Essa interpolação é uma aproximação computacional do projeto. O limite de maior gravidade entre PAS/PAD prevalece, com os tetos absolutos da diretriz. Menores de um ano não são classificados. Aos 18 anos passam a valer os cortes brasileiros para adultos, que diferem dos cortes de adolescentes.

A PPA legada só é harmonizada para comparação de categoria; seu componente PAS/PAD permanece no texto original. Uma concordância não valida retroativamente o diagnóstico.

ID é metadado, nunca preditor. B2, PULSOS e histórico de cardiopatia conhecida permanecem por decisão do exercício: o momento de disponibilidade precisa ser revisto antes de uma aplicação prospectiva. Peso, altura, IMC e sua classificação são redundantes em parte; sua seleção fica para a modelagem. Faltantes continuam vazios e alvos não foram inferidos.

Não houve divisão de dados, imputação estatística, normalização aprendida, balanceamento ou treino. Ganhos de cobertura e organização não demonstram ganho preditivo.

## Fontes

- [DBHA 2025, tabelas 9.1–9.3 e quadro 3.2](https://www.scielo.br/j/abc/a/BXT7Vk4B9VKQnJFsJhgJ4Hn/?lang=pt): classificação, idade, sexo e altura; diagnóstico exige confirmação.
- [AAP 2017](https://publications.aap.org/pediatrics/article/140/3/e20171904/38358): tabelas completas e diferença entre triagem e classificação.
- [RCH: dor torácica](https://www.rch.org.au/clinicalguide/guideline_index/Chest_Pain/): sintomas não são diagnósticos; história e exame importam em conjunto.
- [RCH: variáveis fisiológicas](https://www.rch.org.au/clinicalguide/guideline_index/normal_ranges_for_physiological_variables/): FC e pressão variam com idade e contexto.
- [AHA: sopros](https://www.heart.org/en/health-topics/heart-murmurs): sopros inocentes são comuns.

Os valores de referência e seu hash estão em referencias/pa_dbha_2025.csv e .json. Consulta em 07/11/2026. O gerador funciona sem rede.


## Revisão da discretização de IMC e pressão

IMC, PAS e PAD contínuos e suas categorias clínicas são preservados. CLASSIFICACAO IMC e PPA_CALCULADA já são discretizações clínicas. Converter rótulos em números seria codificação; unir categorias seria agrupamento adicional. Não foram criadas versões binárias, cortes supervisionados nem uma segunda classificação de pressão.

| Método | Avaliação e decisão |
| --- | --- |
| Mesma largura | Sensível a extremos; apenas para histogramas, sem rótulos clínicos. |
| Quantis | Descrição relativa da amostra; empates e mistura de idades limitam interpretação. Não entram na base. |
| K-means | Grupos de proximidade numérica não equivalem a condições médicas; reservado para estudo futuro. |
| Cortes clínicos externos | Mantidos: OMS para IMC e DBHA 2025 para pressão. |
| Entropia/MDL supervisionado | Depende do alvo e exigiria ajuste dentro do treino; fora desta etapa. |

A [documentação do scikit-learn](https://sklearn.org/stable/modules/generated/sklearn.preprocessing.KBinsDiscretizer.html) descreve largura uniforme, quantis e k-means. [Fayyad e Irani](https://ijcai.org/proceedings/1993/141) descrevem discretização por entropia/MDL. A perda de informação ao categorizar preditores é discutida no [BMJ, 2025](https://www.bmj.com/content/390/bmj-2024-082440.short). Não se conclui superioridade preditiva de uma representação sem avaliar modelos.

### Precisão e quartis observados

| Medida | Válidos | Distintos | Q1 | Mediana | Q3 | Intervalos efetivos |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| IMC | 8014 | 39 | 15 | 17 | 19 | 4 |
| PA SISTOLICA | 5140 | 42 | 90 | 100 | 110 | 4 |
| PA DIASTOLICA | 5131 | 29 | 60 | 60 | 70 | 3 |

Os valores iguais permanecem juntos; os grupos podem ter tamanhos diferentes e limites repetidos são descartados. Esses intervalos não são chamados de normalidade ou hipertensão. O IMC disponível tem precisão limitada: poucos valores distintos não autorizam inventar casas decimais. Fronteiras de classificação precisam ser lidas considerando essa precisão.

### IMC por idade e sexo — OMS mantida

| Referência | Cortes em escore-z |
| --- | --- |
| Ambas | Magreza acentuada z < −3; magreza −3 ≤ z < −2; eutrofia −2 ≤ z ≤ +1. |
| OMS 2006, 0–60 meses completos | Risco de sobrepeso +1 < z ≤ +2; sobrepeso +2 < z ≤ +3; obesidade z > +3. |
| OMS 2007, 61–228 meses completos | Sobrepeso +1 < z ≤ +2; obesidade z > +2. |

Mantêm-se as [categorias OMS infantis](https://www.who.int/news-room/questions-and-answers/item/child-growth-standards) e [posteriores](https://www.who.int/tools/growth-reference-data-for-5to19-years/indicators/bmi-for-age), sem acrescentar obesidade grave ou fundir grupos pequenos. A tabela inicial usa dias até 1856; a posterior usa meses completos por floor(dias/30,4375). A extensão inicial até o dia anterior a 61 meses completos está nas [notas oficiais da OMS](https://www.who.int/docs/default-source/child-growth/child-growth-standards/indicators/body-mass-index-for-age/readme-bfa-exp.pdf). Aniversários de 5 anos e as faixas gerais da base não substituem essa escala. Idades fora da referência continuam sem classificação, sem extrapolação para completar 19 anos. Nenhum escore-z individual é estimado apenas pelos pontos de corte.

### Cobertura por referência etária e sexo

| Variável | Referência etária | Sexo | Total | Classificados | Ausentes | Cobertura % |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| CLASSIFICACAO IMC | Fora da referência OMS | Feminino | 8 | 0 | 8 | 0.00 |
| CLASSIFICACAO IMC | Fora da referência OMS | Masculino | 10 | 0 | 10 | 0.00 |
| CLASSIFICACAO IMC | Idade indisponível | Feminino | 335 | 0 | 335 | 0.00 |
| CLASSIFICACAO IMC | Idade indisponível | Indeterminado | 190 | 0 | 190 | 0.00 |
| CLASSIFICACAO IMC | Idade indisponível | Masculino | 413 | 0 | 413 | 0.00 |
| CLASSIFICACAO IMC | OMS 2006: 0–60 meses completos | Feminino | 2558 | 1800 | 758 | 70.37 |
| CLASSIFICACAO IMC | OMS 2006: 0–60 meses completos | Indeterminado | 383 | 0 | 383 | 0.00 |
| CLASSIFICACAO IMC | OMS 2006: 0–60 meses completos | Masculino | 3586 | 2607 | 979 | 72.70 |
| CLASSIFICACAO IMC | OMS 2006: 0–60 meses completos | Sem informação | 3 | 0 | 3 | 0.00 |
| CLASSIFICACAO IMC | OMS 2007: 61–228 meses completos | Feminino | 1823 | 1078 | 745 | 59.13 |
| CLASSIFICACAO IMC | OMS 2007: 61–228 meses completos | Indeterminado | 105 | 0 | 105 | 0.00 |
| CLASSIFICACAO IMC | OMS 2007: 61–228 meses completos | Masculino | 2719 | 1628 | 1091 | 59.87 |
| CLASSIFICACAO IMC | OMS 2007: 61–228 meses completos | Sem informação | 1 | 0 | 1 | 0.00 |
| PPA_CALCULADA | DBHA: 13–17 anos | Feminino | 278 | 238 | 40 | 85.61 |
| PPA_CALCULADA | DBHA: 13–17 anos | Indeterminado | 19 | 19 | 0 | 100.00 |
| PPA_CALCULADA | DBHA: 13–17 anos | Masculino | 335 | 277 | 58 | 82.69 |
| PPA_CALCULADA | DBHA: 13–17 anos | Sem informação | 1 | 1 | 0 | 100.00 |
| PPA_CALCULADA | DBHA: 18–19 anos | Feminino | 21 | 18 | 3 | 85.71 |
| PPA_CALCULADA | DBHA: 18–19 anos | Masculino | 17 | 14 | 3 | 82.35 |
| PPA_CALCULADA | DBHA: 1–12 anos | Feminino | 2999 | 696 | 2303 | 23.21 |
| PPA_CALCULADA | DBHA: 1–12 anos | Indeterminado | 144 | 0 | 144 | 0.00 |
| PPA_CALCULADA | DBHA: 1–12 anos | Masculino | 4558 | 1226 | 3332 | 26.90 |
| PPA_CALCULADA | DBHA: 1–12 anos | Sem informação | 2 | 0 | 2 | 0.00 |
| PPA_CALCULADA | Idade indisponível | Feminino | 335 | 0 | 335 | 0.00 |
| PPA_CALCULADA | Idade indisponível | Indeterminado | 190 | 0 | 190 | 0.00 |
| PPA_CALCULADA | Idade indisponível | Masculino | 413 | 0 | 413 | 0.00 |
| PPA_CALCULADA | Menor de 1 ano: não classificável | Feminino | 1091 | 0 | 1091 | 0.00 |
| PPA_CALCULADA | Menor de 1 ano: não classificável | Indeterminado | 325 | 0 | 325 | 0.00 |
| PPA_CALCULADA | Menor de 1 ano: não classificável | Masculino | 1405 | 0 | 1405 | 0.00 |
| PPA_CALCULADA | Menor de 1 ano: não classificável | Sem informação | 1 | 0 | 1 | 0.00 |

As referências etárias são atribuídas mesmo quando sexo ou medida estão ausentes; isso mantém todos os registros nos denominadores. Cobertura = classificados/total do estrato. As frequências em frequencias_discretizacao.csv mostram percentuais sobre todo o estrato e sobre os classificados; o percentual dos classificados fica vazio para a categoria técnica de ausência.

### Pressão, procedência da altura e significado da PPA

Menores de 1 ano não são classificados; 1–12 anos usam idade, sexo e altura; 13–17 usam cortes de adolescentes; 18–19 usam os cortes brasileiros de adultos. Os limiares e a referência de cada registro estão na auditoria. A categoria mais elevada entre PAS e PAD prevalece; PPA normal não avalia hipotensão nem exclui cardiopatia. Uma única medida não confirma diagnóstico de hipertensão. [DBHA 2025](https://www.scielo.br/j/abc/a/BXT7Vk4B9VKQnJFsJhgJ4Hn/?lang=pt).

Alturas recuperadas por relação antropométrica: **0**; PPA calculada nesses registros: **0**. A auditoria distingue altura informada na origem, recuperada, ausente e origem não auditada. Recuperação algébrica não equivale a uma nova medição direta. Não houve imputação estatística; a aproximação por interpolação entre alturas continua explícita e sem extrapolação.

### Relações com o alvo e comparação das representações

alvo_por_categoria_discretizacao.csv apresenta contagens Normal/Anormal/alvo ausente por categoria, referência e sexo; percentual Anormal usa apenas alvos conhecidos da categoria. Categorias com zero registros e grupos pequenos permanecem identificáveis. continuas_por_alvo_discretizacao.csv apresenta n, ausências, mínimo, quartis e máximo de IMC/PAS/PAD nos mesmos estratos e por alvo, inclusive alvo desconhecido. As tabelas permitem descrição paralela; não constituem comparação de desempenho ou causalidade. As associações com o alvo continuam em associacoes_final.csv. Não há comparação direta de magnitude entre Spearman e V de Cramér como medida de qualidade preditiva.

Resumo global por categoria (mistura idades e sexos; detalhes estratificados no CSV):

| Variável | Categoria | Total | Normal | Anormal | Alvo ausente | % Anormal entre alvos conhecidos |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| CLASSIFICACAO IMC | Magreza acentuada | 135 | 40 | 85 | 10 | 68.00 |
| CLASSIFICACAO IMC | Magreza | 220 | 98 | 117 | 5 | 54.42 |
| CLASSIFICACAO IMC | Eutrofia | 4075 | 2205 | 1695 | 175 | 43.46 |
| CLASSIFICACAO IMC | Risco de sobrepeso | 971 | 505 | 437 | 29 | 46.39 |
| CLASSIFICACAO IMC | Sobrepeso | 985 | 596 | 334 | 55 | 35.91 |
| CLASSIFICACAO IMC | Obesidade | 727 | 472 | 215 | 40 | 31.30 |
| CLASSIFICACAO IMC | Sem informação | 5021 | 2829 | 2077 | 115 | 42.34 |
| PPA_CALCULADA | Normal | 1921 | 1244 | 669 | 8 | 34.97 |
| PPA_CALCULADA | Pré-hipertensão | 203 | 128 | 75 | 0 | 36.95 |
| PPA_CALCULADA | HA estágio 1 | 275 | 177 | 97 | 1 | 35.40 |
| PPA_CALCULADA | HA estágio 2 | 90 | 49 | 41 | 0 | 45.56 |
| PPA_CALCULADA | HA estágio 3 | 0 | 0 | 0 | 0 | — |
| PPA_CALCULADA | Sem informação | 9645 | 5147 | 4078 | 420 | 44.21 |

Uma categoria nutricional ou pressórica não determina NORMAL X ANORMAL. Diferenças nestas proporções podem refletir a composição dos atendimentos e o padrão de dados ausentes; não justificam mudar pontos de corte ou preencher o alvo.
