# Plano de transformação e modelagem

## Protocolo de experimentos atual

Atualização de orçamento em 15/11/2026: quatro configurações por família e por perfil, mantendo os três perfis, validação externa 5×2 e interna de três folds. A execução válida fica em `resultado_experimentos_reduzido/`. A busca anterior de 12 configurações foi encerrada antes do teste e preservada em `resultado_experimentos_representacoes/`, com código e configuração de origem. Candidatos novos são sorteados com sementes fixas, sem seleção por escores antigos.

O plano de treino foi materializado em `config_experimentos.json`, `scripts/treinar_modelos.py` e `referencias/protocolo_experimentos.md`. Por solicitação posterior, compara três representações: contínua (incluindo IMC), clínica (faixa etária, classificação IMC e PPA) e combinada, sem remover os demais campos clínicos aprovados. A seleção por representação acontece por AP nos folds internos, dentro de cada família. A avaliação externa inclui essa escolha; o teste fica reservado até o congelamento. A execução parcial anterior foi preservada e marcada como interrompida antes do teste.

A base supervisionada de 11 preditores continua como contrato de seleção/deduplicação; a visão complementar é incorporada apenas para esses experimentos, pelos mesmos IDs. Todos os perfis têm as mesmas observações e partições. A documentação técnica detalha as fontes por etapa, os modelos, espaços de busca, testes estatísticos e limitações de identidade de paciente, exploração anterior e exclusão de conflitos. As seções históricas abaixo não substituem esse protocolo.

## Estado atual do KDD — preparação antes dos modelos

A seleção supervisionada atual está em `resultado_modelagem_preparo/` e é gerada por `scripts/auditar_base_modelagem.py`. Os valores finais de 17 colunas são preservados como referência; a seleção contém 11 preditores, sem derivados redundantes, com deduplicação concordante e quarentena de conflitos. O preparo em `scripts/preparar_modelagem.py` foi atualizado e não executa mais split/fit em sua CLI. `resultado_modelagem/` permanece como saída histórica. A justificativa de cada regra, fontes, implementação e testes está em `referencias/metodologia_preparo.md`.

O objetivo final é `avaliacao2.md`: organizar dados, testar e comparar modelos, interpretar erros e apresentar resultados em artigo IEEE. Nesta fase não há classificadores. Na próxima, definir partições reproduzíveis, comparar pelo menos um baseline e um modelo complexo com o Pipeline completo por treino, priorizar sensibilidade de Anormal e definir o compromisso com especificidade sem consultar teste. As hipóteses históricas abaixo não são a seleção atual.

> Documento da etapa anterior. A finalização atual gera `resultado_analise/UCMF_base_final.csv`, sem executar este preparo nem alterar as divisões existentes. A base final exclui SOPRO por escolha pedagógica, inclui motivos e HDA unificados e PPA calculada; mantém achados clínicos e histórico de cardiopatia conhecida para o exercício. As decisões abaixo continuam sendo hipóteses para uma modelagem futura, não a descrição do esquema final. O script de modelagem existente ainda lê a base limpa anterior; sua adaptação e a escolha do momento de previsão ficam fora desta entrega.

Este plano complementa a limpeza e a análise da A1. O cenário inicial prevê `NORMAL X ANORMAL` **antes do exame clínico**, após o registro dos dados demográficos, do motivo de encaminhamento e dos sinais vitais. É uma hipótese de trabalho: a equipe deve confirmar em que momento cada campo é conhecido. O script também aceita `--momento apos_exame`, que acrescenta achados do exame, mas esse cenário só é válido se esses achados forem registrados antes do diagnóstico que define o alvo.

## Decisão por variável

| Variável | Plano para o cenário inicial | Motivo |
| --- | --- | --- |
| ID | Remover dos preditores; manter na auditoria | Identifica o registro, não uma característica clínica. |
| Peso | Usar, com imputação e indicador de ausência ajustados no treino | Medida disponível antes do exame. |
| Altura | Usar, com imputação e indicador de ausência ajustados no treino | Medida disponível antes do exame. |
| IMC | Não incluir junto de Peso e Altura na base inicial | É derivado dessas medidas; comparar alternativas apenas no treino. |
| Atendimento | Não usar a data bruta | IDADE já representa a informação temporal relevante; datas atípicas seguem auditadas. |
| DN | Não usar a data bruta | Usada para derivar IDADE, sem incluir o identificador temporal no modelo. |
| IDADE | Usar, com imputação e indicador de ausência ajustados no treino | Atributo derivado por regra fixa de cada linha. |
| Convenio | Remover da base clínica inicial | Não descreve diretamente a condição clínica e tem muitas categorias. |
| PULSOS | Reservar para o cenário após exame | Confirmar disponibilidade antes do diagnóstico. |
| PA SISTOLICA | Usar, com imputação e indicador de ausência ajustados no treino | Sinal vital; há grande proporção de ausências. |
| PA DIASTOLICA | Usar, com imputação e indicador de ausência ajustados no treino | Sinal vital; há grande proporção de ausências. |
| PPA | Não usar na base inicial | Muito ausente e a classificação informada na origem não foi validada. |
| NORMAL X ANORMAL | Usar apenas como alvo | Nunca incluir entre os preditores. |
| B2 | Reservar para o cenário após exame | Confirmar disponibilidade antes do diagnóstico. |
| SOPRO | Reservar para o cenário após exame | Forte associação descritiva exige cuidado com a ordem de registro. |
| FC | Usar, com imputação e indicador de ausência ajustados no treino | Sinal vital. |
| HDA 1 | Reservar para o cenário após exame | Confirmar disponibilidade no momento escolhido. |
| HDA2 | Remover da base inicial | 96,6% de ausências após a limpeza. |
| SEXO | Usar com categoria técnica de informação faltante e codificação one-hot | Categoria nominal, sem ordem numérica. |
| MOTIVO1 | Usar com categoria técnica de informação faltante e codificação one-hot | Motivo de encaminhamento, registrado antes da avaliação. |
| MOTIVO2 | Não usar até confirmar significado e momento de registro | Pode representar informação conhecida após a avaliação. |
| CLASSIFICACAO IMC | Não incluir junto de medidas e idade na base inicial | Derivada de IMC, idade e sexo; alternativa a comparar no treino. |

## Ordem de execução e prevenção de vazamento

1. **Limpeza de regra fixa:** ler o CSV, marcar sentinelas como ausentes, aplicar limites técnicos definidos previamente, converter datas, derivar IDADE e IMC quando houver dados coerentes e padronizar categorias por mapeamentos estáveis. Essas operações não estimam parâmetros a partir da população e são executadas por funções em `scripts/analise_dataset.py`. A tabela da OMS também é uma referência externa fixa.
2. **Separação:** usar apenas registros com alvo conhecido. Reservar aproximadamente um quinto para teste, com semente fixa e estratificação por classe. Registros com atributos idênticos, desconsiderando ID e alvo, ficam no mesmo conjunto. Grupos com rótulos conflitantes são registrados, não corrigidos por votação. Não há IDs repetidos, mas não é possível provar apenas com estes campos que uma pessoa não tenha recebido IDs diferentes em atendimentos distintos.
3. **Ajuste no treino:** a mediana numérica, as médias e desvios da padronização, o agrupamento de categorias raras e o vocabulário one-hot são aprendidos exclusivamente do treino. A categoria técnica para faltantes é distinta de `SOPRO = Ausente`, que significa um achado clínico. Depois, a mesma transformação é aplicada ao teste, sem `fit` adicional. `scripts/preparar_modelagem.py` implementa essa etapa e salva o transformador ajustado.
4. **Validação futura:** dentro de cada partição de validação cruzada, repetir o ajuste do pré-processamento apenas na parte de treino. Seleção supervisionada de atributos, PCA, ajustes de hiperparâmetros ou reamostragem, se necessários, também devem ficar dentro dessa partição. Não há balanceamento automático: a necessidade deve ser verificada na métrica do modelo. O teste reservado só deve ser consultado para avaliação final.

A análise bivariada da A1 usa a base disponível inteira para descrever os dados. Ela não constitui avaliação de um modelo. As decisões finais de seleção ou transformação supervisionada deverão ser reavaliadas apenas no treino para preservar a validade do teste.

O plano segue os temas de limpeza, criação, redução e transformação apresentados em `slides/`. Ele não prescreve PCA nem balanceamento sem evidência de benefício para o método escolhido.
