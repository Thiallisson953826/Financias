import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from supabase import create_client
from fpdf import FPDF
import io

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
    if not resp.data:
        return pd.DataFrame()

    df = pd.DataFrame(resp.data)
    df["data"] = pd.to_datetime(df["data"])
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)
    return df

df = carregar()

# ================= KPIs (NUBANK STYLE) =================
st.markdown("## 💳 Painel Financeiro")

entradas = df[df["tipo"]=="Entrada"]["valor"].sum()
saidas = df[df["tipo"]=="Saída"]["valor"].sum()
saldo = entradas - saidas

col1, col2, col3 = st.columns(3)

col1.metric("💚 Entradas", f"R$ {entradas:,.2f}")
col2.metric("💸 Saídas", f"R$ {saidas:,.2f}")
col3.metric("💜 Saldo", f"R$ {saldo:,.2f}")

st.divider()

# ================= METAS POR CATEGORIA =================
st.subheader("🎯 Metas por Categoria")

categorias = ["Alimentação", "Transporte", "Casa", "Lazer"]

meta_categoria = {}
for c in categorias:
    meta_categoria[c] = st.slider(f"Meta {c}", 0, 5000, 1000)

if not df.empty:
    gastos_cat = df[df["tipo"]=="Saída"].groupby("categoria")["valor"].sum().reset_index()

    for c in categorias:
        gasto = gastos_cat[gastos_cat["categoria"]==c]["valor"].sum()
        st.write(f"**{c}**: R$ {gasto:.2f} / Meta {meta_categoria[c]}")

# ================= EVOLUÇÃO MENSAL =================
st.subheader("📈 Evolução Mensal")

if not df.empty:
    mensal = df.copy()
    mensal["mes"] = mensal["data"].dt.strftime("%Y-%m")

    evolucao = mensal.groupby(["mes","tipo"])["valor"].sum().reset_index()

    fig = px.line(
        evolucao,
        x="mes",
        y="valor",
        color="tipo",
        markers=True,
        title="Evolução Mensal"
    )
    st.plotly_chart(fig, use_container_width=True)

# ================= GRÁFICOS POWER BI STYLE =================
st.subheader("📊 Análise Inteligente")

if not df.empty:
    cat = df[df["tipo"]=="Saída"].groupby("categoria")["valor"].sum().reset_index()

    fig2 = px.pie(cat, names="categoria", values="valor", title="Distribuição de Gastos")
    st.plotly_chart(fig2)

# ================= FORMULÁRIO =================
st.subheader("➕ Nova Movimentação")

col1, col2 = st.columns(2)

with col1:
    tipo = st.selectbox("Tipo", ["Entrada", "Saída"])
    data = st.date_input("Data", date.today())

    categoria = None
    if tipo == "Saída":
        categoria = st.selectbox("Categoria", categorias + ["Outros"])
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

    st.success("Salvo!")
    st.rerun()

# ================= TABELA =================
st.subheader("📋 Histórico")

if not df.empty:
    view = df.copy()
    view["data"] = view["data"].dt.strftime("%d/%m/%Y")

    st.dataframe(view, use_container_width=True)

# ================= EXPORTAÇÃO PDF =================
st.subheader("📤 Exportar relatório")

if not df.empty:
    if st.button("Gerar PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        pdf.cell(200, 10, txt=f"Relatório Financeiro - {user}", ln=True)

        for i, row in df.iterrows():
            texto = f"{row['data'].strftime('%d/%m/%Y')} | {row['tipo']} | {row['valor']}"
            pdf.cell(200, 8, txt=texto, ln=True)

        buffer = io.BytesIO()
        pdf.output(buffer)

        st.download_button(
            "Baixar PDF",
            data=buffer.getvalue(),
            file_name="relatorio.pdf",
            mime="application/pdf"
        )
