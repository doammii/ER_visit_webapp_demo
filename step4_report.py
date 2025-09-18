import streamlit as st
from datetime import datetime
from callbacks import go_to_step

def display() -> None:
    st.markdown(
        """
        <style>
        /* 페이지 폭 좁게, 가운데 정렬 */
        .report-wrap { max-width: 420px; margin: 0 auto; }

        /* 상단 제목/타임스탬프 */
        .report-title { text-align:center; font-weight:700; font-size:20px; margin: 6px 0 4px; }
        .report-ts { text-align:center; color:#6b7280; font-size:12px; margin-bottom: 10px; }

        /* 권고 배너 */
        .badge { display:block; text-align:center; color:#fff; font-weight:700; 
                 border-radius:10px; padding:10px 14px; margin: 10px auto 16px; width: 90%; }
        .badge-emg { background:#f80501; }   /* 응급실 */
        .badge-out { background:#08ec10; }   /* 외래 */
        .badge-home{ background:#255b98; }   /* 휴식 */

        /* 섹션 타이틀 */
        .sec-title { font-weight:700; font-size:16px; margin: 8px 0; }

        /* 정보 카드 3분할 */
        .info-card { background:#f8fafc; border:1px solid #e5e7eb; border-radius:10px; padding:10px; text-align:center; }
        .info-key { color:#6b7280; font-size:12px; margin-bottom:6px; }
        .info-val { font-weight:700; font-size:16px; }

        /* 요약 라인 카드 */
        .line-card { background:#f3f4f6; border:1px solid #e5e7eb; border-radius:10px; padding:10px 12px; margin:8px 0; color:#111827; }

        /* 하단 버튼 중앙 */
        .btn-wrap { display:flex; justify-content:center; margin-top:14px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    now = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")
    p_info = st.session_state.patient_info
    diagnosis_summary = st.session_state.diagnosis.get("summary", "")
    triage_level = st.session_state.diagnosis.get("triage_level")

    with st.container():
        st.markdown('<div class="report-wrap">', unsafe_allow_html=True)

        st.markdown('<div class="report-title">응급실 자가진단 요약 레포트</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="report-ts">레포트 저장 시각: {now}</div>', unsafe_allow_html=True)

        if triage_level == "emergency":
            st.markdown('<div class="badge badge-emg">응급실 방문 권장</div>', unsafe_allow_html=True)
        elif triage_level == "outpatient":
            st.markdown('<div class="badge badge-out">외래 진료 권장</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="badge badge-home">집에서 상태 확인</div>', unsafe_allow_html=True)

        st.markdown('<div class="sec-title">환자 기본 정보</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(
                f"""
                <div class="info-card">
                  <div class="info-key">성별</div>
                  <div class="info-val">{p_info['gender']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""
                <div class="info-card">
                  <div class="info-key">나이</div>
                  <div class="info-val">만 {p_info['age']}세</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c3:
            hist = ", ".join(p_info.get("history", [])) if p_info.get("history") else "과거력 없음"
            st.markdown(
                f"""
                <div class="info-card">
                  <div class="info-key">과거력</div>
                  <div class="info-val">{hist}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # 환자 자가진단 요약
        st.markdown('<div class="sec-title">환자 자가진단 요약</div>', unsafe_allow_html=True)
        if diagnosis_summary:
            for line in [l for l in diagnosis_summary.splitlines() if l.strip()]:
                st.markdown(f'<div class="line-card">{line.strip()}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="line-card">요약 내용이 없습니다.</div>', unsafe_allow_html=True)

        st.markdown('<div class="btn-wrap">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1, 1]) 
        with col2:
            st.button(
                "처음 화면으로 돌아가기",
                on_click=go_to_step,
                args=[1],
                type="primary"
            )
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True) 
