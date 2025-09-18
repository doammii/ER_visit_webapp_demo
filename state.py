import streamlit as st

def initialize_state() -> None:
    if "step" not in st.session_state:
        st.session_state.step = 1

    if "patient_info" not in st.session_state:
        st.session_state.patient_info = {"gender": "남자", "age": 50, "history": ["고혈압"]}

    if "location_consent" not in st.session_state:
        st.session_state.location_consent = False

    if "show_location_modal" not in st.session_state:
        st.session_state.show_location_modal = False

    if "privacy_agree" not in st.session_state:
        st.session_state.privacy_agree = False

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {"role": "assistant", "content": "지금 어디가 가장 불편하신가요?"}
        ]

    if "diagnosis" not in st.session_state:
        st.session_state.diagnosis = {"triage_level": None, "summary": "", "hospitals": []}

    if "qa_pairs" not in st.session_state:
        st.session_state.qa_pairs = 0

    if "last_assistant_question" not in st.session_state:
        st.session_state.last_assistant_question = None

    if "yesno_options" not in st.session_state:
        st.session_state.yesno_options = None

    if "ready_to_diagnose" not in st.session_state:
        st.session_state.ready_to_diagnose = False

    if "slots" not in st.session_state:
        st.session_state.slots = {                      
            "sob_at_rest": None,            
            "gi_combo": None,            
            "pain_worse_with_move": None,   
            "chest_pain_duration": None,   
        }

    if "asked_questions" not in st.session_state:
        st.session_state.asked_questions = []               
