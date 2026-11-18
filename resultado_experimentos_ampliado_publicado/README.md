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

O [executor](../scripts/comparar_modelos_ucmf.py) recria a extensão com as entradas e versões do protocolo. A v3 registrou o hash da base supervisionada em um checkout com finais de linha CRLF. Para reproduzir de um clone novo com os mesmos bytes de entrada, use `git clone --config core.autocrlf=true https://github.com/gustavopfont/mineracao-dados.git`. Na raiz do projeto, execute `python -u scripts/comparar_modelos_ucmf.py` no ambiente correspondente. A saída padrão é `resultado_experimentos_ampliado/`. Os métodos e as referências estão no [plano de comparação](../referencias/plano_comparacao_modelos.md).
