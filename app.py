# ======================================
# TH PROGRAMAÇÃO
# Produzido por Thiallisson
# ======================================

import streamlit as st
import pandas as pd
from datetime import date
import os

st.set_page_config(page_title="Organizador Financeiro - TH PROGRAMAÇÃO")

PASTA = "dados"
ARQUIVO = f"{PASTA}/financeiro.xlsx"
os.makedirs(PASTA, exist_ok=True)

st.title("💰 Organizador Financeiro - TH PROGRAMAÇÃO")

mes_ano = st.selectbox(
    "Selecione o mês",
    pd.date_range(start="2024-01-01", periods=48, freq="MS").strftime("%m-%Y")
)

def carregar_dados(mes):
    if os.path.exists(ARQUIVO):
        try:
            return pd.read_excel(ARQUIVO, sheet_name=mes)
        except:
            return pd.DataFrame(columns=["Data", "Tipo", "Referente", "Valor"])
    return pd.DataFrame(columns=["Data", "Tipo", "Referente", "Valor"])

df = carregar_dados(mes_ano)

st.subheader("Adicionar movimentação")

tipo = st.selectbox("Tipo", ["Entrada", "Saída"])
data_mov = st.date_input("Data", date.today())
referente = st.text_input("Referente a quê")
valor = st.number_input("Valor", min_value=0.0)

if st.button("Salvar"):
    novo = pd.DataFrame([{
        "Data": data_mov.strftime("%d/%m/%Y"),
        "Tipo": tipo,
        "Referente": referente,
        "Valor": valor
    }])
    df = pd.concat([df, novo], ignore_index=True)
    with pd.ExcelWriter(ARQUIVO, engine="openpyxl", mode="a" if os.path.exists(ARQUIVO) else "w", if_sheet_exists="replace") as writer:
        df.to_excel(writer, sheet_name=mes_ano, index=False)
    st.success("Salvo com sucesso")

entradas = df[df["Tipo"] == "Entrada"]["Valor"].sum()
saidas = df[df["Tipo"] == "Saída"]["Valor"].sum()
saldo = entradas - saidas

st.metric("Entradas", entradas)
st.metric("Saídas", saidas)
st.metric("Saldo", saldo)

if not df.empty:
    st.bar_chart(df.groupby("Tipo")["Valor"].sum())
