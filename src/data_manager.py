import json
import pandas as pd
import streamlit as st
from datetime import date
from pathlib import Path
from src.config import BASE_DIR, FOLDERS, CLUSTER_CSV


def get_geojson_path(niveau: str, d: date) -> Path:
    folder = FOLDERS[niveau]
    return BASE_DIR / folder / f"{folder}-polygons-{d.isoformat()}.json"


@st.cache_data(show_spinner=False)
def load_geojson(path: str) -> dict | None:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def load_clusters(niveau: str) -> dict:
    path = CLUSTER_CSV[niveau]
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    nom_col = next(
        (c for c in df.columns if c.lower() in ["nom", "province/state", "name"]), None
    )
    if nom_col is None or "cluster" not in df.columns:
        return {}
    return {str(k): int(v) for k, v in zip(df[nom_col], df["cluster"])}


def geojson_to_df(gj: dict) -> pd.DataFrame:
    rows = []
    for feat in gj.get("features", []):
        p = feat.get("properties", {})

        def _get(obj_key, flat_key, sub):
            obj = p.get(obj_key, {})
            if isinstance(obj, dict):
                return obj.get(sub, 0) or 0
            return p.get(flat_key, 0) or 0

        rows.append({
            "nom":          p.get("Province/State", "?"),
            "hospitalises": p.get("Severe",   0) or 0,
            "reanimation":  p.get("Critical", 0) or 0,
            "deces":        p.get("Deaths",   0) or 0,
            "urg_covid":    _get("Emergencies", "Emergencies.Suspected", "Suspected"),
            "pcr_positifs": _get("PCRTests",    "PCRTests.Confirmed",    "Confirmed"),
        })
    return pd.DataFrame(rows)
