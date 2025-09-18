import streamlit as st

MAX_STEP = 4

def next_step() -> None:
    if st.session_state.step < MAX_STEP:
        st.session_state.step += 1  

def go_to_step(step_number: int) -> None:
    st.session_state.step = max(1, min(step_number, MAX_STEP)) 

def reset_and_go_to_step(step_number: int) -> None:
    st.session_state.chat_messages = [
        {"role": "assistant", "content": "안녕하세요. 다시 답변해주세요."} 
    ]
    st.session_state.diagnosis = {"triage_level": None, "summary": "", "hospitals": []} 
    st.session_state.show_location_modal = False  
    st.session_state.qa_pairs = 0  
    st.session_state.last_assistant_question = None
    st.session_state.yesno_options = None  
    st.session_state.ready_to_diagnose = False 
    st.session_state.step = max(1, min(step_number, MAX_STEP))  
