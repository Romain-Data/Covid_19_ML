import streamlit as st
from src.config import CLUSTER_LABELS, CLUSTER_COLORS


def render_cluster_descriptions(niveau):
    st.markdown("---")
    st.markdown('<div class="sec-title">Description des clusters</div>', unsafe_allow_html=True)

    labels = CLUSTER_LABELS.get(niveau, {})
    cards  = '<div class="cluster-grid">'
    for c_id, (title, desc) in labels.items():
        color  = CLUSTER_COLORS.get(c_id, "#cbd5e1")
        cards += (f'<div class="cluster-card" style="--cc:{color};">'
                  f'<b>Cluster {c_id} — {title}</b>'
                  f'<small>{desc}</small></div>')
    cards += '</div>'
    st.markdown(cards, unsafe_allow_html=True)
