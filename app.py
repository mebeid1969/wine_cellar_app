# app.py
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import io

# --- Load Data ---
sheet_id = '1bK5u9n545BxNfXQeE4yC8gr0xF57ORDyfTecpr7sscE'
xls = pd.ExcelFile(f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx")

df_wl = pd.read_excel(xls, 'library', header=0)
df_cl = pd.read_excel(xls, 'change log', header=0)
df_cl['Change_Date'] = pd.to_datetime(df_cl['Change_Date'])

# Add active flag
df_wl['Active_Storage_Record'] = 'Yes'

# Add decades
bins = [1970, 1980, 1990, 2000, 2010, 2020, 2030]
labels = ['1970s', '1980s', '1990s', '2000s', '2010s', '2020s']
df_wl['Decade'] = pd.cut(df_wl['Vintage'], bins=bins, labels=labels, right=False)

# Mark inactive records
entry_record_ids_to_update = df_cl['Entry_Record_ID'].unique()
df_wl.loc[df_wl['Entry_Record_ID'].isin(entry_record_ids_to_update), 'Active_Storage_Record'] = 'No'

# Keep active bottles only
df_wl_act = df_wl[df_wl['Active_Storage_Record'] == 'Yes'].copy()
df_cl = df_cl.sort_values('Change_Date', ascending=False).drop_duplicates(subset='Entry_Record_ID', keep='first')
columns_to_drop = ["Change_Date", "Change", "Consumption_Notes"]
df_cl_act = df_cl[df_cl['Active_Storage_Record'] == 'Yes'].drop(columns=columns_to_drop).copy()

curr_lib = pd.concat([df_wl_act, df_cl_act], ignore_index=True)

# Ensure Terroir column exists
if 'Terroir' not in curr_lib.columns:
    curr_lib['Terroir'] = 'Unknown'

# --- Streamlit UI ---
st.set_page_config(page_title="Wine Cellar Explorer", layout="wide")

# Initialize session_state keys
if "reset_trigger" not in st.session_state:
    st.session_state["reset_trigger"] = False
if "quick_magnums" not in st.session_state:
    st.session_state["quick_magnums"] = False
if "favorite_producer" not in st.session_state:
    st.session_state["favorite_producer"] = "None"
if "theme_toggle" not in st.session_state:
    st.session_state["theme_toggle"] = False

# --- Sidebar Settings ---
st.sidebar.header("⚙️ Settings")
theme_toggle = st.sidebar.toggle("🌙 Dark mode", value=st.session_state["theme_toggle"])
st.session_state["theme_toggle"] = theme_toggle
theme_name = "dark" if theme_toggle else "light"

# Inject theme CSS
def inject_theme_css(theme_name: str):
    if theme_name == "dark":
        bg_main = "#07101a"
        bg_panel = "#0f1724"
        text_color = "#E6EEF5"
        muted_text = "#B6C6D6"
    else:
        bg_main = "#ffffff"
        bg_panel = "#f8fafc"
        text_color = "#0b1220"
        muted_text = "#475569"
    css = f"""
    <style>
    .stApp {{ background-color: {bg_main}; color: {text_color}; }}
    .css-1d391kg, .css-1v3fvcr {{ background-color: {bg_panel} !important; }}
    .stDataFrame th {{ color: {text_color} !important; }}
    .muted {{ color: {muted_text}; }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
inject_theme_css(theme_name)

# Chart color palette
palette = {"line": "#9fc7e6" if theme_name == "dark" else "#1f77b4"}

# --- Sidebar Quick Queries ---
st.sidebar.header("⚡ Quick Queries")
quick_magnums = st.sidebar.checkbox("Magnums only", key="quick_magnums")
favorite_producer = st.sidebar.selectbox(
    "Favorite producers",
    ["None", "Clos du Val", "Corison", "Heitz Cellars", "Williams Selyem", "A. Rafanelli"],
    key="favorite_producer"
)

# --- Reset Filters Button (safe) ---
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Reset Filters"):
    st.session_state["reset_trigger"] = True
    st.experimental_rerun()

# Apply reset trigger
if st.session_state["reset_trigger"]:
    st.session_state["quick_magnums"] = False
    st.session_state["favorite_producer"] = "None"
    st.session_state["reset_trigger"] = False

# --- Main Filters ---
st.title("🍷 Wine Cellar Explorer")
with st.expander("🔍 Main Filters", expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        producer = st.selectbox("Producer", ["All"] + sorted(curr_lib["Producer"].dropna().unique()), key="producer")
        vintage = st.selectbox("Vintage", ["All"] + sorted(curr_lib["Vintage"].dropna().unique()), key="vintage")
    with col2:
        location = st.selectbox("Location", ["All"] + sorted(curr_lib["Location"].dropna().unique()), key="location")
        varietal = st.selectbox("Varietal", ["All"] + sorted(curr_lib["Varietal"].dropna().unique()), key="varietal")
    with col3:
        terroir = st.selectbox("Terroir", ["All"] + sorted(curr_lib["Terroir"].dropna().unique()), key="terroir")
        decade = st.selectbox("Decade", ["All"] + sorted(curr_lib["Decade"].dropna().unique()), key="decade")

# --- Apply Filters ---
filtered = curr_lib.copy()
if quick_magnums:
    filtered = filtered[filtered["Notes"] == "Magnum"]
if favorite_producer != "None":
    filtered = filtered[filtered["Producer"] == favorite_producer]
if producer != "All":
    filtered = filtered[filtered["Producer"] == producer]
if vintage != "All":
    filtered = filtered[filtered["Vintage"] == vintage]
if location != "All":
    filtered = filtered[filtered["Location"] == location]
if varietal != "All":
    filtered = filtered[filtered["Varietal"] == varietal]
if terroir != "All":
    filtered = filtered[filtered["Terroir"] == terroir]
if decade != "All":
    filtered = filtered[filtered["Decade"] == decade]

# --- Query Results ---
with st.expander("📋 Query Results", expanded=True):
    st.markdown(f"**{len(filtered)} records · {int(filtered['Bottles'].sum())} bottles total**")
    st.dataframe(filtered.sort_values(by=["Producer", "Vintage"]), use_container_width=True)

    # Excel export
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        filtered.to_excel(writer, sheet_name="Results", index=False)
        summary = filtered.groupby("Producer").agg({"Bottles": "sum"}).reset_index()
        summary.to_excel(writer, sheet_name="By Producer", index=False)
    output.seek(0)
    st.download_button(
        label="📊 Download results as Excel",
        data=output,
        file_name="wine_query_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# --- Summary Views (tables only) ---
with st.expander("📊 Summary Views", expanded=False):
    tab1, tab2, tab3, tab4 = st.tabs(["By Location", "By Producer", "By Decade", "By Vintage"])
    with tab1:
        loc_summary = filtered.groupby("Location")["Bottles"].sum().reset_index()
        st.write(loc_summary)
    with tab2:
        prod_summary = filtered.groupby("Producer")["Bottles"].sum().reset_index()
        st.write(prod_summary)
    with tab3:
        dec_summary = filtered.groupby("Decade")["Bottles"].sum().reset_index()
        st.write(dec_summary)
    with tab4:
        vint_summary = filtered.groupby("Vintage")["Bottles"].sum().reset_index().sort_values("Vintage")
        st.write(vint_summary)
        if not vint_summary.empty:
            fig, ax = plt.subplots(figsize=(10,3))
            ax.plot(vint_summary["Vintage"], vint_summary["Bottles"], marker="o", color=palette["line"])
            ax.set_xlabel("Vintage")
            ax.set_ylabel("Bottles")
            ax.set_title("Bottles by Vintage")
            st.pyplot(fig)

# --- Fridge Summary ---
st.header("🧊 Fridge Summary by Row")
fridge_options = sorted(curr_lib['Location'].dropna().unique())
selected_fridge = st.selectbox("Select a fridge location", ["All"] + fridge_options, key="selected_fridge")
if selected_fridge != "All":
    fridge_data = curr_lib[curr_lib['Location'] == selected_fridge]
else:
    fridge_data = curr_lib[curr_lib['Location'].isin([
        'Basement Fridge Left', 'Basement Fridge Right', 'Waiter Fridge'
    ])]

fridge_summary = (
    fridge_data.groupby(['Location', 'Box_Shelf_Number'])
    .agg({'Bottles': 'sum'})
    .reset_index()
    .sort_values(['Location', 'Box_Shelf_Number'])
)
st.dataframe(fridge_summary, use_container_width=True)
st.markdown(f"**Total bottles in selection:** {int(fridge_data['Bottles'].sum())}")

# --- Select Specific Shelf ---
st.subheader("Shelf Details")
available_shelves = sorted(fridge_data['Box_Shelf_Number'].dropna().unique())
selected_shelf = st.selectbox("Select a shelf (row number)", ["All"] + [str(int(s)) for s in available_shelves], key="selected_shelf")
if selected_shelf != "All":
    shelf_data = fridge_data[fridge_data['Box_Shelf_Number'] == int(selected_shelf)]
else:
    shelf_data = fridge_data.copy()
shelf_data = shelf_data.sort_values(by=['Producer', 'Vintage', 'Varietal'])
st.dataframe(
    shelf_data[['Producer', 'Varietal', 'Vintage', 'Bottles', 'Notes', 'Entry_Record_ID']],
    use_container_width=True
)
st.markdown(f"**Bottles shown:** {int(shelf_data['Bottles'].sum())}")

# Excel export for shelf
output_shelf = io.BytesIO()
with pd.ExcelWriter(output_shelf, engine="xlsxwriter") as writer:
    shelf_data.to_excel(writer, sheet_name="Shelf Details", index=False)
output_shelf.seek(0)
st.download_button(
    label="📊 Download Shelf Details as Excel",
    data=output_shelf,
    file_name="shelf_details.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
