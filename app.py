import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import getSampleStyleSheet

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

# ---------------- MIGRAÇÃO BANCO ----------------
def migrar_banco():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("CREATE TABLE IF NOT EXISTS pedidos (id INTEGER PRIMARY KEY)")
    colunas = [i[1] for i in cursor.execute("PRAGMA table_info(pedidos)")]

    if "data_pedido" not in colunas:
        cursor.execute("ALTER TABLE pedidos ADD COLUMN data_pedido TEXT")

    if "id_pedido" not in colunas:
        cursor.execute("ALTER TABLE pedidos ADD COLUMN id_pedido INTEGER")

    if "status" not in colunas:
        cursor.execute("ALTER TABLE pedidos ADD COLUMN status TEXT")

    if "fornecedor" not in colunas:
        cursor.execute("ALTER TABLE pedidos ADD COLUMN fornecedor TEXT")

    if "total" not in colunas:
        cursor.execute("ALTER TABLE pedidos ADD COLUMN total REAL")

    cursor.execute("CREATE TABLE IF NOT EXISTS historico_orcamentos (id INTEGER PRIMARY KEY)")
    colunas_orc = [i[1] for i in cursor.execute("PRAGMA table_info(historico_orcamentos)")]

    if "numero_solicitacao" not in colunas_orc:
        cursor.execute("ALTER TABLE historico_orcamentos ADD COLUMN numero_solicitacao TEXT")

    if "fornecedor" not in colunas_orc:
        cursor.execute("ALTER TABLE historico_orcamentos ADD COLUMN fornecedor TEXT")

    if "valor_unitario" not in colunas_orc:
        cursor.execute("ALTER TABLE historico_orcamentos ADD COLUMN valor_unitario REAL")

    conn.commit()
    conn.close()

# ---------------- APP ----------------
login()
migrar_banco()
st.set_page_config(layout="wide")

menu = st.sidebar.radio("Menu", ["Solicitações","Orçamentos","Pedidos","Dashboard","Projetos","Notas"])

# ---------------- SOLICITAÇÕES ----------------
if menu == "Solicitações":

    df = carregar("solicitacoes")

    file = st.file_uploader("Upload", type=["xlsx","csv"])

    if file:
        df = pd.read_excel(file) if file.name.endswith("xlsx") else pd.read_csv(file)
        salvar(df,"solicitacoes")
        st.success("Importado")

    if not df.empty:

        if "numero_solicitacao" not in df.columns:
            df["numero_solicitacao"] = "SOL-" + pd.Series(range(1, len(df)+1)).astype(str)

        if "data_solicitacao" not in df.columns:
            df["data_solicitacao"] = datetime.now().strftime("%Y-%m-%d")

        modo_visual = st.radio("Visualizar por:", ["Tudo", "Número", "Data"])

        df_filtro = df.copy()

        # PROJETOS
        df_proj = carregar("projetos")
        if not df_proj.empty:
            projetos = df_proj["projeto"].unique()
            projeto_sel = st.selectbox("Projeto", projetos)
            df_filtro["projeto"] = projeto_sel

        # FILTRO
        if modo_visual == "Número":
            numeros = df["numero_solicitacao"].unique()
            selecionados = st.multiselect("Selecione os números", numeros)
            if selecionados:
                df_filtro = df[df["numero_solicitacao"].isin(selecionados)]

        elif modo_visual == "Data":
            datas = df["data_solicitacao"].unique()
            sel = st.selectbox("Selecione a data", datas)
            df_filtro = df[df["data_solicitacao"] == sel]

        df_filtro["excluir"] = False
        df_filtro["pdf"] = False
        df_filtro["pedido"] = False

        df_edit = st.data_editor(df_filtro, use_container_width=True)

        colunas_pdf = st.multiselect("Colunas PDF", df.columns, default=df.columns)

        c1,c2,c3,c4 = st.columns(4)

        if c1.button("Salvar"):
            salvar(df_edit.drop(columns=["excluir","pdf","pedido"]),"solicitacoes")

        if c2.button("Excluir"):
            salvar(df_edit[df_edit["excluir"]==False].drop(columns=["excluir","pdf","pedido"]),"solicitacoes")

        if c3.button("Gerar PDF"):
            df_pdf = df_edit[df_edit["pdf"]==True]
            if not df_pdf.empty:
                pdf = gerar_pdf(df_pdf.drop(columns=["excluir","pdf","pedido"]),"SOLICITAÇÃO",colunas_pdf)
                st.download_button("Baixar PDF",pdf,"solicitacao.pdf")

        if c4.button("📥 Exportar Excel"):
            excel = exportar_excel(df_edit.drop(columns=["excluir","pdf","pedido"]))
            st.download_button("Baixar Excel", excel, "solicitacoes.xlsx")

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

        modo = st.radio("Modo de geração", ["Manual", "Automático"])

        if modo == "Manual":

            fornecedores_unicos = df_orc["fornecedor"].dropna().unique().tolist()
            fornecedor = st.selectbox("Fornecedor vencedor", fornecedores_unicos)

            if st.button("Gerar Pedido"):
                df_pedido = df_orc[df_orc["fornecedor"] == fornecedor].copy()
                df_pedido["data_pedido"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                df_pedido["id_pedido"] = int(datetime.now().timestamp())
                df_pedido["status"] = "PENDENTE"
                append(df_pedido, "pedidos")
                st.success("Pedido gerado")

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
                st.success("Pedido automático gerado")

# ---------------- PEDIDOS ----------------
elif menu == "Pedidos":

    df = carregar("pedidos")

    if df.empty:
        st.warning("Nenhum pedido gerado ainda")
    else:

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

        st.divider()

        colunas_pdf = st.multiselect("Colunas PDF", df.columns, default=df.columns)

        if st.button("Gerar PDF Pedido"):
            pdf = gerar_pdf(df,"PEDIDO",colunas_pdf)
            st.download_button("Baixar PDF",pdf,"pedido.pdf")

# ---------------- DASHBOARD ----------------
elif menu == "Dashboard":

    df_sol = carregar("solicitacoes")
    df_ped = carregar("pedidos")

    st.metric("Solicitações", len(df_sol))
    st.metric("Pedidos", len(df_ped))

# ---------------- PROJETOS ----------------
elif menu == "Projetos":

    st.subheader("Cadastro de Projetos")

    nome = st.text_input("Nome do Projeto")
    cliente = st.text_input("Cliente")

    if st.button("Salvar Projeto"):
        if nome and cliente:
            df = pd.DataFrame([{
                "projeto": nome,
                "cliente": cliente,
                "data": datetime.now().strftime("%Y-%m-%d")
            }])
            append(df, "projetos")
            st.success("Projeto salvo")
        else:
            st.warning("Preencha os campos")

    df_proj = carregar("projetos")

    if not df_proj.empty:
        st.dataframe(df_proj, use_container_width=True)
        
        
        # ---------------- NOTAS / RECEBIMENTO ----------------
elif menu == "Notas":

    st.subheader("Recebimento de Materiais")

    df = carregar("pedidos")

    if df.empty:
        st.warning("Nenhum pedido disponível")
    else:

        pedidos = df["id_pedido"].dropna().unique()
        pedido_sel = st.selectbox("Selecione o Pedido", pedidos)

        df_sel = df[df["id_pedido"] == pedido_sel].copy()

        df_sel["recebido"] = False

        df_edit = st.data_editor(df_sel, use_container_width=True)

        if st.button("Confirmar Recebimento"):

            df_recebido = df_edit[df_edit["recebido"] == True].copy()

            if not df_recebido.empty:
                df_recebido["data_recebimento"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                append(df_recebido, "notas")

                st.success("Recebimento registrado com sucesso")
            else:
                st.warning("Selecione itens recebidos")
