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

# ================= CARREGAR DADOS (CORRIGIDO) =================
def carregar():
    resp = supabase.table("financeiro").select("*").eq("usuario", user).execute()

    colunas = ["data", "tipo", "referente", "valor", "categoria", "mes"]

    if not resp.data:
        return pd.DataFrame(columns=colunas)

    df = pd.DataFrame(resp.data)

    # garante que todas as colunas existam (evita KeyError)
    for c in colunas:
        if c not in df.columns:
            df[c] = None

    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)

    return df

df = carregar()

# ================= FILTRO MÊS + ANO =================
st.sidebar.subheader("📅 Filtro")

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

# ================= KPIs =================
st.markdown("## 💳 Dashboard Financeiro")

entradas = df[df["tipo"] == "Entrada"]["valor"].sum()
saidas = df[df["tipo"] == "Saída"]["valor"].sum()
saldo = entradas - saidas

c1, c2, c3 = st.columns(3)

c1.metric("💚 Entradas", f"R$ {entradas:,.2f}")
c2.metric("💸 Saídas", f"R$ {saidas:,.2f}")
c3.metric("💜 Saldo", f"R$ {saldo:,.2f}")

st.divider()

# ================= METAS =================
st.subheader("🎯 Metas por Categoria")

categorias = ["Alimentação", "Transporte", "Casa", "Lazer"]

meta_categoria = {}
for c in categorias:
    meta_categoria[c] = st.slider(f"Meta {c}", 0, 5000, 1000)

if not df.empty:
    gastos_cat = df[df["tipo"] == "Saída"].groupby("categoria")["valor"].sum().reset_index()

    for c in categorias:
        gasto = gastos_cat[gastos_cat["categoria"] == c]["valor"].sum()
        st.write(f"**{c}**: R$ {gasto:.2f} / Meta {meta_categoria[c]}")

st.divider()

# ================= EVOLUÇÃO =================
st.subheader("📈 Evolução")

if not df.empty:
    mensal = df.copy()
    mensal["mes"] = mensal["data"].dt.strftime("%Y-%m")

    evolucao = mensal.groupby(["mes", "tipo"])["valor"].sum().reset_index()

    fig = px.line(
        evolucao,
        x="mes",
        y="valor",
        color="tipo",
        markers=True
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ================= CATEGORIAS =================
st.subheader("📊 Gastos por Categoria")

if not df.empty:
    cat = df[df["tipo"]=="Saída"].groupby("categoria")["valor"].sum().reset_index()

    fig2 = px.pie(cat, names="categoria", values="valor")
    st.plotly_chart(fig2)

st.divider()

# ================= FORMULÁRIO =================
st.subheader("➕ Nova Movimentação")

col1, col2 = st.columns(2)

with col1:
    tipo = st.selectbox("Tipo", ["Entrada", "Saída"])
    data = st.date_input("Data", date.today())

    categoria = None
    if tipo == "Saída":
        categoria = st.selectbox(
            "Categoria",
            ["Alimentação", "Transporte", "Casa", "Lazer", "Outros"]
        )

        if categoria == "Outros":
            categoria = st.text_input("Digite a categoria")

with col2:
    referente = st.text_input("Referência")
    valor = st.number_input("Valor", min_value=0.0, step=0.01)

if st.button("Salvar"):
    supabase.table("financeiro").insert({
        "usuario": user,
        "data": data.isoformat(),
        "tipo": tipo,
        "referente": referente,
        "valor": float(valor),
        "categoria": categoria,
        "mes": data.strftime("%Y-%m")
    }).execute()

    st.success("Salvo com sucesso!")
    st.rerun()

st.divider()

# ================= HISTÓRICO =================
st.subheader("📋 Histórico")

if not df.empty:
    view = df.copy()
    view["data"] = view["data"].dt.strftime("%d/%m/%Y")

    st.dataframe(view, use_container_width=True)
