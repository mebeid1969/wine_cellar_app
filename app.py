# app.py
import pandas as pd
import streamlit as st
import io
import matplotlib.pyplot as plt

# --- Load Data ---
sheet_id = '1bK5u9n545BxNfXQeE4yC8gr0xF57ORDyfTecpr7sscE'
xls = pd.ExcelFile(f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx")

df_wl = pd.read_excel(xls, 'library', header=0)
df_cl = pd.read_excel(xls, 'change log', header=0)
df_cl['Change_Date'] = pd.to_datetime(df_cl['Change_Date'])

# --- Data Prep ---
df_wl['Active_Storage_Record'] = 'Yes'
inactive_ids = df_cl['Entry_Record_ID'].unique()
df_wl.loc[df_wl['Entry_Record_ID'].isin(inactive_ids), 'Active_Storage_Record'] = 'No'

df_wl_act = df_wl[df_wl['Active_Storage_Record'] == 'Yes'].copy()
df_cl_act = df_cl[df_cl['Active_Storage_Record'] == 'Yes'].copy()
curr_lib = pd.concat([df_wl_act, df_cl_act], ignore_index=True)

bins = [1970, 1980, 1990, 2000, 2010, 2020, 2030]
labels = ['1970s', '1980s', '1990s', '2000s', '2010s', '2020s']
curr_lib['Decade'] = pd.cut(curr_lib['Vintage'], bins=bins, labels=labels, right=False)

# --- Streamlit Config ---
st.set_page_config(page_title="Wine Cellar Explorer", layout="wide")
st.title("🍷 Wine Cellar Explorer")

# --- Sidebar: Theme Toggle ---
st.sidebar.header("⚙ Settings")
theme_choice = st.sidebar.radio("Theme", ["Light", "Dark"], index=0)

# --- Session State Defaults ---
default_filters = {
    "producer": "All",
    "vintage": "All",
    "location": "All",
    "varietal": "All",
    "decade": "All",
    "terroir": "All",
    "quick_magnums": False,
    "favorite_producer": "None",
    "fridge_choice": "None",
    "shelf_choice": "All"
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
    "Favorite producer",
    ["None"] + sorted(curr_lib["Producer"].dropna().unique()),
    key="favorite_producer"
)

# --- Main Filters ---
with st.expander("🔍 Main Filters", expanded=True):
    producer = st.selectbox("Producer", ["All"] + sorted(curr_lib["Producer"].dropna().unique()), key="producer")
    vintage = st.selectbox("Vintage", ["All"] + sorted(curr_lib["Vintage"].dropna().unique()), key="vintage")
    location = st.selectbox("Location", ["All"] + sorted(curr_lib["Location"].dropna().unique()), key="location")
    varietal = st.selectbox("Varietal", ["All"] + sorted(curr_lib["Varietal"].dropna().unique()), key="varietal")
    decade = st.selectbox("Decade", ["All"] + sorted(curr_lib["Decade"].dropna().unique()), key="decade")
    terroir = st.selectbox("Terroir", ["All"] + sorted(curr_lib["Terroir"].dropna().unique()), key="terroir")

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

# --- Results ---
st.subheader(f"Results ({len(filtered)} records, {filtered['Bottles'].sum()} bottles)")
st.dataframe(filtered, use_container_width=True)

# --- Summary Tables in Collapsible Tabs ---
with st.expander("📊 Summaries by Category", expanded=True):
    tab1, tab2, tab3, tab4 = st.tabs(["By Location","By Producer","By Decade","By Vintage"])
    
    with tab1:
        loc_summary = filtered.groupby("Location")["Bottles"].sum().reset_index()
        st.dataframe(loc_summary, use_container_width=True)
    
    with tab2:
        prod_summary = filtered.groupby("Producer")["Bottles"].sum().reset_index()
        st.dataframe(prod_summary, use_container_width=True)
    
    with tab3:
        decade_summary = filtered.groupby("Decade")["Bottles"].sum().reset_index()
        st.dataframe(decade_summary, use_container_width=True)
    
    with tab4:
        vint_summary = filtered.groupby("Vintage")["Bottles"].sum().reset_index()
        st.dataframe(vint_summary, use_container_width=True)
        # Keep line chart visualization for vintage
        fig, ax = plt.subplots()
        ax.plot(vint_summary["Vintage"], vint_summary["Bottles"], marker='o', color='teal')
        ax.set_xlabel("Vintage")
        ax.set_ylabel("Bottles")
        ax.set_title("Bottles by Vintage")
        st.pyplot(fig)

# --- Excel Export ---
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Filtered Results", index=False)
        loc_summary.to_excel(writer, sheet_name="By Location", index=False)
        prod_summary.to_excel(writer, sheet_name="By Producer", index=False)
        decade_summary.to_excel(writer, sheet_name="By Decade", index=False)
        vint_summary.to_excel(writer, sheet_name="By Vintage", index=False)
    output.seek(0)
    return output

st.download_button(
    label="📥 Download Filtered Results as Excel",
    data=to_excel(filtered),
    file_name="wine_cellar_results.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# --- Fridge Summary ---
with st.expander("🧊 Fridge Summary by Row", expanded=True):
    fridges_only = [loc for loc in curr_lib["Location"].dropna().unique() if "Fridge" in loc]
    selected_fridge = st.selectbox("Select a fridge location", ["All"] + sorted(fridges_only))
    fridge_data = curr_lib[curr_lib["Location"].isin(fridges_only)]
    if selected_fridge != "All":
        fridge_data = fridge_data[fridge_data["Location"] == selected_fridge]
    
    fridge_summary = fridge_data.groupby(["Location","Box_Shelf_Number"])["Bottles"].sum().reset_index().sort_values(["Location","Box_Shelf_Number"])
    st.dataframe(fridge_summary, use_container_width=True)
    st.markdown(f"**Total bottles in selection:** {fridge_data['Bottles'].sum()}")

# --- Shelf Details ---
with st.expander("🔍 Shelf Details", expanded=True):
    available_shelves = sorted(fridge_data['Box_Shelf_Number'].dropna().unique())
    selected_shelf = st.selectbox("Select a shelf (row number)", ["All"] + [str(int(s)) for s in available_shelves])
    
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
    def shelf_to_excel(df):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="Shelf Details", index=False)
        output.seek(0)
        return output

    st.download_button(
        label="📥 Download Shelf Details as Excel",
        data=shelf_to_excel(shelf_data),
        file_name="shelf_details.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
