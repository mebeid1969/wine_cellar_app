import pandas as pd
import streamlit as st
import io

# --- Assume filtered DataFrame from Step 3 is available ---
# filtered = ...

# --- Display Summary Tables ---
st.header("📊 Summary Tables")

tab1, tab2, tab3, tab4 = st.tabs(["By Location", "By Producer", "By Decade", "By Vintage"])

with tab1:
    loc_summary = filtered.groupby("Location")["Bottles"].sum().reset_index()
    st.subheader("Bottles by Location")
    st.dataframe(loc_summary, use_container_width=True)

with tab2:
    prod_summary = filtered.groupby("Producer")["Bottles"].sum().reset_index()
    st.subheader("Bottles by Producer")
    st.dataframe(prod_summary, use_container_width=True)

with tab3:
    decade_summary = filtered.groupby("Decade")["Bottles"].sum().reset_index()
    st.subheader("Bottles by Decade")
    st.dataframe(decade_summary, use_container_width=True)

with tab4:
    vint_summary = filtered.groupby("Vintage")["Bottles"].sum().reset_index()
    st.subheader("Bottles by Vintage")
    st.dataframe(vint_summary, use_container_width=True)

# --- Export to Excel ---
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Filtered Results", index=False)
        # Add summaries
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
