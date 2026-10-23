import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from supabase import create_client

st.set_page_config(page_title="Financeiro Pro", page_icon="💰", layout="wide")

st.markdown("""
<style>
.stApp {background: linear-gradient(180deg,#08111f 0%,#0d1728 100%);}
[data-testid="stSidebar"] {background:#0a1322;border-right:1px solid #24324a;}
.block-container {padding-top:1.2rem;padding-bottom:2rem;max-width:1500px;}
h1,h2,h3 {color:#f4f7fb; text-transform:uppercase;}
label, p, button, [data-testid="stMarkdownContainer"] {text-transform:uppercase;}
.card {padding:18px;border-radius:16px;background:linear-gradient(145deg,#142239,#101a2c);border:1px solid #253653;min-height:115px;box-shadow:0 8px 24px rgba(0,0,0,.20);}
.card-label {font-size:.92rem;color:#aab8cc;margin-bottom:8px;}
.card-value {font-size:1.65rem;font-weight:700;color:#fff;}
.loan-card {padding:18px;border-radius:16px;background:#111d31;border:1px solid #2b3c59;margin-bottom:14px;}
div.stButton>button {border-radius:10px;border:1px solid #334b70;min-height:42px;}
@media(max-width:768px){.block-container{padding-left:.75rem;padding-right:.75rem}.card{min-height:95px;padding:14px}.card-value{font-size:1.25rem}}
</style>
""", unsafe_allow_html=True)

SUPABASE_URL = "https://nwloxhyzvijnimmtevry.supabase.co"
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

MESES = {1:"Janeiro",2:"Fevereiro",3:"Março",4:"Abril",5:"Maio",6:"Junho",7:"Julho",8:"Agosto",9:"Setembro",10:"Outubro",11:"Novembro",12:"Dezembro"}
FIN_COLS = ["id","data","tipo","referente","valor","categoria","mes","usuario","conta"]
EMP_COLS = ["id","usuario","banco","tipo","valor_total","quantidade_parcelas","valor_parcela","parcelas_pagas","data_contratacao","observacao","created_at","finalidade","parcelas_restantes"]
INV_COLS = ["id","usuario","nome","instituicao","tipo","valor_aplicado","saldo_atual","data_aplicacao","observacao","created_at"]
BANCOS_PADRAO = ["CAIXA", "BANCO DO BRASIL", "PAGBANK", "AGIBANK", "PICPAY", "EM ESPÉCIE"]


def moeda(valor):
    valor = float(valor or 0)
    texto = f"{valor:,.2f}".replace(",","X").replace(".",",").replace("X",".")
    return f"R$ {texto}"


def carregar_financeiro(usuario):
    try:
        resp = supabase.table("financeiro").select("*").eq("usuario", usuario).order("data", desc=True).execute()
    except Exception as erro:
        st.error(f"Erro ao carregar movimentações: {erro}")
        return pd.DataFrame(columns=FIN_COLS)
    if not resp.data:
        return pd.DataFrame(columns=FIN_COLS)
    dados = pd.DataFrame(resp.data)
    for c in FIN_COLS:
        if c not in dados.columns:
            dados[c] = None
    dados["data"] = pd.to_datetime(dados["data"], errors="coerce")
    dados["valor"] = pd.to_numeric(dados["valor"], errors="coerce").fillna(0)
    return dados


def carregar_emprestimos(usuario):
    try:
        resp = supabase.table("emprestimos").select("*").eq("usuario", usuario).order("created_at", desc=True).execute()
    except Exception:
        return pd.DataFrame(columns=EMP_COLS)
    if not resp.data:
        return pd.DataFrame(columns=EMP_COLS)
    dados = pd.DataFrame(resp.data)
    for c in EMP_COLS:
        if c not in dados.columns:
            dados[c] = None
    for c in ["valor_total","valor_parcela"]:
        dados[c] = pd.to_numeric(dados[c], errors="coerce").fillna(0)
    for c in ["quantidade_parcelas","parcelas_pagas"]:
        dados[c] = pd.to_numeric(dados[c], errors="coerce").fillna(0).astype(int)
    dados["data_contratacao"] = pd.to_datetime(dados["data_contratacao"], errors="coerce")
    return dados


def resumo(dados):
    entradas = dados.loc[dados["tipo"]=="Entrada","valor"].sum() if not dados.empty else 0
    saidas = dados.loc[dados["tipo"]=="Saída","valor"].sum() if not dados.empty else 0
    saldo = entradas - saidas
    c1,c2,c3 = st.columns(3)
    cards = [(c1,"💚 ENTRADAS",entradas),(c2,"🔴 SAÍDAS",saidas),(c3,"📊 SALDO",saldo)]
    for col,titulo,valor in cards:
        with col:
            st.markdown(f"<div class='card'><div class='card-label'>{titulo}</div><div class='card-value'>{moeda(valor)}</div></div>", unsafe_allow_html=True)
    st.write("")


def filtro_periodo(dados, prefixo):
    if dados.empty:
        return dados.copy()
    base = dados.copy()
    base["ano"] = base["data"].dt.year
    base["mes_num"] = base["data"].dt.month
    anos = sorted([int(x) for x in base["ano"].dropna().unique()], reverse=True)
    if not anos:
        return base.iloc[0:0]
    c1,c2 = st.columns(2)
    with c1:
        ano = st.selectbox("📅 Ano", anos, key=f"{prefixo}_ano")
    with c2:
        mes_nome = st.selectbox("🗓️ Mês", ["Todos"]+list(MESES.values()), key=f"{prefixo}_mes")
    filtrado = base[base["ano"]==ano]
    if mes_nome != "Todos":
        mes_num = next(k for k,v in MESES.items() if v==mes_nome)
        filtrado = filtrado[filtrado["mes_num"]==mes_num]
    return filtrado


def atualizar_movimentacao(registro_id, dados):
    supabase.table("financeiro").update(dados).eq("id", int(registro_id)).execute()


def excluir_movimentacao(registro_id):
    supabase.table("financeiro").delete().eq("id", int(registro_id)).execute()


def atualizar_emprestimo(registro_id, dados):
    supabase.table("emprestimos").update(dados).eq("id", int(registro_id)).execute()


def excluir_emprestimo(registro_id):
    supabase.table("emprestimos").delete().eq("id", int(registro_id)).execute()


def selecionar_movimentacao(dados, tipo, chave):
    lista = dados[dados["tipo"]==tipo].sort_values("data", ascending=False)
    if lista.empty:
        return None
    opcoes = {}
    for _,linha in lista.iterrows():
        data_txt = linha["data"].strftime("%d/%m/%Y") if pd.notna(linha["data"]) else "Sem data"
        label = f"#{linha['id']} — {data_txt} — {linha.get('referente') or 'Sem descrição'} — {moeda(linha['valor'])}"
        opcoes[label] = linha["id"]
    escolha = st.selectbox("Selecione o lançamento", list(opcoes), key=chave)
    return lista[lista["id"]==opcoes[escolha]].iloc[0]


def editar_excluir_movimentacao(dados, tipo, prefixo):
    registro = selecionar_movimentacao(dados, tipo, f"{prefixo}_seletor")
    if registro is None:
        st.info(f"Nenhuma {tipo.lower()} cadastrada.")
        return
    data_original = registro["data"].date() if pd.notna(registro["data"]) else date.today()
    with st.form(f"{prefixo}_editar_form"):
        data_edit = st.date_input("📅 Data", data_original, key=f"{prefixo}_data_edit")
        referente_edit = st.text_input("📝 DESCRIÇÃO", value=maiusculas(registro.get("referente")), key=f"{prefixo}_ref_edit")
        contas_disponiveis = carregar_bancos(user)
        conta_atual = maiusculas(registro.get("conta"))
        if conta_atual and conta_atual not in contas_disponiveis: contas_disponiveis = [conta_atual] + contas_disponiveis
        conta_edit = st.selectbox("🏦 BANCO / LOCAL", contas_disponiveis, index=contas_disponiveis.index(conta_atual) if conta_atual in contas_disponiveis else 0, key=f"{prefixo}_conta_edit")
        categoria_edit = None
        if tipo == "Saída":
            categoria_edit = st.text_input("🏷️ Categoria", value=str(registro.get("categoria") or ""), key=f"{prefixo}_cat_edit")
        valor_edit = st.number_input("💰 Valor", min_value=0.0, value=float(registro.get("valor") or 0), step=0.01, key=f"{prefixo}_valor_edit")
        salvar = st.form_submit_button("💾 Salvar alterações")
    if salvar:
        if not referente_edit.strip() or valor_edit <= 0:
            st.warning("Preencha a descrição e informe um valor maior que zero.")
        elif tipo == "Saída" and not categoria_edit.strip():
            st.warning("Informe a categoria.")
        else:
            payload = {"data":data_edit.isoformat(),"referente":maiusculas(referente_edit),"valor":float(valor_edit),"mes":data_edit.strftime("%Y-%m"),"categoria":maiusculas(categoria_edit) if tipo=="Saída" else None,"conta":maiusculas(conta_edit)}
            try:
                atualizar_movimentacao(registro["id"], payload)
                st.success("Movimentação atualizada.")
                st.rerun()
            except Exception as erro:
                st.error(f"Erro ao atualizar: {erro}")
    st.divider()
    confirmar = st.checkbox("Confirmo que desejo excluir este lançamento.", key=f"{prefixo}_confirmar")
    if st.button("🗑️ Excluir definitivamente", disabled=not confirmar, key=f"{prefixo}_excluir"):
        try:
            excluir_movimentacao(registro["id"])
            st.success("Movimentação excluída do banco.")
            st.rerun()
        except Exception as erro:
            st.error(f"Erro ao excluir: {erro}")




def maiusculas(valor):
    return str(valor or "").strip().upper()

def carregar_bancos(usuario):
    try:
        resp = supabase.table("bancos").select("*").eq("usuario", usuario).order("nome").execute()
        nomes = [maiusculas(x.get("nome")) for x in (resp.data or []) if x.get("nome")]
        return list(dict.fromkeys(BANCOS_PADRAO + nomes))
    except Exception:
        # A lista padrão continua funcionando até a tabela bancos ser criada.
        return BANCOS_PADRAO.copy()

def carregar_investimentos(usuario):
    try:
        resp = supabase.table("investimentos").select("*").eq("usuario", usuario).order("data_aplicacao", desc=True).execute()
    except Exception as erro:
        st.error("NÃO FOI POSSÍVEL CARREGAR INVESTIMENTOS. CONFIRA SE EXECUTOU O SQL DE ATUALIZAÇÃO.")
        st.caption(str(erro))
        return pd.DataFrame(columns=INV_COLS)
    if not resp.data:
        return pd.DataFrame(columns=INV_COLS)
    dados = pd.DataFrame(resp.data)
    for c in INV_COLS:
        if c not in dados.columns: dados[c] = None
    for c in ["valor_aplicado", "saldo_atual"]:
        dados[c] = pd.to_numeric(dados[c], errors="coerce").fillna(0)
    dados["data_aplicacao"] = pd.to_datetime(dados["data_aplicacao"], errors="coerce")
    return dados

def salvar_conta_movimentacao(registro_id, conta):
    supabase.table("financeiro").update({"conta": maiusculas(conta)}).eq("id", int(registro_id)).eq("usuario", user).execute()

def editar_excluir_investimento(inv):
    if inv.empty:
        st.info("NENHUM INVESTIMENTO CADASTRADO.")
        return
    opcoes = {}
    for _, r in inv.iterrows():
        opcoes[f"#{r['id']} — {maiusculas(r.get('nome'))} — {moeda(r.get('saldo_atual'))}"] = r
    label = st.selectbox("SELECIONE O INVESTIMENTO", list(opcoes), key="inv_editar_sel")
    r = opcoes[label]
    data_base = r["data_aplicacao"].date() if pd.notna(r["data_aplicacao"]) else date.today()
    with st.form(f"inv_editar_{r['id']}"):
        nome = st.text_input("NOME DA APLICAÇÃO", value=maiusculas(r.get("nome")))
        instituicao = st.text_input("BANCO OU LOCAL", value=maiusculas(r.get("instituicao")))
        tipo = st.text_input("TIPO DE INVESTIMENTO", value=maiusculas(r.get("tipo")))
        aplicado = st.number_input("VALOR APLICADO", min_value=0.0, value=float(r["valor_aplicado"]), step=0.01)
        saldo = st.number_input("SALDO ATUAL", min_value=0.0, value=float(r["saldo_atual"]), step=0.01)
        data_inv = st.date_input("DATA DA APLICAÇÃO", value=data_base)
        obs = st.text_area("OBSERVAÇÃO", value=maiusculas(r.get("observacao")))
        salvar = st.form_submit_button("SALVAR ALTERAÇÕES")
    if salvar:
        if not nome.strip() or not instituicao.strip() or aplicado <= 0:
            st.warning("PREENCHA NOME, LOCAL E VALOR APLICADO.")
        else:
            try:
                supabase.table("investimentos").update({"nome":maiusculas(nome),"instituicao":maiusculas(instituicao),"tipo":maiusculas(tipo),"valor_aplicado":float(aplicado),"saldo_atual":float(saldo),"data_aplicacao":data_inv.isoformat(),"observacao":maiusculas(obs)}).eq("id",int(r["id"])).eq("usuario",user).execute()
                st.success("INVESTIMENTO ATUALIZADO.")
                st.rerun()
            except Exception as erro: st.error(f"ERRO AO ATUALIZAR: {erro}")
    confirmar = st.checkbox("CONFIRMO QUE DESEJO EXCLUIR ESTE INVESTIMENTO.", key=f"inv_confirm_{r['id']}")
    if st.button("EXCLUIR INVESTIMENTO DEFINITIVAMENTE", disabled=not confirmar, key=f"inv_excluir_{r['id']}"):
        try:
            supabase.table("investimentos").delete().eq("id",int(r["id"])).eq("usuario",user).execute()
            st.success("INVESTIMENTO EXCLUÍDO DO BANCO DE DADOS.")
            st.rerun()
        except Exception as erro: st.error(f"ERRO AO EXCLUIR: {erro}")

def investimentos():
    st.title("📈 INVESTIMENTOS")
    resumo(df)
    inv = carregar_investimentos(user)
    bancos = carregar_bancos(user)
    t1, t2 = st.tabs(["➕ NOVA APLICAÇÃO", "📋 CARTEIRA / EDITAR / EXCLUIR"])
    with t1:
        with st.form("novo_investimento", clear_on_submit=True):
            nome = st.text_input("NOME DA APLICAÇÃO", placeholder="EX.: RESERVA DE EMERGÊNCIA")
            local_opcoes = bancos + ["ADICIONAR NOVO BANCO/LOCAL"]
            local = st.selectbox("BANCO OU LOCAL", local_opcoes)
            local_novo = st.text_input("DIGITE O NOVO BANCO/LOCAL") if local == "ADICIONAR NOVO BANCO/LOCAL" else ""
            tipo = st.text_input("TIPO DE INVESTIMENTO", placeholder="EX.: CDB, POUPANÇA, DINHEIRO EM ESPÉCIE")
            c1,c2 = st.columns(2)
            with c1: aplicado = st.number_input("VALOR APLICADO", min_value=0.0, step=0.01)
            with c2: saldo = st.number_input("SALDO ATUAL", min_value=0.0, step=0.01)
            data_inv = st.date_input("DATA DA APLICAÇÃO", value=date.today())
            obs = st.text_area("OBSERVAÇÃO")
            salvar = st.form_submit_button("SALVAR INVESTIMENTO")
        if salvar:
            local_final = maiusculas(local_novo) if local == "ADICIONAR NOVO BANCO/LOCAL" else maiusculas(local)
            if not nome.strip() or not local_final or aplicado <= 0:
                st.warning("PREENCHA NOME, BANCO/LOCAL E VALOR APLICADO.")
            else:
                try:
                    if local == "ADICIONAR NOVO BANCO/LOCAL":
                        supabase.table("bancos").upsert({"usuario":user,"nome":local_final}, on_conflict="usuario,nome").execute()
                    supabase.table("investimentos").insert({"usuario":user,"nome":maiusculas(nome),"instituicao":local_final,"tipo":maiusculas(tipo),"valor_aplicado":float(aplicado),"saldo_atual":float(saldo),"data_aplicacao":data_inv.isoformat(),"observacao":maiusculas(obs)}).execute()
                    st.success("INVESTIMENTO CADASTRADO.")
                    st.rerun()
                except Exception as erro: st.error(f"ERRO AO SALVAR. CONFIRA O SQL DE ATUALIZAÇÃO: {erro}")
    with t2:
        if inv.empty:
            st.info("AINDA NÃO HÁ INVESTIMENTOS CADASTRADOS.")
        else:
            c1,c2,c3 = st.columns(3)
            c1.metric("TOTAL APLICADO", moeda(inv["valor_aplicado"].sum()))
            c2.metric("SALDO ATUAL TOTAL", moeda(inv["saldo_atual"].sum()))
            c3.metric("RENDIMENTO / VARIAÇÃO", moeda(inv["saldo_atual"].sum()-inv["valor_aplicado"].sum()))
            visual = inv.copy()
            visual["nome"] = visual["nome"].map(maiusculas)
            visual["instituicao"] = visual["instituicao"].map(maiusculas)
            visual["tipo"] = visual["tipo"].map(maiusculas)
            visual["data_aplicacao"] = visual["data_aplicacao"].dt.strftime("%d/%m/%Y")
            st.dataframe(visual[["id","nome","instituicao","tipo","valor_aplicado","saldo_atual","data_aplicacao"]], use_container_width=True, hide_index=True)
            st.divider()
            editar_excluir_investimento(inv)

def gerenciar_bancos():
    st.title("🏦 BANCOS E LOCAIS")
    st.caption("CADASTRE OS BANCOS QUE PODERÃO SER SELECIONADOS NAS ENTRADAS, SAÍDAS E INVESTIMENTOS.")
    bancos = carregar_bancos(user)
    st.write("**BANCOS DISPONÍVEIS:** " + " · ".join(bancos))
    with st.form("adicionar_banco_form", clear_on_submit=True):
        novo = st.text_input("NOME DO BANCO OU LOCAL")
        salvar = st.form_submit_button("➕ ADICIONAR BANCO")
    if salvar:
        novo = maiusculas(novo)
        if not novo: st.warning("DIGITE O NOME DO BANCO.")
        elif novo in bancos: st.info("ESSE BANCO JÁ ESTÁ NA LISTA.")
        else:
            try:
                supabase.table("bancos").upsert({"usuario":user,"nome":novo}, on_conflict="usuario,nome").execute()
                st.success("BANCO ADICIONADO.")
                st.rerun()
            except Exception as erro: st.error(f"ERRO AO ADICIONAR BANCO. EXECUTE O SQL DE ATUALIZAÇÃO: {erro}")


# LOGIN
if "user" not in st.session_state:
    st.title("🔐 Sistema Financeiro 💰")
    usuario_login = st.text_input("👤 Usuário")
    if st.button("🚀 Entrar"):
        if usuario_login.strip():
            st.session_state.user = usuario_login.strip()
            st.session_state.page = "dashboard"
            st.rerun()
        else:
            st.warning("Informe um usuário.")
    st.stop()

user = st.session_state.user
if "page" not in st.session_state:
    st.session_state.page = "dashboard"

df = carregar_financeiro(user)
df_emp = carregar_emprestimos(user)

# MENU
st.sidebar.title("📌 MENU")
st.sidebar.caption(f"👤 {user}")
menus = [("🏠 DASHBOARD 📊","dashboard"),("➕ ENTRADA 💚","entrada"),("➖ SAÍDA 🔴","saida"),("💳 EMPRÉSTIMOS","emprestimos"),("📈 INVESTIMENTOS","investimentos"),("🏦 BANCOS / LOCAIS","bancos"),("📊 GRÁFICOS 📈","graficos"),("📋 HISTÓRICO 📁","historico")]
for rotulo,pagina in menus:
    if st.sidebar.button(rotulo, use_container_width=True):
        st.session_state.page = pagina
        st.rerun()
st.sidebar.divider()
if st.sidebar.button("🚪 Sair", use_container_width=True):
    st.session_state.clear()
    st.rerun()


def dashboard():
    st.title("📊 Dashboard Financeiro")
    dados = filtro_periodo(df, "dashboard")
    resumo(dados)
    if dados.empty:
        st.info("Nenhuma movimentação encontrada no período.")
        return
    c1,c2 = st.columns(2)
    with c1:
        por_tipo = dados.groupby("tipo")["valor"].sum().reset_index()
        fig = px.bar(por_tipo, x="tipo", y="valor", title="Entradas e saídas", text_auto=".2s")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        cat = dados[dados["tipo"]=="Saída"].groupby("categoria", dropna=False)["valor"].sum().reset_index()
        if cat.empty:
            st.info("Sem saídas no período.")
        else:
            cat["categoria"] = cat["categoria"].fillna("Sem categoria")
            fig = px.pie(cat, names="categoria", values="valor", title="Saídas por categoria", hole=.45)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)


def entrada():
    st.title("💚 Entrada de Dinheiro")
    resumo(df)
    tab1,tab2 = st.tabs(["➕ Nova entrada","✏️ Editar / 🗑️ Excluir"])
    with tab1:
        with st.form("nova_entrada", clear_on_submit=True):
            data_mov = st.date_input("📅 DATA", date.today(), key="entrada_data")
            conta = st.selectbox("🏦 CONTA ONDE O DINHEIRO ENTROU", carregar_bancos(user), key="entrada_conta")
            referente = st.text_input("📝 DESCRIÇÃO", key="entrada_ref")
            valor = st.number_input("💰 Valor", min_value=0.0, step=0.01, key="entrada_valor")
            salvar = st.form_submit_button("💾 Salvar Entrada")
        if salvar:
            if not referente.strip() or valor <= 0:
                st.warning("Preencha a descrição e informe um valor maior que zero.")
            else:
                try:
                    supabase.table("financeiro").insert({"usuario":user,"data":data_mov.isoformat(),"tipo":"Entrada","referente":maiusculas(referente),"valor":float(valor),"categoria":None,"conta":maiusculas(conta),"mes":data_mov.strftime("%Y-%m")}).execute()
                    st.success("Entrada registrada.")
                    st.rerun()
                except Exception as erro:
                    st.error(f"Erro ao salvar: {erro}")
    with tab2:
        editar_excluir_movimentacao(df, "Entrada", "entrada")


def saida():
    st.title("🔴 Saída de Dinheiro")
    resumo(df)
    tab1,tab2 = st.tabs(["➖ Nova saída","✏️ Editar / 🗑️ Excluir"])
    with tab1:
        with st.form("nova_saida", clear_on_submit=True):
            data_mov = st.date_input("📅 DATA", date.today(), key="saida_data")
            conta = st.selectbox("🏦 CONTA DE ONDE O DINHEIRO SAIU", carregar_bancos(user), key="saida_conta")
            cat_base = st.selectbox("🏷️ Categoria", ["🍔 Alimentação","🚌 Transporte","🏠 Casa","🎮 Lazer","Outros"], key="saida_cat")
            cat_outros = st.text_input("✏️ Digite a categoria", key="saida_outros") if cat_base=="Outros" else ""
            referente = st.text_input("📝 Descrição", key="saida_ref")
            valor = st.number_input("💰 Valor", min_value=0.0, step=0.01, key="saida_valor")
            salvar = st.form_submit_button("💾 Salvar Saída")
        if salvar:
            categoria = cat_outros.strip() if cat_base=="Outros" else cat_base
            if not categoria or not referente.strip() or valor <= 0:
                st.warning("Preencha categoria, descrição e valor.")
            else:
                try:
                    supabase.table("financeiro").insert({"usuario":user,"data":data_mov.isoformat(),"tipo":"Saída","referente":maiusculas(referente),"valor":float(valor),"categoria":maiusculas(categoria),"conta":maiusculas(conta),"mes":data_mov.strftime("%Y-%m")}).execute()
                    st.success("Saída registrada.")
                    st.rerun()
                except Exception as erro:
                    st.error(f"Erro ao salvar: {erro}")
    with tab2:
        editar_excluir_movimentacao(df, "Saída", "saida")


def emprestimos():
    st.title("💳 Empréstimos")
    resumo(df)
    tab1,tab2 = st.tabs(["➕ Novo empréstimo","📋 Lista e controle"])
    with tab1:
        with st.form("novo_emprestimo", clear_on_submit=True):
            c1,c2 = st.columns(2)
            with c1:
                banco = st.text_input("🏦 Banco ou instituição")
                tipo = st.selectbox("📌 Tipo", ["Empréstimo CLT","Consignado","Pessoal","Antecipação FGTS","Cartão","Outro"])
                valor_total = st.number_input("💰 Valor total contratado", min_value=0.0, step=0.01)
                quantidade = st.number_input("🔢 Quantidade de parcelas", min_value=1, value=1, step=1)
            with c2:
                valor_parcela = st.number_input("💵 Valor da parcela", min_value=0.0, step=0.01)
                parcelas_pagas = st.number_input("✅ Parcelas já pagas", min_value=0, max_value=int(quantidade), value=0, step=1)
                data_contratacao = st.date_input("📅 Data da contratação", date.today())
                finalidade = st.text_input("🎯 PARA QUE FOI FEITO O EMPRÉSTIMO")
                parcelas_restantes_manual = st.number_input("⏳ PARCELAS RESTANTES (PREENCHIMENTO MANUAL)", min_value=0, value=max(int(quantidade)-int(parcelas_pagas),0), step=1)
                observacao = st.text_area("📝 OBSERVAÇÃO")
            salvar = st.form_submit_button("💾 Salvar empréstimo")
        if salvar:
            if not banco.strip() or valor_total<=0 or valor_parcela<=0:
                st.warning("Preencha banco, valor total e valor da parcela.")
            else:
                try:
                    supabase.table("emprestimos").insert({"usuario":user,"banco":maiusculas(banco),"tipo":maiusculas(tipo),"valor_total":float(valor_total),"quantidade_parcelas":int(quantidade),"valor_parcela":float(valor_parcela),"parcelas_pagas":int(parcelas_pagas),"data_contratacao":data_contratacao.isoformat(),"observacao":maiusculas(observacao),"finalidade":maiusculas(finalidade),"parcelas_restantes":int(parcelas_restantes_manual)}).execute()
                    st.success("Empréstimo cadastrado.")
                    st.rerun()
                except Exception as erro:
                    st.error(f"Erro ao salvar empréstimo: {erro}")
    with tab2:
        if df_emp.empty:
            st.info("Nenhum empréstimo cadastrado. Caso a tabela ainda não exista, execute o SQL fornecido.")
            return
        total_contratado = df_emp["valor_total"].sum()
        total_pago = (df_emp["parcelas_pagas"]*df_emp["valor_parcela"]).sum()
        total_parcelas = df_emp["quantidade_parcelas"].sum()
        total_pagas = df_emp["parcelas_pagas"].sum()
        saldo_devedor = max(total_contratado-total_pago,0)
        restantes_total = max(total_parcelas-total_pagas,0)
        a,b,c,d = st.columns(4)
        a.metric("💰 Total contratado", moeda(total_contratado))
        b.metric("✅ Total pago", moeda(total_pago))
        c.metric("📉 Saldo devedor", moeda(saldo_devedor))
        d.metric("⏳ Parcelas restantes", int(restantes_total))
        st.divider()
        for _,emp in df_emp.iterrows():
            qtd = int(emp["quantidade_parcelas"])
            pagas = min(int(emp["parcelas_pagas"]),qtd)
            restantes = max(qtd-pagas,0)
            pago = min(pagas*float(emp["valor_parcela"]),float(emp["valor_total"]))
            saldo = max(float(emp["valor_total"])-pago,0)
            percentual = pagas/qtd if qtd else 0
            status = "✅ Quitado" if restantes==0 else "🟡 Ativo"
            st.markdown(f"<div class='loan-card'><h3>🏦 {emp['banco']} — {emp['tipo']}</h3><p><b>Status:</b> {status}<br><b>Finalidade:</b> {maiusculas(emp.get('finalidade'))}<br><b>Valor contratado:</b> {moeda(emp['valor_total'])}<br><b>Valor da parcela:</b> {moeda(emp['valor_parcela'])}<br><b>Parcelas pagas:</b> {pagas} de {qtd}<br><b>Parcelas restantes:</b> {int(emp.get('parcelas_restantes')) if pd.notna(emp.get('parcelas_restantes')) else restantes}<br><b>Saldo devedor:</b> {moeda(saldo)}</p></div>", unsafe_allow_html=True)
            st.progress(min(max(percentual,0.0),1.0))
            c1,c2 = st.columns(2)
            with c1:
                if st.button("✅ Marcar próxima parcela paga", disabled=pagas>=qtd, key=f"pagar_{emp['id']}", use_container_width=True):
                    atualizar_emprestimo(emp["id"], {"parcelas_pagas":pagas+1})
                    st.rerun()
            with c2:
                if st.button("↩️ Desfazer última parcela", disabled=pagas<=0, key=f"desfazer_{emp['id']}", use_container_width=True):
                    atualizar_emprestimo(emp["id"], {"parcelas_pagas":pagas-1})
                    st.rerun()
            with st.expander("✏️ Editar ou 🗑️ excluir"):
                data_original = emp["data_contratacao"].date() if pd.notna(emp["data_contratacao"]) else date.today()
                with st.form(f"editar_emp_{emp['id']}"):
                    banco_e = st.text_input("🏦 Banco", value=str(emp["banco"] or ""), key=f"banco_{emp['id']}")
                    tipo_e = st.text_input("📌 Tipo", value=str(emp["tipo"] or ""), key=f"tipo_{emp['id']}")
                    valor_total_e = st.number_input("💰 Valor total", min_value=0.0, value=float(emp["valor_total"]), step=0.01, key=f"vt_{emp['id']}")
                    qtd_e = st.number_input("🔢 Quantidade de parcelas", min_value=1, value=qtd, step=1, key=f"qtd_{emp['id']}")
                    valor_parcela_e = st.number_input("💵 Valor da parcela", min_value=0.0, value=float(emp["valor_parcela"]), step=0.01, key=f"vp_{emp['id']}")
                    pagas_e = st.number_input("✅ Parcelas pagas", min_value=0, max_value=int(qtd_e), value=min(pagas,int(qtd_e)), step=1, key=f"pg_{emp['id']}")
                    data_e = st.date_input("📅 Data da contratação", data_original, key=f"dt_{emp['id']}")
                    finalidade_e = st.text_input("🎯 PARA QUE FOI FEITO O EMPRÉSTIMO", value=maiusculas(emp.get("finalidade")), key=f"finalidade_{emp['id']}")
                    restantes_e = st.number_input("⏳ PARCELAS RESTANTES (PREENCHIMENTO MANUAL)", min_value=0, value=int(emp.get("parcelas_restantes") if pd.notna(emp.get("parcelas_restantes")) else max(qtd-pagas,0)), step=1, key=f"restantes_{emp['id']}")
                    obs_e = st.text_area("📝 OBSERVAÇÃO", value=maiusculas(emp["observacao"]), key=f"obs_{emp['id']}")
                    salvar_e = st.form_submit_button("💾 Salvar alterações")
                if salvar_e:
                    if not banco_e.strip() or valor_total_e<=0 or valor_parcela_e<=0:
                        st.warning("Preencha os campos obrigatórios.")
                    else:
                        atualizar_emprestimo(emp["id"], {"banco":maiusculas(banco_e),"tipo":maiusculas(tipo_e),"valor_total":float(valor_total_e),"quantidade_parcelas":int(qtd_e),"valor_parcela":float(valor_parcela_e),"parcelas_pagas":int(pagas_e),"data_contratacao":data_e.isoformat(),"observacao":maiusculas(obs_e),"finalidade":maiusculas(finalidade_e),"parcelas_restantes":int(restantes_e)})
                        st.success("Empréstimo atualizado.")
                        st.rerun()
                confirmar = st.checkbox("Confirmo a exclusão deste empréstimo.", key=f"confirmar_emp_{emp['id']}")
                if st.button("🗑️ Excluir empréstimo", disabled=not confirmar, key=f"excluir_emp_{emp['id']}"):
                    excluir_emprestimo(emp["id"])
                    st.rerun()
            st.divider()


def graficos():
    st.title("📈 Gráficos Financeiros")
    dados = filtro_periodo(df, "graficos")
    resumo(dados)
    if dados.empty:
        st.info("Sem dados no período.")
        return
    cat = dados[dados["tipo"]=="Saída"].groupby("categoria", dropna=False)["valor"].sum().reset_index()
    if not cat.empty:
        cat["categoria"] = cat["categoria"].fillna("Sem categoria")
        fig = px.pie(cat, names="categoria", values="valor", title="Distribuição das saídas", hole=.4)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    diario = dados.groupby(["data","tipo"])["valor"].sum().reset_index().sort_values("data")
    if not diario.empty:
        fig = px.line(diario, x="data", y="valor", color="tipo", markers=True, title="Evolução no período")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)


def historico():
    st.title("📁 Histórico Financeiro")
    dados = filtro_periodo(df, "historico")
    resumo(dados)
    if dados.empty:
        st.info("Nenhuma movimentação encontrada.")
        return
    tipo_filtro = st.radio("🔎 TIPO", ["TODOS","SOMENTE ENTRADAS","SOMENTE SAÍDAS"], horizontal=True)
    exibicao = dados.copy()
    if tipo_filtro=="SOMENTE ENTRADAS":
        exibicao = exibicao[exibicao["tipo"]=="Entrada"]
    elif tipo_filtro=="SOMENTE SAÍDAS":
        exibicao = exibicao[exibicao["tipo"]=="Saída"]
    contas_hist = ["TODOS"] + carregar_bancos(user)
    conta_filtro = st.selectbox("🏦 BANCO / LOCAL", contas_hist, key="historico_conta")
    if conta_filtro != "TODOS":
        exibicao = exibicao[exibicao["conta"].fillna("").str.upper() == conta_filtro]
    pesquisa = st.text_input("🔍 PESQUISAR DESCRIÇÃO OU CATEGORIA")
    if pesquisa.strip():
        termo = pesquisa.strip().lower()
        exibicao = exibicao[exibicao["referente"].fillna("").str.lower().str.contains(termo,regex=False) | exibicao["categoria"].fillna("").str.lower().str.contains(termo,regex=False)]
    view = exibicao.copy()
    view["data"] = view["data"].dt.strftime("%d/%m/%Y")
    view["valor"] = view["valor"].apply(moeda)
    for coluna in ["tipo", "categoria", "referente", "conta"]:
        if coluna in view.columns: view[coluna] = view[coluna].fillna("").astype(str).str.upper()
    st.dataframe(view[["id","data","tipo","conta","categoria","referente","valor"]], use_container_width=True, hide_index=True)


if st.session_state.page=="dashboard":
    dashboard()
elif st.session_state.page=="entrada":
    entrada()
elif st.session_state.page=="saida":
    saida()
elif st.session_state.page=="emprestimos":
    emprestimos()
elif st.session_state.page=="investimentos":
    investimentos()
elif st.session_state.page=="bancos":
    gerenciar_bancos()
elif st.session_state.page=="graficos":
    graficos()
elif st.session_state.page=="historico":
    historico()
