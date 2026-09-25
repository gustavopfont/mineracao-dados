# Referências de IMC por idade

Os dois CSVs desta pasta foram extraídos das tabelas expandidas de escore Z publicadas pela Organização Mundial da Saúde. Contêm apenas os cortes necessários à classificação usada neste projeto: −3, −2, +1, +2 e +3 desvios padrão. As tabelas originais da OMS também incluem outros valores e parâmetros.

| Arquivo | Idade | Origem |
| --- | --- | --- |
| imc_oms_0_5.csv | Dia 0 a 1856, por sexo | [OMS: IMC por idade, nascimento a 5 anos](https://www.who.int/toolkits/child-growth-standards/standards/body-mass-index-for-age-bmi-for-age), tabelas expandidas de meninas e meninos |
| imc_oms_5_19.csv | Mês 61 a 228, por sexo | [OMS: IMC por idade, 5 a 19 anos](https://www.who.int/toolkits/growth-reference-data-for-5to19-years/indicators/bmi-for-age), tabelas expandidas de meninas e meninos |

Fontes diretas dos arquivos da OMS consultados em 23/09/2026:

- [Meninas, 0–5 anos](https://cdn.who.int/media/docs/default-source/child-growth/child-growth-standards/indicators/body-mass-index-for-age/expanded-tables/bfa-girls-zscore-expanded-tables.xlsx)
- [Meninos, 0–5 anos](https://cdn.who.int/media/docs/default-source/child-growth/child-growth-standards/indicators/body-mass-index-for-age/expanded-tables/bfa-boys-zscore-expanded-tables.xlsx)
- [Meninas, 5–19 anos](https://cdn.who.int/media/docs/default-source/child-growth/growth-reference-5-19-years/bmi-for-age-%285-19-years%29/bmi-girls-z-who-2007-exp.xlsx)
- [Meninos, 5–19 anos](https://cdn.who.int/media/docs/default-source/child-growth/growth-reference-5-19-years/bmi-for-age-%285-19-years%29/bmi-boys-z-who-2007-exp.xlsx)

O classificador usa a idade exata em dias até 60 meses completos e a idade em meses completos de 61 a 228 meses. Não procura uma idade aproximada entre poucos pontos de referência. A classificação é descritiva e não substitui avaliação clínica.
