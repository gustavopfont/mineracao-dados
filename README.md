# Mineração de dados no conjunto UCMF

Projeto acadêmico sobre registros de atendimento em cardiologia pediátrica. O fluxo audita e prepara os dados e compara modelos para o alvo `NORMAL X ANORMAL`. A v3 inclui a avaliação no teste reservado. A r01 e a comparação ampliada usam o conjunto de desenvolvimento.

## Estrutura do repositório

| Pasta | Conteúdo |
| --- | --- |
| [`dados/`](dados/) | CSV original e [dicionário das variáveis](dados/dicionario.md), com os esquemas da base limpa, final e supervisionada. |
| [`config/`](config/) | Sementes, número de folds e orçamento de busca para a v3 e as rodadas adicionais. |
| [`referencias/`](referencias/) | Tabelas de referência para IMC e pressão arterial, fontes e inventário das buscas históricas. |
| [`scripts/`](scripts/) | Limpeza, análise exploratória, preparo supervisionado, treinamento e geração de relatórios. |
| [`tests/`](tests/) | Testes das regras de limpeza, do preparo e dos experimentos. |
| [`resultados/`](resultados/) | Bases derivadas, auditorias, figuras, métricas e relatórios versionados. |
| `execucoes/` | Saídas locais ignoradas pelo Git. Contém os registros históricos parciais em `v1/` e `v2/`, a execução em `ampliado/` e pode receber novas reproduções. |

### Onde consultar os resultados

| Pasta | Conteúdo |
| --- | --- |
| [`resultados/analise/`](resultados/analise/) | Base limpa, base final, auditorias e análises da A1. Os gráficos estão em [`graficos/`](resultados/analise/graficos/) e [`graficos_bivariada/`](resultados/analise/graficos_bivariada/). |
| [`resultados/preparo/`](resultados/preparo/) | Base supervisionada, atributos complementares e rastreabilidade de correções, conflitos e duplicatas. |
| [`resultados/modelagem_legada/`](resultados/modelagem_legada/) | Partições e transformador da preparação inicial, guardados para consulta histórica. |
| [`resultados/experimentos/`](resultados/experimentos/) | Reúne os resultados de treinamento e validação. |
| [`resultados/experimentos/v3/`](resultados/experimentos/v3/) | Modelos selecionados, métricas do teste reservado e [relatório da v3](resultados/experimentos/v3/relatorio_experimentos.md). |
| [`resultados/experimentos/rodadas/`](resultados/experimentos/rodadas/) | Rodada r01, análise exploratória de hipóteses e [comparação consolidada](resultados/experimentos/rodadas/consolidado/comparacao_rodadas.md). |
| [`resultados/experimentos/ampliado/`](resultados/experimentos/ampliado/) | Comparações de orçamento, curvas de aprendizado, ablações e subgrupos. |
| [`resultados/a2/`](resultados/a2/) | Tabelas, figuras, análise de erros e [estimativas do teto de desempenho](resultados/a2/teto_desempenho/). |

## Executar

Na raiz do repositório, instale as dependências e rode os testes com o ambiente Python ativo.

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests
```

Estes comandos regeneram a análise e a base supervisionada nos diretórios padrão.

```powershell
python scripts/analise_dataset.py
python scripts/finalizar_dataset.py
python scripts/auditar_base_modelagem.py
python scripts/preparar_modelagem.py
```

O último comando valida o esquema e declara o pré-processador. O ajuste ocorre nos dados de treino de cada partição durante o treinamento.

Use uma pasta local para reproduzir e acompanhar a v3.

```powershell
python scripts/treinar_modelos.py --fase todos --saida execucoes/v3_reproducao
python scripts/status_experimentos.py --saida execucoes/v3_reproducao
```

Consulte as configurações das rodadas adicionais com `python scripts/rodadas_experimentos.py --listar`. Use `--rodada ID --saida execucoes/rodadas_reproducao` para executar uma rodada e `--consolidar` com o mesmo diretório para reunir as métricas. O [guia da comparação ampliada](resultados/experimentos/ampliado/README.md) registra as versões e o comando para reproduzi-la.

Os checkpoints e logs locais da v3 e das rodadas também são ignorados pelo Git em suas respectivas pastas. Os relatórios e manifestos históricos podem citar os caminhos usados na época. Para retomar uma execução anterior à reorganização, use o commit correspondente com a estrutura e os checkpoints originais. Para uma execução nova, use uma pasta de saída nova.
