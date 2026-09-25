# Pré-processamento do conjunto UCMF

Projeto da Avaliação 1 de Mineração de Dados. O conjunto bruto registra atendimentos em cardiologia pediátrica. O objetivo desta etapa é examinar a qualidade dos dados, limpar inconsistências, criar atributos justificados e comparar as variáveis com NORMAL X ANORMAL.

## Organização

| Local | Conteúdo |
| --- | --- |
| UCMF_raw.csv | Dados recebidos. Não é modificado pelo processamento. |
| scripts/analise_dataset.py | Leitura, limpeza, auditoria, análise e gráficos. |
| scripts/classificacao_imc.py | Classificação descritiva do IMC com referências da OMS. |
| referencias/ | Pontos de corte da OMS e indicação das fontes. |
| resultado_analise/UCMF_limpo.csv | Conjunto processado, com 21 colunas originais e CLASSIFICACAO IMC. |
| resultado_analise/alteracoes.csv | Valores originais e finais por ID e regra aplicada. |
| resultado_analise/pendencias.csv | Casos que não admitem correção segura apenas com o CSV. |
| resultado_analise/linhas_removidas.csv | Registros sem dados clínicos excluídos. |
| resultado_analise/registros_semelhantes.csv | Registros iguais nos demais campos, mantidos para revisão. |
| resultado_analise/qualidade_dados.csv | Ausências, limites e pendências por variável. |
| resultado_analise/resumo_*.csv | Resumos univariados numéricos, categóricos e de datas. |
| resultado_analise/bivariada_*.csv | Comparações com NORMAL X ANORMAL. |
| resultado_analise/graficos/ e graficos_bivariada/ | Visualizações correspondentes. |
| resultado_analise/relatorio_analise.md | Resumo interpretativo das saídas. |
| scripts/gerar_relatorio_a1.py | Geração do relatório paginado para a A1. |
| resultado_analise/relatorio_A1.pdf | Versão de cinco páginas, Arial 10, com gráfico inserido. |
| scripts/preparar_modelagem.py | Divisão reproduzível e transformações ajustadas apenas no treino. |
| resultado_modelagem/ | IDs de treino e teste, conflitos de rótulo, transformador e resumo. |
| plano_modelagem.md | Decisão e justificativa para cada variável na próxima etapa. |
| docs.md | Registro da limpeza, justificativas e limites. |
| dataset.md | Dicionário de variáveis e regras de representação. |
| slides/ | Material das aulas. |

## Executar

Na raiz do projeto:

```powershell
python -m pip install -r requirements.txt
python scripts/analise_dataset.py
python scripts/gerar_relatorio_a1.py
```

O comando regenera os arquivos de resultado_analise/ e docs.md. O CSV bruto permanece intacto. Para verificar as regras principais:

```powershell
python -m unittest discover -s tests
```

Para preparar uma divisão de treino e teste sem treinar um classificador:

```powershell
python scripts/preparar_modelagem.py --momento antes_exame
```

O cenário `antes_exame` é provisório. Após confirmar que achados clínicos foram registrados antes do diagnóstico, é possível executar `--momento apos_exame`. O comando ajusta imputação, categorias e escala só no treino, salva o transformador e mantém registros semelhantes no mesmo conjunto.

## Critérios de interpretação

O arquivo limpo mantém valores ausentes quando não há informação suficiente para recuperar um valor confiável. PPA não é recalculada: Não Calculado passou a vazio e as classificações informadas na origem permanecem sem validação clínica. Os dados e gráficos não devem ser usados para diagnóstico. Consulte pendencias.csv antes de concluir que uma variável está completa.

O relatório em Markdown guarda o detalhamento técnico. O PDF aplica o limite de cinco páginas e Arial 10 da A1; o grupo deve revisar a redação e os resultados antes da submissão no SIGAA. A apresentação oral de 15 minutos é uma entrega separada.

## Uso de IA generativa

OpenAI Codex auxiliou a auditoria, a correção dos scripts, a organização das saídas e a redação inicial da documentação. O grupo deve revisar os resultados e registrar o uso da ferramenta na entrega.
