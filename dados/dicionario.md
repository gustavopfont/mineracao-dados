# Variáveis do conjunto UCMF

## Seleção supervisionada

`resultados/preparo/UCMF_supervisionado.csv` mantém ID (metadado), alvo e 11 preditores: IDADE, Peso, Altura, FC, PA SISTOLICA, PA DIASTOLICA, SEXO, PULSOS, B2, MOTIVO_UNIFICADO e HDA_UNIFICADA. São seis numéricos, quatro nominais e um conjunto de menções de sintomas. IMC, classificação de IMC, faixa etária e PPA permanecem em `atributos_complementares.csv`, alinhados pela mesma ordem de ID. A base final de 17 colunas abaixo continua preservada.

Perfis são comparados após normalização e correções usando os 11 preditores, sem ID/alvo: concordantes são representados pelo menor ID numérico; grupos com alvos conflitantes são integralmente separados; desconhecidos ficam em registros_sem_alvo.csv. Igualdade de perfis não identifica pacientes, e essa escolha pode alterar frequências. Destinos e multiplicidade estão em rastreabilidade.csv. A HDA Assintomático + sintoma fica vazia nesta seleção, mantendo o original em correcoes.csv e na referência. Não há imputação no CSV, descarte automático de casos incompletos ou inferência de rótulos.

O transformador mantém dimensões para colunas vazias e indicadores de ausência em todas as numéricas. Imputação e codificação são ajustadas dentro das partições de treino. HDA tem menções binárias, ausência e categoria inédita; não mencionado não equivale a negado. `__SEM_INFORMACAO__` é categoria técnica, diferente de Indeterminado e Outro. Consulte [a fundamentação por etapa](../resultados/preparo/relatorio_adequacao.md), incluindo decisões locais e limitações da imputação por mediana.

## Esquema da base final

`resultados/analise/UCMF_base_final.csv` contém 17 colunas. Datas e campos originais continuam na base limpa e nas auditorias; as regras abaixo se aplicam exclusivamente à base final. O alvo e os valores clínicos mantidos não são imputados nem alterados nesta etapa.

| Coluna | Significado e representação |
| --- | --- |
| ID | Identificador preservado, somente rastreabilidade; excluir dos preditores. |
| SEXO | Masculino, Feminino ou Indeterminado; vazio quando desconhecido. |
| IDADE | Idade contínua da limpeza anterior, em anos; preservada. |
| FAIXA_ETARIA | [0,1), [1,3), [3,6), [6,13), [13,18), [18,20); rótulos Menor de 1 ano, 1–2 anos, 3–5 anos, 6–12 anos, 13–17 anos e 18–19 anos. |
| Peso | kg; valor da base limpa. |
| Altura | cm; valor da base limpa. |
| IMC | kg/m²; valor da base limpa. |
| CLASSIFICACAO IMC | Categoria OMS já calculada na limpeza; preservada. |
| FC | bpm; numérica, sem discretização automática. |
| PA SISTOLICA | mmHg; valor da base limpa. |
| PA DIASTOLICA | mmHg; valor da base limpa. |
| PPA_CALCULADA | Normal, Pré-hipertensão, HA estágio 1, HA estágio 2 ou HA estágio 3; categoria da medida, não diagnóstico. Estágio 3 aplica-se somente a adultos. |
| PULSOS | Categoria clínica preservada. |
| B2 | Categoria do segundo som cardíaco preservada. |
| MOTIVO_UNIFICADO | Grupo → detalhe; preserva códigos/textos, inclusive divergências, sopro e cardiopatia conhecida. Somente o campo disponível quando o outro falta. |
| HDA_UNIFICADA | Conjunto de sintomas distintos separado por ` \| `; ordem fixa: Assintomático, Palpitação, Dispneia, Dor precordial, Desmaio/tontura, Cianose, Ganho de peso, Outro; categorias novas ao final em ordem alfabética. |
| NORMAL X ANORMAL | Alvo Normal/Anormal; 429 registros sem alvo permanecem vazios. |

Aniversários calculados por DN/Atendimento coerentes determinam anos completos, faixa e referência de pressão; IDADE decimal é alternativa quando as datas não permitem o cálculo. IDADE contínua pode diferir na fronteira por arredondamento prévio; a auditoria guarda anos completos e origem. Para nascimento em 29/02, anos completos avançam em 01/03 nos anos não bissextos.

PPA usa DBHA 2025: de 1 a 12 anos, sexo, anos completos e altura, com interpolação linear em cm entre pontos da referência, sem extrapolação; 13–17 anos, cortes fixos da tabela 9.1; 18–19 anos, quadro 3.2 para adultos. A categoria mais elevada de PAS/PAD prevalece. Requer as duas medidas válidas; menores de um ano e casos insuficientes ficam vazios, com motivo em `comparacao_ppa_final.csv`. A PPA antiga não é usada para completar a nova nem para inferir o alvo.

`Assintomático` é informação clínica; não equivale a vazio. Contradições com sintomas são preservadas e sinalizadas. HDA2 é incorporada mesmo sem HDA1; duplicatas são removidas apenas dentro do conjunto de sintomas da mesma linha. Normalizações explícitas: Palpitacao → Palpitação; Dispnéia → Dispneia nos motivos; congenica → congênita; familia → família; cianose e dispnéia → cianose e dispneia.

SOPRO, Convenio, Atendimento, DN, PPA legada e pares originais de motivos/HDA não integram o esquema final. A auditoria retém os atributos retirados; as associações são calculadas antes da exclusão de SOPRO. Os campos com sufixo `original` na auditoria de finalização referem-se à base limpa; alterações desde o bruto estão em `alteracoes_limpeza_reproduzida.csv`.

B2, PULSOS e diagnósticos conhecidos permanecem por decisão acadêmica; sua disponibilidade temporal exige revisão na modelagem futura. IMC/classificação e peso/altura são parcialmente redundantes. Nenhum atributo é descartado automaticamente com base na associação ao alvo.

### Revisão de discretização

IMC, PAS e PAD permanecem numéricos. Suas classificações clínicas são complementares; não há grupos binários nem outra classificação equivalente a PPA_CALCULADA. As categorias OMS foram mantidas, incluindo limites de igualdade: magreza acentuada abaixo de −3; magreza de −3 inclusive a −2 exclusivo; eutrofia de −2 a +1 inclusive. Até 60 meses completos: risco de sobrepeso acima de +1 até +2 inclusive, sobrepeso acima de +2 até +3 inclusive, obesidade acima de +3. Na referência de 61–228 meses completos: sobrepeso acima de +1 até +2 inclusive, obesidade acima de +2. Não se acrescentou obesidade grave.

A escala OMS usa dias até 1856 e meses completos por `floor(dias / 30.4375)` na tabela posterior, incluindo todo o mês completo 228, sem extrapolar a partir do mês 229. Isso difere dos aniversários usados na pressão. A auditoria de IMC registra referência e idade aplicada; a referência etária dos resumos independe da presença de sexo ou medida. A precisão limitada do IMC registrado é documentada, sem inventar casas decimais.

Os resumos de cobertura incluem cada registro uma vez por variável e usam classificados/total do estrato. As frequências incluem categorias clínicas sem registros e a categoria técnica `Sem informação` apenas nas saídas de análise. O percentual entre classificados não inclui essa categoria técnica. Os resumos com o alvo mostram separadamente Normal, Anormal e desconhecido; proporção Anormal usa somente alvos conhecidos. Divisões por zero permanecem vazias, não viram 0%.

Quartis são apenas descrições da amostra: empates não são desfeitos e podem reduzir o número de intervalos; os métodos uniformes, k-means e supervisionados não geram atributos novos. `origem_altura` na auditoria distingue valor informado, recuperado pela relação antropométrica, ausente ou sem auditoria disponível; `formula_altura` só é preenchida para recuperação. Nenhum desses metadados amplia as 17 colunas da base final. PPA normal não significa ausência de hipotensão ou cardiopatia; a categoria refere-se aos limites superiores de pressão adotados.

## Esquema da base limpa de referência

O conjunto descreve atendimentos em cardiologia de crianças e jovens de 0 a 19 anos. O arquivo UCMF_raw.csv tem 21 colunas; UCMF_limpo.csv mantém essas colunas e acrescenta CLASSIFICACAO IMC.

| Variável | Significado | Tipo na análise |
| --- | --- | --- |
| ID | Identificador anônimo do registro | Identificador |
| Peso | Peso do paciente, em kg | Numérica |
| Altura | Altura do paciente, em cm | Numérica |
| IMC | Índice de massa corporal, em kg/m² | Numérica |
| Atendimento | Data da visita | Data |
| DN | Data de nascimento | Data |
| IDADE | Idade em anos | Numérica |
| Convenio | Seguro de saúde | Categórica |
| PULSOS | Descrição dos pulsos | Categórica |
| PA SISTOLICA | Pressão arterial sistólica | Numérica |
| PA DIASTOLICA | Pressão arterial diastólica | Numérica |
| PPA | Classificação de pressão informada na origem | Categórica |
| NORMAL X ANORMAL | Ausência ou presença de patologia cardíaca | Alvo |
| B2 | Segundo som cardíaco | Categórica |
| SOPRO | Tipo de sopro | Categórica |
| FC | Frequência cardíaca | Numérica |
| HDA 1 | Histórico da doença 1 | Categórica |
| HDA2 | Histórico da doença 2 | Categórica |
| SEXO | Sexo registrado | Categórica |
| MOTIVO1 | Primeiro motivo do encaminhamento | Categórica |
| MOTIVO2 | Segundo motivo do encaminhamento | Categórica |
| CLASSIFICACAO IMC | Categoria derivada do IMC por idade e sexo | Categórica derivada |

## Regras de representação

- O CSV limpo usa cabeçalhos sem espaços externos, datas em ISO 8601 (AAAA-MM-DD), ponto decimal e células vazias para valores ausentes.
- SEXO é padronizado como Masculino, Feminino ou Indeterminado. O alvo é Normal ou Anormal; valores sem rótulo ficam vazios.
- Convenio é padronizado para maiúsculas sem acentos por regra fixa, sem consultar frequências de outras linhas.
- Peso, Altura e IMC iguais a zero não representam medições e passam a ausentes. PPA igual a Não Calculado também passa a ausente.
- IDADE é recalculada por (Atendimento − DN) / 365,25 quando ambas as datas produzem uma idade de 0 a menos de 20 anos. Em outros casos, a idade original dentro dessa faixa é mantida ou fica ausente, com indicação em pendencias.csv.
- CLASSIFICACAO IMC usa pontos de corte por sexo e idade das referências oficiais da OMS em referencias/. O resultado é descritivo e não substitui avaliação clínica.
- PPA preenchida na origem é mantida, sem recálculo. A tabela simplificada de pressão antes presente no projeto não fornece validação clínica suficiente para completar os casos ausentes.

## Limites técnicos de consistência

Os limites abaixo detectam erros evidentes de registro. Eles não são limites diagnósticos. Valores fora deles ficam ausentes no CSV limpo e são listados em alteracoes.csv e pendencias.csv.

| Variável | Faixa mantida |
| --- | --- |
| Peso | maior que 0 e até 200 kg |
| Altura | maior que 30 e até 220 cm |
| IMC | maior que 8 e até 70 kg/m² |
| IDADE | de 0 a menos de 20 anos |
| FC | maior que 30 e até 250 bpm |
| PA SISTOLICA | maior que 40 e até 250 mmHg |
| PA DIASTOLICA | maior que 20 e até 150 mmHg |

As pressões sistólica e diastólica são deixadas ausentes quando a sistólica é menor ou igual à diastólica. Medidas antropométricas que produzem IMC fora do limite técnico permanecem em pendencias.csv para revisão da origem.

As regras de seleção estão na [metodologia de preparo](../resultados/preparo/relatorio_adequacao.md). O conjunto limpo mantém as colunas para análise e auditoria; a seleção de preditores ocorre separadamente.
