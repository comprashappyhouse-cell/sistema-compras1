import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm

# ---------------- LOGIN ----------------
def login():
    if "logado" not in st.session_state:
        st.session_state.logado = False

    if not st.session_state.logado:
        st.title("🔐 Login")

        user = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")

        if st.button("Entrar"):
            if user == "adm" and senha == "123":
                st.session_state.logado = True
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos")
        st.stop()

# ---------------- BANCO ----------------
def conectar():
    return sqlite3.connect("compras.db", check_same_thread=False)

def salvar(df, tabela):
    conn = conectar()
    df.to_sql(tabela, conn, if_exists="replace", index=False)
    conn.close()

def carregar(tabela):
    conn = conectar()
    try:
        df = pd.read_sql(f"SELECT * FROM {tabela}", conn)
    except:
        df = pd.DataFrame()
    conn.close()
    return df

# ---------------- PDF AJUSTADO ----------------
def gerar_pdf(df, titulo):
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=5,
        leftMargin=5,
        topMargin=5,
        bottomMargin=5
    )

    elements = []
    styles = getSampleStyleSheet()

    # Logo menor
    try:
        img = Image("logo.png", width=35, height=35)
        elements.append(img)
    except:
        pass

    # Título
    elements.append(Paragraph(f"<b>{titulo}</b>", styles["Heading2"]))
    elements.append(Spacer(1, 6))

    df = df.fillna("").astype(str)

    data = [df.columns.tolist()]

    for _, row in df.iterrows():
        linha = []
        for col in df.columns:
            texto = str(row[col]).replace(",", "<br/>")
            linha.append(Paragraph(texto, styles["Normal"]))
        data.append(linha)

    # 🔥 AJUSTE DE ESCALA (ZOOM CORRETO)
    largura_total = 280 * mm
    col_width = largura_total / len(df.columns)

    table = Table(
        data,
        repeatRows=1,
        colWidths=[col_width] * len(df.columns)
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.black),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),

        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),

        ("FONTSIZE", (0,0), (-1,-1), 6),

        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),

        ("GRID", (0,0), (-1,-1), 0.3, colors.grey),

        ("LEFTPADDING", (0,0), (-1,-1), 2),
        ("RIGHTPADDING", (0,0), (-1,-1), 2),
        ("TOPPADDING", (0,0), (-1,-1), 1),
        ("BOTTOMPADDING", (0,0), (-1,-1), 1),
    ]))

    elements.append(table)

    elements.append(Spacer(1, 5))
    elements.append(Paragraph(
        f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        styles["Normal"]
    ))

    doc.build(elements)

    buffer.seek(0)
    return buffer

# ---------------- APP ----------------
login()

st.set_page_config(layout="wide")

# Logo
try:
    st.image("logo.png", width=120)
except:
    pass

st.title("Sistema de Compras")

menu = st.sidebar.selectbox("Menu", ["Solicitações", "Orçamentos", "Pedidos"])

# ---------------- SOLICITAÇÕES ----------------
if menu == "Solicitações":

    st.subheader("Upload de Solicitações")

    file = st.file_uploader("Subir planilha", type=["xlsx", "csv"])

    if file:
        if file.name.endswith("csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)

        df = st.data_editor(df, use_container_width=True)

        if st.button("Salvar"):
            salvar(df, "solicitacoes")
            st.success("Salvo com sucesso")

    df = carregar("solicitacoes")

    if not df.empty:
        st.dataframe(df, use_container_width=True)

        pdf = gerar_pdf(df, "SOLICITAÇÃO DE COMPRA")

        st.download_button("📄 Baixar PDF", pdf, "solicitacao.pdf")

# ---------------- ORÇAMENTOS ----------------
if menu == "Orçamentos":

    df = carregar("solicitacoes")

    if df.empty:
        st.warning("Nenhuma solicitação")
    else:
        fornecedores = ["Fornecedor 1", "Fornecedor 2", "Fornecedor 3"]

        lista = []

        for _, row in df.iterrows():
            for f in fornecedores:
                lista.append({
                    **row,
                    "fornecedor": f,
                    "valor_unitario": 0,
                    "total": 0
                })

        df_orc = pd.DataFrame(lista)

        df_orc = st.data_editor(df_orc, use_container_width=True)

        if "quantidade" in df_orc.columns:
            df_orc["quantidade"] = pd.to_numeric(df_orc["quantidade"], errors="coerce").fillna(0)
            df_orc["valor_unitario"] = pd.to_numeric(df_orc["valor_unitario"], errors="coerce").fillna(0)
            df_orc["total"] = df_orc["quantidade"] * df_orc["valor_unitario"]

        if st.button("Salvar Orçamentos"):
            salvar(df_orc, "orcamentos")
            st.success("Orçamentos salvos")

        fornecedor_sel = st.selectbox("Fornecedor vencedor", fornecedores)

        df_filtrado = df_orc[df_orc["fornecedor"] == fornecedor_sel]

        if st.button("Gerar Pedido"):
            salvar(df_filtrado, "pedidos")
            st.success("Pedido gerado")

# ---------------- PEDIDOS ----------------
if menu == "Pedidos":

    df = carregar("pedidos")

    if df.empty:
        st.warning("Nenhum pedido")
    else:
        fornecedor = st.selectbox("Fornecedor", df["fornecedor"].unique())

        df_f = df[df["fornecedor"] == fornecedor]

        st.dataframe(df_f, use_container_width=True)

        pdf = gerar_pdf(df_f, "PEDIDO DE COMPRA")

        st.download_button("📄 Baixar PDF Pedido", pdf, "pedido.pdf")
