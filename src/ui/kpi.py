import streamlit as st


def render_kpis(indicateur, df_day, col_key, accent_color):
    st.markdown(
        f'<h2 style="font-size:20px;font-weight:600;color:#0f172a;margin:0 0 16px 0;">'
        f'{indicateur}'
        f'<span style="font-size:13px;font-weight:400;color:#94a3b8;margin-left:12px;">'
        f'📅 Somme nationale</span></h2>',
        unsafe_allow_html=True,
    )

    def kpi_card(label, val, color):
        return (f'<div class="kpi-card" style="--c:{color};">'
                f'<div class="kpi-label">{label}</div>'
                f'<div class="kpi-value">{int(val):,}</div></div>')

    st.markdown(
        '<div class="kpi-row">'
        + kpi_card(indicateur,       df_day[col_key].sum(),        accent_color)
        + kpi_card("Hospitalisés",   df_day["hospitalises"].sum(),  "#3b82f6")
        + kpi_card("En réanimation", df_day["reanimation"].sum(),   "#ef4444")
        + kpi_card("Urgences COVID", df_day["urg_covid"].sum(),     "#8b5cf6")
        + '</div>',
        unsafe_allow_html=True,
    )
