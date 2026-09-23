ID ID do paciente anônimo
Peso peso do paciente
Altura altura do paciente
IMC índice de massa corporal
Atendimento data da visita
DN data de nascimento
IDADE idade
Convenio seguro de saúde
PULSOS pulsação
PA SISTOLICA pressão arterial sistólica (PAS)
PA DIASTOLICA pressão arterial diastólica (PAD)
PPA hipertensão arterial (resultado de PAS e PAD)
NORMAL X ANORMAL ausência ou presença de patologia cardíaca (variável-alvo)
B2 tipo do segundo som cardíaco
SOPRO tipo de sopro
FC frequência cardíaca
HDA 1 histórico da doença 1
HDA2 histórico da doença 2 (outro histórico)
SEXO sexo do paciente
MOTIVO1 primeiro motivo para ser encaminhado para a clínica de cardiologia
MOTIVO2 segundo motivo para ser encaminhado para a clínica de cardiologia

| Variável         | Tipo esperado      | Verificações principais                      |
| ---------------- | ------------------ | -------------------------------------------- |
| ID               | identificador      | duplicatas, valores faltantes                |
| Peso             | numérica contínua  | zero, ausentes, valores impossíveis/outliers |
| Altura           | numérica contínua  | zero, ausentes, unidade                      |
| IMC              | numérica contínua  | ausentes, consistência com peso/altura       |
| Atendimento      | data               | data inválida/ausente                        |
| DN               | data               | data inválida, DN > atendimento              |
| IDADE            | numérica contínua  | negativa, inconsistente com datas            |
| Convenio         | categórica nominal | ausentes, categorias inconsistentes          |
| PULSOS           | categórica         | ausentes, categorias e grafia                |
| PA SISTOLICA     | numérica           | ausentes, valores extremos                   |
| PA DIASTOLICA    | numérica           | ausentes, valores extremos                   |
| PPA              | categórica         | consistência com PA                          |
| NORMAL X ANORMAL | categórica binária | ausentes, equilíbrio das classes             |
| B2               | categórica         | padronização das categorias                  |
| SOPRO            | categórica         | `Sistólico` × `sistólico`, ausentes          |
| FC               | numérica           | extremos, valores incompatíveis              |
| HDA 1            | categórica         | ausentes, grafia/categorias                  |
| HDA2             | categórica         | muitos ausentes                              |
| SEXO             | categórica binária | categorias inválidas/ausentes                |
| MOTIVO1          | categórica         | padronização                                 |
| MOTIVO2          | categórica         | muitos ausentes                              |
