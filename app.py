import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client
import io

st.set_page_config(page_title="Dashboard Financeiro", layout="wide")

# ================= SUPABASE =================
SUPABASE_URL = "https://nwloxhyzvijnimmtevry.supabase.co"
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================= CARREGAR DADOS =================
def carregar_dados():
    resp = supabase.table("financeiro").select("*").execute()

    if not resp.data:
        return pd.DataFrame(columns=["data","tipo","referente","valor","mes"])

    df = pd.DataFrame(resp.data)

    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)

    return df

df = carregar_dados()

# ================= FILTRO POR MÊS =================
st.sidebar.title("📅 Filtros")

if not df.empty:
    meses = sorted(df["mes"].dropna().unique())
    mes_selecionado = st.sidebar.selectbox("Selecionar mês", ["Todos"] + meses)

    if mes_selecionado != "Todos":
        df = df[df["mes"] == mes_selecionado]

# ================= KPIs =================
st.title("📊 Dashboard Financeiro")

col1, col2, col3 = st.columns(3)

entradas = df[df["tipo"] == "Entrada"]["valor"].sum()
saidas = df[df["tipo"] == "Saída"]["valor"].sum()
saldo = entradas - saidas

col1.metric("💰 Entradas", f"R$ {entradas:,.2f}")
col2.metric("💸 Saídas", f"R$ {saidas:,.2f}")
col3.metric("📌 Saldo", f"R$ {saldo:,.2f}")

st.divider()

# ================= FORMULÁRIO =================
st.subheader("➕ Nova movimentação")

c1, c2 = st.columns(2)

with c1:
    tipo = st.selectbox("Tipo", ["Entrada", "Saída"])
    data_mov = st.date_input("Data", date.today())

with c2:
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

    st.success("Movimentação salva!")
    st.rerun()

st.divider()

# ================= TABELA =================
st.subheader("📋 Movimentações")

if not df.empty:
    df_view = df.copy()
    df_view["data"] = df_view["data"].dt.strftime("%d/%m/%Y")

    st.dataframe(
        df_view[["data","tipo","referente","valor","mes"]],
        use_container_width=True
    )

# ================= GRÁFICOS =================
if not df.empty:
    st.subheader("📈 Análise")

    st.bar_chart(df.groupby("tipo")["valor"].sum())

    df_sorted = df.sort_values("data")
    df_sorted["fluxo"] = df_sorted.apply(
        lambda x: x["valor"] if x["tipo"] == "Entrada" else -x["valor"],
        axis=1
    ).cumsum()

    st.line_chart(df_sorted.set_index("data")["fluxo"])

# ================= EXPORTAÇÃO EXCEL =================
st.divider()
st.subheader("📤 Exportar dados")

if not df.empty:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="financeiro")

    st.download_button(
        "Baixar Excel",
        data=output.getvalue(),
        file_name="financeiro.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
