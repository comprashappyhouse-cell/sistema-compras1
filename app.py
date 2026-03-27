from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image, Spacer
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from datetime import datetime
import os

def gerar_pdf_solicitacao(df):

    file_path = "solicitacao.pdf"

    doc = SimpleDocTemplate(
        file_path,
        pagesize=landscape(A4),
        leftMargin=1*cm,
        rightMargin=1*cm,
        topMargin=1*cm,
        bottomMargin=1*cm
    )

    styles = getSampleStyleSheet()

    # 🔥 ESTILOS PERSONALIZADOS
    titulo_style = ParagraphStyle(
        name="Titulo",
        fontSize=18,
        alignment=1,
        spaceAfter=10,
        spaceBefore=10
    )

    info_style = ParagraphStyle(
        name="Info",
        fontSize=9,
        spaceAfter=6
    )

    elements = []

    # 🔷 CABEÇALHO COM LOGO + EMPRESA
    if os.path.exists("logo.png"):
        logo = Image("logo.png", width=3*cm, height=3*cm)
        elements.append(logo)

    empresa = Paragraph("<b>SUA EMPRESA LTDA</b>", styles["Normal"])
    elements.append(empresa)

    elements.append(Spacer(1, 10))

    # 🔷 TÍTULO
    titulo = Paragraph("<b>SOLICITAÇÃO DE COMPRA</b>", titulo_style)
    elements.append(titulo)

    # 🔷 INFO (DATA / NUMERO)
    data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M")

    info = Paragraph(f"<b>Data de emissão:</b> {data_hoje}", info_style)
    elements.append(info)

    elements.append(Spacer(1, 10))

    # 🔥 TRATAMENTO DF
    df = df.fillna("")
    df = df.astype(str)

    # 🔥 MELHORAR DESCRIÇÃO (quebra de linha)
    def quebra_texto(texto):
        return Paragraph(texto, styles["Normal"])

    data = [list(df.columns)]

    for _, row in df.iterrows():
        linha = []
        for col in df.columns:
            if col.lower() == "descricao":
                linha.append(quebra_texto(row[col]))
            else:
                linha.append(row[col])
        data.append(linha)

    # 🔥 LARGURA INTELIGENTE
    col_widths = []
    for col in df.columns:
        if col.lower() == "descricao":
            col_widths.append(8*cm)
        else:
            col_widths.append(3*cm)

    table = Table(data, colWidths=col_widths, repeatRows=1)

    table.setStyle(TableStyle([
        # Cabeçalho
        ("BACKGROUND", (0,0), (-1,0), colors.black),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),

        # Corpo
        ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME", (0,1), (-1,-1), "Helvetica"),

        ("FONTSIZE", (0,0), (-1,-1), 8),

        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),

        # Alternar cor linha (zebra)
        ("BACKGROUND", (0,1), (-1,-1), colors.whitesmoke),
    ]))

    elements.append(table)

    elements.append(Spacer(1, 20))

    # 🔷 RODAPÉ
    rodape = Paragraph(
        f"Documento gerado automaticamente em {data_hoje}",
        ParagraphStyle(name="rodape", fontSize=8, alignment=1)
    )

    elements.append(rodape)

    doc.build(elements)

    return file_path
