import streamlit as st
from state import initialize_state
import step1_info, step2_chatbot, step3_triage, step4_report

st.set_page_config(page_title="AEGIS Talk", page_icon="🩺", layout="centered")

initialize_state()

# 앱 제목 및 단계 표시
st.title("AEGIS Talk")
step = st.session_state.step
step_labels = {1: "기본정보", 2: "챗봇 대화", 3: "응급실 방문여부 안내", 4: "요약 레포트"}
st.caption(f"진행 단계: {step} / 4 · {step_labels.get(step, '')}")

# 단계별 화면
if step == 1:
    step1_info.display()
elif step == 2:
    step2_chatbot.display()
elif step == 3:
    step3_triage.display()
elif step == 4:
    step4_report.display()
