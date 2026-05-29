import copy
import pandas as pd
import streamlit as st
from datetime import timedelta

from src.config import INDICATEURS
from src.data_manager import (
    get_geojson_path,
    load_geojson,
    load_clusters,
    geojson_to_df
)
from src.ui.styles import inject_custom_css
from src.ui.sidebar import render_sidebar
from src.ui.kpi import render_kpis
from src.ui.map import render_map
from src.ui.charts import render_top_10, render_time_series
from src.ui.clusters import render_cluster_descriptions


def render_dashboard():
    inject_custom_css()

    # Render Sidebar and get selections
    niveau, indicateur, date_sel, ts_start, ts_end, ts_step = render_sidebar()

    col_key, accent_color = INDICATEURS[indicateur]

    # ─────────────────────────────────────────────────────────────────────────────
    # DATA LOADING
    # ─────────────────────────────────────────────────────────────────────────────
    path_jour = get_geojson_path(niveau, date_sel)

    with st.spinner("Chargement des données…"):
        gj_raw = load_geojson(str(path_jour))

    if gj_raw is None:
        st.error(
            f"❌ Fichier introuvable : `{path_jour.name}`\n\n"
            f"Essaie une autre date — les données couvrent du **01/03/2020** au **30/06/2021**."
        )
        st.stop()

    gj = copy.deepcopy(gj_raw)
    df_day = geojson_to_df(gj_raw)
    clusters = load_clusters(niveau)

    # ─────────────────────────────────────────────────────────────────────────────
    # MAIN DASHBOARD
    # ─────────────────────────────────────────────────────────────────────────────
    # Title and KPIs
    st.markdown(
        f'<h2 style="font-size:20px;font-weight:600;color:#0f172a;margin:0 0 16px 0;">'
        f'{indicateur} — {niveau}'
        f'<span style="font-size:13px;font-weight:400;color:#94a3b8;margin-left:12px;">'
        f'📅 {date_sel.strftime("%d %B %Y")}</span></h2>',
        unsafe_allow_html=True,
    )

    render_kpis(indicateur, df_day, col_key, accent_color)

    # Map and Top 10
    map_col, right_col = st.columns([6, 4], gap="large")

    with map_col:
        render_map(gj, indicateur, date_sel, clusters, df_day, col_key, niveau)

    with right_col:
        render_top_10(df_day, col_key, indicateur, accent_color)

    # Cluster Descriptions
    render_cluster_descriptions(niveau)

    # ─────────────────────────────────────────────────────────────────────────────
    # TIME SERIES EVOLUTION
    # ─────────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="sec-title">Évolution temporelle</div>', unsafe_allow_html=True)

    cache_key = f"{niveau}|{ts_start}|{ts_end}|{ts_step}"
    n_files = max(1, (ts_end - ts_start).days // ts_step + 1)

    btn_col, info_col = st.columns([2, 8])
    with btn_col:
        load_btn = st.button("🔄 Charger la série", type="primary")
    with info_col:
        st.caption(f"~{n_files} fichiers · pas de {ts_step} jour(s)")

    if load_btn or st.session_state.get("_ts_key") != cache_key:
        frames, current, idx = [], ts_start, 0
        prog = st.progress(0, text="Chargement…")
        while current <= ts_end:
            gj_path = get_geojson_path(niveau, current)
            gj_ = load_geojson(str(gj_path))
            if gj_:
                df_ = geojson_to_df(gj_)
                df_["date"] = pd.Timestamp(current)
                frames.append(df_)
            current += timedelta(days=ts_step)
            idx += 1
            prog.progress(min(idx / n_files, 1.0), text=f"← {current.isoformat()}")
        prog.empty()
        st.session_state["_ts_df"] = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        st.session_state["_ts_key"] = cache_key

    ts_df = st.session_state.get("_ts_df", pd.DataFrame())

    if ts_df.empty:
        st.info("Clique sur **Charger la série** pour afficher l'évolution temporelle.")
    else:
        ts_agg = ts_df.groupby("date").agg(
            hospitalises=("hospitalises",  "sum"),
            reanimation=("reanimation",   "sum"),
            urg_covid=("urg_covid",     "sum"),
            pcr_positifs=("pcr_positifs",  "sum"),
            deces=("deces",         "sum"),
        ).reset_index()

        render_time_series(ts_agg, date_sel)

        with st.expander("📋 Données brutes"):
            disp = ts_agg.copy()
            disp["date"] = disp["date"].dt.strftime("%d/%m/%Y")
            disp.columns = ["Date", "Hospitalisés", "Réanimation", "Urgences COVID", "PCR+", "Décès"]
            st.dataframe(disp, width='stretch', hide_index=True)

    # ─────────────────────────────────────────────────────────────────────────────
    # FOOTER
    # ─────────────────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center;font-size:10px;color:#cbd5e1;
                margin-top:32px;padding-top:16px;border-top:1px solid #f1f5f9;">
        Sources : Santé Publique France · CSSE Johns Hopkins ·
        <a href="https://github.com/kalisio/covid-19" style="color:#94a3b8;">kalisio/covid-19</a>
        · Licence MIT
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG & UI INITIALIZATION
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="COVID-19 France",
    page_icon="🦠",
    layout="wide",
    initial_sidebar_state="expanded",
)

pg = st.navigation([
    st.Page(render_dashboard, title="Données géographiques", icon="🦠"),
    st.Page("pages/Chatbot.py", title="Chatbot", icon="🏥")
])
pg.run()
