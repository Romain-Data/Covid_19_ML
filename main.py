import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import streamlit.components.v1 as components
import plotly.graph_objects as go
import json
import copy
import branca.colormap as cm
from datetime import date, timedelta
from pathlib import Path

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
.metric-card {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    border: 1px solid #e2e8f0; border-radius: 12px;
    padding: 18px 22px; margin-bottom: 8px;
    position: relative; overflow: hidden;
}
.metric-card::before { content:''; position:absolute; top:0;left:0;right:0; height:3px; background:var(--accent); }
.metric-label { font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:1.5px; color:#6b7280; margin-bottom:6px; }
.metric-value { font-family:'JetBrains Mono',monospace; font-size:26px; font-weight:600; color:#1e293b; line-height:1; }
.section-header {
    font-size:13px; font-weight:600; text-transform:uppercase;
    letter-spacing:2px; color:#4b5563; margin:24px 0 12px 0;
    padding-bottom:6px; border-bottom:1px solid #e2e8f0;
}
.error-box {
    background:#fff1f2; border:1px solid #fecdd3; border-radius:8px;
    padding:16px; color:#9f1239; font-size:13px; margin:8px 0;
}
.info-box {
    background:#eff6ff; border:1px solid #bfdbfe; border-radius:8px;
    padding:12px 16px; color:#1d4ed8; font-size:12px; margin:8px 0;
}
</style>
""", unsafe_allow_html=True)

# ─── CONFIG ───────────────────────────────────────────────────────────────────
FOLDERS = {
    "Régions":      "regions-france",
    "Départements": "departements-france",
}

HEX_TO_RGB = {
    "#3b82f6": (59,130,246), "#ef4444": (239,68,68),
    "#6366f1": (99,102,241), "#8b5cf6": (139,92,246),
    "#f59e0b": (245,158,11),
}

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def build_path(niveau: str, target_date: date, polygons: bool = False) -> str:
    folder = FOLDERS[niveau]
    return f"{folder}/{folder}-polygons-{target_date.isoformat()}.json"


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

        # ── Sous-objets (le GeoJSON kalisio utilise des clés plates ET imbriquées)
        # FIX 3 : Gestion des deux formats possibles (plat ou imbriqué)
        def get_nested(props, key_nested, key_flat, subkey):
            """Cherche d'abord dans l'objet imbriqué, puis dans la clé plate."""
            nested = props.get(key_nested, {}) or {}
            if isinstance(nested, dict) and subkey in nested:
                return nested.get(subkey, 0) or 0
            return props.get(key_flat, 0) or 0

        emerg  = props.get("Emergencies", {}) or {}
        medact = props.get("MedicalActs", {}) or {}
        pcr    = props.get("PCRTests", {}) or {}
        pop    = props.get("Population", {}) or {}
        beds   = props.get("Beds", {}) or {}

        rows.append({
            "nom":          props.get("Province/State", "?"),
            "lat":          lat,
            "lon":          lon,
            # Hôpitaux
            "hospitalises": props.get("Severe", 0) or 0,
            "reanimation":  props.get("Critical", 0) or 0,
            "deces":        props.get("Deaths", 0) or 0,
            # Urgences — gestion format plat ET imbriqué
            "urg_total":    emerg.get("Total", 0) or props.get("Emergencies.Total", 0) or 0,
            "urg_covid":    emerg.get("Suspected", 0) or props.get("Emergencies.Suspected", 0) or 0,
            "urg_hosp":     emerg.get("Severe", 0) or props.get("Emergencies.Severe", 0) or 0,
            # SOS Médecins
            "sos_total":    medact.get("Total", 0) or props.get("MedicalActs.Total", 0) or 0,
            "sos_covid":    medact.get("Suspected", 0) or props.get("MedicalActs.Suspected", 0) or 0,
            # Tests PCR
            "pcr_total":    pcr.get("Total", 0) or props.get("PCRTests.Total", 0) or 0,
            "pcr_positifs": pcr.get("Confirmed", 0) or props.get("PCRTests.Confirmed", 0) or 0,
            # Population & lits
            "population":   pop.get("Total", 0) or props.get("Population.Total", 0) or 0,
            "lits_total":   beds.get("Total", 0) or props.get("Beds.Total", 0) or 0,
            "lits_rea":     beds.get("Resuscitation", 0) or props.get("Beds.Resuscitation", 0) or 0,
        })

    return pd.DataFrame(rows)


def load_clusters(niveau: str) -> dict:
    """
    FIX 4 : Recherche le fichier clusters dans plusieurs emplacements possibles.
    Retourne un dict {nom: cluster_id}.
    """
    base_dir = Path(__file__).parent
    niveau_key = niveau.lower().replace('é', 'e').replace('è', 'e')

    # Chemins possibles selon où le notebook a exporté les clusters
    candidates = [
        base_dir / "KMeans" / f"clusters_{niveau_key}.csv",
        base_dir / f"clusters_{niveau_key}.csv",
        base_dir / "data" / f"clusters_{niveau_key}.csv",
    ]

    for path in candidates:
        if path.exists():
            df = pd.read_csv(path)
            # Cherche la colonne nom (peut s'appeler 'nom', 'Province/State', 'name'...)
            nom_col = next((c for c in df.columns if c.lower() in ['nom', 'province/state', 'name']), None)
            if nom_col and 'cluster' in df.columns:
                return dict(zip(df[nom_col], df['cluster']))

    # Fallback : lire le cluster depuis les propriétés GeoJSON si injecté par le notebook
    return {}


# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div style="font-size:22px;font-weight:700;">🦠 COVID-19</div>',
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
    rv, gv, bv = HEX_TO_RGB[accent_color]

    st.markdown('<div class="section-header">Date (carte)</div>', unsafe_allow_html=True)
    date_sel = st.date_input(
        "Date sélectionnée",
        value=date(2020, 11, 15),
        min_value=date(2020, 3, 1),
        max_value=date(2021, 6, 30),
    )

    st.markdown('<div class="section-header">Carte</div>', unsafe_allow_html=True)
    show_labels = st.checkbox("Étiquettes sur la carte", value=False)

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

    folder = FOLDERS[niveau]
    st.markdown(f"""
    <div class="info-box">
    📡 Source : <code>Données locales</code><br>
    🗂️ Dossier : <code>{folder}</code>
    </div>
    """, unsafe_allow_html=True)


# ─── CHARGEMENT CARTE DU JOUR ─────────────────────────────────────────────────
path_jour = build_path(niveau, date_sel)

with st.spinner(f"⏳ Chargement — {date_sel.isoformat()} …"):
    gj_jour = fetch_geojson(path_jour)

if gj_jour is None:
    st.markdown(f"""
    <div class="error-box">
    ❌ <b>Fichier introuvable</b><br><br>
    Chemin testé : <code>{path_jour}</code><br><br>
    Causes possibles :<br>
    • Aucun fichier pour cette date dans le dossier<br>
    • Les données vont du <b>01/03/2020</b> au <b>~30/06/2021</b><br><br>
    👉 Essaie une autre date.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# FIX 5 : Ne pas faire deepcopy sur le GeoJSON chargé depuis le cache —
#          on travaille sur une copie locale pour ne pas polluer le cache
gj_poly = copy.deepcopy(gj_jour)
df_day  = geojson_to_df(gj_jour)

if df_day.empty:
    st.error("Le fichier GeoJSON est vide ou son format est inattendu.")
    with st.expander("Voir le JSON brut"):
        st.json(gj_jour)
    st.stop()


# ─── HEADER ──────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-bottom:16px;">
  <span style="font-size:22px;font-weight:700;">{emoji} {indicateur} — {niveau}</span>
  <span style="font-size:13px;color:#4b5563;margin-left:12px;">
    📅 {date_sel.strftime('%d %B %Y')}
  </span>
  &nbsp;
  <span style="font-size:11px;color:#9ca3af;">source : {path_jour}</span>
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
kpi(k1, indicateur,       df_day[col_key].sum(),        accent_color)
kpi(k2, "Hospitalisés",   df_day["hospitalises"].sum(),  "#3b82f6")
kpi(k3, "En réanimation", df_day["reanimation"].sum(),   "#ef4444")
kpi(k4, "Urgences COVID", df_day["urg_covid"].sum(),     "#8b5cf6")

st.markdown("---")

# ─── CARTE + GRAPHIQUES ───────────────────────────────────────────────────────
map_col, chart_col = st.columns([6, 4])

with map_col:
    st.markdown(
        f'<div class="section-header">Carte — {indicateur} ({date_sel.strftime("%d/%m/%Y")})</div>',
        unsafe_allow_html=True,
    )

    # Couleurs de contour par cluster
    if niveau == "Départements":
        CLUSTER_COLORS = {
            0: "#10b981",  # Vert   — modérément touchés
            1: "#eab308",  # Jaune  — grandes métropoles
            2: "#9ca3af",  # Gris   — zones rurales/données partielles
            3: "#ef4444",  # Rouge  — épicentres
           -1: "#d1d5db",  # Gris clair — non classé
        }
    else:
        CLUSTER_COLORS = {
            0: "#10b981",  # Vert   — régions préservées
            1: "#f59e0b",  # Orange — régions fortement touchées
            2: "#ef4444",  # Rouge  — Île-de-France
           -1: "#d1d5db",
        }

    # Chargement des clusters (depuis CSV ou propriété GeoJSON)
    cluster_map = load_clusters(niveau)

    # Enrichissement du GeoJSON avec les valeurs de l'indicateur et le cluster
    vals = []
    for feat in gj_poly["features"]:
        nom = feat["properties"].get("Province/State", "?")
        row = df_day[df_day["nom"] == nom]

        val  = int(row[col_key].values[0])      if not row.empty else 0
        hosp = int(row["hospitalises"].values[0]) if not row.empty else 0
        rea  = int(row["reanimation"].values[0])  if not row.empty else 0
        decs = int(row["deces"].values[0])        if not row.empty else 0

        vals.append(val)

        c_id = feat["properties"].get("cluster", cluster_map.get(nom, -1))
        if isinstance(c_id, float):
            c_id = int(c_id)

        feat["properties"]["_val"]         = val
        feat["properties"]["_cluster_id"]  = c_id
        feat["properties"]["_cluster_lbl"] = str(c_id) if c_id != -1 else "Non classé"
        feat["properties"]["_hosp"]        = hosp
        feat["properties"]["_rea"]         = rea
        feat["properties"]["_deces"]       = decs

    # Colormap pour le remplissage (indicateur principal)
    max_val = max(vals) if vals else 1
    colormap = cm.linear.Blues_09.scale(0, max_val)
    colormap.caption = indicateur

    # Création de la carte Folium
    m = folium.Map(location=[46.5, 2.5], zoom_start=5.5, tiles="CartoDB positron")

    def style_function(feature):
        val  = feature["properties"].get("_val", 0)
        c_id = feature["properties"].get("_cluster_id", -1)
        # Tronquer à 7 caractères pour garantir un code Hex #RRGGBB (sans l'Alpha)
        # car Leaflet/SVG peut échouer silencieusement avec un format RGBA hexadécimal
        return {
            "fillColor":   str(colormap(val))[:7],
            "fillOpacity": 0.75,
            "color":       CLUSTER_COLORS.get(c_id, "#d1d5db"),
            "weight":      3.5,
        }

    tooltip = folium.GeoJsonTooltip(
        fields=["Province/State", "_cluster_lbl", "_hosp", "_rea", "_deces", "_val"],
        aliases=["Territoire :", "Cluster :", "Hospitalisés :", "Réanimation :", "Décès :", f"{indicateur} :"],
        style="background-color:white;color:#333;font-family:arial;font-size:13px;padding:10px;",
    )

    folium.GeoJson(
        gj_poly,
        style_function=style_function,
        tooltip=tooltip,
    ).add_to(m)

    colormap.add_to(m)

    # Légende clusters (HTML custom)
    legend_items = "".join([
        f'<div style="display:flex;align-items:center;gap:6px;margin:3px 0;">'
        f'<div style="width:16px;height:4px;background:{color};border-radius:2px;"></div>'
        f'<span style="font-size:11px;color:#374151;">Cluster {k}</span></div>'
        for k, color in CLUSTER_COLORS.items() if k != -1
    ])
    legend_html = f"""
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;
                background:white;padding:10px 14px;border-radius:8px;
                border:1px solid #e5e7eb;box-shadow:0 2px 8px rgba(0,0,0,.1);">
        <div style="font-size:11px;font-weight:600;color:#6b7280;
                    text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">
            Clusters (contour)
        </div>
        {legend_items}
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # Remplacement de st_folium par components.html pour éviter l'écran blanc
    components.html(m._repr_html_(), height=480)


# ── GRAPHIQUES ────────────────────────────────────────────────────────────────
with chart_col:
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
    st.plotly_chart(fig_bar, width='stretch', config={"displayModeBar": False})


# ─── SÉRIE TEMPORELLE ─────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-header">Évolution temporelle</div>',
            unsafe_allow_html=True)

cache_key = f"{niveau}|{ts_start}|{ts_end}|{ts_step}"
load_btn  = st.button("🔄 Charger / Rafraîchir la série temporelle")

if load_btn or ("ts_cache_key" in st.session_state and
                st.session_state["ts_cache_key"] != cache_key):

    n_calls  = max(1, (ts_end - ts_start).days // ts_step + 1)
    progress = st.progress(0, text=f"Chargement de ~{n_calls} fichiers…")
    frames   = []
    current  = ts_start
    idx      = 0

    while current <= ts_end:
        path = build_path(niveau, current)
        gj   = fetch_geojson(path)
        if gj:
            df_t = geojson_to_df(gj)
            df_t["date"] = pd.Timestamp(current)
            frames.append(df_t)
        current += timedelta(days=ts_step)
        idx += 1
        progress.progress(min(idx / n_calls, 1.0), text=f"← {current.isoformat()}")

    progress.empty()
    st.session_state["ts_df"]        = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    st.session_state["ts_cache_key"] = cache_key

ts_df = st.session_state.get("ts_df", pd.DataFrame())

if ts_df.empty:
    st.markdown("""
    <div class="info-box">
    ℹ️ Clique sur <b>Charger / Rafraîchir</b> pour charger les données sur la période.<br>
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
        xaxis=dict(gridcolor="#e5e7eb", tickfont=dict(color="#4b5563", size=10), showgrid=False),
        yaxis=dict(gridcolor="#e5e7eb", tickfont=dict(color="#4b5563", size=10), gridwidth=0.5),
    )
    vline = dict(x=pd.Timestamp(date_sel), line_dash="dash",
                 line_color="rgba(100,100,100,0.4)", line_width=1.5)

    with c1:
        st.markdown('<div class="section-header">Hospitalisés & Réanimation</div>',
                    unsafe_allow_html=True)
        fig1 = go.Figure()
        for col, color, lbl in [
            ("hospitalises", "#3b82f6", "Hospitalisés"),
            ("reanimation",  "#ef4444", "Réanimation"),
        ]:
            r2, g2, b2 = HEX_TO_RGB[color]
            fig1.add_trace(go.Scatter(
                x=ts_agg["date"], y=ts_agg[col], name=lbl,
                line=dict(color=color, width=2),
                fill="tozeroy", fillcolor=f"rgba({r2},{g2},{b2},0.08)",
            ))
        fig1.add_vline(**vline)
        fig1.update_layout(**CHART_LAYOUT)
        st.plotly_chart(fig1, width='stretch', config={"displayModeBar": False})

    with c2:
        st.markdown('<div class="section-header">Urgences COVID & PCR+</div>',
                    unsafe_allow_html=True)
        fig2 = go.Figure()
        for col, color, lbl in [
            ("urg_covid",    "#8b5cf6", "Urgences COVID"),
            ("pcr_positifs", "#f59e0b", "PCR positifs"),
        ]:
            r2, g2, b2 = HEX_TO_RGB[color]
            fig2.add_trace(go.Scatter(
                x=ts_agg["date"], y=ts_agg[col], name=lbl,
                line=dict(color=color, width=2),
                fill="tozeroy", fillcolor=f"rgba({r2},{g2},{b2},0.08)",
            ))
        fig2.add_vline(**vline)
        fig2.update_layout(**CHART_LAYOUT)
        st.plotly_chart(fig2, width='stretch', config={"displayModeBar": False})

    with st.expander("📋 Tableau des données chargées"):
        disp = ts_agg.copy()
        disp["date"] = disp["date"].dt.strftime("%d/%m/%Y")
        disp.columns = ["Date", "Hospitalisés", "Réanimation", "Urgences COVID", "PCR+", "Décès"]
        st.dataframe(disp, width='stretch', hide_index=True)

# ─── FOOTER ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;font-size:11px;color:#9ca3af;margin-top:24px;
            padding-top:16px;border-top:1px solid #e5e7eb;">
    Sources : <b>Santé Publique France</b> · <b>CSSE Johns Hopkins</b> ·
    Projet open-source <a href="https://github.com/kalisio/covid-19"
    style="color:#9ca3af;" target="_blank">kalisio/covid-19</a> · Licence MIT
</div>
""", unsafe_allow_html=True)