# app.py
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import io
import textwrap

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

# If Terroir column does not exist, create a placeholder so UI doesn't break
if 'Terroir' not in curr_lib.columns:
    curr_lib['Terroir'] = 'Unknown'

# --- Streamlit Config ---
st.set_page_config(page_title="Wine Cellar Explorer", layout="wide")
st.title("🍷 Wine Cellar Explorer")

# --- Chart Color Palette (cool, subtle) ---
palette = {
    "primary": "#7fb3d5",   # cool blue
    "accent": "#567892",    # darker slate
    "line": "#9fc7e6",
    "bg": "#ffffff"
}

# --- Session State Defaults with Reset Callback ---
default_filters = {
    "quick_magnums": False,
    "favorite_producer": "None",
    "producer": "All",
    "vintage": "All",
    "location": "All",
    "varietal": "All",
    "terroir": "All",
    "decade": "All",
    "selected_fridge": "All",
    "selected_shelf": "All"
}

for key, default in default_filters.items():
    if key not in st.session_state:
        st.session_state[key] = default

def reset_filters():
    for key, default in default_filters.items():
        st.session_state[key] = default

st.sidebar.button("🔄 Reset Filters", on_click=reset_filters)

# --- Sidebar Quick Queries ---
st.sidebar.header("⚡ Quick Queries")
st.sidebar.checkbox("Magnums only", key="quick_magnums")
st.sidebar.selectbox(
    "Favorite producers",
    ["None", "Clos du Val", "Corison", "Heitz Cellars", "Williams Selyem", "A. Rafanelli"],
    key="favorite_producer"
)

# --- Main Filters in 3 Columns ---
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

if st.session_state["quick_magnums"]:
    filtered = filtered[filtered["Notes"] == "Magnum"]
if st.session_state["favorite_producer"] != "None":
    filtered = filtered[filtered["Producer"] == st.session_state["favorite_producer"]]

for key, col in zip(
    ["producer","vintage","location","varietal","decade","terroir"],
    ["Producer","Vintage","Location","Varietal","Decade","Terroir"]
):
    val = st.session_state[key]
    if val != "All":
        filtered = filtered[filtered[col] == val]

# --- Results (collapsible) ---
with st.expander("📋 Query Results", expanded=True):
    st.markdown(f"**{len(filtered)} records · {int(filtered['Bottles'].sum())} bottles total**")
    st.dataframe(filtered.sort_values(by=["Producer", "Vintage"]), use_container_width=True)

    # Excel export for overall results
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

# --- Summary Views (collapsible with tabs) ---
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
        # Decade bar chart
        if not dec_summary.empty:
            fig, ax = plt.subplots(figsize=(8,3))
            ax.bar(dec_summary['Decade'].astype(str), dec_summary['Bottles'], color=palette["primary"])
            ax.set_xlabel("Decade")
            ax.set_ylabel("Bottles")
            ax.set_title("Bottles by Decade")
            st.pyplot(fig)

    with tab4:
        vint_summary = filtered.groupby("Vintage")["Bottles"].sum().reset_index().sort_values("Vintage")
        st.write(vint_summary)
        # Vintage line chart
        if not vint_summary.empty:
            fig, ax = plt.subplots(figsize=(10,3))
            ax.plot(vint_summary["Vintage"], vint_summary["Bottles"], marker="o", color=palette["line"])
            ax.set_xlabel("Vintage")
            ax.set_ylabel("Bottles")
            ax.set_title("Bottles by Vintage")
            st.pyplot(fig)

# --- Fridge & Shelf ---
with st.expander("🧊 Fridge Summary by Row", expanded=True):
    fridges_only = [loc for loc in curr_lib["Location"].dropna().unique() if "Fridge" in loc]
    selected_fridge = st.selectbox("Select a fridge location", ["All"] + sorted(fridges_only), key="selected_fridge")
    fridge_data = curr_lib[curr_lib["Location"].isin(fridges_only)]
    if selected_fridge != "All":
        fridge_data = fridge_data[fridge_data["Location"] == selected_fridge]

    fridge_summary = fridge_data.groupby(["Location","Box_Shelf_Number"])["Bottles"].sum().reset_index().sort_values(["Location","Box_Shelf_Number"])
    st.dataframe(fridge_summary, use_container_width=True)
    st.markdown(f"**Total bottles in selection:** {fridge_data['Bottles'].sum()}")

with st.expander("🔍 Shelf Details", expanded=True):
    available_shelves = sorted(fridge_data['Box_Shelf_Number'].dropna().unique())
    selected_shelf = st.selectbox("Select a shelf (row number)", ["All"] + [str(int(s)) for s in available_shelves], key="selected_shelf")
    
    if selected_shelf != "All":
        shelf_data = fridge_data[fridge_data['Box_Shelf_Number'] == int(selected_shelf)]
    else:
        shelf_data = fridge_data.copy()
    
    shelf_data = shelf_data.sort_values(by=['Producer','Vintage','Varietal'])
    st.dataframe(
        shelf_data[['Producer','Varietal','Vintage','Bottles','Notes','Entry_Record_ID']],
        use_container_width=True
    )
    st.markdown(f"**Bottles shown:** {shelf_data['Bottles'].sum()}")

    # Excel export for shelf
    output_shelf = io.BytesIO()
    with pd.ExcelWriter(output_shelf, engine="xlsxwriter") as writer:
        shelf_data.to_excel(writer, sheet_name="Shelf Details", index=False)
    output_shelf.seek(0)
    st.download_button(
        label="📥 Download Shelf Details as Excel",
        data=output_shelf,
        file_name="shelf_details.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
