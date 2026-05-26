import streamlit as st
from src.config import FOLDERS, INDICATEURS, DATE_MIN, DATE_MAX, DATE_DEF


def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="padding:6px 0 2px;">
            <span style="font-size:22px;font-weight:600;color:#f1f5f9;">🦠 COVID-19</span><br>
            <span style="font-size:11px;color:#475569;">France — Tableau de bord</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="sb-sep">Géographie</div>', unsafe_allow_html=True)
        niveau = st.selectbox("Niveau", ["Régions", "Départements"], label_visibility="collapsed")

        st.markdown('<div class="sb-sep">Indicateur (remplissage carte)</div>', unsafe_allow_html=True)
        indicateur = st.selectbox("Indicateur", list(INDICATEURS.keys()), label_visibility="collapsed")

        st.markdown('<div class="sb-sep">Date</div>', unsafe_allow_html=True)
        date_sel = st.date_input(
            "Date", value=DATE_DEF,
            min_value=DATE_MIN, max_value=DATE_MAX,
            label_visibility="collapsed",
        )

        st.markdown('<div class="sb-sep">Série temporelle</div>', unsafe_allow_html=True)
        ts_start = st.date_input("Début", value=DATE_MIN, min_value=DATE_MIN, max_value=DATE_MAX)
        ts_end   = st.date_input("Fin",   value=DATE_MAX, min_value=DATE_MIN, max_value=DATE_MAX)
        ts_step  = st.select_slider(
            "Pas d'échantillonnage", options=[1, 3, 7, 14], value=7,
            format_func=lambda v: f"{v} jour{'s' if v > 1 else ''}",
        )

        st.markdown("---")
        st.markdown(
            f'<div style="font-size:9px;color:#334155;line-height:1.8;">'
            f'📁 {FOLDERS[niveau]}<br>📅 {date_sel.isoformat()}</div>',
            unsafe_allow_html=True,
        )

    return niveau, indicateur, date_sel, ts_start, ts_end, ts_step
