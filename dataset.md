# Variáveis do conjunto UCMF

O conjunto descreve atendimentos em cardiologia de crianças e jovens de 0 a 19 anos. A descrição original está em Variáveis do conjunto de dados.pdf. O arquivo UCMF_raw.csv tem 21 colunas; UCMF_limpo.csv mantém essas colunas e acrescenta CLASSIFICACAO IMC.

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

O destino de cada variável na modelagem está em `plano_modelagem.md`. O conjunto limpo mantém as colunas para análise e auditoria; a seleção de preditores ocorre separadamente.
