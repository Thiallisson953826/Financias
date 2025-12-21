# ======================================
# TH PROGRAMAÇÃO
# Produzido por Thiallisson
# ======================================

import streamlit as st
import pandas as pd
from datetime import date
import os

# Configuração da página
st.set_page_config(
    page_title="Organizador Financeiro - TH PROGRAMAÇÃO",
    layout="centered"
)

# Caminhos
PASTA = "dados"
ARQUIVO = f"{PASTA}/financeiro.xlsx"
os.makedirs(PASTA, exist_ok=True)

st.title("💰 Organizador Financeiro - TH PROGRAMAÇÃO")

# ===============================
# Seleção do mês
# ===============================
mes_ano = st.selectbox(
    "📅 Selecione o mês",
    pd.date_range(start="2024-01-01", periods=60, freq="MS").strftime("%m-%Y")
)

# ===============================
# Função para carregar dados
# ===============================
def carregar_dados(mes):
    if os.path.exists(ARQUIVO):
        try:
            df = pd.read_excel(ARQUIVO, sheet_name=mes)
            df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
            return df
        except:
            pass
    return pd.DataFrame(columns=["Data", "Tipo", "Referente", "Valor"])

df = carregar_dados(mes_ano)

st.divider()

# ===============================
# Adicionar movimentação
# ===============================
st.subheader("➕ Adicionar movimentação")

col1, col2 = st.columns(2)

with col1:
    tipo = st.selectbox("Tipo", ["Entrada", "Saída"])
    data_mov = st.date_input("Data", date.today())

with col2:
    referente = st.text_input("Referente a quê")
    valor = st.number_input("Valor", min_value=0.0, step=0.01)

if st.button("💾 Salvar movimentação"):
    novo = pd.DataFrame([{
        "Data": data_mov.strftime("%d/%m/%Y"),
        "Tipo": tipo,
        "Referente": referente,
        "Valor": valor
    }])

    df = pd.concat([df, novo], ignore_index=True)

    # Salvamento correto no Excel
    if os.path.exists(ARQUIVO):
        with pd.ExcelWriter(
            ARQUIVO,
            engine="openpyxl",
            mode="a",
            if_sheet_exists="replace"
        ) as writer:
            df.to_excel(writer, sheet_name=mes_ano, index=False)
    else:
        with pd.ExcelWriter(
            ARQUIVO,
            engine="openpyxl",
            mode="w"
        ) as writer:
            df.to_excel(writer, sheet_name=mes_ano, index=False)

    st.success("Movimentação salva com sucesso!")

st.divider()

# ===============================
# Resumo financeiro
# ===============================
entradas = df[df["Tipo"] == "Entrada"]["Valor"].sum()
saidas = df[df["Tipo"] == "Saída"]["Valor"].sum()
saldo = entradas - saidas

st.subheader("📊 Resumo do mês")

colA, colB, colC = st.columns(3)
colA.metric("💵 Entradas", f"R$ {entradas:,.2f}")
colB.metric("💸 Saídas", f"R$ {saidas:,.2f}")
colC.metric("📌 Saldo", f"R$ {saldo:,.2f}")

st.divider()

# ===============================
# Gráficos mensais
# ===============================
st.subheader("📈 Gráficos do mês")

if not df.empty:
    resumo = df.groupby("Tipo")["Valor"].sum()
    st.markdown("### Entradas x Saídas")
    st.bar_chart(resumo)

    df_graf = df.copy()
    df_graf["Data"] = pd.to_datetime(df_graf["Data"], format="%d/%m/%Y")
    df_graf = df_graf.sort_values("Data")

    df_graf["Saldo Acumulado"] = df_graf.apply(
        lambda x: x["Valor"] if x["Tipo"] == "Entrada" else -x["Valor"],
        axis=1
    ).cumsum()

    st.markdown("### Evolução do saldo no mês")
    st.line_chart(df_graf.set_index("Data")["Saldo Acumulado"])
else:
    st.info("Nenhuma movimentação registrada neste mês.")

st.divider()

# ===============================
# Tabela detalhada
# ===============================
st.subheader("📄 Detalhamento das movimentações")
st.dataframe(df, use_container_width=True)

st.divider()

# ===============================
# Download do Excel
# ===============================
st.subheader("📥 Exportar planilha")

if os.path.exists(ARQUIVO):
    with open(ARQUIVO, "rb") as file:
        st.download_button(
            label="📊 Baixar Excel",
            data=file,
            file_name="organizador_financeiro.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Nenhuma planilha disponível para download.")
