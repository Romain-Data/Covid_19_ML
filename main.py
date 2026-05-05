import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
import json
import math
import copy
import branca.colormap as cm
from datetime import datetime, date, timedelta

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="COVID-19 France — Dashboard",
    page_icon="🦠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── STYLE ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
.stApp { background: #0d0f14; color: #e8eaf0; }
section[data-testid="stSidebar"] { background: #13161e !important; border-right: 1px solid #1e2230; }
section[data-testid="stSidebar"] * { color: #c8cad8 !important; }
.metric-card {
    background: linear-gradient(135deg, #161a25 0%, #1a1f2e 100%);
    border: 1px solid #252a3a; border-radius: 12px;
    padding: 18px 22px; margin-bottom: 8px;
    position: relative; overflow: hidden;
}
.metric-card::before { content:''; position:absolute; top:0;left:0;right:0; height:3px; background:var(--accent); }
.metric-label { font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:1.5px; color:#6b7280; margin-bottom:6px; }
.metric-value { font-family:'JetBrains Mono',monospace; font-size:26px; font-weight:600; color:#e8eaf0; line-height:1; }
.section-header {
    font-size:13px; font-weight:600; text-transform:uppercase;
    letter-spacing:2px; color:#4b5563; margin:24px 0 12px 0;
    padding-bottom:6px; border-bottom:1px solid #1e2230;
}
.error-box {
    background:#1f1215; border:1px solid #7f1d1d; border-radius:8px;
    padding:16px; color:#fca5a5; font-size:13px; margin:8px 0;
}
.info-box {
    background:#0f1f2e; border:1px solid #1e3a5f; border-radius:8px;
    padding:12px 16px; color:#93c5fd; font-size:12px; margin:8px 0;
}
div[data-testid="stSelectbox"] > div > div {
    background:#1a1f2e !important; border-color:#252a3a !important; color:#e8eaf0 !important;
}
</style>
""", unsafe_allow_html=True)

# ─── LOCAL CONFIG ────────────────────────────────────────────────────────────
# Le projet kalisio/covid-19 génère un fichier GeoJSON par date dans chaque dossier.
# Structure locale : {dossier}/{dossier}-{YYYY-MM-DD}.json
# Exemple      : regions-france/regions-france-2020-11-15.json
#
# Chaque Feature du GeoJSON contient dans ses "properties" :
#   Severe        → hospitalisés à date
#   Critical      → réanimations à date
#   Deaths        → décès cumulés
#   Emergencies.{Total, Suspected, Severe}
#   MedicalActs.{Total, Suspected}
#   PCRTests.{Total, Confirmed}
#   Population.Total
#   Beds.{Total, Resuscitation, IntensiveCare}

FOLDERS = {
    "Régions":      "regions-france",
    "Départements": "departements-france",
}


# ─── HELPERS ─────────────────────────────────────────────────────────────────
def build_path(niveau: str, target_date: date, polygons: bool = False) -> str:
    folder = FOLDERS[niveau]
    suffix = "-polygons" if polygons else ""
    return f"{folder}/{folder}{suffix}-{target_date.isoformat()}.json"


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_geojson(path: str) -> dict | None:
    """Charge un GeoJSON depuis le dossier local. Retourne None si indisponible."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def geojson_to_df(gj: dict) -> pd.DataFrame:
    """
    Convertit un GeoJSON FeatureCollection en DataFrame plat.
    Gère Point (barycentre) et Polygon/MultiPolygon (centroïde approx.).
    """
    rows = []
    for feat in gj.get("features", []):
        props = feat.get("properties", {})
        geom  = feat.get("geometry", {})

        # ── Coordonnées ──────────────────────────────────────────────────────
        if geom.get("type") == "Point":
            lon, lat = geom["coordinates"]
        elif geom.get("type") in ("Polygon", "MultiPolygon"):
            coords = geom["coordinates"]
            if geom["type"] == "MultiPolygon":
                coords = [ring for poly in coords for ring in poly]
            flat = [pt for ring in coords for pt in ring]
            if not flat:
                continue
            lon = sum(p[0] for p in flat) / len(flat)
            lat = sum(p[1] for p in flat) / len(flat)
        else:
            continue

        # ── Sous-objets ───────────────────────────────────────────────────────
        emerg  = props.get("Emergencies", {}) or {}
        medact = props.get("MedicalActs", {}) or {}
        pcr    = props.get("PCRTests", {}) or {}
        pop    = props.get("Population", {}) or {}
        beds   = props.get("Beds", {}) or {}

        rows.append({
            "nom":          props.get("Province/State", "?"),
            "lat":          lat,
            "lon":          lon,
            # Hospitaux
            "hospitalises": props.get("Severe", 0) or 0,
            "reanimation":  props.get("Critical", 0) or 0,
            "deces":        props.get("Deaths", 0) or 0,
            # Urgences
            "urg_total":    emerg.get("Total", 0) or 0,
            "urg_covid":    emerg.get("Suspected", 0) or 0,
            "urg_hosp":     emerg.get("Severe", 0) or 0,
            # SOS Médecins
            "sos_total":    medact.get("Total", 0) or 0,
            "sos_covid":    medact.get("Suspected", 0) or 0,
            # Tests PCR
            "pcr_total":    pcr.get("Total", 0) or 0,
            "pcr_positifs": pcr.get("Confirmed", 0) or 0,
            # Population & lits
            "population":   pop.get("Total", 0) or 0,
            "lits_total":   beds.get("Total", 0) or 0,
            "lits_rea":     beds.get("Resuscitation", 0) or 0,
        })

    return pd.DataFrame(rows)


# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div style="font-size:22px;font-weight:700;color:#e8eaf0;">🦠 COVID-19</div>',
                unsafe_allow_html=True)
    st.markdown('<div style="font-size:12px;color:#4b5563;margin-top:2px;">'
                'France — Données locales</div>', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown('<div class="section-header">Géographie</div>', unsafe_allow_html=True)
    niveau = st.selectbox("Niveau géographique", ["Régions", "Départements"])

    st.markdown('<div class="section-header">Indicateur</div>', unsafe_allow_html=True)
    indicateur = st.selectbox("Indicateur principal", [
        "Hospitalisations",
        "Réanimations",
        "Décès cumulés",
        "Urgences COVID",
        "Tests PCR positifs",
    ])

    IND_MAP = {
        "Hospitalisations":   ("hospitalises",  "#3b82f6", "🏥"),
        "Réanimations":       ("reanimation",   "#ef4444", "🚨"),
        "Décès cumulés":      ("deces",         "#6366f1", "💀"),
        "Urgences COVID":     ("urg_covid",     "#8b5cf6", "🚑"),
        "Tests PCR positifs": ("pcr_positifs",  "#f59e0b", "🧪"),
    }
    col_key, accent_color, emoji = IND_MAP[indicateur]

    HEX_TO_RGB = {
    "#3b82f6": (59,130,246), "#ef4444": (239,68,68),
    "#6366f1": (99,102,241), "#8b5cf6": (139,92,246),
    "#f59e0b": (245,158,11),
}
    rv, gv, bv = HEX_TO_RGB[accent_color]

    st.markdown('<div class="section-header">Date (carte)</div>', unsafe_allow_html=True)
    date_sel = st.date_input(
        "Date sélectionnée",
        value=date(2020, 11, 15),
        min_value=date(2020, 3, 1),
        max_value=date(2021, 6, 30),
    )

    st.markdown('<div class="section-header">Carte</div>', unsafe_allow_html=True)
    fill_opacity = st.slider("Opacité de la carte", 0.1, 1.0, 0.7, 0.1)
    show_labels  = st.checkbox("Étiquettes sur la carte", value=False)

    st.markdown('<div class="section-header">Série temporelle</div>', unsafe_allow_html=True)
    ts_start = st.date_input("Début période", value=date(2020, 3, 1),
                              min_value=date(2020, 3, 1), max_value=date(2021, 6, 30))
    ts_end   = st.date_input("Fin période",   value=date(2021, 6, 30),
                              min_value=date(2020, 3, 1), max_value=date(2021, 6, 30))
    ts_step  = st.select_slider(
        "Fréquence d'échantillonnage",
        options=[1, 3, 7, 14], value=7,
        format_func=lambda v: f"tous les {v} jour{'s' if v>1 else ''}",
    )

    st.markdown("---")
    st.markdown(f"""
    <div class="info-box">
    📡 Source : <code>Données locales</code><br>
    🗂️ Dossier : <code>{FOLDERS[niveau]}</code><br>
    Sources : <b>SPF</b> · <b>CSSE</b>
    </div>
    """, unsafe_allow_html=True)


# ─── CHARGEMENT CARTE DU JOUR ────────────────────────────────────────────────
path_jour = build_path(niveau, date_sel, polygons=True)

with st.spinner(f"⏳ Chargement local — {date_sel.isoformat()} …"):
    gj_jour = copy.deepcopy(fetch_geojson(path_jour))

if gj_jour is None:
    st.markdown(f"""
    <div class="error-box">
    ❌ <b>Fichier introuvable localement</b><br><br>
    Chemin testé : <code>{path_jour}</code><br><br>
    Causes possibles :<br>
    • Aucun fichier pour cette date dans le dossier<br>
    • Les données vont du <b>01/03/2020</b> au <b>~30/06/2021</b><br><br>
    👉 Essaie une autre date.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

df_day = geojson_to_df(gj_jour)

if df_day.empty:
    st.error("Le fichier GeoJSON est vide ou son format est inattendu.")
    with st.expander("Voir le JSON brut"):
        st.json(gj_jour)
    st.stop()


# ─── HEADER ──────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-bottom:16px;">
  <span style="font-size:22px;font-weight:700;color:#e8eaf0;">{emoji} {indicateur} — {niveau}</span>
  <span style="font-size:13px;color:#4b5563;margin-left:12px;">
    📅 {date_sel.strftime('%d %B %Y')}
  </span>
  &nbsp;
  <span style="font-size:11px;color:#374151;text-decoration:none;">source locale ({path_jour})</span>
</div>
""", unsafe_allow_html=True)

# ─── KPI ─────────────────────────────────────────────────────────────────────
def kpi(col, label, val, color):
    col.markdown(f"""
    <div class="metric-card" style="--accent:{color};">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{int(val):,}</div>
    </div>
    """, unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)
kpi(k1, indicateur,       df_day[col_key].sum(),     accent_color)
kpi(k2, "Hospitalisés",   df_day["hospitalises"].sum(), "#3b82f6")
kpi(k3, "En réanimation", df_day["reanimation"].sum(),  "#ef4444")
kpi(k4, "Urgences COVID", df_day["urg_covid"].sum(),    "#8b5cf6")

st.markdown("---")

# ─── CARTE + GRAPHIQUES ──────────────────────────────────────────────────────
map_col, chart_col = st.columns([6, 4])

# ── CARTE CHOROPLÈTHE (Plotly) ────────────────────────────────────────────────
with map_col:
    st.markdown(
        f'<div class="section-header">Carte — {indicateur} ({date_sel.strftime("%d/%m/%Y")})</div>',
        unsafe_allow_html=True,
    )

    # Charger le GeoJSON polygones (même path qu'avant)
    path_poly = build_path(niveau, date_sel, polygons=True)
    gj_poly = fetch_geojson(path_poly)

    if gj_poly is None:
        st.warning("Fichier polygones introuvable.")
    else:
        # Construire un id unique par feature pour le join avec df_day
        ids, vals, noms = [], [], []
        for feat in gj_poly["features"]:
            nom = feat["properties"].get("Province/State", "?")
            # Plotly a besoin d'un id sur chaque feature
            feat["id"] = nom
            row = df_day[df_day["nom"] == nom]
            val = int(row[col_key].values[0]) if not row.empty else 0
            ids.append(nom)
            vals.append(val)
            noms.append(nom)

        # Palette selon l'indicateur
        COLORSCALES = {
            "#3b82f6": [[0, "#161a25"], [1, "#3b82f6"]],
            "#ef4444": [[0, "#161a25"], [1, "#ef4444"]],
            "#6366f1": [[0, "#161a25"], [1, "#6366f1"]],
            "#8b5cf6": [[0, "#161a25"], [1, "#8b5cf6"]],
            "#f59e0b": [[0, "#161a25"], [1, "#f59e0b"]],
        }

        fig_map = go.Figure(go.Choropleth(
            geojson=gj_poly,
            locations=ids,
            z=vals,
            colorscale=COLORSCALES[accent_color],
            zmin=0,
            zmax=max(vals) if max(vals) > 0 else 1,
            marker_line_color="#0d0f14",   # trait noir entre régions = contraste max
            marker_line_width=1.8,
            marker_opacity=fill_opacity,
            colorbar=dict(
            thickness=8,
            len=0.5,
            x=1.01,
            y=0.5,
            bgcolor="rgba(0,0,0,0)",
            tickfont=dict(color="#4b5563", size=9),
            outlinewidth=0,
            title=dict(
                text=indicateur[:10],
                font=dict(color="#4b5563", size=9),
                side="right",
            ),
            ),
            customdata=list(zip(
                noms,
                [df_day[df_day["nom"]==n]["hospitalises"].values[0]
                 if not df_day[df_day["nom"]==n].empty else 0 for n in noms],
                [df_day[df_day["nom"]==n]["reanimation"].values[0]
                 if not df_day[df_day["nom"]==n].empty else 0 for n in noms],
                [df_day[df_day["nom"]==n]["deces"].values[0]
                 if not df_day[df_day["nom"]==n].empty else 0 for n in noms],
            )),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "🏥 Hospitalisés : %{customdata[1]:,}<br>"
                "🚨 Réanimation  : %{customdata[2]:,}<br>"
                "💀 Décès        : %{customdata[3]:,}<br>"
                f"📊 {indicateur}  : %{{z:,}}"
                "<extra></extra>"
            ),
        ))

        fig_map.update_geos(
        visible=True,
        bgcolor="rgba(13,15,20,1)",
        showland=True,
        landcolor="#1a1f2e",
        showocean=True,
        oceancolor="#0d0f14",
        showcoastlines=True,
        coastlinecolor="#252a3a",
        coastlinewidth=0.8,
        showframe=True,          # ← showborder n'existe pas, c'est showframe
        framecolor="#252a3a",
        framewidth=0.5,
        showcountries=True,      # bonus : frontières pays voisins
        countrycolor="#1e2230",
        countrywidth=0.5,
        center=dict(lat=46.5, lon=2.5),
        projection_scale=1,
        lataxis_range=[41, 52],
        lonaxis_range=[-6, 10],
        )

        fig_map.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            geo=dict(bgcolor="rgba(13,15,20,1)"),
            margin=dict(l=0, r=0, t=0, b=0),
            height=480,
        )
        st.plotly_chart(fig_map, use_container_width=True,
                        config={"displayModeBar": False})

        if show_labels:
            st.caption("ℹ️ Les étiquettes ne sont pas supportées en mode Choroplèthe Plotly.")

# ── GRAPHIQUES ────────────────────────────────────────────────────────────────
with chart_col:
    # Top 10
    st.markdown(f'<div class="section-header">Top 10 — {indicateur}</div>',
                unsafe_allow_html=True)
    top10 = df_day.nlargest(10, col_key)[["nom", col_key]].sort_values(col_key)
    colors_bar = [
        f"rgba({rv},{gv},{bv},{0.35 + 0.6*i/max(len(top10)-1,1):.2f})"
        for i in range(len(top10))
    ]
    fig_bar = go.Figure(go.Bar(
        x=top10[col_key], y=top10["nom"], orientation="h",
        marker=dict(color=colors_bar, line=dict(width=0)),
        text=top10[col_key].apply(lambda v: f"{int(v):,}"),
        textposition="outside", textfont=dict(color="#6b7280", size=10),
    ))
    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=55, t=0, b=0), height=260,
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(tickfont=dict(color="#9ca3af", size=10)),
    )
    st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

    # Radar
    st.markdown('<div class="section-header">Profil épidémique national</div>',
                unsafe_allow_html=True)
    cat  = ["Hospitalisés", "Réanimation", "Urg. COVID", "PCR+"]
    vals = [df_day["hospitalises"].sum(), df_day["reanimation"].sum(),
            df_day["urg_covid"].sum(),    df_day["pcr_positifs"].sum()]
    mx   = max(vals) or 1
    fig_radar = go.Figure(go.Scatterpolar(
        r=[v/mx for v in vals] + [vals[0]/mx],
        theta=cat + [cat[0]],
        fill="toself",
        fillcolor=f"rgba({rv},{gv},{bv},0.15)",
        line=dict(color=accent_color, width=2),
        mode="lines+markers", marker=dict(color=accent_color, size=6),
    ))
    fig_radar.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=False, range=[0, 1.15]),
            angularaxis=dict(tickfont=dict(color="#6b7280", size=11),
                             gridcolor="#1e2230", linecolor="#1e2230"),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=10, b=10), height=200, showlegend=False,
    )
    st.plotly_chart(fig_radar, use_container_width=True, config={"displayModeBar": False})

# ─── SÉRIE TEMPORELLE ─────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-header">Évolution temporelle — données locales</div>',
            unsafe_allow_html=True)

# Clé de cache unique selon les paramètres choisis
cache_key = f"{niveau}|{ts_start}|{ts_end}|{ts_step}"
load_btn  = st.button("🔄 Charger / Rafraîchir la série temporelle")

if load_btn or ("ts_cache_key" in st.session_state and
                st.session_state["ts_cache_key"] != cache_key):

    n_calls  = max(1, (ts_end - ts_start).days // ts_step + 1)
    progress = st.progress(0, text=f"Chargement de ~{n_calls} fichiers locaux…")
    frames   = []
    current  = ts_start
    idx      = 0

    while current <= ts_end:
        path = build_path(niveau, current, polygons=False)
        gj  = fetch_geojson(path)
        if gj:
            df_t = geojson_to_df(gj)
            df_t["date"] = pd.Timestamp(current)
            frames.append(df_t)
        current += timedelta(days=ts_step)
        idx += 1
        progress.progress(min(idx / n_calls, 1.0),
                          text=f"Local ← {current.isoformat()}")

    progress.empty()
    st.session_state["ts_df"]        = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    st.session_state["ts_cache_key"] = cache_key

ts_df = st.session_state.get("ts_df", pd.DataFrame())

if ts_df.empty:
    st.markdown("""
    <div class="info-box">
    ℹ️ Clique sur <b>Charger / Rafraîchir</b> pour charger les données locales sur la période.<br>
    Conseil : commence avec une fréquence de <b>7 jours</b> pour limiter le temps de traitement.
    </div>
    """, unsafe_allow_html=True)
else:
    ts_agg = ts_df.groupby("date").agg({
        "hospitalises": "sum", "reanimation": "sum",
        "urg_covid":    "sum", "pcr_positifs": "sum",
        "deces":        "sum",
    }).reset_index()

    c1, c2 = st.columns(2)
    CHART_LAYOUT = dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0), height=230,
        legend=dict(font=dict(color="#6b7280", size=10),
                    bgcolor="rgba(0,0,0,0)", orientation="h", y=-0.35),
        xaxis=dict(gridcolor="#1e2230", tickfont=dict(color="#4b5563", size=10), showgrid=False),
        yaxis=dict(gridcolor="#1e2230", tickfont=dict(color="#4b5563", size=10), gridwidth=0.5),
    )
    vline = dict(x=pd.Timestamp(date_sel), line_dash="dash",
                 line_color="rgba(255, 255, 255, 0.2)", line_width=1.5)

    with c1:
        st.markdown('<div class="section-header">Hospitalisés & Réanimation</div>',
                    unsafe_allow_html=True)
        fig1 = go.Figure()
        for col, color, lbl in [
            ("hospitalises", "#3b82f6", "Hospitalisés"),
            ("reanimation",  "#ef4444", "Réanimation"),
        ]:
            r2,g2,b2 = HEX_TO_RGB[color]
            fig1.add_trace(go.Scatter(
                x=ts_agg["date"], y=ts_agg[col], name=lbl,
                line=dict(color=color, width=2),
                fill="tozeroy", fillcolor=f"rgba({r2},{g2},{b2},0.08)",
            ))
        fig1.add_vline(**vline)
        fig1.update_layout(**CHART_LAYOUT)
        st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False})

    with c2:
        st.markdown('<div class="section-header">Urgences COVID & PCR+</div>',
                    unsafe_allow_html=True)
        fig2 = go.Figure()
        for col, color, lbl in [
            ("urg_covid",    "#8b5cf6", "Urgences COVID"),
            ("pcr_positifs", "#f59e0b", "PCR positifs"),
        ]:
            r2,g2,b2 = HEX_TO_RGB[color]
            fig2.add_trace(go.Scatter(
                x=ts_agg["date"], y=ts_agg[col], name=lbl,
                line=dict(color=color, width=2),
                fill="tozeroy", fillcolor=f"rgba({r2},{g2},{b2},0.08)",
            ))
        fig2.add_vline(**vline)
        fig2.update_layout(**CHART_LAYOUT)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    with st.expander("📋 Tableau des données chargées"):
        disp = ts_agg.copy()
        disp["date"] = disp["date"].dt.strftime("%d/%m/%Y")
        disp.columns = ["Date","Hospitalisés","Réanimation","Urgences COVID","PCR+","Décès"]
        st.dataframe(disp, use_container_width=True, hide_index=True)

# ─── FOOTER ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;font-size:11px;color:#374151;margin-top:24px;
            padding-top:16px;border-top:1px solid #1e2230;">
    Sources : <b>Santé Publique France</b> · <b>CSSE Johns Hopkins</b> ·
    Projet open-source <a href="https://github.com/kalisio/covid-19"
    style="color:#374151;" target="_blank">kalisio/covid-19</a> · Licence MIT
</div>
""", unsafe_allow_html=True)