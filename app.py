# step1_minimal_app.py
import pandas as pd
import streamlit as st

# --- Load Data ---
sheet_id = '1bK5u9n545BxNfXQeE4yC8gr0xF57ORDyfTecpr7sscE'
xls = pd.ExcelFile(f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx")

df_wl = pd.read_excel(xls, 'library', header=0)
df_cl = pd.read_excel(xls, 'change log', header=0)
df_cl['Change_Date'] = pd.to_datetime(df_cl['Change_Date'])

# Mark active records
df_wl['Active_Storage_Record'] = 'Yes'
inactive_ids = df_cl['Entry_Record_ID'].unique()
df_wl.loc[df_wl['Entry_Record_ID'].isin(inactive_ids), 'Active_Storage_Record'] = 'No'

# Keep active bottles
df_wl_act = df_wl[df_wl['Active_Storage_Record'] == 'Yes'].copy()
df_cl_act = df_cl[df_cl['Active_Storage_Record'] == 'Yes'].copy()
curr_lib = pd.concat([df_wl_act, df_cl_act], ignore_index=True)

# --- Streamlit App ---
st.set_page_config(page_title="Wine Cellar Explorer - Step 1", layout="wide")
st.title("🍷 Wine Cellar Explorer - Step 1")

# --- Simple Filter ---
if "producer_filter" not in st.session_state:
    st.session_state["producer_filter"] = "All"

producer = st.selectbox(
    "Filter by Producer",
    ["All"] + sorted(curr_lib["Producer"].dropna().unique()),
    key="producer_filter"
)

# --- Reset Filters Button ---
if st.button("🔄 Reset Filters"):
    st.session_state["producer_filter"] = "All"

# --- Apply Filter ---
filtered = curr_lib.copy()
if producer != "All":
    filtered = filtered[filtered["Producer"] == producer]

# --- Display Table ---
st.subheader(f"Results ({len(filtered)} records)")
st.dataframe(filtered, use_container_width=True)

