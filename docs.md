# Pré-processamento do conjunto UCMF

O processamento parte de UCMF_raw.csv, mantém o arquivo original intacto e gera as saídas em resultado_analise/. A execução pode ser repetida com python scripts/analise_dataset.py.

## Controle do conjunto

- Linhas de entrada: **12873**.
- Linhas sem dados clínicos excluídas: **739**.
- Linhas no conjunto limpo: **12134**.
- Linhas semelhantes ainda presentes, sem considerar ID: **373**. Elas não foram removidas automaticamente.
- SHA-256 do CSV bruto: 85ecef54e5f53dd78066eb3255a9badd1b731475f6d8d1cb94bfc674dbd60acb

## Limpeza e transformação

| Etapa | O que foi feito | Justificativa |
| --- | --- | --- |
| Leitura do CSV | Aspas após espaços e exatamente 21 campos por registro | Evitar o deslocamento das colunas em datas com vírgula. |
| Exclusão de registros | 739 registros sem dados clínicos | Remover linhas do padrão vazio do ID 65, preservando os IDs no relatório. |
| Padronização de categorias | Grafias equivalentes consolidadas | Evitar que uma mesma categoria seja contada mais de uma vez. |
| Ausências | Zeros de Peso/Altura/IMC e Não Calculado em PPA tratados como ausentes | Esses marcadores não representam medidas ou diagnóstico. |
| Datas e idade | 9849 idades recalculadas | Usar Atendimento menos DN quando as duas datas são coerentes. |
| Antropometria | 0 valores calculados ou corrigidos | Aplicar a relação entre Peso, Altura e IMC apenas com entradas válidas. |
| Classificação de IMC | 7113 registros classificados | Usar os cortes oficiais da OMS por sexo e idade. |
| PPA | 10055 valores ausentes após a limpeza | Não inferir classificação clínica com a tabela simplificada anterior. |

As alterações por ID estão em alteracoes.csv; as linhas excluídas em linhas_removidas.csv; os casos que exigem interpretação da origem em pendencias.csv. Os valores originais continuam disponíveis em UCMF_raw.csv. O relatório de qualidade inclui todas as variáveis, inclusive as verificações com resultado zero.

## Resultado dos atributos

- Alvo NORMAL X ANORMAL: **6745 Normal**, **4960 Anormal** e **429 ausentes**.
- IMC classificado: **7113**; sem classificação: **5021**.
- Questões não resolvidas pela origem: **537 verificações em 366 IDs**; elas não impedem a leitura do CSV e constam em pendencias.csv.
- Datas de origem inválidas após leitura robusta: **127**; detalhes em pendencias.csv.
- Idades originais que divergiam das datas em mais de 0,10 ano: **6583**; as datas coerentes prevaleceram.
- PPA: a categoria Não Calculado passou a ausente. Os valores já informados foram mantidos, mas não foram recalculados nem validados como diagnóstico.
- A classificação do IMC é descritiva e não substitui avaliação clínica.

## Análises geradas

As sete variáveis numéricas estão em resumo_numericas.csv; datas em resumo_datas.csv; categorias e ausências em resumo_categoricas.csv. As comparações com NORMAL X ANORMAL estão em bivariada_numericas.csv, bivariada_categoricas.csv e nos diretórios graficos/ e graficos_bivariada/. A variável ID não entra como explicativa.

O relatório técnico está em relatorio_analise.md. A versão paginada em relatorio_A1.pdf é gerada depois da análise por python scripts/gerar_relatorio_a1.py e mantém a figura de IDADE × alvo dentro do documento.

Na comparação IDADE × NORMAL X ANORMAL, a mediana é **4.77 anos** no grupo Normal (n válido = 6202) e **2.62 anos** no grupo Anormal (n válido = 4607). A diferença descreve os registros disponíveis e não estabelece causalidade. O gráfico omite pontos extremos do desenho; as estatísticas usam todos os valores válidos.

## Limites e referências

Os limites numéricos são verificações técnicas amplas para erros de registro, não pontos de corte diagnósticos. Datas ou medidas contraditórias sem solução segura permanecem ausentes ou constam em pendencias.csv. A tabela simplificada de pressão arterial foi retirada do fluxo; o arquivo antigo calculos_ppa.csv não é produzido.

Referências do IMC: OMS, Child Growth Standards 2006 (0–5 anos) e Growth Reference 2007 (5–19 anos). Os pontos de corte compactos e suas fontes estão em referencias/. O CSV limpo não contém codificação, padronização numérica, PCA nem balanceamento; o preparo de modelagem é separado para impedir que parâmetros sejam aprendidos no teste.

## Plano para a próxima etapa

`plano_modelagem.md` registra a decisão prevista para cada variável e a ordem das transformações. A limpeza acima usa regras fixas por registro; a padronização de Convenio agora converte grafias para maiúsculas sem acentos e não consulta frequências da base. A divisão de treino e teste, a imputação, a codificação e a padronização ajustadas apenas no treino estão em `scripts/preparar_modelagem.py`. O cenário inicial é anterior ao exame e depende da confirmação do momento em que cada campo foi registrado. Não há modelo treinado nesta etapa.

## Uso de IA generativa

OpenAI Codex foi usado para revisar os dados, corrigir os scripts, organizar as saídas e redigir esta documentação. As regras, os resultados e as conclusões devem ser conferidos pelo grupo antes da submissão.
