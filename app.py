import streamlit as st
import pandas as pd
import sqlite3
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import getSampleStyleSheet
import datetime

# =============================
# CONFIG
# =============================
st.set_page_config(layout="wide")

conn = sqlite3.connect("compras.db", check_same_thread=False)

# =============================
# LOGIN
# =============================
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
            st.error("Login inválido")
    st.stop()

# =============================
# TEMA
# =============================
tema = st.selectbox("🎨 Tema", ["Claro", "Escuro", "ERP"])

if tema == "Escuro":
    st.markdown("<style>body{background:#111;color:white}</style>", unsafe_allow_html=True)
elif tema == "ERP":
    st.markdown("<style>body{background:#f4f6f9}</style>", unsafe_allow_html=True)

# =============================
# MENU
# =============================
menu = st.sidebar.selectbox("Menu", ["Dashboard","Solicitações","Orçamentos","Pedidos"])

# =============================
# FUNÇÕES
# =============================
def salvar(df, nome):
    df.to_sql(nome, conn, if_exists="replace", index=False)

def carregar(nome):
    try:
        return pd.read_sql(f"SELECT * FROM {nome}", conn)
    except:
        return pd.DataFrame()

# =============================
# DASHBOARD
# =============================
if menu == "Dashboard":
    st.title("📊 Dashboard")

    sol = carregar("solicitacoes")
    ped = carregar("pedidos")

    col1, col2, col3 = st.columns(3)

    col1.metric("Solicitações", len(sol))
    col2.metric("Pedidos", len(ped))

    if not ped.empty and "total" in ped.columns:
        col3.metric("Total Comprado", f"R$ {ped['total'].sum():,.2f}")
    else:
        col3.metric("Total Comprado", "R$ 0")

# =============================
# SOLICITAÇÕES
# =============================
elif menu == "Solicitações":
    st.title("📋 Solicitações")

    uploaded = st.file_uploader("Upload Excel")

    if uploaded:
        df = pd.read_excel(uploaded)
        st.session_state.df_sol = df

    if "df_sol" not in st.session_state:
        st.session_state.df_sol = carregar("solicitacoes")

    df_edit = st.data_editor(st.session_state.df_sol, num_rows="dynamic", use_container_width=True)

    col1, col2 = st.columns(2)

    if col1.button("💾 Salvar"):
        salvar(df_edit, "solicitacoes")
        st.success("Salvo!")

    if col2.button("🗑️ Limpar Tudo"):
        st.session_state.df_sol = pd.DataFrame()
        salvar(pd.DataFrame(), "solicitacoes")
        st.rerun()

    # PDF com seleção de colunas
    st.subheader("📄 Gerar PDF")

    colunas = list(df_edit.columns)
    colunas_sel = st.multiselect("Escolher colunas", colunas, default=colunas)

    if st.button("Gerar PDF Solicitação"):
        doc = SimpleDocTemplate("solicitacao.pdf", pagesize=landscape(A4))
        data = [colunas_sel] + df_edit[colunas_sel].astype(str).values.tolist()

        tabela = Table(data, repeatRows=1)
        tabela.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
            ('FONTSIZE', (0,0), (-1,-1), 7),
        ]))

        doc.build([tabela])

        with open("solicitacao.pdf", "rb") as f:
            st.download_button("📥 Baixar PDF", f, "solicitacao.pdf")

# =============================
# ORÇAMENTOS
# =============================
elif menu == "Orçamentos":
    st.title("💰 Orçamentos")

    df = carregar("solicitacoes")

    if df.empty:
        st.warning("Sem dados")
        st.stop()

    cod = st.selectbox("Filtrar Solicitação", df["id_solicitacao"].unique())

    df_filtrado = df[df["id_solicitacao"] == cod]

    df_edit = st.data_editor(df_filtrado, use_container_width=True)

    if st.button("Salvar Orçamento"):
        salvar(df_edit, "orcamentos")
        st.success("Salvo!")

    if st.button("Gerar Pedido"):
        df_edit["total"] = df_edit["quantidade"] * df_edit.get("valor_unitario",1)
        salvar(df_edit, "pedidos")
        st.success("Pedido gerado!")

# =============================
# PEDIDOS
# =============================
elif menu == "Pedidos":
    st.title("📦 Pedidos")

    df = carregar("pedidos")

    if df.empty:
        st.warning("Sem pedidos")
        st.stop()

    st.dataframe(df, use_container_width=True)

    if st.button("📄 Gerar PDF Pedido"):
        doc = SimpleDocTemplate("pedido.pdf", pagesize=landscape(A4))

        data = [df.columns.tolist()] + df.astype(str).values.tolist()

        tabela = Table(data, repeatRows=1)
        tabela.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
            ('FONTSIZE', (0,0), (-1,-1), 7),
        ]))

        doc.build([tabela])

        with open("pedido.pdf", "rb") as f:
            st.download_button("📥 Baixar PDF", f, "pedido.pdf")
