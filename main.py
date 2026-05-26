import streamlit as st

st.set_page_config(
    page_title="COVID-19 France",
    page_icon="🦠",
    layout="wide",
    initial_sidebar_state="expanded",
)

pg = st.navigation([
    st.Page("src/pages/geography.py", title="Données géographiques", icon="🌍"),
    st.Page("src/pages/chatbot.py", title="Aide au diagnostique", icon="🤖"),
])

pg.run()
