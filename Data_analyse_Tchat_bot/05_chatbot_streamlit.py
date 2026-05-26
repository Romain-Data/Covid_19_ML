import streamlit as st
import pandas as pd
import numpy as np
import joblib
import warnings
warnings.filterwarnings('ignore')

# Configuration simple de la page
st.set_page_config(
    page_title="Assistant COVID-19",
    page_icon="🏥",
    layout="centered"
)

# Liste stricte des 22 colonnes (l'ordre doit être identique au X_train)
FEATURE_COLUMNS = [
    'Fever', 'Tiredness', 'Dry-Cough', 'Difficulty-in-Breathing', 'Sore-Throat',
    'None_Sympton', 'Pains', 'Nasal-Congestion', 'Runny-Nose', 'Diarrhea',
    'None_Experiencing', 'Age_0-9', 'Age_10-19', 'Age_20-24', 'Age_25-59', 'Age_60+',
    'Gender_Female', 'Gender_Male', 'Gender_Transgender', 
    'Contact_Dont-Know', 'Contact_No', 'Contact_Yes'
]

# Chargement du modèle Random Forest
@st.cache_resource
def load_rf_model():
    try:
        model = joblib.load('best_covid_randomforest.pkl')
        return model
    except Exception as e:
        st.error(f"Impossible de charger le modèle Random Forest : {e}")
        return None

model = load_rf_model()

# Interface utilisateur
st.title("🏥 Assistant Diagnostic COVID-19 (Random Forest)")
st.write("Évaluation clinique optimisée et équilibrée.")

if model is None:
    st.error("🚨 Le fichier 'best_covid_randomforest.pkl' est introuvable.")
    st.stop()

# Formulaire unique du Chatbot
with st.form("chatbot_form"):
    st.subheader("📋 Profil du Patient")
    age_cat = st.selectbox("Tranche d'âge", ["0-9 ans", "10-19 ans", "20-24 ans", "25-59 ans", "60 ans et plus"])
    gender_cat = st.selectbox("Genre", ["Homme", "Femme", "Transgenre"])
    contact_cat = st.selectbox("Avez-vous été en contact avec un cas COVID-19 ?", ["Oui", "Non", "Je ne sais pas"])
    
    st.divider()
    st.subheader("🤒 Vos Symptômes")
    c1, c2 = st.columns(2)
    with c1:
        fever = st.checkbox("Fièvre")
        tiredness = st.checkbox("Fatigue inhabituelle")
        cough = st.checkbox("Toux Sèche")
        breathing = st.checkbox("Difficultés à respirer")
    with c2:
        throat = st.checkbox("Maux de gorge")
        pains = st.checkbox("Courbatures ou douleurs")
        congestion = st.checkbox("Congestion nasale")
        diarrhea = st.checkbox("Diarrhée")

    submit = st.form_submit_button("💬 Lancer le Diagnostic")

if submit:
    st.subheader("✨ Résultat du Modèle")
    
    # 1. Construction du dictionnaire initialisé à 0
    patient_data = {col: 0 for col in FEATURE_COLUMNS}
    
    # 2. Remplissage des symptômes
    patient_data['Fever'] = 1 if fever else 0
    patient_data['Tiredness'] = 1 if tiredness else 0
    patient_data['Dry-Cough'] = 1 if cough else 0
    patient_data['Difficulty-in-Breathing'] = 1 if breathing else 0
    patient_data['Sore-Throat'] = 1 if throat else 0
    patient_data['Pains'] = 1 if pains else 0
    patient_data['Nasal-Congestion'] = 1 if congestion else 0
    patient_data['Diarrhea'] = 1 if diarrhea else 0
    
    nb_symptomes = fever + tiredness + cough + breathing + throat + pains + congestion + diarrhea
    
    # 3. Encodage démographique
    if age_cat == "0-9 ans": patient_data['Age_0-9'] = 1
    elif age_cat == "10-19 ans": patient_data['Age_10-19'] = 1
    elif age_cat == "20-24 ans": patient_data['Age_20-24'] = 1
    elif age_cat == "25-59 ans": patient_data['Age_25-59'] = 1
    elif age_cat == "60 ans et plus": patient_data['Age_60+'] = 1

    if gender_cat == "Homme": patient_data['Gender_Male'] = 1
    elif gender_cat == "Femme": patient_data['Gender_Female'] = 1
    elif gender_cat == "Transgenre": patient_data['Gender_Transgender'] = 1

    if contact_cat == "Oui": patient_data['Contact_Yes'] = 1
    elif contact_cat == "Non": patient_data['Contact_No'] = 1
    elif contact_cat == "Je ne sais pas": patient_data['Contact_Dont-Know'] = 1

    # ============================================================================
    # SÉCURITÉ CLINIQUE : PATIENT PARFAITEMENT SAIN
    # ============================================================================
    if nb_symptomes == 0 and contact_cat == "Non":
        probability_percentage = 0
        is_covid = False
    else:
        # Encodage si aucun symptôme mais contact suspect
        if nb_symptomes == 0:
            patient_data['None_Sympton'] = 1
            patient_data['None_Experiencing'] = 1
            
        # 4. Conversion en DataFrame ordonné pour scikit-learn
        X_patient = pd.DataFrame([patient_data])[FEATURE_COLUMNS]

        # 5. Prédiction directe des probabilités par Random Forest
        # [0][1] permet de récupérer la probabilité de la classe 1 (Positif)
        prediction_proba = model.predict_proba(X_patient)[0][1]
        probability_percentage = int(prediction_proba * 100)
        
        is_covid = probability_percentage >= 50

    # 6. Affichage du Verdict
    if is_covid:
        st.error(f"🚨 **Verdict : Diagnostic POSITIF** (Confiance de l'IA : {probability_percentage}%)")
        st.write("Le modèle Random Forest estime que vos symptômes ou vos antécédents de contact concordent fortement avec un profil COVID-19.")
    else:
        st.success(f"✅ **Verdict : Diagnostic NÉGATIF** (Confiance de l'IA : {probability_percentage}%)")
        st.write("Le modèle Random Forest estime que le risque d'infection est faible au vu des éléments déclarés.")