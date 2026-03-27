import streamlit as st
import pandas as pd
import sqlite3
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import os

# =========================
# CONFIG
# =========================
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
                st.error("Usuário ou senha inválidos")
        st.stop()

login()

# =========================
# BANCO
# =========================
conn = sqlite3.connect("compras.db", check_same_thread=False)

def salvar_tabela(df, nome):
    df.columns = [c.lower().strip() for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    df.to_sql(nome, conn, if_exists="replace", index=False)

def carregar_tabela(nome):
    try:
        return pd.read_sql(f"SELECT * FROM {nome}", conn)
    except:
        return pd.DataFrame()

# =========================
# LOGO
# =========================
if os.path.exists("logo.png"):
    st.image("logo.png", width=200)

st.title("Sistema de Compras")

# =========================
# MENU
# =========================
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

        st.dataframe(df, use_container_width=True)

        if st.button("Salvar Solicitações"):
            salvar_tabela(df, "solicitacoes")
            st.success("Salvo com sucesso!")

    df = carregar_tabela("solicitacoes")

    if not df.empty:
        st.dataframe(df, use_container_width=True)

        if st.button("Gerar PDF Solicitação"):
            doc = SimpleDocTemplate("solicitacao.pdf")
            styles = getSampleStyleSheet()

            elementos = []
            elementos.append(Paragraph("SOLICITAÇÃO DE COMPRA", styles["Title"]))
            elementos.append(Spacer(1, 10))

            tabela = [df.columns.tolist()] + df.values.tolist()

            t = Table(tabela)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.grey),
                ("TEXTCOLOR",(0,0),(-1,0),colors.white),
                ("GRID",(0,0),(-1,-1),1,colors.black)
            ]))

            elementos.append(t)
            doc.build(elementos)

            st.success("PDF gerado!")

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
            df_edit["total"] = df_edit["quantidade"] * df_edit["valor_unitario"]
            salvar_tabela(df_edit, "orcamentos")
            st.success("Orçamento salvo!")

        if st.button("Gerar Pedido"):
            st.session_state.ir_pedidos = True
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

        if st.button("Gerar PDF Pedido"):
            doc = SimpleDocTemplate("pedido.pdf")
            styles = getSampleStyleSheet()

            elementos = []
            elementos.append(Paragraph("PEDIDO DE COMPRA", styles["Title"]))
            elementos.append(Spacer(1, 10))

            tabela = [df_filtro.columns.tolist()] + df_filtro.values.tolist()

            t = Table(tabela)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.black),
                ("TEXTCOLOR",(0,0),(-1,0),colors.white),
                ("GRID",(0,0),(-1,-1),1,colors.black)
            ]))

            elementos.append(t)
            doc.build(elementos)

            st.success("PDF gerado!")
