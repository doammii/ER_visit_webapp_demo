import streamlit as st
from callbacks import go_to_step, reset_and_go_to_step

def center_text(
    text: str,
    size: str = "medium",
    bold: bool = False,
    margin_px: int = 8,
    color: str = "#111827",
) -> None:
    sizes = {"small": "16px", "medium": "20px", "large": "26px"}
    weight = "bold" if bold else "normal"
    st.markdown(
        f"""
        <div style="
            text-align:center;
            font-size:{sizes.get(size,'20px')};
            font-weight:{weight};
            line-height:1.35;
            margin:{margin_px}px 0;
            color:{color};
        ">{text}</div>
        """,
        unsafe_allow_html=True,
    )

def vspace(px: int = 12):
    st.markdown(f"<div style='height:{px}px'></div>", unsafe_allow_html=True)

def display() -> None:
    triage_level = st.session_state.diagnosis.get("triage_level")
    show_hospital_list = False

    if triage_level == "emergency":
        center_text("🚨 응급실 방문을 권장합니다 🚨", size="large", bold=True, margin_px=10, color="#f80501")
        center_text(
            "빠른 응급실 방문을 위해, 응급실 안내를 도와드릴게요. 방문 전 전화확인 후 내원하시길 안내드립니다.",
            size="small",
        )
        show_hospital_list = True
    elif triage_level == "outpatient":
        center_text("👨‍⚕️ 외래 진료를 권장합니다 👨‍⚕️", size="large", bold=True, margin_px=10, color="#08ec10")
        center_text("외래 진료받을 수 있는 병원 안내를 도와드릴게요.", size="small")
        show_hospital_list = True
    else:
        center_text("🏠 집에서 상태를 확인하며 휴식을 취하세요 🏠", size="large", bold=True, margin_px=10)
        center_text("증상이 심해지거나 새로운 증상이 나타나면 다시 진단해주세요.", size="small")

    vspace(10)

    # 병원 리스트
    if show_hospital_list:
        st.write("---")
        center_text("주변 병원 정보", size="large", bold=True, margin_px=6)

        hospitals = st.session_state.diagnosis.get("hospitals", [])

        if hospitals and isinstance(hospitals[0], str):
            tmp = []
            for i, s in enumerate(hospitals, start=1):
                tmp.append({
                    "name": s,
                    "distance_km": 0.8 + i * 0.4,
                    "address": "서울특별시 어딘가",
                    "phone": "02-000-0000",
                    "doctors": 10 + i * 3,
                    "beds": 20 + i * 5,
                })
            hospitals = tmp

        # 정렬 토글
        sort_choice = st.selectbox(
            "정렬",                     
            ["거리순", "의사수순", "병상수순"],
            index=0,
            key="hospital_sort_choice",  
            label_visibility="collapsed" 
        )

        def sort_key(h):
            if sort_choice == "거리순":
                return (h.get("distance_km", 1e9), -(h.get("doctors", 0)), -(h.get("beds", 0)))
            elif sort_choice == "의사수순":
                return (-(h.get("doctors", 0)), h.get("distance_km", 1e9), -(h.get("beds", 0)))
            else:  # 병상수순
                return (-(h.get("beds", 0)), h.get("distance_km", 1e9), -(h.get("doctors", 0)))

        hospitals_sorted = sorted(hospitals, key=sort_key)

        st.markdown(
            """
            <style>
            .h-card{
                background:#ffffff;
                border:1px solid #e5e7eb;
                border-radius:16px;
                padding:14px 14px 10px;
                margin:10px 0;
                box-shadow: 0 1px 2px rgba(0,0,0,0.04);
            }
            .h-title{font-weight:800; font-size:16px; text-align:left;}
            .h-meta{color:#6b7280; font-size:12px; margin-top:2px; text-align:left;}
            .h-row{display:flex; align-items:center; gap:8px; color:#374151; font-size:14px; margin-top:8px;}
            .h-ico{width:18px; text-align:center;}
            </style>
            """,
            unsafe_allow_html=True,
        )

        if hospitals_sorted:
            for h in hospitals_sorted:
                name = h.get("name", "병원")
                dist = h.get("distance_km", None)
                dist_txt = f"{dist:.1f}km" if isinstance(dist, (int, float)) else "-"
                addr = h.get("address", "-")
                phone = h.get("phone", "-")
                doctors = h.get("doctors", "-")
                beds = h.get("beds", "-")

                st.markdown(
                    f"""
                    <div class="h-card">
                        <div class="h-title">{name}</div>
                        <div class="h-meta">🧑‍⚕️ 의사 {doctors} · 🛏 병상 {beds}</div>
                        <div class="h-row"><div class="h-ico">📍</div> <div>{dist_txt}</div></div>
                        <div class="h-row"><div class="h-ico">🗺️</div> <div>{addr}</div></div>
                        <div class="h-row"><div class="h-ico">☎</div> <div>{phone}</div></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            center_text("주변 병원 정보를 불러올 수 없습니다. (위치 정보 미동의)", size="small", margin_px=4)

        st.divider()

    vspace(6)

    st.markdown(
        """
        <style>.stButton>button { padding: 0.45rem 0.9rem; }</style>
        """,
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        b1, b2 = st.columns(2)
        if triage_level == "emergency":
            with b1:
                st.button("자가진단 저장", on_click=go_to_step, args=[4])
            with b2:
                st.button("119 호출하기", type="primary")
        else:
            with b1:
                st.button("자가진단 저장", on_click=go_to_step, args=[4])
            with b2:
                st.button("자가진단 다시하기", on_click=reset_and_go_to_step, args=[2])
