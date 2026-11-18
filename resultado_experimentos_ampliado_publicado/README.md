# Resultados publicados da comparação ampliada

Execução concluída em **18/11/2026, às 03h24 (Brasília)**. Foram avaliados Dummy, regressão logística, Random Forest e HistGradientBoosting nos 9.148 registros do desenvolvimento histórico da v3. No 5×2, o experimento usou as mesmas partições externas da v3 e buscou 12 ou 16 configurações por família e perfil. No 2×5, usou 12. A rodada de dez folds externos foi retirada antes de começar.

A comparação complementa a [v3 e seu teste reservado](../resultado_experimentos_reduzido/relatorio_experimentos.md). Para os novos ajustes, as estimativas vêm dos folds externos do desenvolvimento. `referencia_teste_historico_v3.csv` reproduz as métricas congeladas do teste da v3 para consulta.

| Conteúdo | Arquivos |
| --- | --- |
| Protocolo, grades exatas, versões e integridade | [Protocolo](protocolo.json) · [Manifesto](manifesto_publicacao.json) |
| Comparação de modelos, orçamentos e perfis | [Relatório](relatorio_comparativo.md) · [Resumo](resumo_modelos.csv) · [Por fold](metricas_por_fold.csv) · [Por repetição](metricas_por_repeticao.csv) · [Perfis fixos](metricas_perfis_fixos.csv) |
| Diferenças pareadas e testes | [Orçamentos na mesma partição](diferencas_pareadas_orcamento.csv) · [F/t 5×2 com Holm](testes_exploratorios_5x2.json) · [Discordâncias por fold](discordancias_por_fold.csv) |
| Dados de treino, retirada de atributos e subgrupos | [Curvas de aprendizado](curvas_aprendizado.csv) · [Ablações](ablacoes.csv) · [Diferenças das ablações](diferencas_pareadas_ablacoes.csv) · [Subgrupos](subgrupos_por_fold.csv) |
| Qualidade dos rótulos e cobertura | [Conflitos](auditoria_conflitos.csv) · [Contagens da quarentena](rotulos_quarentena.csv) · [Cobertura](cobertura_desenvolvimento.csv) |

As tabelas trazem medidas por grupo, fold ou repetição. Para localizar uma configuração nos resultados, a coluna `candidate` usa índice começando em zero na grade da família em `protocolo.json`. As linhas históricas `v3_4` usam os artefatos da v3. O manifesto relaciona os 420 checkpoints verificados às fases e registra hashes dos arquivos publicados. As previsões individuais, os checkpoints e os logs permanecem na área de execução local.

## Comparação com a r01

A tabela usa a média aritmética dos dez folds externos de cada desenho 2×5, sempre com o limiar aprendido no treino. O consolidado da r01 apresenta AP calculada em previsões reunidas por repetição. As duas rodadas usam os mesmos 9.148 registros, com partições, grades e versões de bibliotecas próprias. A r01 também avalia árvore e KNN. Consulte as [métricas por fold da r01](../resultado_experimentos_rodadas/r01_5folds_2rep_12cand/metricas_externas.csv) e as [da extensão](metricas_por_fold.csv).

| Rodada | Modelo | Sensibilidade | Especificidade | AP | ROC-AUC | F1 | Brier | Folds abaixo de 80% de especificidade |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| r01 | Logística | 0,6397 | 0,8035 | 0,7547 | 0,7851 | 0,6718 | 0,1814 | 3/10 |
| r01 | Floresta | 0,6493 | 0,8066 | 0,7647 | 0,7937 | 0,6799 | 0,1796 | 4/10 |
| r01 | Boosting | 0,6442 | 0,8083 | 0,7653 | 0,7966 | 0,6772 | 0,1773 | 3/10 |
| Extensão | Logística | 0,6406 | 0,8043 | 0,7539 | 0,7846 | 0,6728 | 0,1817 | 4/10 |
| Extensão | Floresta | 0,6520 | 0,8047 | 0,7609 | 0,7928 | 0,6809 | 0,1837 | 4/10 |
| Extensão | Boosting | 0,6426 | 0,8089 | 0,7641 | 0,7956 | 0,6764 | 0,1779 | 1/10 |

Entre os modelos em comum, a floresta liderou em sensibilidade média e F1 nas duas rodadas. O boosting teve as maiores AP e ROC-AUC e o menor Brier. A floresta ficou abaixo da meta de especificidade em quatro folds nas duas rodadas. Os valores descrevem o desempenho interno com partições distintas e registros compartilhados.

### Testes de hipótese disponíveis

| Rodada | Comparação | Onde consultar |
| --- | --- | --- |
| v3 | F combinado e t no desenho 5×2 para erro global de árvore, KNN, floresta e boosting contra logística, com Holm | [F/t 5×2](../resultado_experimentos_reduzido/testes_5x2.json) |
| v3, teste reservado | McNemar exato para a floresta contra logística, com comparações separadas para detecção de anormais e classificação de normais | [McNemar](../resultado_experimentos_reduzido/mcnemar_teste.json) · [IC95% bootstrap pareado](../resultado_experimentos_reduzido/bootstrap_ic95.csv) |
| r01 | Teste t pareado corrigido para 2×5, em sensibilidade, especificidade e erro global, com Holm nos 30 contrastes entre os cinco modelos | [Resultados da r01](../resultado_experimentos_rodadas/r01_5folds_2rep_12cand/inferencia_exploratoria/relatorio.md) |
| 2×5 da extensão | Comparação descritiva por fold e repetição | [Resumo da extensão](resumo_modelos.csv) |
| 5×2 da extensão | F combinado e t exploratórios para erro global de floresta e boosting contra logística, nas grades de 12 e 16, com Holm | [F/t 5×2 da extensão](testes_exploratorios_5x2.json) |

No 5×2 da extensão, o p ajustado pelo teste F foi 1,000 nos quatro contrastes. O menor p ajustado pelo teste t foi 0,293. Esses testes não rejeitaram a hipótese nula de mesma taxa de erro. A comparação de sensibilidade da v3 no teste reservado também não detectou diferença (McNemar com Holm, p = 0,828). Equivalência ou superioridade na sensibilidade exigem perguntas e análises próprias.

O [executor](../scripts/comparar_modelos_ucmf.py) recria a extensão com as entradas e versões do protocolo. A v3 registrou o hash da base supervisionada em um checkout com finais de linha CRLF. Para reproduzir de um clone novo com os mesmos bytes de entrada, use `git clone --config core.autocrlf=true https://github.com/gustavopfont/mineracao-dados.git`. Na raiz do projeto, execute `python -u scripts/comparar_modelos_ucmf.py` no ambiente correspondente. A saída padrão é `resultado_experimentos_ampliado/`. Os métodos e as referências estão no [plano de comparação](../referencias/plano_comparacao_modelos.md).
