"""Gera o relatório de submissão da A1 em até cinco páginas A4, Arial 10."""

from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "resultados/analise"
OUTPUT = RESULT / "relatorio_A1.pdf"
TARGET = "NORMAL X ANORMAL"
NUMERIC = ["Peso", "Altura", "IMC", "IDADE", "FC", "PA SISTOLICA", "PA DIASTOLICA"]
DATES = ["Atendimento", "DN"]
CATEGORICAL = [
    "Convenio", "PULSOS", "PPA", TARGET, "B2", "SOPRO", "HDA 1",
    "HDA2", "SEXO", "MOTIVO1", "MOTIVO2", "CLASSIFICACAO IMC",
]


def register_fonts() -> None:
    font_dir = Path("C:/Windows/Fonts")
    pdfmetrics.registerFont(TTFont("Arial", str(font_dir / "arial.ttf")))
    pdfmetrics.registerFont(TTFont("Arial-Bold", str(font_dir / "arialbd.ttf")))
    pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold")


def integer(value: object) -> str:
    return f"{int(value):,}".replace(",", ".")


def decimal(value: object, digits: int = 1) -> str:
    return f"{float(value):.{digits}f}".replace(".", ",")


def main() -> None:
    register_fonts()
    clean = pd.read_csv(RESULT / "UCMF_limpo.csv", dtype="string", encoding="utf-8-sig")
    numeric = pd.read_csv(RESULT / "resumo_numericas.csv", encoding="utf-8-sig").set_index("variavel")
    dates = pd.read_csv(RESULT / "resumo_datas.csv", encoding="utf-8-sig").set_index("variavel")
    bi_numeric = pd.read_csv(RESULT / "bivariada_numericas.csv", encoding="utf-8-sig")
    bi_categorical = pd.read_csv(RESULT / "bivariada_categoricas.csv", encoding="utf-8-sig")
    pending = pd.read_csv(RESULT / "pendencias.csv", encoding="utf-8-sig")
    similar = pd.read_csv(RESULT / "registros_semelhantes.csv", encoding="utf-8-sig")
    removed = pd.read_csv(RESULT / "linhas_removidas.csv", encoding="utf-8-sig")

    body = ParagraphStyle("body", fontName="Arial", fontSize=10, leading=13, spaceAfter=5)
    title = ParagraphStyle("title", parent=body, fontName="Arial-Bold", fontSize=15,
                           leading=18, spaceAfter=8, alignment=TA_LEFT)
    section = ParagraphStyle("section", parent=body, fontName="Arial-Bold", fontSize=11,
                             leading=14, spaceBefore=7, spaceAfter=4)
    cell = ParagraphStyle("cell", parent=body, fontSize=10, leading=11.5, spaceAfter=0)
    head = ParagraphStyle("head", parent=cell, fontName="Arial-Bold", alignment=TA_CENTER)
    centered = ParagraphStyle("centered", parent=body, alignment=TA_CENTER)

    def para(text: str, style=body) -> Paragraph:
        return Paragraph(text, style)

    def grid(headers: list[str], rows: list[list[str]], widths: list[int]) -> Table:
        content = [[para(escape(str(x)), head) for x in headers]]
        content += [[para(escape(str(x)), cell) for x in row] for row in rows]
        table = Table(content, colWidths=widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbe8ed")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#6d8994")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f9fa")]),
        ]))
        return table

    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4, leftMargin=40, rightMargin=40,
        topMargin=38, bottomMargin=39, title="A1 - Pré-processamento do conjunto UCMF",
        author="Grupo de Mineração de Dados",
    )
    width = int(A4[0] - 80)
    story = []

    # Página 1: análise univariada de todas as variáveis.
    story += [para("A1 — Pré-processamento do conjunto UCMF", title)]
    story += [para(
        f"O arquivo bruto tem {integer(len(clean) + len(removed))} atendimentos e 21 variáveis. "
        f"Após retirar {integer(len(removed))} linhas sem dados clínicos, restam "
        f"{integer(len(clean))} registros. O alvo é {TARGET}: "
        f"{integer(clean[TARGET].eq('Normal').sum())} Normal, "
        f"{integer(clean[TARGET].eq('Anormal').sum())} Anormal e "
        f"{integer(clean[TARGET].isna().sum())} sem rótulo. ID é identificador, "
        f"com {integer(clean['ID'].nunique())} valores únicos."
    )]
    story += [para("Análise univariada após a limpeza", section)]
    num_rows = [[name, integer(numeric.at[name, "validos"]),
                 integer(numeric.at[name, "ausentes"]),
                 decimal(numeric.at[name, "mediana"], 2),
                 f"{decimal(numeric.at[name, 'minimo'], 2)}–{decimal(numeric.at[name, 'maximo'], 2)}"]
                for name in NUMERIC]
    story += [grid(["Numérica", "Válidos", "Ausentes", "Mediana", "Mín.–máx."],
                   num_rows, [116, 69, 72, 76, width - 333]), Spacer(1, 5)]
    date_rows = [[name, integer(dates.at[name, "validos"]),
                  integer(dates.at[name, "ausentes"]),
                  f"{dates.at[name, 'data_inicial']} a {dates.at[name, 'data_final']}"]
                 for name in DATES]
    story += [grid(["Data", "Válidas", "Ausentes", "Intervalo observado"],
                   date_rows, [116, 69, 72, width - 257]), Spacer(1, 5)]
    cat_rows = []
    for name in CATEGORICAL:
        values = clean[name].dropna()
        top = str(values.value_counts().index[0]) if len(values) else "—"
        cat_rows.append([name, integer(clean[name].isna().sum()),
                         f"{100 * clean[name].isna().mean():.1f}%".replace(".", ","), top])
    story += [grid(["Categórica", "Ausentes", "% ausente", "Mais frequente entre válidos"],
                   cat_rows, [135, 70, 77, width - 282])]
    story += [para("HDA2 e PPA têm ausência especialmente elevada; médias, quartis e frequências completas constam nos CSVs de resumo.")]
    story.append(PageBreak())

    # Página 2: um problema e uma decisão para cada variável.
    story += [para("Qualidade e soluções por variável", title)]
    story += [para(
        f"A leitura preserva as datas com vírgula entre aspas. Foram auditadas "
        f"{integer(len(pending))} verificações em {integer(pending.ID.nunique())} IDs. "
        f"Há {integer(len(similar))} linhas semelhantes com IDs distintos; "
        "sem confirmação da origem, elas não foram excluídas."
    )]
    quality = {
        "ID": ("Unicidade; registros quase vazios", "Manter ID único; retirar 739 linhas vazias; não usar ID no modelo"),
        "Peso": ("Zero e extremo; ausências", "Tratar zero como faltante; aplicar limite técnico e auditar"),
        "Altura": ("Zero e extremos; ausências", "Tratar zero como faltante; aplicar limite técnico e auditar"),
        "IMC": ("Zero, extremos e conflito com medidas", "Marcar inválidos; conferir Peso/Altura; não estimar sem base"),
        "Atendimento": ("Formatos mistos; ano atípico", "Ler texto/serial, padronizar ISO; sinalizar ano atípico"),
        "DN": ("Formatos mistos; datas ilegíveis", "Ler texto/serial, padronizar ISO; invalidar ilegíveis"),
        "IDADE": ("Idades fora da faixa ou divergentes", "Recalcular de datas coerentes; manter dúvida auditada"),
        "Convenio": ("Grafias e ausências", "Padronizar maiúsculas sem acentos; preservar faltantes"),
        "PULSOS": ("Grafias e ausências", "Unificar categorias equivalentes; preservar faltantes"),
        "PA SISTOLICA": ("Extremos, ausências, conflito com PAD", "Aplicar limite; invalidar par contraditório"),
        "PA DIASTOLICA": ("Extremos, ausências, conflito com PAS", "Aplicar limite; invalidar par contraditório"),
        "PPA": ("Não Calculado e valores sem validação", "Converter marcador em faltante; não recalcular"),
        TARGET: ("Rótulos ausentes", "Padronizar classes; excluir sem rótulo só da modelagem"),
        "B2": ("Grafias e ausências", "Unificar categorias equivalentes; preservar faltantes"),
        "SOPRO": ("Grafias e ausências", "Unificar categorias; separar Ausente de faltante"),
        "FC": ("Extremos e ausências", "Aplicar limite técnico; auditar valores retirados"),
        "HDA 1": ("Ausências", "Manter faltantes; avaliar disponibilidade temporal"),
        "HDA2": ("96,6% ausentes", "Preservar na A1; não usar na base inicial do modelo"),
        "SEXO": ("M/F e grafias; quatro ausências", "Padronizar Masculino/Feminino; manter faltantes"),
        "MOTIVO1": ("Grafias e ausências", "Padronizar categorias; preservar faltantes"),
        "MOTIVO2": ("Grafias, ausências e momento incerto", "Padronizar; não usar sem confirmar o registro"),
        "CLASSIFICACAO IMC": ("Depende de idade, sexo e IMC válidos", "Derivar pela OMS; deixar vazio se entrada insuficiente"),
    }
    quality_rows = [[name, f"{integer(clean[name].isna().sum())} ausentes; {quality[name][0]}",
                     quality[name][1]] for name in ["ID"] + NUMERIC[:3] + DATES + ["IDADE", "Convenio", "PULSOS",
                                           "PA SISTOLICA", "PA DIASTOLICA", "PPA", TARGET,
                                           "B2", "SOPRO", "FC", "HDA 1", "HDA2", "SEXO",
                                           "MOTIVO1", "MOTIVO2", "CLASSIFICACAO IMC"]]
    story += [grid(["Variável", "Problema observado", "Solução ou decisão"],
                   quality_rows, [113, 178, width - 291])]
    story += [para("Limites numéricos são verificações técnicas, não cortes diagnósticos. As 537 pendências, inclusive relações entre campos, estão identificadas por ID em pendencias.csv; nenhum valor ambíguo foi inventado.")]
    story.append(PageBreak())

    # Página 3: comparação de todas as variáveis explicativas com o alvo.
    story += [para("Análise bivariada com o alvo", title)]
    story += [para("As tabelas usam apenas registros rotulados. Diferenças descrevem esta amostra; não demonstram causalidade. Ausências e tamanhos de grupo devem acompanhar a leitura.")]
    bi_num_rows = []
    for name in NUMERIC:
        normal = bi_numeric.loc[(bi_numeric.variavel == name) & (bi_numeric.classe_alvo == "Normal")].iloc[0]
        abnormal = bi_numeric.loc[(bi_numeric.variavel == name) & (bi_numeric.classe_alvo == "Anormal")].iloc[0]
        direction = "Normal maior" if normal.mediana > abnormal.mediana else (
            "Anormal maior" if abnormal.mediana > normal.mediana else "medianas iguais"
        )
        bi_num_rows.append([name, f"{decimal(normal.mediana, 2)} (n={integer(normal.validos)})",
                            f"{decimal(abnormal.mediana, 2)} (n={integer(abnormal.validos)})", direction])
    story += [grid(["Numérica", "Normal: mediana", "Anormal: mediana", "Leitura"],
                   bi_num_rows, [120, 125, 125, width - 370]), Spacer(1, 7)]
    bi_cat_rows = []
    for name in [c for c in CATEGORICAL if c != TARGET]:
        labeled = clean.loc[clean[TARGET].isin(["Normal", "Anormal"])]
        top = str(labeled[name].dropna().value_counts().index[0])
        normal = bi_categorical.loc[(bi_categorical.variavel == name) &
                                    (bi_categorical.categoria == top) &
                                    (bi_categorical.classe_alvo == "Normal")].iloc[0]
        abnormal = bi_categorical.loc[(bi_categorical.variavel == name) &
                                      (bi_categorical.categoria == top) &
                                      (bi_categorical.classe_alvo == "Anormal")].iloc[0]
        difference = float(normal.porcentagem_na_classe - abnormal.porcentagem_na_classe)
        reading = "Normal" if difference > 0.5 else ("Anormal" if difference < -0.5 else "próximas")
        bi_cat_rows.append([name, top, decimal(normal.porcentagem_na_classe),
                            decimal(abnormal.porcentagem_na_classe), reading])
    story += [grid(["Categórica", "Categoria comparada", "% Normal", "% Anormal", "Maior em"],
                   bi_cat_rows, [104, 177, 78, 78, width - 437])]
    sopro = bi_categorical.loc[(bi_categorical.variavel == "SOPRO") &
                               (bi_categorical.categoria == "Ausente")].set_index("classe_alvo")
    story += [para(
        f"SOPRO = Ausente é {decimal(sopro.at['Normal', 'porcentagem_na_classe'])}% "
        f"no grupo Normal e {decimal(sopro.at['Anormal', 'porcentagem_na_classe'])}% "
        "no Anormal; a interpretação depende de quando o exame foi registrado. "
        "A categoria mais frequente de SEXO varia pouco (56,4% e 54,5%). "
        "PPA e HDA2 exigem cautela pela alta ausência. ID não é preditor; "
        "Atendimento e DN foram representados por IDADE. Todas as categorias "
        "e percentuais estão em bivariada_categoricas.csv."
    )]
    story.append(PageBreak())

    # Página 4: figura e interpretação explícita de duas variáveis após limpeza.
    story += [para("Comparação gráfica após a limpeza", title)]
    story += [para("Exemplo: IDADE × NORMAL X ANORMAL. Datas coerentes prevaleceram no cálculo da idade; valores originais discrepantes foram registrados na auditoria. Há 6.202 idades válidas no grupo Normal e 4.607 no Anormal.")]
    figure_path = RESULT / "graficos_bivariada" / "bivariada_numerica_idade.png"
    figure = Image(str(figure_path), width=width - 5, height=(width - 5) * 5 / 8)
    story += [figure, Spacer(1, 7)]
    story += [para("Figura 1 — Distribuição da idade por classe; as caixas mostram a parte central e pontos extremos são omitidos apenas do desenho.", centered)]
    story += [para("A mediana é 4,77 anos no grupo Normal e 2,62 anos no Anormal. As caixas indicam uma distribuição deslocada para idades menores no grupo Anormal, com sobreposição entre grupos. O gráfico não representa todos os valores extremos, mas as estatísticas e contagens usam os valores válidos. A diferença pode refletir a composição dos atendimentos e não estabelece causalidade.")]
    story += [para("Os demais gráficos bivariados foram gerados em graficos_bivariada/. Neles, verde representa Normal e vermelho, Anormal.")]
    story.append(PageBreak())

    # Página 5: decisões de transformação, limites e transparência.
    story += [para("Transformações, justificativas e limites", title)]
    plan_rows = [
        ["Limpeza por linha", "Datas, sentinelas, limites e categorias por regras fixas", "Corrigir erros observáveis sem estimar a distribuição do teste"],
        ["Criação", "IDADE e IMC quando há medidas coerentes; categoria OMS de IMC", "Representar idade e antropometria com significado clínico"],
        ["Redução inicial", "Excluir ID e datas brutas; avaliar redundância de IMC; reservar HDA2 e PPA", "Evitar identificadores, redundância e campos muito ausentes"],
        ["Seleção temporal", "Antes do exame: idade, medidas, sinais vitais, sexo e MOTIVO1", "Usar apenas informações disponíveis antes do alvo; confirmar com o grupo"],
        ["Ausências", "Mediana numérica e categoria técnica de faltante", "Permitir modelagem sem confundir SOPRO = Ausente com dado faltante"],
        ["Representação", "One-hot para nominais; padronização numérica quando útil", "Evitar ordem artificial e diferenças de escala"],
        ["Validação", "Dividir grupos semelhantes; ajustar operações somente no treino", "Evitar vazamento; reaplicar o mesmo transformador ao teste"],
        ["Condicionais", "Seleção supervisionada, PCA e balanceamento só se justificarem", "Ajustar dentro de cada treino da validação cruzada"],
    ]
    story += [grid(["Etapa", "Transformação proposta ou aplicada", "Justificativa"],
                   plan_rows, [100, 205, width - 305])]
    story += [Spacer(1, 5), para("A base mantém 429 alvos ausentes e 537 verificações em 366 IDs. Os valores de PPA da origem não foram validados como diagnóstico. Quatro grupos de linhas idênticas sem ID e alvo têm rótulos conflitantes; eles ficam juntos na divisão de treino e teste para revisão. O teste não foi usado para ajustar imputação, codificação ou escala. Não há classificador treinado nesta etapa.")]
    story += [para("Fontes e rastreabilidade", section)]
    story += [para("Descrição das avaliações.pdf; Variáveis do conjunto de dados.pdf; slides das aulas; OMS, padrões de IMC por idade de 2006 e referência de 2007. Regras, limites, fontes OMS, alterações por ID e plano por variável estão em dados/dicionario.md, docs.md, referencias/ e plano_modelagem.md.")]
    story += [para("Uso de IA generativa", section)]
    story += [para("OpenAI Codex foi usado nesta pasta para revisar scripts e CSVs, verificar inconsistências, gerar tabelas e figuras e redigir a versão inicial deste relatório. O objetivo foi apoiar a limpeza, a documentação e a interpretação descritiva. As decisões clínicas, a conferência dos resultados e a apresentação final cabem ao grupo.")]

    def footer(canvas, document) -> None:
        canvas.saveState()
        canvas.setFont("Arial", 10)
        canvas.setFillColor(colors.HexColor("#52636a"))
        canvas.drawString(40, 22, "Mineração de Dados — Avaliação 1 | UCMF")
        canvas.drawRightString(A4[0] - 40, 22, f"Página {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT)


if __name__ == "__main__":
    main()
