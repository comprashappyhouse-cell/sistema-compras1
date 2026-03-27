import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image, Spacer
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

# ================= BANCO =================
conn = sqlite3.connect("compras.db", check_same_thread=False)

def carregar_tabela(nome):
    try:
        return pd.read_sql(f"SELECT * FROM {nome}", conn)
    except:
        return pd.DataFrame()

def salvar_tabela(df, nome):
    df.to_sql(nome, conn, if_exists="replace", index=False)

# ================= LOGIN =================
if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("Login")

    user = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if user == "adm" and senha == "123":
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Login inválido")

    st.stop()

# ================= LAYOUT =================
st.set_page_config(layout="wide")

if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

st.title("Sistema de Compras")

menu = st.sidebar.selectbox("Menu", ["Solicitações", "Orçamentos", "Pedidos"])

# ================= PDF =================
def gerar_pdf(df, nome="arquivo.pdf"):

    doc = SimpleDocTemplate(
        nome,
        pagesize=landscape(A4),
        leftMargin=1*cm,
        rightMargin=1*cm,
        topMargin=1*cm,
        bottomMargin=1*cm
    )

    styles = getSampleStyleSheet()
    elements = []

    if os.path.exists("logo.png"):
        elements.append(Image("logo.png", width=3*cm, height=3*cm))

    elements.append(Paragraph("<b>DOCUMENTO DE COMPRA</b>", styles["Title"]))

    df = df.fillna("").astype(str)

    data = [list(df.columns)] + df.values.tolist()

    largura_total = 27 * cm
    col_width = largura_total / len(df.columns)

    table = Table(data, colWidths=[col_width]*len(df.columns), repeatRows=1)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.black),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
        ("FONTSIZE", (0,0), (-1,-1), 7),
    ]))

    elements.append(table)

    elements.append(Spacer(1, 20))
    elements.append(Paragraph(
        f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        ParagraphStyle(name="rodape", fontSize=8)
    ))

    doc.build(elements)

    return nome

# ================= SOLICITAÇÕES =================
if menu == "Solicitações":

    st.subheader("Solicitações")

    file = st.file_uploader("Upload Excel", type=["xlsx", "csv"])

    if file:
        df_upload = pd.read_excel(file) if file.name.endswith("xlsx") else pd.read_csv(file)
        st.data_editor(df_upload, use_container_width=True, key="edit_solic")

        if st.button("Salvar Solicitações"):
            salvar_tabela(df_upload, "solicitacoes")
            st.success("Salvo!")

    df = carregar_tabela("solicitacoes")

    if not df.empty:
        st.dataframe(df, use_container_width=True)

        if st.button("Gerar PDF Solicitação"):
            path = gerar_pdf(df, "solicitacao.pdf")
            with open(path, "rb") as f:
                st.download_button("Baixar PDF", f, file_name="solicitacao.pdf")

# ================= ORÇAMENTOS =================
if menu == "Orçamentos":

    st.subheader("Orçamentos")

    df = carregar_tabela("solicitacoes")

    if not df.empty:

        fornecedores = ["Fornecedor 1", "Fornecedor 2", "Fornecedor 3"]

        lista = []

        for _, row in df.iterrows():
            for f in fornecedores:
                lista.append({
                    "id_solicitacao": row.get("id_solicitacao", ""),
                    "codigo_material": row.get("codigo_material", ""),
                    "descricao": row.get("descricao", ""),
                    "quantidade": row.get("quantidade", 1),
                    "fornecedor": f,
                    "valor_unitario": 0,
                    "total": 0
                })

        df_orc = pd.DataFrame(lista)

        df_edit = st.data_editor(df_orc, use_container_width=True)

        if st.button("Salvar Orçamentos"):
            df_edit["total"] = df_edit["quantidade"].astype(float) * df_edit["valor_unitario"].astype(float)
            salvar_tabela(df_edit, "orcamentos")
            st.success("Orçamentos salvos!")

        if st.button("Gerar Pedido"):
            salvar_tabela(df_edit, "pedidos")
            st.success("Pedido gerado!")

# ================= PEDIDOS =================
if menu == "Pedidos":

    st.subheader("Pedidos")

    df = carregar_tabela("pedidos")

    if not df.empty:

        fornecedor = st.selectbox("Fornecedor", df["fornecedor"].unique())

        df_filtrado = df[df["fornecedor"] == fornecedor]

        st.dataframe(df_filtrado, use_container_width=True)

        if st.button("Gerar PDF Pedido"):
            path = gerar_pdf(df_filtrado, "pedido.pdf")
            with open(path, "rb") as f:
                st.download_button("Baixar PDF", f, file_name="pedido.pdf")
