import streamlit as st
import pandas as pd
import joblib
import warnings
import os
warnings.filterwarnings('ignore')

# ─── FEATURES — ordre identique au X_train du dataset réel ───────────────────
# Attention : 'Fatigue ' et 'Gastrointestinal ' contiennent un espace de fin
FEATURE_COLUMNS = [
    'Breathing Problem',
    'Fever',
    'Dry Cough',
    'Sore throat',
    'Running Nose',
    'Asthma',
    'Chronic Lung Disease',
    'Headache',
    'Heart Disease',
    'Diabetes',
    'Hyper Tension',
    'Fatigue ',
    'Gastrointestinal ',
    'Abroad travel',
    'Contact with COVID Patient',
    'Attended Large Gathering',
    'Visited Public Exposed Places',
    'Family working in Public Exposed Places',
]


# ─── Chargement du modèle ─────────────────────────────────────────────────────
@st.cache_resource
def load_model():
    possible_paths = [
        os.path.join("Data_analyse_Tchat_bot", "Dataset 2", "best_covid_randomforest_reel.pkl"),
        os.path.join(os.path.dirname(__file__), "..", "Data_analyse_Tchat_bot", "Dataset 2", "best_covid_randomforest_reel.pkl"),
        os.path.join(os.path.dirname(__file__), "best_covid_randomforest_reel.pkl"),
        "best_covid_randomforest_reel.pkl"
    ]
    for path in possible_paths:
        if os.path.exists(path):
            try:
                return joblib.load(path)
            except Exception:
                pass
    st.error("🚨 Fichier 'best_covid_randomforest_reel.pkl' introuvable.")
    return None


model = load_model()

# ─── Interface ────────────────────────────────────────────────────────────────
st.title("🏥 Assistant Diagnostic COVID-19")
st.caption("Basé sur un Random Forest entraîné sur données réelles — F1=0.988 | Accuracy 98%")

if model is None:
    st.stop()

with st.form("diagnostic_form"):

    # ── Bloc 1 : Symptômes cliniques ──────────────────────────────────────────
    st.subheader("🤒 Symptômes cliniques")
    col1, col2 = st.columns(2)

    with col1:
        breathing = st.checkbox("Difficultés à respirer")
        fever = st.checkbox("Fièvre")
        dry_cough = st.checkbox("Toux sèche")
        sore_throat = st.checkbox("Maux de gorge")
        running_nose = st.checkbox("Nez qui coule")
        headache = st.checkbox("Maux de tête")
        fatigue = st.checkbox("Fatigue inhabituelle")
        gastro = st.checkbox("Troubles gastro-intestinaux")

    with col2:
        asthma = st.checkbox("Asthme")
        lung = st.checkbox("Maladie pulmonaire chronique")
        heart = st.checkbox("Maladie cardiaque")
        diabetes = st.checkbox("Diabète")
        hypertension = st.checkbox("Hypertension")

    st.divider()

    # ── Bloc 2 : Contexte épidémiologique ────────────────────────────────────
    st.subheader("🌍 Contexte & Exposition")
    col3, col4 = st.columns(2)

    with col3:
        abroad = st.checkbox("Voyage à l'étranger récent")
        contact_covid = st.checkbox("Contact avec un cas COVID-19 confirmé")

    with col4:
        gathering = st.checkbox("Participation à un grand rassemblement")
        public_places = st.checkbox("Fréquentation de lieux publics exposés")
        family_public = st.checkbox("Membre de la famille travaillant en lieu exposé")

    st.divider()
    submit = st.form_submit_button("💬 Lancer le Diagnostic", use_container_width=True)

# ─── Prédiction ───────────────────────────────────────────────────────────────
if submit:

    # Construction du vecteur patient dans l'ordre exact des features
    patient = {
        'Breathing Problem': int(breathing),
        'Fever': int(fever),
        'Dry Cough': int(dry_cough),
        'Sore throat': int(sore_throat),
        'Running Nose': int(running_nose),
        'Asthma': int(asthma),
        'Chronic Lung Disease': int(lung),
        'Headache': int(headache),
        'Heart Disease': int(heart),
        'Diabetes': int(diabetes),
        'Hyper Tension': int(hypertension),
        'Fatigue ': int(fatigue),
        'Gastrointestinal ': int(gastro),
        'Abroad travel': int(abroad),
        'Contact with COVID Patient': int(contact_covid),
        'Attended Large Gathering': int(gathering),
        'Visited Public Exposed Places': int(public_places),
        'Family working in Public Exposed Places': int(family_public),
    }

    # Nombre total de facteurs cochés
    nb_facteurs = sum(patient.values())

    # ── Cas : aucun facteur coché ─────────────────────────────────────────────
    if nb_facteurs == 0:
        probability_pct = 0
        is_covid = False
    else:
        X_patient = pd.DataFrame([patient])[FEATURE_COLUMNS]
        proba = model.predict_proba(X_patient)[0][1]
        probability_pct = int(proba * 100)
        is_covid = probability_pct >= 50

    # ── Affichage du verdict ──────────────────────────────────────────────────
    st.subheader("📋 Résultat du Diagnostic")

    if is_covid:
        st.error(f"🚨 **Verdict : Risque ÉLEVÉ de COVID-19** — Confiance du modèle : **{probability_pct}%**")
        st.markdown(
            "Le modèle détecte un profil **fortement associé** au COVID-19 "
            "au vu des symptômes et du contexte épidémiologique déclarés. "
            "**Consultez un médecin et réalisez un test de dépistage.**"
        )
    else:
        st.success(f"✅ **Verdict : Risque FAIBLE de COVID-19** — Confiance du modèle : **{100 - probability_pct}%**")
        st.markdown(
            "Le modèle estime que votre profil **ne correspond pas** au profil "
            "typique d'un cas COVID-19. Surveillez l'évolution de vos symptômes."
        )

    # ── Jauge de probabilité ──────────────────────────────────────────────────
    st.divider()
    st.markdown("**Probabilité estimée COVID+ :**")
    st.progress(probability_pct / 100)
    st.caption(f"{probability_pct}% de probabilité de COVID-19 selon le Random Forest")

    # ── Facteurs déclenchants ─────────────────────────────────────────────────
    if nb_facteurs > 0:
        st.divider()
        facteurs_coches = [k.strip() for k, v in patient.items() if v == 1]

        # Facteurs à fort impact selon feature_importances_ (top 5 du modèle)
        TOP_FEATURES = {
            'Abroad travel', 'Sore throat', 'Attended Large Gathering',
            'Dry Cough', 'Breathing Problem'
        }
        forts = [f for f in facteurs_coches if f in TOP_FEATURES]
        autres = [f for f in facteurs_coches if f not in TOP_FEATURES]

        if forts:
            st.markdown("**⚠️ Facteurs à fort impact détectés :**")
            for f in forts:
                st.markdown(f"- {f}")

        if autres:
            st.markdown("**Autres facteurs déclarés :**")
            for f in autres:
                st.markdown(f"- {f}")

    # ── Disclaimer médical ────────────────────────────────────────────────────
    st.divider()
    st.info(
        "⚕️ **Avertissement** : Cet outil est un prototype pédagogique basé sur un "
        "modèle de machine learning (Random Forest, F1=0.988). Il ne remplace en aucun "
        "cas un avis médical. En cas de doute, consultez un professionnel de santé."
    )
