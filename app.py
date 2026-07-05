import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client

st.set_page_config(page_title="Dashboard Financeiro Pro", layout="wide")

# ================= SUPABASE =================
SUPABASE_URL = "https://nwloxhyzvijnimmtevry.supabase.co"
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================= LOGIN SIMPLES =================
if "user" not in st.session_state:
    st.title("🔐 Acesso ao Sistema")
    user = st.text_input("Digite seu nome")
    if st.button("Entrar"):
        if user.strip() == "":
            st.warning("Informe um nome")
        else:
            st.session_state.user = user
            st.rerun()
    st.stop()

user = st.session_state.user

st.sidebar.success(f"Usuário: {user}")

# ================= METAS =================
meta = st.sidebar.number_input("Meta mensal de gastos (R$)", value=1000.0)

# ================= CARREGAR DADOS =================
def carregar_dados():
    resp = supabase.table("financeiro").select("*").eq("usuario", user).execute()

    if not resp.data:
        return pd.DataFrame(columns=["data","tipo","referente","valor","categoria","mes"])

    df = pd.DataFrame(resp.data)

    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)

    return df

df = carregar_dados()

# ================= KPIs =================
st.title("📊 Dashboard Financeiro")

entradas = df[df["tipo"] == "Entrada"]["valor"].sum()
saidas = df[df["tipo"] == "Saída"]["valor"].sum()
saldo = entradas - saidas

col1, col2, col3 = st.columns(3)

col1.metric("💰 Entradas", f"R$ {entradas:,.2f}")
col2.metric("💸 Saídas", f"R$ {saidas:,.2f}")
col3.metric("📌 Saldo", f"R$ {saldo:,.2f}")

# ================= ALERTAS =================
st.divider()

if saidas > meta:
    st.error("⚠️ Você ultrapassou sua meta mensal!")
elif saidas > meta * 0.8:
    st.warning("⚠️ Você já usou mais de 80% da sua meta")
else:
    st.success("✔️ Dentro da meta mensal")

st.progress(min(saidas / meta, 1.0))

# ================= FORMULÁRIO =================
st.subheader("➕ Nova movimentação")

col1, col2 = st.columns(2)

with col1:
    tipo = st.selectbox("Tipo", ["Entrada", "Saída"])
    data_mov = st.date_input("Data", date.today())
    categoria = st.selectbox("Categoria", ["Alimentação", "Transporte", "Casa", "Lazer", "Outros"])

with col2:
    referente = st.text_input("Referente")
    valor = st.number_input("Valor", min_value=0.0, step=0.01)

if st.button("Salvar"):
    supabase.table("financeiro").insert({
        "usuario": user,
        "data": data_mov.isoformat(),
        "tipo": tipo,
        "referente": referente,
        "valor": float(valor),
        "categoria": categoria,
        "mes": data_mov.strftime("%m-%Y")
    }).execute()

    st.success("Salvo com sucesso!")
    st.rerun()

st.divider()

# ================= FILTRO MÊS =================
if not df.empty:
    meses = sorted(df["mes"].dropna().unique())
    mes_sel = st.selectbox("Filtrar mês", ["Todos"] + meses)

    if mes_sel != "Todos":
        df = df[df["mes"] == mes_sel]

# ================= TABELA =================
st.subheader("📋 Movimentações")

if not df.empty:
    df_view = df.copy()
    df_view["data"] = df_view["data"].dt.strftime("%d/%m/%Y")

    st.dataframe(
        df_view[["data","tipo","categoria","referente","valor"]],
        use_container_width=True
    )

# ================= GRÁFICOS =================
st.subheader("📈 Análises")

if not df.empty:
    st.bar_chart(df.groupby("tipo")["valor"].sum())

    st.subheader("Gastos por categoria")
    st.bar_chart(df[df["tipo"]=="Saída"].groupby("categoria")["valor"].sum())

    df_sorted = df.sort_values("data")
    df_sorted["fluxo"] = df_sorted.apply(
        lambda x: x["valor"] if x["tipo"] == "Entrada" else -x["valor"],
        axis=1
    ).cumsum()

    st.line_chart(df_sorted.set_index("data")["fluxo"])
