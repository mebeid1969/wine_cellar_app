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

# --- Streamlit UI ---
st.set_page_config(page_title="Wine Cellar Explorer", layout="wide")
st.title("🍷 Wine Cellar Explorer")

# --- Quick Queries Sidebar ---
st.sidebar.header("⚡ Quick Queries")

# Quick Queries with keys for session_state
quick_magnums = st.sidebar.checkbox("Magnums only", key="quick_magnums")
quick_closet = st.sidebar.checkbox("Closet holdings", key="quick_closet")
quick_france = st.sidebar.checkbox("French wines", key="quick_france")

favorite_producer = st.sidebar.selectbox(
    "Favorite producers",
    ["None", "Clos du Val", "Corison", "Heitz Cellars", "Williams Selyem", "A. Rafanelli"],
    key="favorite_producer"
)

# --- Main Filters ---
producer = st.selectbox("Producer", ["All"] + sorted(curr_lib["Producer"].dropna().unique()), key="producer")
vintage = st.selectbox("Vintage", ["All"] + sorted(curr_lib["Vintage"].dropna().unique()), key="vintage")
location = st.selectbox("Location", ["All"] + sorted(curr_lib["Location"].dropna().unique()), key="location")
varietal = st.selectbox("Varietal", ["All"] + sorted(curr_lib["Varietal"].dropna().unique()), key="varietal")
decade = st.selectbox("Decade", ["All"] + sorted(curr_lib["Decade"].dropna().unique()), key="decade")

# --- Fridge/Shelf lookup ---
st.markdown("### 🧊 Fridge & Shelf Lookup")
fridges_only = [loc for loc in curr_lib["Location"].dropna().unique() if "Fridge" in loc]
fridge_choice = st.selectbox("Fridge", ["None"] + sorted(fridges_only), key="fridge_choice")

shelf_choice = None
if fridge_choice != "None":
    shelves = sorted(curr_lib[curr_lib["Location"] == fridge_choice]["Box_Shelf_Number"].dropna().unique())
    shelf_choice = st.selectbox("Shelf Number", ["All"] + shelves, key="shelf_choice")

# --- Reset Filters Button ---
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Reset Filters"):
    # Quick Queries
    st.session_state["quick_magnums"] = False
    st.session_state["quick_closet"] = False
    st.session_state["quick_france"] = False
    st.session_state["favorite_producer"] = "None"
    # Main filters
    st.session_state["producer"] = "All"
    st.session_state["vintage"] = "All"
    st.session_state["location"] = "All"
    st.session_state["varietal"] = "All"
    st.session_state["decade"] = "All"
    # Fridge/Shelf
    st.session_state["fridge_choice"] = "None"
    st.session_state["shelf_choice"] = "All"
    st.experimental_rerun()

# --- Apply filters dynamically ---
filtered = curr_lib.copy()

# Quick Queries
if quick_magnums:
    filtered = filtered[filtered["Notes"] == "Magnum"]
if quick_closet:
    filtered = filtered[filtered["Location"] == "Closet"]
if quick_france:
    filtered = filtered[filtered["Region"] == "France"]
if favorite_producer != "None":
    filtered = filtered[filtered["Producer"] == favorite_producer]

# Main filters
if producer != "All":
    filtered = filtered[filtered["Producer"] == producer]
if vintage != "All":
    filtered = filtered[filtered["Vintage"] == vintage]
if location != "All":
    filtered = filtered[filtered["Location"] == location]
if varietal != "All":
    filtered = filtered[filtered["Varietal"] == varietal]
if decade != "All":
    filtered = filtered[filtered["Decade"] == decade]
if fridge_choice != "None":
    filtered = filtered[filtered["Location"] == fridge_choice]
    if shelf_choice != "All":
        filtered = filtered[filtered["Box_Shelf_Number"] == shelf_choice]

# --- Show results ---
st.subheader(f"Results ({len(filtered)} records, {filtered['Bottles'].sum()} bottles)")
st.dataframe(filtered.sort_values(by=["Producer", "Vintage"]))

# --- Export filtered results ---
# CSV
st.download_button(
    label="📥 Download results as CSV",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name="wine_query_results.csv",
    mime="text/csv"
)

# Excel
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

# --- Summary stats with charts ---
st.markdown("### 📊 Summaries")
tab1, tab2, tab3, tab4 = st.tabs(["By Location", "By Producer", "By Decade", "By Vintage"])

with tab1:
    loc_summary = filtered.groupby("Location")["Bottles"].sum().reset_index()
    st.write(loc_summary)
    st.bar_chart(loc_summary.set_index("Location"))

with tab2:
    prod_summary = filtered.groupby("Producer")["Bottles"].sum().reset_index()
    st.write(prod_summary)
    top_producers = prod_summary.sort_values("Bottles", ascending=False).head(10)
    st.bar_chart(top_producers.set_index("Producer"))

with tab3:
    dec_summary = filtered.groupby("Decade")["Bottles"].sum().reset_index()
    st.write(dec_summary)
    st.bar_chart(dec_summary.set_index("Decade"))

with tab4:
    vint_summary = filtered.groupby("Vintage")["Bottles"].sum().reset_index()
    st.write(vint_summary)
    fig, ax = plt.subplots()
    ax.plot(vint_summary["Vintage"], vint_summary["Bottles"], marker="o")
    ax.set_xlabel("Vintage")
    ax.set_ylabel("Bottles")
    ax.set_title("Bottles by Vintage")
    st.pyplot(fig)
