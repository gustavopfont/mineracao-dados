# Preparo para modelagem

Esta saída usa UCMF_limpo.csv, gerado pela limpeza determinística da A1. O momento provisório da previsão é **antes_exame**. Nenhum classificador foi treinado e o teste não foi usado para escolher atributos nem para ajustar transformações.

| Conjunto | Distribuição |
| --- | --- |
| Treino | 9364 registros; 5396 Normal; 3968 Anormal |
| Teste reservado | 2341 registros; 1349 Normal; 992 Anormal |
| Sem rótulo, fora da divisão | 429 registros |

Os grupos de registros idênticos sem ID e alvo foram mantidos no mesmo conjunto. Há **4 grupos** com rótulos conflitantes, listados em rotulos_conflitantes.csv. Não há IDs repetidos; ainda assim, não é possível provar apenas com estes campos que uma pessoa não tenha recebido IDs diferentes em atendimentos distintos.

## Atributos e funções

- Numéricos: IDADE, Peso, Altura, FC, PA SISTOLICA, PA DIASTOLICA.
- Categóricos: SEXO, MOTIVO1.
- `select_features` define as colunas; `row_features` converte tipos sem aprender com outras linhas; `split_labeled` separa grupos; `build_preprocessor` declara as operações ajustáveis; `fit_on_train` executa `fit_transform` somente no treino e `transform` no teste.
- Numéricos: mediana do treino para ausências, indicador de ausência e padronização com média e desvio do treino.
- Categóricos: categoria técnica Sem informação, distinta de valores clínicos como SOPRO = Ausente; agrupamento de níveis com menos de 10 ocorrências no treino e codificação one-hot. Categorias inéditas no teste não alteram o vocabulário aprendido.
- A matriz resultante tem 22 atributos, com 9364 linhas no treino e 2341 no teste. Ela não é duplicada em CSV: o objeto ajustado está em preprocessador_treino.joblib e os IDs em divisao_treino_teste.csv.

As escolhas de variáveis e o momento da previsão precisam ser confirmados antes de treinar um modelo. Seleção supervisionada, PCA e eventual reamostragem são decisões da próxima etapa e deverão ocorrer dentro de cada treino da validação cruzada. O teste reservado só poderá ser usado na avaliação final.
