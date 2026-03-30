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

# 🔥 RESET CONTROLADO DA TABELA PEDIDOS (RODA 1 VEZ)
def reset_pedidos():
    if "reset_db" not in st.session_state:
        conn = conectar()
        conn.execute("DROP TABLE IF EXISTS pedidos")
        conn.close()
        st.session_state.reset_db = True

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

# 🔥 executa reset 1 vez
reset_pedidos()

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
elif menu == "Orçamentos":

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

        modo = st.radio("Modo de geração", ["Manual", "Automático (menor preço)"])

        if modo == "Manual":

            fornecedor = st.selectbox("Fornecedor vencedor", fornecedores)

            if st.button("Gerar Pedido"):
                df_pedido = df_orc[df_orc["fornecedor"] == fornecedor].copy()

                df_pedido["data_pedido"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                df_pedido["id_pedido"] = int(datetime.now().timestamp())
                df_pedido["status"] = "PENDENTE"

                append(df_pedido, "pedidos")

                st.success("Pedido gerado (manual)")

        else:

            if st.button("Gerar Pedido Inteligente"):

                df_temp = df_orc.copy()
                df_temp["valor_unitario"] = pd.to_numeric(df_temp["valor_unitario"], errors="coerce").fillna(999999)

                idx = df_temp.groupby("descricao")["valor_unitario"].idxmin()
                df_pedido = df_temp.loc[idx].copy()

                df_pedido["data_pedido"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                df_pedido["id_pedido"] = int(datetime.now().timestamp())
                df_pedido["status"] = "PENDENTE"

                append(df_pedido, "pedidos")

                st.success("Pedido gerado automaticamente")

# ---------------- PEDIDOS ----------------
elif menu == "Pedidos":

    df = carregar("pedidos")

    if not df.empty:

        df["aprovar"] = False
        df["reprovar"] = False

        df_edit = st.data_editor(df, use_container_width=True)

        c1, c2 = st.columns(2)

        if c1.button("✅ Aprovar Pedido"):
            df_edit.loc[df_edit["aprovar"] == True, "status"] = "APROVADO"
            salvar(df_edit.drop(columns=["aprovar","reprovar"]), "pedidos")
            st.success("Pedidos aprovados")

        if c2.button("❌ Reprovar Pedido"):
            df_edit.loc[df_edit["reprovar"] == True, "status"] = "REPROVADO"
            salvar(df_edit.drop(columns=["aprovar","reprovar"]), "pedidos")
            st.warning("Pedidos reprovados")

        colunas_pdf = st.multiselect("Colunas PDF", df.columns, default=df.columns)

        if st.button("Gerar PDF Pedido"):
            pdf = gerar_pdf(df,"PEDIDO",colunas_pdf)
            st.download_button("Baixar PDF",pdf,"pedido.pdf")

# ---------------- DASHBOARD ----------------
elif menu == "Dashboard":

    df_sol = carregar("solicitacoes")
    df_ped = carregar("pedidos")

    c1,c2,c3 = st.columns(3)

    c1.metric("Solicitações", len(df_sol))
    c2.metric("Pedidos", len(df_ped))

    if not df_ped.empty:
        total = pd.to_numeric(df_ped["total"], errors="coerce").sum()
        c3.metric("Total Comprado", f"R$ {total:,.2f}")

        st.subheader("📊 Ranking de Fornecedores")
        resumo = df_ped.groupby("fornecedor")["total"].sum().sort_values(ascending=False)
        st.bar_chart(resumo)

        st.subheader("📊 Status dos Pedidos")
        status_count = df_ped["status"].value_counts()
        st.bar_chart(status_count)
