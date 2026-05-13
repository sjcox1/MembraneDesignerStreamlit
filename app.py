import streamlit as st

st.set_page_config(
    page_title="Membrane Designer",
    page_icon="💧",
    layout="wide",
)

st.title("Membrane Plant Designer")
st.subheader("Design and simulation tool for membrane filtration systems")

st.info("This tool is under development. Features will be added here soon.")

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="Feed Flow Rate", value="—", delta=None)

with col2:
    st.metric(label="Recovery Rate", value="—", delta=None)

with col3:
    st.metric(label="Permeate Quality", value="—", delta=None)

st.divider()
st.caption("Membrane Designer — coming soon")
