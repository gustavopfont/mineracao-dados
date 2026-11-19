# Relatório de análise do conjunto UCMF

## Conjunto e objetivo

O arquivo bruto contém 12873 registros e 21 variáveis de atendimento em cardiologia pediátrica. A variável-alvo é NORMAL X ANORMAL, que indica presença ou ausência de patologia cardíaca. Após a exclusão de 739 registros sem dados clínicos, o conjunto analisado tem 12134 registros. O significado das variáveis está em dataset.md.

## Análise univariada após a limpeza

| Variável numérica | Válidos | Ausentes | Mediana | Mínimo | Máximo |
| --- | ---: | ---: | ---: | ---: | ---: |
| Peso | 9945 | 2189 | 16.00 | 0.30 | 157.00 |
| Altura | 8407 | 3727 | 100.00 | 31.00 | 198.00 |
| IMC | 8014 | 4120 | 17.00 | 9.00 | 56.00 |
| IDADE | 11196 | 938 | 3.86 | 0.00 | 19.91 |
| FC | 10974 | 1160 | 92.00 | 43.00 | 230.00 |
| PA SISTOLICA | 5140 | 6994 | 100.00 | 60.00 | 180.00 |
| PA DIASTOLICA | 5131 | 7003 | 60.00 | 23.00 | 120.00 |

| Data | Válidas | Ausentes | Primeira | Última |
| --- | ---: | ---: | --- | --- |
| Atendimento | 11889 | 245 | 1967-12-31 | 2023-06-25 |
| DN | 11371 | 763 | 1969-07-14 | 2022-07-09 |

| Variável categórica | Ausentes | Percentual ausente | Categoria mais frequente entre os válidos |
| --- | ---: | ---: | --- |
| Convenio | 3369 | 27.8% | GS |
| PULSOS | 455 | 3.7% | Normais |
| PPA | 10055 | 82.9% | Normal |
| NORMAL X ANORMAL | 429 | 3.5% | Normal |
| B2 | 439 | 3.6% | Normal |
| SOPRO | 428 | 3.5% | Ausente |
| HDA 1 | 3531 | 29.1% | Assintomático |
| HDA2 | 11727 | 96.6% | Dispneia |
| SEXO | 4 | 0.0% | Masculino |
| MOTIVO1 | 316 | 2.6% | 5 - Parecer cardiológico |
| MOTIVO2 | 2757 | 22.7% | 5 - Cirurgia |
| CLASSIFICACAO IMC | 5021 | 41.4% | Eutrofia |

As frequências completas de cada categoria, incluindo Ausente, estão em resumo_categoricas.csv. O alvo apresenta 6745 registros Normal e 4960 Anormal; 429 não têm rótulo. ID identifica registros e não deve ser interpretado como medida clínica. HDA2 e PPA exigem cautela devido à alta proporção de ausências.

## Qualidade e soluções

A leitura do CSV foi corrigida para preservar campos entre aspas. Valores vazios, #VALUE! e marcadores que não são medidas foram convertidos em ausentes. Categorias equivalentes foram padronizadas. Idades foram recalculadas a partir de datas coerentes; 6583 idades originais divergiam em mais de 0,10 ano. Os demais casos permanecem auditáveis. Valores fora dos limites técnicos foram retirados da análise, sem imputação por média. Restam 537 verificações em 366 IDs que não podem ser resolvidas com segurança apenas pelo CSV. Registros semelhantes com IDs diferentes ficaram para revisão, pois não há evidência suficiente para excluí-los. Os quantitativos por variável estão em qualidade_dados.csv e as decisões por ID em alteracoes.csv e pendencias.csv.

| Variável | Ausentes finais | Pendências diretas | Solução aplicada ou critério |
| --- | ---: | ---: | --- |
| ID | 0 | 0 | conferir unicidade; manter como identificador |
| Peso | 2189 | 1 | retirar sentinelas e valores fora do limite |
| Altura | 3727 | 6 | retirar sentinelas e valores fora do limite |
| IMC | 4120 | 23 | conferir com peso e altura; corrigir quando possível |
| Atendimento | 245 | 13 | converter para ISO; invalidar data ilegível |
| DN | 763 | 127 | converter para ISO; invalidar data ilegível |
| IDADE | 938 | 186 | recalcular com as duas datas coerentes |
| Convenio | 3369 | 0 | unificar grafias equivalentes; manter ausentes |
| PULSOS | 455 | 0 | unificar grafias equivalentes; manter ausentes |
| PA SISTOLICA | 6994 | 2 | conferir limite e coerência com diastólica |
| PA DIASTOLICA | 7003 | 1 | conferir limite e coerência com sistólica |
| PPA | 10055 | 0 | converter Não Calculado em ausente; não recalcular |
| NORMAL X ANORMAL | 429 | 0 | padronizar Normal/Anormal; manter ausentes |
| B2 | 439 | 0 | unificar grafias equivalentes; manter ausentes |
| SOPRO | 428 | 0 | unificar grafias equivalentes; manter ausentes |
| FC | 1160 | 31 | retirar valores fora do limite técnico |
| HDA 1 | 3531 | 0 | unificar grafias equivalentes; manter ausentes |
| HDA2 | 11727 | 0 | unificar grafias equivalentes; manter ausentes |
| SEXO | 4 | 0 | padronizar M/F; manter ausentes |
| MOTIVO1 | 316 | 0 | unificar grafias equivalentes; manter ausentes |
| MOTIVO2 | 2757 | 0 | unificar grafias equivalentes; manter ausentes |
| CLASSIFICACAO IMC | 5021 | 0 | derivar com tabelas OMS se entradas válidas |

Pendências de relações entre Atendimento/DN, Peso/Altura/IMC e PAS/PAD aparecem como linhas próprias em qualidade_dados.csv. Contagens de ausentes não significam que todos os valores possam ser recuperados.

## Comparação de duas variáveis

IDADE e NORMAL X ANORMAL foram comparadas após a limpeza. A mediana de idade é 4.77 anos entre os registros Normal e 2.62 anos entre os Anormal. O boxplot em graficos_bivariada/bivariada_numerica_idade.png mostra as distribuições; a tabela bivariada_numericas.csv informa os tamanhos de amostra e dispersões. O gráfico mostra a parte central da distribuição para preservar legibilidade; os valores válidos extremos permanecem nas estatísticas. A associação observada não implica relação causal.

## Análise bivariada com o alvo

As sete variáveis numéricas e as variáveis categóricas foram comparadas com NORMAL X ANORMAL. As categorias de alvo ausente ficaram fora desta etapa. As medianas abaixo descrevem apenas registros com a medida preenchida:

| Variável numérica | n Normal | Mediana Normal | n Anormal | Mediana Anormal |
| --- | ---: | ---: | ---: | ---: |
| Peso | 5451 | 19.00 | 4136 | 13.00 |
| Altura | 4587 | 107.00 | 3485 | 90.00 |
| IMC | 4378 | 17.00 | 3307 | 16.00 |
| IDADE | 6202 | 4.77 | 4607 | 2.62 |
| FC | 6366 | 90.00 | 4589 | 100.00 |
| PA SISTOLICA | 3277 | 100.00 | 1851 | 100.00 |
| PA DIASTOLICA | 3274 | 60.00 | 1845 | 60.00 |

Para cada variável categórica, a tabela mostra sua categoria mais frequente e a proporção dela em cada classe. Ela permite ver a direção e o tamanho das diferenças sem confundir frequência absoluta com percentual. As tabelas CSV e os gráficos mostram todas as categorias, inclusive Ausente.

| Variável categórica | Categoria de referência | % Normal | % Anormal |
| --- | --- | ---: | ---: |
| Convenio | GS (n=2004) | 17.0% | 17.3% |
| PULSOS | Normais (n=11511) | 99.3% | 97.0% |
| PPA | Normal (n=1790) | 17.4% | 12.5% |
| B2 | Normal (n=11077) | 99.3% | 88.3% |
| SOPRO | Ausente (n=7260) | 97.0% | 14.5% |
| HDA 1 | Assintomático (n=6533) | 51.7% | 61.4% |
| HDA2 | Palpitacao (n=83) | 0.8% | 0.6% |
| SEXO | Masculino (n=6502) | 56.4% | 54.5% |
| MOTIVO1 | 5 - Parecer cardiológico (n=5182) | 57.1% | 26.9% |
| MOTIVO2 | 5 - Cirurgia (n=2847) | 32.4% | 13.3% |
| CLASSIFICACAO IMC | Eutrofia (n=3900) | 32.7% | 34.2% |

As medianas de IDADE diferem entre as classes (4.77 e 2.62 anos). A ausência de SOPRO é muito mais frequente no grupo Normal, enquanto as medianas de PAS e PAD são iguais nos dois grupos. Na variável SEXO, Masculino representa 56.4% do grupo Normal e 54.5% do grupo Anormal, diferença pequena. As outras diferenças nas tabelas também são descritivas: faltantes, composição da amostra e categorias raras podem mudar a comparação. PPA e CLASSIFICACAO IMC têm restrições descritas abaixo. Gráficos usam verde para Normal e vermelho para Anormal; não há inferência causal ou teste de significância nesta etapa.

## Transformações e limites

O processamento criou IDADE, IMC e CLASSIFICACAO IMC somente quando os dados necessários eram consistentes. CLASSIFICACAO IMC usa as referências oficiais da OMS por idade e sexo. PPA não foi recalculada: a implementação anterior empregava cortes simplificados e faltam dados para conferir todas as situações. Por isso, Não Calculado passou a ausente e os valores informados na origem continuam identificáveis. A ausência de alguns campos pode ser informativa; não foi preenchida por estimativa estatística.

Para a modelagem, a seleção provisória antes do exame usa IDADE, Peso, Altura, FC, PAS, PAD, SEXO e MOTIVO1. ID, datas brutas e alvo não entram como preditores; IMC e CLASSIFICACAO IMC são derivados das medidas mantidas. HDA2 e PPA têm ausências elevadas, e achados do exame dependem da confirmação do momento de registro. `plano_modelagem.md` justifica a decisão para cada campo. `scripts/preparar_modelagem.py` reserva grupos semelhantes no mesmo conjunto e ajusta imputação, categorias e escala apenas no treino; o teste recebe somente a transformação aprendida. Seleção supervisionada, PCA ou reamostragem, se adotadas, ficarão dentro de cada treino da validação cruzada. Nenhum classificador foi treinado nesta etapa.

Este relatório em Markdown conserva o detalhamento técnico dos arquivos reproduzíveis em resultado_analise/. A versão paginada para submissão é gerada por scripts/gerar_relatorio_a1.py em relatorio_A1.pdf; o grupo deve conferir o texto e os resultados antes do envio.

## Uso de IA generativa

OpenAI Codex auxiliou a revisão dos dados, a correção dos scripts, a geração das tabelas e gráficos e a redação inicial deste relatório. O grupo deve conferir os resultados e assumir a interpretação final.
