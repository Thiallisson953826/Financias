import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client

st.set_page_config(page_title="Financeiro Pro", layout="wide")

# ================= SUPABASE =================
SUPABASE_URL = "https://nwloxhyzvijnimmtevry.supabase.co"
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================= LOGIN =================
if "user" not in st.session_state:
    st.title("🔐 Acesso")
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

    if not resp.data:
        return pd.DataFrame()

    df = pd.DataFrame(resp.data)
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)
    return df

df = carregar()

# ================= CABEÇALHO =================
st.markdown("## 💼 Sistema Financeiro")

entradas = df[df["tipo"] == "Entrada"]["valor"].sum()
saidas = df[df["tipo"] == "Saída"]["valor"].sum()
saldo = entradas - saidas

c1, c2, c3 = st.columns(3)
c1.metric("Entradas", f"R$ {entradas:,.2f}")
c2.metric("Saídas", f"R$ {saidas:,.2f}")
c3.metric("Saldo", f"R$ {saldo:,.2f}")

st.divider()

# ================= TABS =================
tab1, tab2, tab3 = st.tabs(["➕ Entradas", "➖ Saídas", "📋 Movimentações"])

# ================= ENTRADAS =================
with tab1:
    st.subheader("Nova Entrada")

    col1, col2 = st.columns(2)

    with col1:
        data = st.date_input("Data", date.today())
        referencia = st.text_input("Referência")

    with col2:
        valor = st.number_input("Valor", min_value=0.0, step=0.01)

    if st.button("Salvar Entrada"):
        supabase.table("financeiro").insert({
            "usuario": user,
            "data": data.isoformat(),
            "tipo": "Entrada",
            "referente": referencia,
            "valor": float(valor),
            "categoria": None,
            "mes": data.strftime("%m-%Y")
        }).execute()

        st.success("Entrada salva")
        st.rerun()

# ================= SAÍDAS =================
with tab2:
    st.subheader("Nova Saída")

    col1, col2 = st.columns(2)

    with col1:
        data = st.date_input("Data saída", date.today())
        categoria = st.selectbox(
            "Categoria",
            ["Alimentação", "Transporte", "Casa", "Lazer", "Outros"]
        )

    with col2:
        referencia = st.text_input("Referência saída")
        valor = st.number_input("Valor saída", min_value=0.0, step=0.01)

    if st.button("Salvar Saída"):
        supabase.table("financeiro").insert({
            "usuario": user,
            "data": data.isoformat(),
            "tipo": "Saída",
            "referente": referencia,
            "valor": float(valor),
            "categoria": categoria,
            "mes": data.strftime("%m-%Y")
        }).execute()

        st.success("Saída salva")
        st.rerun()

# ================= MOVIMENTAÇÕES =================
with tab3:
    st.subheader("Histórico")

    if not df.empty:
        df_view = df.copy()
        df_view["data"] = df_view["data"].dt.strftime("%d/%m/%Y")

        st.dataframe(
            df_view[["data","tipo","categoria","referente","valor"]],
            use_container_width=True
        )

# ================= GRÁFICOS =================
st.divider()
st.subheader("📊 Análise Geral")

if not df.empty:
    st.bar_chart(df.groupby("tipo")["valor"].sum())

    st.subheader("Gastos por categoria")
    st.bar_chart(df[df["tipo"]=="Saída"].groupby("categoria")["valor"].sum())
