import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client

st.set_page_config(
    page_title="Organizador Financeiro - TH PROGRAMAÇÃO",
    layout="centered"
)

# Supabase
SUPABASE_URL = "https://nwloxhyzvijnimmtevry.supabase.co"
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("Organizador Financeiro")

# Carregar dados (SEM filtro problemático)
def carregar_dados():
    resp = supabase.table("financeiro").select("*").execute()

    if not resp.data:
        return pd.DataFrame(columns=["Data", "Tipo", "Referente", "Valor", "Mes"])

    df = pd.DataFrame(resp.data)

    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)

    df.rename(columns={
        "data": "Data",
        "tipo": "Tipo",
        "referente": "Referente",
        "valor": "Valor",
        "mes": "Mes"
    }, inplace=True)

    return df


df = carregar_dados()

# Entrada de dados
st.subheader("Adicionar movimentação")

col1, col2 = st.columns(2)

with col1:
    tipo = st.selectbox("Tipo", ["Entrada", "Saída"])
    data_mov = st.date_input("Data", date.today())

with col2:
    referente = st.text_input("Referente")
    valor = st.number_input("Valor", min_value=0.0, step=0.01)

if st.button("Salvar"):
    supabase.table("financeiro").insert({
        "data": data_mov.isoformat(),
        "tipo": tipo,
        "referente": referente,
        "valor": float(valor),
        "mes": data_mov.strftime("%m-%Y")
    }).execute()

    st.success("Registro salvo")
    st.rerun()

# Cálculos
entradas = df[df["Tipo"] == "Entrada"]["Valor"].sum()
saidas = df[df["Tipo"] == "Saída"]["Valor"].sum()
saldo = entradas - saidas

col1, col2, col3 = st.columns(3)
col1.metric("Entradas", f"R$ {entradas:,.2f}")
col2.metric("Saídas", f"R$ {saidas:,.2f}")
col3.metric("Saldo", f"R$ {saldo:,.2f}")

# Gráficos
if not df.empty:
    st.bar_chart(df.groupby("Tipo")["Valor"].sum())

    df_sorted = df.sort_values("Data")
    df_sorted["Saldo"] = df_sorted.apply(
        lambda x: x["Valor"] if x["Tipo"] == "Entrada" else -x["Valor"],
        axis=1
    ).cumsum()

    st.line_chart(df_sorted.set_index("Data")["Saldo"])

# Tabela
st.dataframe(df, use_container_width=True)
