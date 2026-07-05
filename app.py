import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from supabase import create_client

st.set_page_config(page_title="Financeiro Pro", layout="wide")

# ================= SUPABASE =================
SUPABASE_URL = "https://nwloxhyzvijnimmtevry.supabase.co"
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================= LOGIN =================
if "user" not in st.session_state:
    st.title("🔐 Acesso ao Sistema")
    user = st.text_input("Digite seu nome")
    if st.button("Entrar"):
        if user.strip():
            st.session_state.user = user
            st.rerun()
        else:
            st.warning("Informe um nome")
    st.stop()

user = st.session_state.user

# ================= DADOS =================
def carregar():
    resp = supabase.table("financeiro").select("*").eq("usuario", user).execute()

    colunas = ["data", "tipo", "referente", "valor", "categoria", "mes"]

    if not resp.data:
        return pd.DataFrame(columns=colunas)

    df = pd.DataFrame(resp.data)

    for c in colunas:
        if c not in df.columns:
            df[c] = None

    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)

    return df

df = carregar()

# ================= SIDEBAR (CONTROLE TOTAL) =================
st.sidebar.title("⚙️ Controle")

# Filtro tipo
filtro_tipo = st.sidebar.radio(
    "Visualizar",
    ["Todos", "Entradas", "Saídas"]
)

# Filtro mês/ano
if not df.empty:
    df["ano"] = df["data"].dt.year
    df["mes_num"] = df["data"].dt.month

    anos = sorted(df["ano"].dropna().unique())
    ano_sel = st.sidebar.selectbox("Ano", anos)

    meses = {
        1:"Janeiro",2:"Fevereiro",3:"Março",4:"Abril",
        5:"Maio",6:"Junho",7:"Julho",8:"Agosto",
        9:"Setembro",10:"Outubro",11:"Novembro",12:"Dezembro"
    }

    mes_sel = st.sidebar.selectbox("Mês", list(meses.values()))
    mes_num_sel = list(meses.keys())[list(meses.values()).index(mes_sel)]

    df = df[(df["ano"] == ano_sel) & (df["mes_num"] == mes_num_sel)]

# filtro tipo aplicado
if filtro_tipo == "Entradas":
    df = df[df["tipo"] == "Entrada"]
elif filtro_tipo == "Saídas":
    df = df[df["tipo"] == "Saída"]

# ================= FORMULÁRIO SIDEBAR =================
st.sidebar.divider()
st.sidebar.subheader("➕ Nova Movimentação")

tipo = st.sidebar.selectbox("Tipo", ["Entrada", "Saída"])
data = st.sidebar.date_input("Data", date.today())
referente = st.sidebar.text_input("Referência")
valor = st.sidebar.number_input("Valor", min_value=0.0, step=0.01)

categoria = None
if tipo == "Saída":
    categoria = st.sidebar.selectbox(
        "Categoria",
        ["Alimentação", "Transporte", "Casa", "Lazer", "Outros"]
    )

    if categoria == "Outros":
        categoria = st.sidebar.text_input("Digite a categoria")

if st.sidebar.button("Salvar"):
    supabase.table("financeiro").insert({
        "usuario": user,
        "data": data.isoformat(),
        "tipo": tipo,
        "referente": referente,
        "valor": float(valor),
        "categoria": categoria,
        "mes": data.strftime("%Y-%m")
    }).execute()

    st.sidebar.success("Salvo!")
    st.rerun()

# ================= DASHBOARD =================
st.markdown("## 💳 Dashboard Financeiro")

entradas = df[df["tipo"] == "Entrada"]["valor"].sum()
saidas = df[df["tipo"] == "Saída"]["valor"].sum()
saldo = entradas - saidas

c1, c2, c3 = st.columns(3)

c1.metric("💚 Entradas", f"R$ {entradas:,.2f}")
c2.metric("💸 Saídas", f"R$ {saidas:,.2f}")
c3.metric("💜 Saldo", f"R$ {saldo:,.2f}")

st.divider()

# ================= GRÁFICOS =================
if not df.empty:
    st.subheader("📊 Categorias")

    cat = df[df["tipo"] == "Saída"].groupby("categoria")["valor"].sum().reset_index()

    st.plotly_chart(px.pie(cat, names="categoria", values="valor"), use_container_width=True)

    st.subheader("📈 Evolução")

    mensal = df.copy()
    mensal["mes"] = mensal["data"].dt.strftime("%Y-%m")

    evolucao = mensal.groupby(["mes", "tipo"])["valor"].sum().reset_index()

    st.plotly_chart(
        px.line(evolucao, x="mes", y="valor", color="tipo", markers=True),
        use_container_width=True
    )

# ================= TABELA =================
st.subheader("📋 Histórico")

if not df.empty:
    view = df.copy()
    view["data"] = view["data"].dt.strftime("%d/%m/%Y")
    st.dataframe(view, use_container_width=True)
