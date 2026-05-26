import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import timedelta


def render_top_10(df_day, col_key, indicateur, accent_color):
    st.markdown(f'<div class="sec-title">Top 10 — {indicateur}</div>', unsafe_allow_html=True)

    top10 = df_day.nlargest(10, col_key)[["nom", col_key]].sort_values(col_key)
    n     = max(len(top10) - 1, 1)
    r, g, b = bytes.fromhex(accent_color.lstrip("#"))
    bar_colors = [f"rgba({r},{g},{b},{0.25 + 0.75 * i / n:.2f})" for i in range(len(top10))]

    fig = go.Figure(go.Bar(
        x=top10[col_key], y=top10["nom"], orientation="h",
        marker=dict(color=bar_colors, line=dict(width=0)),
        text=top10[col_key].apply(lambda v: f"{int(v):,}"),
        textposition="outside",
        textfont=dict(color="#94a3b8", size=10, family="DM Mono"),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=65, t=0, b=0), height=420,
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(tickfont=dict(color="#475569", size=11, family="DM Sans")),
    )
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})


def render_time_series(ts_agg, date_sel):
    vline_kw = dict(
        x=int(pd.Timestamp(date_sel).timestamp() * 1000), line_dash="dot",
        line_color="#94a3b8", line_width=1.5,
        annotation_text=date_sel.strftime("%d/%m"),
        annotation_font=dict(size=9, color="#94a3b8"),
    )
    layout_kw = dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=8, b=0), height=190,
        font=dict(family="DM Sans"),
        legend=dict(font=dict(color="#94a3b8", size=10),
                    bgcolor="rgba(0,0,0,0)", orientation="h", y=-0.45),
        xaxis=dict(showgrid=False, tickfont=dict(color="#94a3b8", size=10), zeroline=False),
        yaxis=dict(gridcolor="#f1f5f9", tickfont=dict(color="#94a3b8", size=10), gridwidth=1),
    )

    c1, c2 = st.columns(2)
    series = [
        (c1, "Hospitalisés & Réanimation",
         [("hospitalises", "#3b82f6", "Hospitalisés"), ("reanimation", "#ef4444", "Réanimation")]),
        (c2, "Urgences COVID & PCR+",
         [("urg_covid", "#8b5cf6", "Urgences COVID"), ("pcr_positifs", "#f59e0b", "PCR+")]),
    ]
    for col_widget, title, traces in series:
        with col_widget:
            st.markdown(f'<div class="sec-title">{title}</div>', unsafe_allow_html=True)
            fig = go.Figure()
            for col_name, color, lbl in traces:
                ri, gi, bi = bytes.fromhex(color.lstrip("#"))
                fig.add_trace(go.Scatter(
                    x=ts_agg["date"], y=ts_agg[col_name], name=lbl,
                    line=dict(color=color, width=2),
                    fill="tozeroy", fillcolor=f"rgba({ri},{gi},{bi},0.07)",
                ))
            fig.add_vline(**vline_kw)
            fig.update_layout(**layout_kw)
            st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
