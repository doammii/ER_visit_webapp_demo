import streamlit as st
from callbacks import next_step

def display() -> None:
    st.markdown("#### 안녕하세요.")
    st.markdown("#### :blue[응급실 자가진단 AEGIS Talk]입니다.")
    st.markdown("#### :blue[환자분의 기본 정보]를 먼저 작성해주세요.")

    hx_options = [
        "심혈관 질환 (심근경색, 심부전, 말초혈관질환 등)",
        "호흡기 질환 (천식, 만성폐쇄성폐질환 등)",
        "암 (고형암, 혈액암, 림프암 등)",
        "간 질환 (간염, 간경화 등)",
        "신장 질환 (만성신부전, 투석 등)",
        "거동불가 (침상생활)",
        "당뇨병",
    ]
    NONE_LABEL = "해당없음"
    OTHER_LABEL = "기타"

    # 기존 기록(있다면)을 보여주되, 새 UI에서는 제출 시 덮어씌워진다.
    prev_history = st.session_state.patient_info.get("history", [])

    with st.form("patient_info_form", clear_on_submit=False):
        st.markdown("**성별**")
        st.session_state.patient_info["gender"] = st.radio(
            "성별", ["남자", "여자"], horizontal=True, label_visibility= "collapsed"
        )
        
        st.markdown("**나이(만)**")
        st.session_state.patient_info["age"] = int(
            st.number_input(
                "나이(만)",
                min_value=1,
                max_value=120,
                value=int(st.session_state.patient_info["age"]),
                step=1,
                label_visibility= "collapsed",
            )
        )
        
        st.markdown("**과거력**")
        st.caption(
            "과거 앓았거나 현재 앓고있는 질병을 전부 선택해주세요. 없다면, '해당없음'을 선택해주세요."
        )

        selected = []
        cols = st.columns(2)
        for i, opt in enumerate(hx_options):
            with cols[i % 2]:
                checked = st.checkbox(opt, key=f"hx_{i}")
                if checked:
                    selected.append(opt)

        # 기타 입력
        other_checked = st.checkbox(OTHER_LABEL, key="hx_other")

        other_text = ""

        if other_checked:
            other_text = st.text_input(
                "기타 과거력 입력",
                key="hx_other_text",
                placeholder="예시: 갑상선질환, 류마티스 등"
            )

        if other_checked and other_text.strip():
            selected.append(f"{OTHER_LABEL}: {other_text.strip()}")

        none_checked = st.checkbox(NONE_LABEL, key="hx_none")
        if none_checked:
            selected = []
        st.markdown("\n\n\n")

        st.markdown("**[개인정보 수집 및 이용 동의]**")
        st.write(
            "이 챗봇은 증상 분석을 위해 성별, 나이, 병력(민감정보 포함), 위치정보를 일시적으로 수집합니다.\n"
            "- 수집 목적: 응급실 방문 필요 여부 판단 및 응급실 정보 제공"
        )
        st.checkbox("위 내용을 읽고 동의합니다.", value=st.session_state.get("privacy_agree", False), key="privacy_agree")

        submitted = st.form_submit_button("자가진단 시작하기", use_container_width=True, type="primary")
        if submitted:
            if not st.session_state.get("privacy_agree", False):
                st.error("개인정보 수집 및 이용에 **동의**해 주세요.")
            else:
                st.session_state.patient_info["history"] = selected
                st.session_state.show_location_modal = True

    if st.session_state.get("show_location_modal", False):
        st.markdown("### [위치정보 제공 동의]")
        with st.container(border=True):
            st.write(
                "AEGIS Talk이(가) 사용자의 위치에 접근하도록 허용하겠습니까?"
            )
            c1, c2, c3= st.columns(3)
            app_yes = c1.button("앱을 사용하는 동안 허용", use_container_width=True, type="primary", key="loc_yes")
            once_yes = c2.button("한 번 허용", use_container_width=True, key="loc_once")
            no  = c3.button("허용 안 함", use_container_width=True, key="loc_no")

            if (app_yes or once_yes):
                st.session_state.location_consent = True
                st.session_state.show_location_modal = False
                next_step()
                st.rerun()

            if no:
                st.session_state.location_consent = False
                st.session_state.show_location_modal = False
                next_step()
                st.rerun()

        st.stop()
