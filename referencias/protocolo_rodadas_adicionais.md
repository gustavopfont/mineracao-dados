# Protocolo das rodadas adicionais de comparação (desenvolvimento)

Fixado em 17/11/2026, antes de qualquer resultado das rodadas. Implementa os itens 2 e 3 do [plano da próxima comparação](plano_comparacao_modelos.md) sobre o mesmo desenvolvimento da [v3](../resultado_experimentos_reduzido/relatorio_experimentos.md), que continua sendo a referência da A2. As rodadas são declaradas em [`config_rodadas.json`](../config_rodadas.json), executadas por [`scripts/rodadas_experimentos.py`](../scripts/rodadas_experimentos.py) e gravadas em `resultado_experimentos_rodadas/`.

## Decisões, fontes e implementação

| Etapa | Decisão | Fonte e limite | Código / evidência |
| --- | --- | --- | --- |
| População | Os 9.148 registros de desenvolvimento da v3, identificados por `particao_principal.csv` e conferidos pelo hash do [inventário](inventario_experimentos.json). Os 2.288 registros de teste são descartados ao carregar. | TRIPOD+AI [S2]; o teste já foi avaliado na v3 e **não é aberto de novo**, nem para escolher modelos | `load_development`, `protocolo.json` |
| Folds externos | Cada rodada declara número de folds e sementes próprias. A primeira usa 5 folds × 2 repetições (sementes 606 e 707), diferentes dos 2 folds × 5 repetições da v3. | [S3]; folds de repetições distintas reaproveitam registros e não são independentes | `folds`, `particao_externa_r*.csv` |
| Validação aninhada | Três folds internos em cada treino externo, semente interna = semente externa × 10 + índice do fold. Pré-processamento, busca, perfil e limiar são ajustados só no treino do fold. | [S4]; escores internos são otimistas por seleção | `fit_representations`, `search_and_fit` (reaproveitados da v3) |
| Hiperparâmetros | 12 candidatos por família/perfil: os 4 da v3 primeiro, mais 8 sorteados sem reposição da mesma grade com semente 4242 + índice da família. A logística percorre a grade inteira (12). Lista idêntica nos três perfis e folds. | [S8]; a grade segue `modelos_ucmf.py`. Mantém o contraste de orçamento; um orçamento maior não garante o ótimo global | `build_candidates`, `candidates_notes` em `protocolo.json` |
| Grades alternativas | Uma rodada pode substituir a grade de uma família com `espacos`. Combinações, sementes e orçamento devem ser registrados antes de executar. | Plano, item 2; sem uso na primeira rodada | `build_candidates` |
| Perfis, métricas e limiar | Iguais à [v3](protocolo_experimentos.md): contínua, clínica e combinada; AP escolhe candidato e perfil; limiar de maior recall com especificidade interna ≥80%. | [S10–S12]; 80% é escolha acadêmica | `metricas_modelagem.py` |
| Inferência | Sem testes de hipótese para folds ≠ 2×5. Médias, desvios, contagem de folds abaixo da meta e métricas agregadas por repetição são descritivos. O F combinado 5×2 só é calculado em rodadas 2×5. | [S13–S14]; [Bengio e Grandvalet](https://jmlr.csail.mit.edu/papers/v5/grandvalet04a.html): folds sobrepostos não dão variância independente | `consolidate_round` |
| Comparabilidade | Diferenças em relação à v3 misturam tamanho do treino externo (50% → 80%), orçamento e folds. Não se atribui a diferença a um único fator. | Plano, item 3 | `comparacao_rodadas.md` |
| Persistência | Checkpoint por modelo/perfil/fold. Após cada fold externo completo, regeneram-se as tabelas da rodada e o consolidado com a v3. Retomada exige hashes idênticos de dados, código, configuração e ambiente; mudanças exigem novo `id`. | [S2]; o cache só reaproveita ajustes sobre os mesmos dados | `run_round`, `protocolo.json`, `estado_rodada.json` |

## Organização das saídas

| Local | Conteúdo |
| --- | --- |
| `resultado_experimentos_rodadas/<id>/relatorio_rodada.md` | Desenho, candidatos, médias por fold e por repetição, perfis, hiperparâmetros escolhidos e limites |
| `resultado_experimentos_rodadas/<id>/metricas_externas.csv`, `metricas_por_representacao.csv`, `metricas_repeticoes.csv`, `resumo_desenvolvimento.csv`, `hiperparametros_selecionados.csv` | Mesmas colunas da v3, com `rodada` |
| `resultado_experimentos_rodadas/<id>/protocolo.json`, `estado_rodada.json`, `particao_externa_r*.csv` | Configuração, candidatos, hashes, andamento e IDs de cada fold |
| `resultado_experimentos_rodadas/consolidado/` | `registro_rodadas.csv/json`, `metricas_*_todas_rodadas.csv`, `hiperparametros_selecionados_todas_rodadas.csv` e `comparacao_rodadas.md`, incluindo a v3 como `v3_5x2_4cand` |

Pipelines, cache, previsões por fold, logs e locks ficam locais (ver `.gitignore`), como na v3.

## Executar e acompanhar

```powershell
python scripts/rodadas_experimentos.py --listar
python scripts/rodadas_experimentos.py --rodada r01_5folds_2rep_12cand
python scripts/rodadas_experimentos.py --rodada r01_5folds_2rep_12cand --max-folds 2
python scripts/rodadas_experimentos.py --consolidar
```

`--max-folds N` para após N folds externos novos e pode ser retomado depois. Para uma nova rodada, acrescente um objeto com `id` inédito em `config_rodadas.json` e execute-o; as anteriores e a v3 não são reescritas. Um `rodada.lock` remanescente exige conferir se há processo ativo antes de retomar.

## Referências

As fontes S2–S4, S8, S10–S14 são as do [protocolo da v3](protocolo_experimentos.md#referências). Acrescenta-se [Bengio e Grandvalet (2004)](https://jmlr.csail.mit.edu/papers/v5/grandvalet04a.html), *No unbiased estimator of the variance of K-fold cross-validation*, e [Varma e Simon (2006)](https://pubmed.ncbi.nlm.nih.gov/16504092/) sobre viés de seleção sem validação aninhada. Nenhum resultado de validação interna é descrito como validação clínica externa.
