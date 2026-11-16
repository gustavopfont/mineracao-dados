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

As [notas oficiais das tabelas expandidas](https://www.who.int/docs/default-source/child-growth/child-growth-standards/indicators/body-mass-index-for-age/readme-bfa-exp.pdf) esclarecem que a tabela inicial vai até 1856 dias (antes de 61 meses completos) e que um mês corresponde a 30,4375 dias. A transição usada no projeto é 1856/1857 dias; a tabela posterior cobre meses completos 61 a 228, sem extrapolação. As faixas etárias gerais por aniversário não substituem a idade da referência OMS.

Na revisão de discretização, os limites foram conferidos contra [OMS 2006](https://www.who.int/news-room/questions-and-answers/item/child-growth-standards) e [OMS 2007](https://www.who.int/tools/growth-reference-data-for-5to19-years/indicators/bmi-for-age). Foram mantidas as categorias OMS, sem adotar agrupamentos adicionais do SISVAN. A justificativa estatística para preservar também as medidas contínuas está no [BMJ, 2025](https://www.bmj.com/content/390/bmj-2024-082440.short); as estratégias não supervisionadas estão descritas pelo [scikit-learn](https://sklearn.org/stable/modules/generated/sklearn.preprocessing.KBinsDiscretizer.html) e a discretização supervisionada por [Fayyad e Irani, 1993](https://ijcai.org/proceedings/1993/141). Fontes consultadas em 07/11/2026.

## Pressão arterial — DBHA 2025

`pa_dbha_2025.csv` contém 168 pontos: dois sexos × idades completas de 1 a 12 anos × sete alturas. Foi extraído das tabelas 9.2 (meninos) e 9.3 (meninas) da [Diretriz Brasileira de Hipertensão Arterial — 2025](https://www.scielo.br/j/abc/a/BXT7Vk4B9VKQnJFsJhgJ4Hn/?lang=pt), DOI 10.36660/abc.20250624, consulta em 07/11/2026. Unidades: altura em cm; PAS/PAD em mmHg. Inclui percentil da altura e limiares P90/P95 de PAS/PAD; o limiar P95+12 é derivado aritmeticamente. O JSON associado registra fonte e SHA-256, verificado ao carregar a tabela.

O gerador final usa a tabela 9.1 para menores de 18 anos e o quadro 3.2 a partir de 18. Para cada componente, os limiares pediátricos são o mínimo entre P90 e 120/80 (pré-hipertensão), P95 e 130/80 (estágio 1), P95+12 e 140/90 (estágio 2). Prevalece a maior categoria entre PAS e PAD. Menores de um ano ficam fora da referência adotada nesta versão.

Interpolação linear entre as alturas publicadas é uma aproximação computacional explícita do projeto, não uma recomendação adicional da diretriz. Não se extrapola, não se arredondam limiares interpolados e não se usa altura imputada. Não se usa a tabela simplificada de triagem como classificador. `PPA_CALCULADA` descreve uma medida, sem confirmação diagnóstica ou alegação de validação clínica do algoritmo.

Para atualizar a extração, salvar o HTML completo da fonte e executar:

```powershell
python -m pip install lxml
python scripts/extrair_referencia_pa.py caminho/para/diretriz.html
```

O extrator é uma ferramenta de manutenção: a execução normal de `scripts/finalizar_dataset.py` não baixa fontes nem requer lxml. Revisar os pontos extraídos e executar os testes antes de aceitar uma nova versão.
