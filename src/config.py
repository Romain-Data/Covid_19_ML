from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).parent.parent
DATE_MIN = date(2020, 3, 1)
DATE_MAX = date(2021, 6, 30)
DATE_DEF = date(2020, 11, 15)

FOLDERS = {
    "Régions":      "regions-france",
    "Départements": "departements-france",
}

CLUSTER_CSV = {
    "Régions":      BASE_DIR / "KMeans" / "clusters_regions.csv",
    "Départements": BASE_DIR / "KMeans" / "clusters_departements.csv",
}

CLUSTER_COLORS = {
    0:  "#22c55e",  # vert   – peu touchés
    1:  "#f59e0b",  # ambre  – moyennement touchés
    2:  "#ef4444",  # rouge  – fortement touchés
    3:  "#7c3aed",  # violet – épicentres (départements)
    -1: "#cbd5e1",  # gris   – non classé
}

CLUSTER_LABELS = {
    "Départements": {
        0: ("Peu touchés",         "Zones rurales à faible densité, impact épidémique limité sur toute la période."),
        1: ("Modérément touchés",  "Villes moyennes avec une pression hospitalière contenue."),
        2: ("Zones intermédiaires","Impact significatif, données partielles sur les cas confirmés."),
        3: ("Épicentres",          "Grandes métropoles concentrant les hospitalisations et décès les plus élevés."),
    },
    "Régions": {
        0: ("Régions préservées",        "Faible volume sur tous les indicateurs, système hospitalier non saturé."),
        1: ("Régions fortement touchées","Volume élevé mais capacité hospitalière maintenue proportionnellement."),
        2: ("Épicentre national",        "Île-de-France seule — indicateurs 3 à 10× supérieurs aux autres régions."),
    },
}

INDICATEURS = {
    "Hospitalisations":   ("hospitalises",  "#3b82f6"),
    "Réanimations":       ("reanimation",   "#ef4444"),
    "Décès cumulés":      ("deces",         "#6366f1"),
    "Urgences COVID":     ("urg_covid",     "#8b5cf6"),
    "Tests PCR positifs": ("pcr_positifs",  "#f59e0b"),
}
