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

# Add Decade column
bins = [1970, 1980, 1990, 2000, 2010, 2020, 2030]
labels = ['1970s', '1980s', '1990s', '2000s', '2010s', '2020s']
curr_lib['Decade'] = pd.cut(curr_lib['Vintage'], bins=bins, labels=labels, right=False)

# --- Streamlit App ---
st.set_page_config(page_title="Wine Cellar Explorer - Step 3", layout="wide")
st.title("🍷 Wine Cellar Explorer - Step 3")

# --- Initialize session_state defaults ---
default_filters = {
    "producer": "All",
    "vintage": "All",
    "location": "All",
    "varietal": "All",
    "decade": "All",
    "terroir": "All",
    "quick_magnums": False,
    "favorite_producer": "None"
}

for key, default in default_filters.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- Callback function for Reset Filters ---
def reset_filters():
    for key, default in default_filters.items():
        st.session_state[key] = default

# --- Sidebar Quick Queries ---
st.sidebar.header("⚡ Quick Queries")
st.sidebar.checkbox("Magnums only", key="quick_magnums")
st.sidebar.selectbox(
    "Favorite producer",
    ["None"] + sorted(curr_lib["Producer"].dropna().unique()),
    key="favorite_producer"
)

# --- Main Filters ---
producer = st.selectbox("Producer", ["All"] + sorted(curr_lib["Producer"].dropna().unique()), key="producer")
vintage = st.selectbox("Vintage", ["All"] + sorted(curr_lib["Vintage"].dropna().unique()), key="vintage")
location = st.selectbox("Location", ["All"] + sorted(curr_lib["Location"].dropna().unique()), key="location")
varietal = st.selectbox("Varietal", ["All"] + sorted(curr_lib["Varietal"].dropna().unique()), key="varietal")
decade = st.selectbox("Decade", ["All"] + sorted(curr_lib["Decade"].dropna().unique()), key="decade")
terroir = st.selectbox("Terroir", ["All"] + sorted(curr_lib["Terroir"].dropna().unique()), key="terroir")

# --- Reset Filters Button ---
st.button("🔄 Reset Filters", on_click=reset_filters)

# --- Apply Filters ---
filtered = curr_lib.copy()

# Quick Queries
if st.session_state["quick_magnums"]:
    filtered = filtered[filtered["Notes"] == "Magnum"]

if st.session_state["favorite_producer"] != "None":
    filtered = filtered[filtered["Producer"] == st.session_state["favorite_producer"]]

# Main Filters
if st.session_state["producer"] != "All":
    filtered = filtered[filtered["Producer"] == st.session_state["producer"]]
if st.session_state["vintage"] != "All":
    filtered = filtered[filtered["Vintage"] == st.session_state["vintage"]]
if st.session_state["location"] != "All":
    filtered = filtered[filtered["Location"] == st.session_state["location"]]
if st.session_state["varietal"] != "All":
    filtered = filtered[filtered["Varietal"] == st.session_state["varietal"]]
if st.session_state["decade"] != "All":
    filtered = filtered[filtered["Decade"] == st.session_state["decade"]]
if st.session_state["terroir"] != "All":
    filtered = filtered[filtered["Terroir"] == st.session_state["terroir"]]

# --- Display Table ---
st.subheader(f"Results ({len(filtered)} records)")
st.dataframe(filtered, use_container_width=True)
