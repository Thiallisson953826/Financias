import streamlit as st
from supabase import create_client

st.title("TESTE SUPABASE")

url = "https://nwloxhyzvijnimmtevry.supabase.co"
key = st.secrets["SUPABASE_KEY"]

supabase = create_client(url, key)

resp = supabase.table("financeiro").select("id").execute()

st.write(resp)
