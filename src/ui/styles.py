import streamlit as st


def inject_custom_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #0f172a !important;
    border-right: 1px solid #1e293b;
}
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div { color: #94a3b8 !important; }
section[data-testid="stSidebar"] label {
    font-size: 10px !important;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #475569 !important;
}
section[data-testid="stSidebar"] .stSelectbox > div > div > div,
section[data-testid="stSidebar"] input[type="text"] {
    background: #1e293b !important;
    border: 1px solid #334155 !important;
    color: #e2e8f0 !important;
    border-radius: 6px !important;
}

/* ── KPI ── */
.kpi-row { display:flex; gap:12px; margin-bottom:20px; }
.kpi-card {
    flex:1; background:#fff;
    border:1px solid #e2e8f0; border-radius:10px;
    padding:16px 20px; position:relative; overflow:hidden;
}
.kpi-card::after {
    content:''; position:absolute; top:0; left:0; right:0;
    height:3px; background:var(--c); border-radius:10px 10px 0 0;
}
.kpi-label {
    font-size:10px; font-weight:600; text-transform:uppercase;
    letter-spacing:1.5px; color:#94a3b8; margin-bottom:8px;
}
.kpi-value {
    font-family:'DM Mono',monospace; font-size:26px;
    font-weight:500; color:#0f172a; line-height:1;
}

/* ── Section titles ── */
.sec-title {
    font-size:10px; font-weight:600; text-transform:uppercase;
    letter-spacing:2px; color:#94a3b8;
    margin:0 0 10px; padding-bottom:8px;
    border-bottom:1px solid #f1f5f9;
}

/* ── Sidebar section titles ── */
.sb-sep {
    font-size:9px; font-weight:600; text-transform:uppercase;
    letter-spacing:2px; color:#334155;
    margin:18px 0 6px; padding-bottom:5px;
    border-bottom:1px solid #1e293b;
}

/* ── Cluster cards ── */
.cluster-grid {
    display:grid;
    grid-template-columns:repeat(auto-fill, minmax(200px,1fr));
    gap:10px; margin-top:8px;
}
.cluster-card {
    border-radius:8px; padding:12px 14px;
    border-left:4px solid var(--cc);
    background:#f8fafc;
}
.cluster-card b { font-size:12px; color:#1e293b; display:block; margin-bottom:4px; }
.cluster-card small { font-size:11px; color:#64748b; line-height:1.5; }
</style>
""", unsafe_allow_html=True)
