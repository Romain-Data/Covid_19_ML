import time
import streamlit as st


st.markdown('<h1 style="color:#0f172a;">Aide au diagnostique</h1>', unsafe_allow_html=True)
st.markdown("Répondez à quelques questions pour obtenir un pré-diagnostic basé sur vos symptômes.")


QUESTIONS = [
    {
        "id": "age",
        "text": "Quel est votre âge ?",
        "choices": ["0-9 ans", "10-19 ans", "20-24 ans", "25-59 ans", "60+ ans"],
        "mapping": {"0-9 ans": "Age_0-9", "10-19 ans": "Age_10-19", "20-24 ans": "Age_20-24", "25-59 ans": "Age_25-59", "60+ ans": "Age_60+"}
    },
    {
        "id": "gender",
        "text": "Quel est votre genre ?",
        "choices": ["Femme", "Homme", "Autre"],
        "mapping": {"Femme": "Gender_Female", "Homme": "Gender_Male", "Transgenre": "Gender_Transgender"}
    },
    {
        "id": "contact",
        "text": "Avez-vous été en contact avec une personne testée positive ?",
        "choices": ["Oui", "Non", "Ne sait pas"],
        "mapping": {"Oui": "Contact_Yes", "Non": "Contact_No", "Ne sait pas": "Contact_Dont-Know"}
    },
    {
        "id": "fever",
        "text": "Avez-vous de la fièvre ?",
        "choices": ["Oui", "Non"],
        "mapping": {"Oui": "Fever"}
    },
    {
        "id": "tiredness",
        "text": "Ressentez-vous une grande fatigue ?",
        "choices": ["Oui", "Non"],
        "mapping": {"Oui": "Tiredness"}
    },
    {
        "id": "dry_cough",
        "text": "Avez-vous une toux sèche ?",
        "choices": ["Oui", "Non"],
        "mapping": {"Oui": "Dry-Cough"}
    },
    {
        "id": "breathing",
        "text": "Avez-vous des difficultés à respirer ?",
        "choices": ["Oui", "Non"],
        "mapping": {"Oui": "Difficulty-in-Breathing"}
    },
    {
        "id": "throat",
        "text": "Avez-vous des maux de gorge ?",
        "choices": ["Oui", "Non"],
        "mapping": {"Oui": "Sore-Throat"}
    },
    {
        "id": "pains",
        "text": "Ressentez-vous des douleurs corporelles ?",
        "choices": ["Oui", "Non"],
        "mapping": {"Oui": "Pains"}
    },
    {
        "id": "nasal",
        "text": "Avez-vous une congestion nasale ?",
        "choices": ["Oui", "Non"],
        "mapping": {"Oui": "Nasal-Congestion"}
    },
    {
        "id": "runny_nose",
        "text": "Avez-vous le nez qui coule ?",
        "choices": ["Oui", "Non"],
        "mapping": {"Oui": "Runny-Nose"}
    },
    {
        "id": "diarrhea",
        "text": "Avez-vous la diarrhée ?",
        "choices": ["Oui", "Non"],
        "mapping": {"Oui": "Diarrhea"}
    }
]


EXPECTED_COLUMNS = [
    "Fever", "Tiredness", "Dry-Cough", "Difficulty-in-Breathing", "Sore-Throat", "None_Sympton",
    "Pains", "Nasal-Congestion", "Runny-Nose", "Diarrhea", "None_Experiencing",
    "Age_0-9", "Age_10-19", "Age_20-24", "Age_25-59", "Age_60+",
    "Gender_Female", "Gender_Male", "Gender_Transgender",
    "Contact_Dont-Know", "Contact_No", "Contact_Yes"
]

# Initialisation session_state
if "step" not in st.session_state:
    st.session_state.step = 0
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Ajouter la première question
    st.session_state.messages.append({"role": "assistant", "content": QUESTIONS[0]["text"]})
if "user_data" not in st.session_state:
    st.session_state.user_data = {}

# Afficher l'historique du chat
if len(st.session_state.messages) > 1:
    with st.expander("Questions précédentes", expanded=False):
        for msg in st.session_state.messages[:-1]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
    last_msg = st.session_state.messages[-1]
    with st.chat_message(last_msg["role"]):
        st.markdown(last_msg["content"])
else:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


# Prédiction
def dummy_predict(data_dict):
    """Fonction fictive de prédiction"""
    time.sleep(2)
    # Simple logique fictive basée sur la fièvre ou le contact
    if data_dict.get("Fever", 0) == 1 and data_dict.get("Difficulty-in-Breathing", 0) == 1:
        return "Risque élevé de Covid-19. Veuillez consulter un médecin."
    elif data_dict.get("Contact_Yes", 0) == 1:
        return "Risque modéré. Vous êtes cas contact, surveillez vos symptômes."
    else:
        return "Risque faible. Continuez à respecter les gestes barrières."


def compile_data():
    """Prépare le dictionnaire final avec des 0 et des 1"""
    final_data = {col: 0 for col in EXPECTED_COLUMNS}
    
    # Remplissage à partir des réponses
    for q_id, answer in st.session_state.user_data.items():
        q_info = next(q for q in QUESTIONS if q["id"] == q_id)
        if answer in q_info["mapping"]:
            col_name = q_info["mapping"][answer]
            final_data[col_name] = 1
            
    # Gestion des None_Sympton et None_Experiencing
    if not any(final_data[col] for col in ["Fever", "Tiredness", "Dry-Cough", "Difficulty-in-Breathing", "Sore-Throat"]):
        final_data["None_Sympton"] = 1
        
    if not any(final_data[col] for col in ["Pains", "Nasal-Congestion", "Runny-Nose", "Diarrhea"]):
        final_data["None_Experiencing"] = 1
        
    return final_data


if st.session_state.step < len(QUESTIONS):
    current_q = QUESTIONS[st.session_state.step]
    
    # Afficher les choix pour la question courante via des pills
    # On utilise key avec le step pour forcer le rafraîchissement
    selection = st.pills(
        "Votre réponse :", 
        options=current_q["choices"], 
        key=f"pill_{st.session_state.step}",
        label_visibility="collapsed"
    )
    
    if selection:
        # Enregistrer la réponse
        st.session_state.user_data[current_q["id"]] = selection
        st.session_state.messages.append({"role": "user", "content": selection})
        
        # Passer à la question suivante
        st.session_state.step += 1

        # Pause pour effet naturel
        time.sleep(0.5)
        
        # Ajouter la prochaine question ou terminer
        if st.session_state.step < len(QUESTIONS):
            next_q = QUESTIONS[st.session_state.step]
            st.session_state.messages.append({"role": "assistant", "content": next_q["text"]})
        else:
            st.session_state.messages.append({"role": "assistant", "content": "Merci pour vos réponses. Je prépare votre diagnostique..."})
            
        st.rerun()

else:
    # Fin du questionnaire
    if "prediction_done" not in st.session_state:
        # Afficher le spinner
        with st.chat_message("assistant"):
            with st.spinner("Diagnostique en cours..."):
                final_features = compile_data()
                result = dummy_predict(final_features)
                st.session_state.prediction_result = result
                st.session_state.final_features = final_features
                st.session_state.prediction_done = True
        
        st.session_state.messages.append({"role": "assistant", "content": st.session_state.prediction_result})
        st.rerun()
    else:
        # Afficher un résumé des données envoyées (optionnel)
        with st.expander("Voir les données envoyées au modèle"):
            st.json(st.session_state.final_features)
        
        if st.button("Recommencer le test"):
            st.session_state.clear()
            st.rerun()
