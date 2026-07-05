import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from supabase import create_client

st.set_page_config(page_title="Financeiro Pro", layout="wide")

# ================= ESTILO VISUAL =================
st.markdown("""
<style>
body {
    background-color: #0B1220;
}

.block-container {
    padding-top: 2rem;
}

h1, h2, h3 {
    color: #E6EDF3;
}

.card {
    padding: 15px;
    border-radius: 12px;
    background-color: #111A2E;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# ================= SUPABASE =================
SUPABASE_URL = "https://nwloxhyzvijnimmtevry.supabase.co"
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================= LOGIN =================
if "user" not in st.session_state:
    st.title("🔐 Sistema Financeiro 💰")
    user = st.text_input("👤 Usuário")
    if st.button("🚀 Entrar"):
        if user.strip():
            st.session_state.user = user
            st.session_state.page = "dashboard"
            st.rerun()
    st.stop()

user = st.session_state.user

if "page" not in st.session_state:
    st.session_state.page = "dashboard"

# ================= DADOS =================
def carregar():
    resp = supabase.table("financeiro").select("*").eq("usuario", user).execute()

    cols = ["data", "tipo", "referente", "valor", "categoria", "mes"]

    if not resp.data:
        return pd.DataFrame(columns=cols)

    df = pd.DataFrame(resp.data)

    for c in cols:
        if c not in df.columns:
            df[c] = None

    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)

    return df

df = carregar()

# ================= MENU =================
st.sidebar.title("📌 MENU")

if st.sidebar.button("🏠 Dashboard 📊"):
    st.session_state.page = "dashboard"

if st.sidebar.button("➕ Entrada 💚"):
    st.session_state.page = "entrada"

if st.sidebar.button("➖ Saída 🔴"):
    st.session_state.page = "saida"

if st.sidebar.button("📊 Gráficos 📈"):
    st.session_state.page = "graficos"

if st.sidebar.button("📋 Histórico 📁"):
    st.session_state.page = "historico"

# ================= RESUMO =================
def resumo(df_local):
    entradas = df_local[df_local["tipo"] == "Entrada"]["valor"].sum()
    saidas = df_local[df_local["tipo"] == "Saída"]["valor"].sum()
    saldo = entradas - saidas

    col1, col2, col3 = st.columns(3)

    col1.markdown(f"<div class='card'>💚 ENTRADAS<br><h2>R$ {entradas:,.2f}</h2></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='card'>🔴 SAÍDAS<br><h2>R$ {saidas:,.2f}</h2></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='card'>📊 SALDO<br><h2>R$ {saldo:,.2f}</h2></div>", unsafe_allow_html=True)

# ================= FILTRO =================
def filtro_base(df_local):
    if df_local.empty:
        return df_local

    df_local["ano"] = df_local["data"].dt.year
    df_local["mes_num"] = df_local["data"].dt.month

    meses = {
        1:"Janeiro",2:"Fevereiro",3:"Março",4:"Abril",
        5:"Maio",6:"Junho",7:"Julho",8:"Agosto",
        9:"Setembro",10:"Outubro",11:"Novembro",12:"Dezembro"
    }

    ano = st.selectbox("📅 Ano", sorted(df_local["ano"].dropna().unique()))
    mes = st.selectbox("🗓️ Mês", list(meses.values()))
    mes_num = list(meses.keys())[list(meses.values()).index(mes)]

    return df_local[(df_local["ano"] == ano) & (df_local["mes_num"] == mes_num)]

# ================= DASHBOARD =================
def dashboard():
    st.title("📊 Dashboard Financeiro")

    df_f = filtro_base(df)
    resumo(df_f)

# ================= ENTRADA =================
def entrada():
    st.title("💚 Entrada de Dinheiro")

    resumo(df)

    data = st.date_input("📅 Data", date.today())
    referente = st.text_input("📝 Descrição")
    valor = st.number_input("💰 Valor", min_value=0.0, step=0.01)

    if st.button("💾 Salvar Entrada"):
        supabase.table("financeiro").insert({
            "usuario": user,
            "data": data.isoformat(),
            "tipo": "Entrada",
            "referente": referente,
            "valor": float(valor),
            "categoria": None,
            "mes": data.strftime("%Y-%m")
        }).execute()

        st.success("💚 Entrada registrada!")
        st.rerun()

# ================= SAÍDA =================
def saida():
    st.title("🔴 Saída de Dinheiro")

    resumo(df)

    data = st.date_input("📅 Data", date.today())

    categoria = st.selectbox(
        "🏷️ Categoria",
        ["🍔 Alimentação", "🚌 Transporte", "🏠 Casa", "🎮 Lazer", "Outros"]
    )

    if categoria == "Outros":
        categoria = st.text_input("✏️ Digite a categoria")

    referente = st.text_input("📝 Descrição")
    valor = st.number_input("💰 Valor", min_value=0.0, step=0.01)

    if st.button("💾 Salvar Saída"):
        supabase.table("financeiro").insert({
            "usuario": user,
            "data": data.isoformat(),
            "tipo": "Saída",
            "referente": referente,
            "valor": float(valor),
            "categoria": categoria,
            "mes": data.strftime("%Y-%m")
        }).execute()

        st.success("🔴 Saída registrada!")
        st.rerun()

# ================= GRÁFICOS =================
def graficos():
    st.title("📈 Gráficos Financeiros")

    df_f = filtro_base(df)
    resumo(df_f)

    if not df_f.empty:
        cat = df_f[df_f["tipo"] == "Saída"].groupby("categoria")["valor"].sum().reset_index()

        st.plotly_chart(px.pie(cat, names="categoria", values="valor"), use_container_width=True)

        mensal = df_f.copy()
        mensal["mes"] = mensal["data"].dt.strftime("%Y-%m")

        evolucao = mensal.groupby(["mes", "tipo"])["valor"].sum().reset_index()

        st.plotly_chart(
            px.line(evolucao, x="mes", y="valor", color="tipo", markers=True),
            use_container_width=True
        )

# ================= HISTÓRICO =================
def historico():
    st.title("📁 Histórico Financeiro")

    df_f = filtro_base(df)
    resumo(df_f)

    if not df_f.empty:
        view = df_f.copy()
        view["data"] = view["data"].dt.strftime("%d/%m/%Y")
        st.dataframe(view, use_container_width=True)

# ================= RENDER =================
if st.session_state.page == "dashboard":
    dashboard()
elif st.session_state.page == "entrada":
    entrada()
elif st.session_state.page == "saida":
    saida()
elif st.session_state.page == "graficos":
    graficos()
elif st.session_state.page == "historico":
    historico()
