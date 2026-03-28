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

def append(df, tabela):
    conn = conectar()
    df.to_sql(tabela, conn, if_exists="append", index=False)
    conn.close()

def carregar(tabela):
    conn = conectar()
    try:
        df = pd.read_sql(f"SELECT * FROM {tabela}", conn)
    except:
        df = pd.DataFrame()
    conn.close()
    return df

# ---------------- PDF ----------------
def gerar_pdf(df, titulo, colunas):
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

    try:
        elements.append(Image("logo.png", width=40, height=40))
    except:
        pass

    elements.append(Paragraph(f"<b>{titulo}</b>", styles["Heading2"]))
    elements.append(Spacer(1, 6))

    df = df[colunas].fillna("").astype(str)

    data = [df.columns.tolist()] + df.values.tolist()

    largura_total = 260 * mm
    col_width = largura_total / len(df.columns)

    table = Table(data, repeatRows=1, colWidths=[col_width]*len(df.columns))

    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.black),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTSIZE", (0,0), (-1,-1), 7),
        ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
    ]))

    elements.append(table)
    doc.build(elements)

    buffer.seek(0)
    return buffer

# ---------------- APP ----------------
login()
st.set_page_config(layout="wide")

# 🎨 TEMA
if "tema" not in st.session_state:
    st.session_state.tema = "Bege"

col_top1, col_top2 = st.columns([8,2])
with col_top2:
    tema = st.selectbox("🎨 Tema", ["Bege", "Claro", "Escuro"])
    st.session_state.tema = tema

if tema == "Bege":
    st.markdown("<style>.stApp{background:#D6C5A4}</style>", unsafe_allow_html=True)
elif tema == "Escuro":
    st.markdown("<style>.stApp{background:#121212;color:white}</style>", unsafe_allow_html=True)

# HEADER
col1, col2, col3 = st.columns([1,2,1])
with col2:
    try:
        st.image("logo.png", width=120)
    except:
        pass
    st.markdown("<h1 style='text-align:center'>Sistema de Compras</h1>", unsafe_allow_html=True)

# MENU
menu = st.sidebar.radio("Menu", ["Solicitações","Orçamentos","Pedidos","Dashboard"])

# ---------------- SOLICITAÇÕES ----------------
if menu == "Solicitações":

    df = carregar("solicitacoes")

    file = st.file_uploader("Upload", type=["xlsx","csv"])

    if file:
        df = pd.read_excel(file) if file.name.endswith("xlsx") else pd.read_csv(file)
        salvar(df,"solicitacoes")
        st.success("Importado")

    if not df.empty:

        df["excluir"] = False
        df["pdf"] = False
        df["pedido"] = False

        df_edit = st.data_editor(df, use_container_width=True)

        colunas_pdf = st.multiselect("Colunas PDF", df.columns, default=df.columns)

        c1,c2,c3 = st.columns(3)

        if c1.button("Salvar"):
            salvar(df_edit.drop(columns=["excluir","pdf","pedido"]),"solicitacoes")

        if c2.button("Excluir"):
            salvar(df_edit[df_edit["excluir"]==False].drop(columns=["excluir","pdf","pedido"]),"solicitacoes")

        if c3.button("Gerar PDF"):
            df_pdf = df_edit[df_edit["pdf"]==True]

            if not df_pdf.empty:
                pdf = gerar_pdf(df_pdf.drop(columns=["excluir","pdf","pedido"]),"SOLICITAÇÃO",colunas_pdf)
                st.download_button("Baixar PDF",pdf,"solicitacao.pdf")
            else:
                st.warning("Selecione linhas para PDF")

# ---------------- ORÇAMENTOS ----------------
if menu == "Orçamentos":

    df = carregar("solicitacoes")

    if not df.empty:

        fornecedores = ["Fornecedor 1","Fornecedor 2","Fornecedor 3"]

        lista = []
        for _,row in df.iterrows():
            for f in fornecedores:
                lista.append({**row,"fornecedor":f,"valor_unitario":0})

        df_orc = pd.DataFrame(lista)

        df_orc = st.data_editor(df_orc, use_container_width=True)

        df_orc["quantidade"] = pd.to_numeric(df_orc.get("quantidade",0), errors="coerce").fillna(0)
        df_orc["valor_unitario"] = pd.to_numeric(df_orc["valor_unitario"], errors="coerce").fillna(0)
        df_orc["total"] = df_orc["quantidade"] * df_orc["valor_unitario"]

        if st.button("Salvar Orçamento"):
            append(df_orc,"historico_orcamentos")
            st.success("Histórico salvo")

        fornecedor = st.selectbox("Fornecedor vencedor", fornecedores)

        if st.button("Gerar Pedido"):
            df_pedido = df_orc[df_orc["fornecedor"]==fornecedor]
            salvar(df_pedido,"pedidos")
            st.success("Pedido gerado")

# ---------------- PEDIDOS ----------------
if menu == "Pedidos":

    df = carregar("pedidos")

    if not df.empty:
        st.dataframe(df, use_container_width=True)

        colunas_pdf = st.multiselect("Colunas PDF", df.columns, default=df.columns)

        if st.button("Gerar PDF Pedido"):
            pdf = gerar_pdf(df,"PEDIDO",colunas_pdf)
            st.download_button("Baixar PDF",pdf,"pedido.pdf")

# ---------------- DASHBOARD ----------------
if menu == "Dashboard":

    df_sol = carregar("solicitacoes")
    df_ped = carregar("pedidos")

    c1,c2,c3 = st.columns(3)

    c1.metric("Solicitações", len(df_sol))
    c2.metric("Pedidos", len(df_ped))

    if not df_ped.empty:
        total = pd.to_numeric(df_ped["total"], errors="coerce").sum()
        c3.metric("Total Comprado", f"R$ {total:,.2f}")

    if not df_ped.empty:
        resumo = df_ped.groupby("fornecedor")["total"].sum()
        st.bar_chart(resumo)
