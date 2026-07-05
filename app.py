# Organizador Financeiro - versão base para Supabase
# IMPORTANTE:
# 1. Adicione "supabase" ao requirements.txt
# 2. Configure no Streamlit Cloud:
#    SUPABASE_KEY="sua_chave_publishable"

import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client

st.set_page_config(page_title="Organizador Financeiro - TH PROGRAMAÇÃO", layout="centered")

SUPABASE_URL = "https://nwloxhyzvijnimmtevry.supabase.co"
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("💰 Organizador Financeiro - TH PROGRAMAÇÃO")

mes_ano = st.selectbox(
    "📅 Selecione o mês",
    pd.date_range(start="2024-01-01", periods=60, freq="MS").strftime("%m-%Y")
)

def carregar_dados(mes):
    resp = supabase.table("financeiro").select("*").eq("mes", mes).execute()
    if not resp.data:
        return pd.DataFrame(columns=["Data","Tipo","Referente","Valor"])
    df = pd.DataFrame(resp.data)
    df.rename(columns={
        "data":"Data",
        "tipo":"Tipo",
        "referente":"Referente",
        "valor":"Valor"
    }, inplace=True)
    df["Data"] = pd.to_datetime(df["Data"]).dt.strftime("%d/%m/%Y")
    df["Valor"] = pd.to_numeric(df["Valor"])
    return df[["Data","Tipo","Referente","Valor"]]

df = carregar_dados(mes_ano)

st.subheader("➕ Adicionar movimentação")

c1,c2=st.columns(2)
with c1:
    tipo=st.selectbox("Tipo",["Entrada","Saída"])
    data_mov=st.date_input("Data",date.today())
with c2:
    referente=st.text_input("Referente a quê")
    valor=st.number_input("Valor",min_value=0.0,step=0.01)

if st.button("💾 Salvar movimentação"):
    supabase.table("financeiro").insert({
        "data":data_mov.isoformat(),
        "tipo":tipo,
        "referente":referente,
        "valor":float(valor),
        "mes":mes_ano
    }).execute()
    st.success("Movimentação salva!")
    st.rerun()

entradas=df[df["Tipo"]=="Entrada"]["Valor"].sum()
saidas=df[df["Tipo"]=="Saída"]["Valor"].sum()
saldo=entradas-saidas

a,b,c=st.columns(3)
a.metric("💵 Entradas",f"R$ {entradas:,.2f}")
b.metric("💸 Saídas",f"R$ {saidas:,.2f}")
c.metric("📌 Saldo",f"R$ {saldo:,.2f}")

if not df.empty:
    st.bar_chart(df.groupby("Tipo")["Valor"].sum())
    g=df.copy()
    g["Data"]=pd.to_datetime(g["Data"],format="%d/%m/%Y")
    g=g.sort_values("Data")
    g["Saldo Acumulado"]=g.apply(lambda x:x["Valor"] if x["Tipo"]=="Entrada" else -x["Valor"],axis=1).cumsum()
    st.line_chart(g.set_index("Data")["Saldo Acumulado"])

st.dataframe(df,use_container_width=True)
