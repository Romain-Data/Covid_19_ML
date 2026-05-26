import streamlit as st
import pydeck as pdk
import branca.colormap as cm
from src.config import CLUSTER_COLORS, CLUSTER_LABELS


def hex_to_rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i+2], 16) for i in (0, 2, 4)]


def render_map(gj, indicateur, date_sel, clusters, df_day, col_key, niveau="Départements"):
    # Enrichissement GeoJSON
    vals = []
    for feat in gj["features"]:
        nom  = feat["properties"].get("Province/State", "?")
        row  = df_day[df_day["nom"] == nom]
        val  = int(row[col_key].values[0])       if not row.empty else 0
        hosp = int(row["hospitalises"].values[0]) if not row.empty else 0
        rea  = int(row["reanimation"].values[0])  if not row.empty else 0
        decs = int(row["deces"].values[0])        if not row.empty else 0
        vals.append(val)

        # Cluster : propriété GeoJSON en priorité, puis CSV, puis -1
        c_id = feat["properties"].get("cluster", clusters.get(nom, -1))
        try:
            c_id = int(c_id)
        except (ValueError, TypeError):
            c_id = -1

        feat["properties"].update({
            "_val":   val,
            "_cid":   c_id,
            "_clbl":  f"Cluster {c_id}" if c_id >= 0 else "Non classé",
            "_hosp":  hosp,
            "_rea":   rea,
            "_deces": decs,
        })

    max_val  = max(vals) if vals else 1
    colormap = cm.linear.Blues_09.scale(0, max_val)  # type: ignore


    st.markdown(
        f'<div class="sec-title">Carte — {indicateur} · {date_sel.strftime("%d/%m/%Y")}'
        f'&nbsp;&nbsp;<span style="font-weight:400;color:#cbd5e1;">|&nbsp; contour = cluster · remplissage = {indicateur.lower()}</span></div>',
        unsafe_allow_html=True,
    )

    # Ajout des couleurs directement dans les properties du GeoJSON pour Pydeck
    for feat in gj.get("features", []):
        val = feat["properties"].get("_val", 0)
        c_id = feat["properties"].get("_cid", -1)
        
        fill_hex = str(colormap(val))[:7]
        feat["properties"]["_fill_color"] = hex_to_rgb(fill_hex) + [200]
        
        line_hex = CLUSTER_COLORS.get(c_id, "#cbd5e1")
        feat["properties"]["_line_color"] = hex_to_rgb(line_hex) + [255]

    layer = pdk.Layer(
        "GeoJsonLayer",
        gj,
        opacity=0.8,
        stroked=True,
        filled=True,
        extruded=False,
        wireframe=True,
        get_fill_color="properties._fill_color",
        get_line_color="properties._line_color",
        get_line_width=3000,
        line_width_min_pixels=2,
        pickable=True,
    )

    import copy
    gj_highlight = copy.deepcopy(gj)
    gj_highlight["features"] = [f for f in gj_highlight.get("features", []) if f["properties"].get("_cid", -1) >= 2]

    layer_highlight = pdk.Layer(
        "GeoJsonLayer",
        gj_highlight,
        opacity=1.0,
        stroked=True,
        filled=False,
        extruded=False,
        wireframe=True,
        get_line_color="properties._line_color",
        get_line_width=3000,
        line_width_min_pixels=3,
        pickable=False,
        parameters={"depthTest": False},
    )

    view_state = pdk.ViewState(
        latitude=46.6,
        longitude=2.5,
        zoom=4.8,
        pitch=0,
    )
    
    tooltip = {
        "html": "<b>{Province/State}</b><br/>"
                "Cluster: {_clbl}<br/>"
                "Hospitalisés: {_hosp}<br/>"
                "Réanimation: {_rea}<br/>"
                "Décès: {_deces}<br/>"
                f"{indicateur}: {{_val}}",
        "style": {
            "backgroundColor": "white",
            "color": "#1e293b",
            "fontFamily": "DM Sans, sans-serif",
            "border": "1px solid #e2e8f0",
            "borderRadius": "8px",
            "boxShadow": "0 4px 16px rgba(0,0,0,.08)",
            "padding": "8px 12px"
        }
    }

    r = pdk.Deck(
        layers=[layer, layer_highlight],
        initial_view_state=view_state,
        map_style=pdk.map_styles.LIGHT,
        tooltip=tooltip,
    )
    
    st.pydeck_chart(r, width='stretch')

    # Légende clusters sous la carte
    labels = CLUSTER_LABELS.get(niveau, {})
    keys = sorted(k for k in labels if k >= 0) if labels else sorted(k for k in CLUSTER_COLORS if k >= 0)
    items = "".join([
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<div style="width:20px;height:4px;background:{CLUSTER_COLORS[k]};border-radius:2px;"></div>'
        f'<span style="font-size:11px;color:#374151;font-family:DM Sans,sans-serif;">Cluster {k}</span></div>'
        for k in keys
    ])
    st.markdown(f"""
    <div style="margin-top: 10px; padding: 12px 16px; border-radius: 10px; background: #f8fafc; border: 1px solid #e2e8f0;">
        <div style="font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:2px;color:#94a3b8;margin-bottom:8px;">
            Clusters (contour)
        </div>
        <div style="display:flex; gap:16px; flex-wrap:wrap;">
            {items}
        </div>
    </div>
    """, unsafe_allow_html=True)
