import streamlit as st
import pandas as pd
import sqlite3
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4, landscape
from io import BytesIO
import os

st.set_page_config(layout="wide")

# =========================
# LOGIN
# =========================
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
                st.error("Login inválido")
        st.stop()

login()

# =========================
# BANCO
# =========================
conn = sqlite3.connect("compras.db", check_same_thread=False)

def salvar_tabela(df, nome):
    df.columns = df.columns.str.lower().str.strip()
    df = df.loc[:, ~df.columns.duplicated()]
    df.to_sql(nome, conn, if_exists="replace", index=False)

def carregar_tabela(nome):
    try:
        return pd.read_sql(f"SELECT * FROM {nome}", conn)
    except:
        return pd.DataFrame()

# =========================
# HEADER
# =========================
if os.path.exists("logo.png"):
    st.image("logo.png", width=150)

st.title("Sistema de Compras")

menu = st.sidebar.selectbox("Menu", ["Solicitações", "Orçamentos", "Pedidos"])

# =========================
# SOLICITAÇÕES
# =========================
if menu == "Solicitações":
    st.header("Solicitações")

    arquivo = st.file_uploader("Upload planilha", type=["xlsx", "csv"])

    if arquivo:
        if arquivo.name.endswith("csv"):
            df = pd.read_csv(arquivo)
        else:
            df = pd.read_excel(arquivo)

        df.columns = df.columns.str.lower().str.strip()

        st.subheader("Editar antes de salvar")
        df_edit = st.data_editor(df, use_container_width=True, num_rows="dynamic")

        if st.button("Salvar Solicitações"):
            salvar_tabela(df_edit, "solicitacoes")
            st.success("Salvo com sucesso!")

    df = carregar_tabela("solicitacoes")

    if not df.empty:
        st.subheader("Dados Salvos")
        st.dataframe(df, use_container_width=True)

        # PDF DOWNLOAD
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
        styles = getSampleStyleSheet()

        elementos = []

        if os.path.exists("logo.png"):
            elementos.append(Image("logo.png", width=100, height=50))

        elementos.append(Paragraph("SOLICITAÇÃO DE COMPRA", styles["Title"]))
        elementos.append(Spacer(1, 10))

        tabela = [df.columns.tolist()] + df.values.tolist()

        t = Table(tabela, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.black),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID",(0,0),(-1,-1),0.5,colors.grey),
        ]))

        elementos.append(t)
        doc.build(elementos)
        buffer.seek(0)

        st.download_button(
            "📥 Baixar PDF Solicitação",
            buffer,
            file_name="solicitacao.pdf",
            mime="application/pdf"
        )

# =========================
# ORÇAMENTOS
# =========================
elif menu == "Orçamentos":
    st.header("Orçamentos")

    df = carregar_tabela("solicitacoes")

    if df.empty:
        st.warning("Sem solicitações")
    else:
        fornecedores = ["Fornecedor 1", "Fornecedor 2", "Fornecedor 3"]

        linhas = []
        for _, row in df.iterrows():
            for f in fornecedores:
                linhas.append({
                    "id_solicitacao": row.get("id_solicitacao", ""),
                    "codigo_material": row.get("codigo_material", ""),
                    "descricao": row.get("descricao", ""),
                    "quantidade": row.get("quantidade", 0),
                    "fornecedor": f,
                    "valor_unitario": 0,
                    "total": 0
                })

        df_orc = pd.DataFrame(linhas)

        df_edit = st.data_editor(df_orc, use_container_width=True)

        if st.button("Salvar Orçamentos"):
            df_edit["quantidade"] = pd.to_numeric(df_edit["quantidade"], errors="coerce").fillna(0)
            df_edit["valor_unitario"] = pd.to_numeric(df_edit["valor_unitario"], errors="coerce").fillna(0)

            df_edit["total"] = df_edit["quantidade"] * df_edit["valor_unitario"]

            salvar_tabela(df_edit, "orcamentos")
            st.success("Orçamento salvo!")

        if st.button("Gerar Pedido"):
            st.success("Vá para aba PEDIDOS")

# =========================
# PEDIDOS
# =========================
elif menu == "Pedidos":
    st.header("Pedidos")

    df = carregar_tabela("orcamentos")

    if df.empty:
        st.warning("Sem dados")
    else:
        fornecedor = st.selectbox("Fornecedor", df["fornecedor"].unique())

        df_filtro = df[df["fornecedor"] == fornecedor]

        st.dataframe(df_filtro, use_container_width=True)

        # PDF DOWNLOAD
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
        styles = getSampleStyleSheet()

        elementos = []

        if os.path.exists("logo.png"):
            elementos.append(Image("logo.png", width=100, height=50))

        elementos.append(Paragraph("PEDIDO DE COMPRA", styles["Title"]))
        elementos.append(Spacer(1, 10))

        tabela = [df_filtro.columns.tolist()] + df_filtro.values.tolist()

        t = Table(tabela, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.black),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID",(0,0),(-1,-1),0.5,colors.grey),
        ]))

        elementos.append(t)
        doc.build(elementos)
        buffer.seek(0)

        st.download_button(
            "📥 Baixar PDF Pedido",
            buffer,
            file_name="pedido.pdf",
            mime="application/pdf"
        )
