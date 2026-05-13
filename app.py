import streamlit as st

st.set_page_config(
    page_title="Membrane Designer",
    page_icon="💧",
    layout="wide",
)

def login():
    st.title("Membrane Plant Designer")
    st.subheader("Please enter your name to continue")

    name_input = st.text_input("Your name", placeholder="e.g. Alice")

    if st.button("Login", type="primary"):
        authorised = [n.lower() for n in st.secrets["users"]["names"]]
        if name_input.strip().lower() in authorised:
            st.session_state["user"] = name_input.strip().title()
            st.rerun()
        else:
            st.error("Name not recognised. Please check with your trainer.")

def main():
    user = st.session_state["user"]

    with st.sidebar:
        st.markdown(f"Logged in as **{user}**")
        if st.button("Logout"):
            del st.session_state["user"]
            st.rerun()

    st.title("Membrane Plant Designer")
    st.subheader("Design and simulation tool for membrane filtration systems")

    st.info("This tool is under development. Features will be added here soon.")

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="Feed Flow Rate", value="—")

    with col2:
        st.metric(label="Recovery Rate", value="—")

    with col3:
        st.metric(label="Permeate Quality", value="—")

    st.divider()
    st.caption("Membrane Designer — coming soon")

if "user" not in st.session_state:
    login()
else:
    main()
