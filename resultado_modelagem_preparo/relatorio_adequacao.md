# Adequação da base supervisionada

Base apta ao preparo computacional; não constitui validação clínica ou desempenho de modelo.

| Destino | Registros |
| --- | ---: |
| mantido | 11436 |
| duplicata | 127 |
| conflito | 142 |
| sem_alvo | 429 |

Total de entrada: 12134; soma dos destinos: 12134.
Correções de campos auditadas: 1. Grupos conflitantes: 6.
Os 11436 perfis supervisionados são únicos nos 11 preditores selecionados.
Cada ID de entrada possui exatamente um destino em rastreabilidade.csv. O menor ID numérico representa duplicatas concordantes.

## Seleção e faltantes

ID é metadado. IMC, CLASSIFICACAO IMC, FAIXA_ETARIA e PPA_CALCULADA ficam na visão complementar alinhada por ID, por sua derivação parcial de outros campos. SOPRO, convênio e datas brutas não entram nos preditores. Sintomas contraditórios ficam indisponíveis na cópia supervisionada; originais e correções são preservados.

O CSV mantém faltantes. O transformador declara mediana do treino e indicadores para todos os campos numéricos. Se uma coluna for inteiramente ausente no treino, o imputador mantém sua dimensão com zero técnico e indicador; isso não é uma medição clínica. Escala, medianas e vocabulários serão ajustados exclusivamente dentro de cada treino da validação cruzada futura. Categorias ausentes usam __SEM_INFORMACAO__, diferente de Indeterminado e Outro. Categorias inéditas não alteram o vocabulário e geram zeros no bloco one-hot. Não se agrupam categorias clínicas raras automaticamente.

HDA usa menções de sintomas separadas, indicador de informação ausente e indicador de categoria inédita. Sintoma não mencionado não significa negação clínica confirmada. Não se recalculam diagnósticos ou categorias a partir de medidas imputadas.

## Limitações e próxima etapa do KDD

Perfil idêntico não comprova mesmo paciente: a deduplicação reduz multiplicidade e muda a distribuição empírica. multiplicidade e IDs continuam rastreáveis. Grupos com alvos conflitantes são separados integralmente, sem escolher por maioria. Não se excluem categorias raras ou extremos válidos por associação ao alvo. As ausências variam entre classes e podem refletir a rotina de registro.

B2, PULSOS, HDA, motivo de sopro e cardiopatia já conhecida permanecem para o exercício acadêmico; podem conter informação próxima à definição do alvo. Não se declara validade para triagem prospectiva. Há exploração anterior da base inteira; a avaliação futura será interna, com essa limitação documentada.

Nenhum classificador foi treinado, nenhuma divisão real nova foi feita e nenhum parâmetro foi aprendido da base inteira. As saídas em resultado_modelagem/ são legadas e não devem ser usadas como avaliação do esquema atual. A próxima etapa definirá a validação, comparação dos modelos e o compromisso entre sensibilidade de Anormal e especificidade. Colocar o pré-processamento e o classificador no mesmo Pipeline por partição. Fontes metodológicas: [scikit-learn: prevenção de vazamento](https://scikit-learn.org/stable/common_pitfalls.html), [imputação e colunas vazias](https://scikit-learn.org/stable/modules/impute.html).


---

# Fundamentação das etapas de preparação e KDD

Consulta das fontes metodológicas: 15/11/2026. Fontes das tabelas clínicas e datas de extração estão em `referencias/README.md`. Esta matriz liga decisões, evidência, implementação e testes. Não atribui à OMS regras estatísticas específicas que ela não prescreve.

## Matriz de decisões

| Etapa / regra | Fundamento e limites | Implementação | Verificação |
| --- | --- | --- | --- |
| R1 — Preservar fonte e trilha por ID | OMS [S1–S2] recomenda qualidade, transparência e documentação; hashes e destino por registro são escolhas de implementação. | `finalizar_dataset.py`, `auditar_base_modelagem.run` | Hashes de fontes, reconciliação de destinos e teste de reprodução. |
| R2 — Validar tipos, unidades e domínios | OMS [S1–S2] apoia verificação de qualidade. Os limites amplos de `LIMITS` são verificações técnicas locais, **não intervalos diagnósticos publicados pela OMS**. Valores fora deles são marcados para revisão, sem diagnóstico. | `analise_dataset.clean_numbers`, `auditar_base_modelagem.normalize` | Testes de não finitos, limites, categoria desconhecida e preservação do alvo. |
| R3 — Conferir antropometria e IMC | OMS [S3–S5] define referências por idade e sexo. IMC = peso/altura² é a relação usada; tolerância absoluta de 1 kg/m² para consistência é herdada do projeto, não recomendação OMS. Não se afirma qual medida é a errada. | `classificacao_imc.py`, `normalize`, `validate_context` | Fronteiras −3, −2, +1, +2, +3, ambos os sexos; 1856/1857 dias e mês 228. |
| R4 — Conferir pressão e PPA | DBHA [S6] diferencia percentis pediátricos e cortes de adolescentes/adultos. Interpolação em centímetros é aproximação computacional local; não é nova medição nem confirmação diagnóstica. | `classificacao_pa.py`, `validate_context` | Aniversários, limites e gravidade máxima PAS/PAD, ausência de requisitos e não extrapolação. |
| R5 — Sintomas e inconsistências de história | RCH [S7] fundamenta interpretar sintomas em conjunto com história/exame. Marcar Assintomático + sintoma como indisponível é decisão conservadora local: **não adjudica o prontuário**. Ausência de menção não prova ausência de sintoma. | `normalize`, `HistoryEncoder` | Contradição preservada na auditoria; multimenções, informação ausente e categoria inédita. |
| R6 — Deduplicar perfis concordantes | OMS [S1–S2] e TRIPOD+AI [S8] apoiam documentação da seleção e limitações. Não prescrevem excluir pacientes com perfis iguais. Deduplicação foi solicitada para este exercício: igualdade de preditores não identifica pessoas. Pode modificar frequências e introduzir viés de seleção; multiplicidade permanece no mapa. | `profile_keys`, `duplicate_groups`, `prepare` | Igualdade de valores completos, menor ID numérico, nova checagem após correções e nenhuma duplicata residual. |
| R7 — Quarentena de alvos conflitantes | Qualidade de dados/rótulos e relato transparente [S1–S2, S8]. A quarentena integral é política local de elegibilidade, **não prova de erro dos rótulos**: pacientes diferentes com mesmos preditores podem ter diagnósticos diferentes. Não se escolhe por maioria. | `prepare` | Grupos inteiros separados; alvo nunca corrigido; todos os IDs reconciliados. Comparar sensibilidade a essa seleção em estudo futuro. |
| R8 — Reduzir redundância sem apagar informação | Guia de predição clínica [S9] trata seleção de preditores e disponibilidade. Preferir peso/altura na seleção principal e reservar IMC/PPA/faixas é uma escolha prévia de representação, não evidência de superioridade. | `FEATURE_COLUMNS`, `DERIVED_COLUMNS`, visão complementar | ID fora de X, derivados alinhados, valores válidos preservados. Comparação de representações fica para experimentos. |
| R9 — Preservar faltantes e evitar casos completos como regra | [S9] discute perda amostral e recomenda considerar imputação; imputação múltipla representa incerteza melhor que métodos simples em muitos contextos. Não inferir mecanismo MCAR/MAR/MNAR apenas dos percentuais observados. | Exportação sem imputação, `faltantes_por_classe.csv` | Contagens por classe e estágio; os sem alvo não são rotulados. |
| R10 — Mediana + indicadores como **baseline metodológico** | Estudo de simulação [S10] avalia imputação/indicadores; resultados dependem do contexto e não garantem validade para UCMF. A mediana univariada é a escolha inicial simples do projeto, não uma recomendação clínica OMS nem solução definitiva. Documentar a limitação e comparar abordagens em experimentos futuros. | `build_preprocessor` | Mediana aprendida só no treino sintético, ausência inédita e dimensões estáveis em colunas vazias. Zero técnico em coluna totalmente vazia não é uma medida. |
| R11 — Codificação e ajuste dentro das partições | [S11–S12] documenta imputação, categorias inéditas e pipelines contra vazamento. One-hot nominal, menções HDA e indicadores não inventam ordem clínica. Não se recalculam categorias clínicas após imputação. | `row_features`, `build_preprocessor`, `HistoryEncoder` | Clonagem não ajustada, exclusão ID/alvo/SOPRO, categorias inéditas e estabilidade. |
| R12 — Adequação, avaliação e relato do KDD | TRIPOD+AI [S8] e guia clínico [S9] orientam relatar dados, métodos, desempenho e limitações. OMS [S1] distingue validação e uso pretendido. Preparação computacional não equivale a validação clínica. | `relatorio_adequacao.md`, `manifesto_adequacao.json`, roteiro no README | Nenhum fit global, modelo ou split real nesta fase. Modelos e limiar para Anormal somente na etapa futura; sem resultados inventados. |

## Referências

- **S1 — OMS (2023).** [WHO outlines considerations for regulation of artificial intelligence for health](https://www.who.int/news/item/19-10-2023-who-outlines-considerations-for-regulation-of-artificial-intelligence-for-health); [publicação técnica](https://www.who.int/publications/i/item/9789240078871). Qualidade, documentação, validação e uso pretendido; não certifica este algoritmo.
- **S2 — OMS (2023).** [Data quality assurance: module 3 — data verification and system assessment](https://www.who.int/publications/i/item/9789240049123). Referência geral para verificação; não é uma prescrição específica para deduplicação de perfis clínicos individuais.
- **S3 — OMS (2025).** [Child growth standards: perguntas e respostas](https://www.who.int/news-room/questions-and-answers/item/child-growth-standards).
- **S4 — OMS.** [BMI-for-age, 5–19 years](https://www.who.int/tools/growth-reference-data-for-5to19-years/indicators/bmi-for-age).
- **S5 — OMS.** [Notas das tabelas expandidas de IMC](https://www.who.int/docs/default-source/child-growth/child-growth-standards/indicators/body-mass-index-for-age/readme-bfa-exp.pdf): dias, conversão mensal e limite inicial.
- **S6 — SBC/SBN/SBH (2025).** [Diretriz Brasileira de Hipertensão Arterial](https://www.scielo.br/j/abc/a/BXT7Vk4B9VKQnJFsJhgJ4Hn/?lang=pt), DOI 10.36660/abc.20250624; tabelas 9.1–9.3 e quadro 3.2.
- **S7 — Royal Children’s Hospital.** [Clinical Practice Guidelines: Chest pain](https://www.rch.org.au/clinicalguide/guideline_index/Chest_Pain/).
- **S8 — Collins et al. (2024).** [TRIPOD+AI statement](https://www.bmj.com/content/385/bmj-2023-078378), BMJ 385:e078378, DOI 10.1136/bmj-2023-078378.
- **S9 — Efthimiou et al. (2024).** [Developing clinical prediction models: a step-by-step guide](https://www.bmj.com/content/386/bmj-2023-078276), BMJ 386:e078276, DOI 10.1136/bmj-2023-078276; principalmente seleção de preditores, faltantes e avaliação.
- **S10 — Sisk et al. (2023).** [Imputation and missing indicators for handling missing data in the development and deployment of clinical prediction models: A simulation study](https://pmc.ncbi.nlm.nih.gov/articles/PMC10515473/).
- **S11 — scikit-learn.** [Common pitfalls: data leakage](https://scikit-learn.org/stable/common_pitfalls.html).
- **S12 — scikit-learn.** [Imputation](https://scikit-learn.org/stable/modules/impute.html), [SimpleImputer](https://scikit-learn.org/stable/modules/generated/sklearn.impute.SimpleImputer), [OneHotEncoder](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.OneHotEncoder.html). Fundamentação técnica do comportamento, sem substituir referência clínica.

## Relação com a Avaliação 2

`avaliacao2.md` é o enunciado da entrega final, preservado. Esta fase fornece dados organizados, código e evidências para Dados/Análise Exploratória e pré-processamento da Metodologia. A próxima fase deverá comparar pelo menos um baseline simples e um modelo mais complexo com partições reproduzíveis, prioridade para detecção de Anormal e métricas incluindo sensibilidade/especificidade, discriminação e calibração. Os critérios e limiares serão definidos sem consultar o teste. Só então haverá resultados para o artigo IEEE de até cinco páginas e apresentação; não antecipar números nem interpretar adequação como desempenho.
