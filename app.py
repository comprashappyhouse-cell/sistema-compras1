import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# =========================
# BANCO
# =========================
def conectar():
    return sqlite3.connect("compras.db", check_same_thread=False)

def criar_usuarios():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        usuario TEXT PRIMARY KEY,
        senha TEXT
    )
    """)

    cursor.execute("INSERT OR IGNORE INTO usuarios VALUES ('admin','123')")

    conn.commit()
    conn.close()

def autenticar(usuario, senha):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM usuarios WHERE usuario=? AND senha=?", (usuario, senha))
    resultado = cursor.fetchone()

    conn.close()
    return resultado is not None

def limpar_colunas(df):
    df.columns = df.columns.str.strip().str.lower()
    df = df.loc[:, ~df.columns.duplicated()].copy()
    return df

def carregar_tabela(nome):
    conn = conectar()
    try:
        df = pd.read_sql(f"SELECT * FROM {nome}", conn)
    except:
        df = pd.DataFrame()
    conn.close()
    return df

def salvar_tabela(df, nome):
    conn = conectar()
    df = limpar_colunas(df)
    df.to_sql(nome, conn, if_exists="replace", index=False)
    conn.close()

# =========================
# LOGIN
# =========================
criar_usuarios()

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Login")

    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if autenticar(usuario, senha):
            st.session_state.logado = True
            st.success("Login realizado!")
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")

    st.stop()

# =========================
# LOGOUT
# =========================
if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

# =========================
# PDF
# =========================
def gerar_pdf_solicitacao(df, nome_arquivo="solicitacao.pdf"):
    doc = SimpleDocTemplate(nome_arquivo)
    elementos = []
    styles = getSampleStyleSheet()

    elementos.append(Paragraph("Solicitação de Cotação", styles["Title"]))
    elementos.append(Paragraph(f"Data: {datetime.now().strftime('%d/%m/%Y')}", styles["Normal"]))

    dados = [["Código","Descrição","Qtd"]]

    for _, row in df.iterrows():
        dados.append([
            str(row.get("codigo_material","")),
            str(row.get("descricao","")),
            str(row.get("quantidade",""))
        ])

    tabela = Table(dados)
    tabela.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),0.5,colors.grey)
    ]))

    elementos.append(tabela)
    doc.build(elementos)
    return nome_arquivo

def gerar_pdf_pedido(df, nome_arquivo="pedido.pdf"):
    doc = SimpleDocTemplate(nome_arquivo)
    elementos = []
    styles = getSampleStyleSheet()

    fornecedor = df["fornecedor"].iloc[0]

    elementos.append(Paragraph(f"Pedido - {fornecedor}", styles["Title"]))

    dados = [["Código","Qtd","Unitário","Total"]]

    for _, row in df.iterrows():
        dados.append([
            row.get("codigo_material",""),
            row.get("quantidade",""),
            row.get("valor_unitario",""),
            row.get("total","")
        ])

    tabela = Table(dados)
    elementos.append(tabela)
    doc.build(elementos)
    return nome_arquivo

# =========================
# INTERFACE
# =========================
st.title("Sistema de Compras")

menu = st.sidebar.selectbox("Menu", ["Solicitações","Orçamentos","Pedidos"])

# =========================
# SOLICITAÇÕES
# =========================
if menu == "Solicitações":

    arquivo = st.file_uploader("Upload", type=["xlsx","csv"])

    if arquivo:
        df_upload = pd.read_excel(arquivo) if arquivo.name.endswith("xlsx") else pd.read_csv(arquivo)

        df_upload = limpar_colunas(df_upload)

        mapa = {}
        for col in df_upload.columns:
            nome = col.lower()

            if "id" in nome:
                mapa[col] = "id_solicitacao"
            elif any(x in nome for x in ["codigo","material"]):
                mapa[col] = "codigo_material"
            elif "descricao" in nome:
                mapa[col] = "descricao"
            elif any(x in nome for x in ["qtd","quant"]):
                mapa[col] = "quantidade"

        df_upload = df_upload.rename(columns=mapa)

        if "quantidade" in df_upload.columns:
            df_upload["quantidade"] = pd.to_numeric(df_upload["quantidade"], errors="coerce").fillna(0)

        salvar_tabela(df_upload,"solicitacoes")
        st.success("Importado!")

    df = carregar_tabela("solicitacoes")

    df_editado = st.data_editor(df, num_rows="dynamic")

    if st.button("Salvar"):
        salvar_tabela(df_editado,"solicitacoes")

    if st.button("Gerar PDF"):
        arq = gerar_pdf_solicitacao(df)
        with open(arq,"rb") as f:
            st.download_button("Baixar PDF", f, arq)

# =========================
# ORÇAMENTOS
# =========================
elif menu == "Orçamentos":

    base = carregar_tabela("solicitacoes")

    if base.empty:
        st.warning("Sem dados")
        st.stop()

    linhas = []
    for _, row in base.iterrows():
        for f in ["Fornecedor 1","Fornecedor 2","Fornecedor 3"]:
            linhas.append({
                "id_solicitacao": row.get("id_solicitacao",""),
                "codigo_material": row.get("codigo_material",""),
                "descricao": row.get("descricao",""),
                "quantidade": row.get("quantidade",0),
                "fornecedor": f,
                "valor_unitario": "",
                "total": ""
            })

    df = pd.DataFrame(linhas)

    df_editado = st.data_editor(df)

    if st.button("Salvar Orçamentos"):
        salvar_tabela(df_editado,"orcamentos")

    if st.button("Gerar Pedido"):
        salvar_tabela(df_editado,"orcamentos")
        st.success("Pedidos atualizados!")

# =========================
# PEDIDOS
# =========================
elif menu == "Pedidos":

    df = carregar_tabela("orcamentos")

    if df.empty:
        st.warning("Sem orçamentos")
    else:
        fornecedor = st.selectbox("Fornecedor", df["fornecedor"].unique())

        df_f = df[df["fornecedor"]==fornecedor]

        if st.button("PDF Pedido"):
            arq = gerar_pdf_pedido(df_f)
            with open(arq,"rb") as f:
                st.download_button("Baixar", f, arq)