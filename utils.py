import streamlit as st
import time
import re
import json  # (유지)
from typing import List, Optional, Dict, Tuple


client = None
ft_model_id: Optional[str] = None
try:
    import openai
    openai.api_key = st.secrets["OPENAI_API_KEY"]
    ft_model_id = st.secrets.get("FT_KTAS_MODEL_ID")
except Exception:
    openai = None
    ft_model_id = None

# 한국어 엔티티/슬롯 추출용 사전
_duration_pat = re.compile(r"(\d+)\s*(분|시간|일|주|개월)")
_ko_num_pat   = re.compile(r"(한|두|세|네)\s*(분|시간|일|주|개월)")   

_severity_words = ["조금", "약간", "중간", "보통", "많이", "매우", "심하게", "너무"]
_pain_words = ["아파", "아픔", "통증", "찌릿", "쑤심", "콕", "조이", "체한"]
_resp_words = ["숨", "호흡", "호흡곤란", "숨차", "가쁨"]
_sweat_words = ["식은땀", "땀"]
_fever_words = ["열", "발열", "미열", "고열"]
_gi_words = ["구토", "메스꺼", "구역", "설사", "변", "소변", "빈뇨", "배뇨통"]

_region_map = {
    "가슴": ["가슴", "흉통", "흉부", "흉골", "명치"],
    "복부": ["복부", "배", "아랫배", "윗배"],
    "우측": ["오른쪽", "우측", "우상", "우하"],
    "좌측": ["왼쪽", "좌측", "좌상", "좌하"],
}

# 1회 질문 보장용 
def _ensure_flags() -> None:   
    if "asked_flags" not in st.session_state:
        st.session_state.asked_flags = {
            "duration": False,
            "worse_move": False,
            "sob_rest": False,
            "gi_combo": False,
            "sweat": False,
            "clarify": False,
        }

def _mark_question_asked_by_text(q: str) -> None:   
    _ensure_flags()
    af = st.session_state.asked_flags
    t = (q or "").strip()
    if ("언제부터" in t) or ("지속" in t) or ("몇 분/시간" in t):
        af["duration"] = True
    elif "움직이거나 숨쉴 때 더 심해지나요" in t:
        af["worse_move"] = True
    elif "안정 시에도 숨이 차신가요" in t:
        af["sob_rest"] = True
    elif "구토나 설사가 동반되나요" in t:
        af["gi_combo"] = True
    elif "식은땀" in t:
        af["sweat"] = True
    elif "불편하신 부위와 증상" in t:
        af["clarify"] = True

# 예/아니오 판별 & 슬롯 반영
def _is_yes(text: str) -> bool:
    t = text.strip()
    return t.startswith("네") or "예" in t or "있습니다" in t or "맞아요" in t

def _is_no(text: str) -> bool:
    t = text.strip()
    return t.startswith("아니") or "없습니다" in t or "괜찮습니다" in t or "아닙니다" in t

def _apply_yesno_to_slots(last_q: str, user_text: str) -> None:
    yes = _is_yes(user_text)
    no = _is_no(user_text)
    if not (yes or no):
        return

    slots = st.session_state.slots
    if "안정 시에도 숨이 차신가요" in last_q:
        slots["sob_at_rest"] = True if yes else False
    elif "구토나 설사가 동반되나요" in last_q:
        slots["gi_combo"] = True if yes else False
    elif "통증이 움직이거나 숨쉴 때 더 심해지나요" in last_q:
        slots["pain_worse_with_move"] = True if yes else False

    asked = st.session_state.asked_questions
    if last_q not in asked:
        asked.append(last_q)
    _mark_question_asked_by_text(last_q)   
    st.session_state.yesno_options = None

# 기간 문자열 보강 추출
def _extract_duration_str(t: str) -> str:   
    m = _duration_pat.search(t)
    if m:
        return f"{m.group(1)}{m.group(2)}"
    m2 = _ko_num_pat.search(t)
    if m2:
        return f"{m2.group(1)}{m2.group(2)}"  # 예: '두 시간'
    if "어제" in t:
        return "어제부터"
    if "오늘" in t:
        return "오늘부터"
    return ""

# 엔티티/토픽 추출
def _extract_entities(text: str) -> Dict[str, str]:
    t = text.strip()

    region = None
    for key, kws in _region_map.items():
        if any(kw in t for kw in kws):
            region = key
            break

    duration = _extract_duration_str(t)   
    if duration:
        st.session_state.slots["chest_pain_duration"] = duration   

    severity = None
    for w in _severity_words:
        if w in t:
            severity = w
            break

    main_symptom = None
    if any(w in t for w in _pain_words):
        main_symptom = "통증"
    elif any(w in t for w in _resp_words):
        main_symptom = "호흡곤란/호흡불편"
    elif any(w in t for w in _gi_words):
        main_symptom = "위장관 증상"

    assoc: List[str] = []
    if any(w in t for w in _sweat_words):
        assoc.append("식은땀")
    if any(w in t for w in _fever_words):
        assoc.append("발열")

    return {
        "region": region or "",
        "duration": duration or "",
        "severity": severity or "",
        "main_symptom": main_symptom or "",
        "assoc": ", ".join(assoc) if assoc else "",
    }

def _detect_topics(text: str) -> List[str]:
    t = text.lower()
    topics: List[str] = []
    if any(k in t for k in ["통증", "아픔", "쑤심", "찌름", "아려움"]):
        topics.append("통증")
    if any(k in t for k in ["가슴", "흉통", "심장", "흉부", "명치"]):
        topics.append("가슴")
    if any(k in t for k in ["호흡", "숨", "호흡곤란"]):
        topics.append("호흡")
    if any(k in t for k in ["기침", "가래"]):
        topics.append("기침")
    if any(k in t for k in ["발열", "열", "식은땀"]):
        topics.append("발열/식은땀")
    if any(k in t for k in ["어지럼", "실신", "쓰러짐"]):
        topics.append("어지럼증")
    if any(k in t for k in ["복부", "배", "아랫배", "윗배"]):
        topics.append("복부")
    return topics

# 후속 질문 & 빠른 응답
def _yesno_options_for(question: str) -> List[str]:
    q = question
    if "숨" in q or "호흡" in q:
        return ["네. 안정 시에도 숨이 찹니다.", "아니요. 활동 시에만 숨이 찹니다."]
    if "쓰러" in q or "의식" in q:
        return ["네. 쓰러졌습니다.", "아니요. 쓰러지지 않았습니다."]
    if "땀" in q:
        return ["네. 식은땀이 있습니다.", "아니요. 식은땀은 없습니다."]
    if "통증이 움직이거나 숨쉴 때 더 심해지나요" in q:
        return ["네. 더 심해집니다.", "아니요. 비슷합니다."]
    if "구토" in q or "설사" in q:
        return ["네. 있습니다.", "아니요. 없습니다."]
    return []

def _is_closed_question(q: str) -> bool:
    return any(tok in q for tok in ["인가요", "있나요", "하셨나요", "합니까", "되나요", "않나요"])

def _choose_followup(ents: Dict[str, str], context_topics: List[str]) -> Tuple[str, List[str]]:
    _ensure_flags()
    slots = st.session_state.slots
    af = st.session_state.asked_flags

    region, duration, severity, ms, assoc = (
        ents["region"], ents["duration"], ents["severity"], ents["main_symptom"], ents["assoc"]
    )

    chest_ctx = (ms == "통증" and (region == "가슴" or "가슴" in context_topics)) or \
                (("가슴" in context_topics) and ("통증" in context_topics))
    resp_ctx  = (ms == "호흡곤란/호흡불편") or ("호흡" in context_topics)              
    gi_ctx    = (ms == "위장관 증상") or ("복부" in context_topics)                   

    if chest_ctx:
        if not slots.get("chest_pain_duration") and not af["duration"]:
            q = "통증은 언제부터 시작되었나요? 대략 몇 분/시간 정도 지속되었는지 알려주세요."
            return q, []
        if slots.get("pain_worse_with_move") is None and not af["worse_move"]:
            q = "통증이 움직이거나 숨쉴 때 더 심해지나요?"
            return q, ["네. 더 심해집니다.", "아니요. 비슷합니다."]
        if slots.get("sob_at_rest") is None and not af["sob_rest"]:
            q = "안정 시에도 숨이 차신가요?"
            return q, ["네. 안정 시에도 숨이 찹니다.", "아니요. 활동 시에만 숨이 찹니다."]

    if resp_ctx:
        if slots.get("sob_at_rest") is None and not af["sob_rest"]:
            q = "안정 시에도 숨이 차신가요?"
            return q, ["네. 안정 시에도 숨이 찹니다.", "아니요. 활동 시에만 숨이 찹니다."]

    if gi_ctx:
        if slots.get("gi_combo") is None and not af["gi_combo"]:
            q = "구토나 설사가 동반되나요?"
            return q, ["네. 있습니다.", "아니요. 없습니다."]

    if "식은땀" in assoc and not af["sweat"]:
        q = "식은땀이 지금도 계속 나시나요?"
        return q, ["네. 계속 납니다.", "아니요. 지금은 없습니다."]

    # ----- 컨텍스트별 '충분 조건'을 만족하면 종료 -----       
    chest_done = chest_ctx and bool(slots.get("chest_pain_duration")) \
                 and (slots.get("pain_worse_with_move") is not None) \
                 and (slots.get("sob_at_rest") is not None)
    resp_done  = resp_ctx and (slots.get("sob_at_rest") is not None)
    gi_done    = gi_ctx and (slots.get("gi_combo") is not None)

    if chest_done or resp_done or gi_done:                               
        st.session_state.ready_to_diagnose = True
        return "진단을 진행하겠습니다.", []

    if not af["clarify"]:
        q = "지금 불편하신 부위와 증상을 한 번 더 구체적으로 말씀해주시겠어요? (예: '가슴 중앙이 조이고 30분째 심함')"
        return q, []

    if slots.get("pain_worse_with_move") is None and not af["worse_move"]:
        q = "통증이 움직이거나 숨쉴 때 더 심해지나요?"
        return q, ["네. 더 심해집니다.", "아니요. 비슷합니다."]
    if slots.get("sob_at_rest") is None and not af["sob_rest"]:
        q = "안정 시에도 숨이 차신가요?"
        return q, ["네. 안정 시에도 숨이 찹니다.", "아니요. 활동 시에만 숨이 찹니다."]
    if slots.get("gi_combo") is None and not af["gi_combo"]:
        q = "구토나 설사가 동반되나요?"
        return q, ["네. 있습니다.", "아니요. 없습니다."]

    st.session_state.ready_to_diagnose = True                             # modification
    return "진단을 진행하겠습니다.", []


# 대화 요약(진단용)
def _generate_summary_from_conversation(messages: List[dict]) -> str:
    text = " ".join(m.get("content", "") for m in messages)
    found: List[str] = []
    if ("가슴" in text and "통증" in text) or "흉통" in text:
        found.append("가슴 통증")
    if ("숨" in text or "호흡" in text or "호흡곤란" in text):
        found.append("호흡 곤란")
    if "식은땀" in text:
        found.append("식은땀")
    if "실신" in text or "의식" in text:
        found.append("실신/의식저하")
    if "복부" in text and "통증" in text:
        found.append("복부 통증")
    if "발열" in text or "열" in text:
        found.append("발열")
    if "기침" in text:
        found.append("기침")
    if all(kw in text for kw in ["가슴", "통증", "식은땀"]) and ("숨" in text or "호흡" in text or "호흡곤란" in text):
        return "가슴 통증, 식은땀, 호흡 곤란 증상."
    if not found:
        return "특이 증상 없음."
    return f"{', '.join(found)} 증상."

def _safe_followup(text: Optional[str]) -> str:
    t = (text or "").strip()
    return t if t else "지금 증상을 조금 더 구체적으로 말씀해주시겠어요?"

# ==============================
# OpenAI ChatCompletion (질문만 생성)
# ==============================
def _llm_question_only(
    ents: Dict[str, str],
    context_topics: List[str],
    slots: Dict[str, Optional[str]],
    user_text: str,
) -> Tuple[str, List[str]]:
    """
    OpenAI로 '질문 1개 + (선택)예/아니오 옵션'만 생성. 공감문 금지.
    실패 시 규칙 기반 폴백.
    """
    if openai is None:
        return _choose_followup(ents, context_topics)  # 폴백

    system_prompt = (
        "당신은 한국어 의학 챗봇입니다. 공감 문장은 쓰지 말고, 다음 단계에 꼭 필요한 "
        "구체적인 질문을 단 한 문장으로 반환하세요. 이미 답한 항목은 반복하지 않습니다. "
        "가능하면 예/아니오로 답할 수 있는 질문을 선호하세요. "
        "반드시 JSON만 출력하세요: "
        "{\"followup\": \"질문?\", \"yesno_options\": [\"선택지1\",\"선택지2\"]}"
    )

    tool_context = {
        "entities": ents,
        "context_topics": context_topics,
        "slots": slots,
        "rule": "질문은 1개, 공감문 금지, 한국어 존댓말",
    }

    try:
        resp = openai.ChatCompletion.create(
            model=ft_model_id or "gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"사용자 입력: {user_text}"},
                {"role": "user", "content": f"컨텍스트: {json.dumps(tool_context, ensure_ascii=False)}"},
            ],
            temperature=0.2,
        )
        content = resp.choices[0].message["content"]
        data = json.loads(content)
        followup = _safe_followup(data.get("followup"))
        if not followup:
            return _choose_followup(ents, context_topics)  # 폴백
        yesno = data.get("yesno_options") or _yesno_options_for(followup)
        return followup, yesno
    except Exception:
        return _choose_followup(ents, context_topics)  # 폴백

# 챗봇 대화 응답 생성 (질문만)
def simulate_model_response(prompt: str) -> None:
    """사용자 입력 → 슬롯 반영 → (LLM/규칙) 질문 1개 생성 → 상태 반영"""
    last_q = st.session_state.get("last_assistant_question")
    if last_q:
        _apply_yesno_to_slots(last_q, prompt)

    time.sleep(0.2)

    ents = _extract_entities(prompt)
    recent = " ".join([m["content"] for m in st.session_state.chat_messages[-3:]])
    context_topics = _detect_topics(recent + " " + prompt)

    # LLM으로 '질문만' 생성 (폴백은 규칙)
    followup, yn_opts = _llm_question_only(
        ents=ents,
        context_topics=context_topics,
        slots=st.session_state.slots,
        user_text=prompt,
    )

    # 기록/상태 업데이트: 질문만 저장
    if followup and followup.strip():
        _mark_question_asked_by_text(followup)   
        st.session_state.chat_messages.append({"role": "assistant", "content": followup})

        if "?" in followup:
            st.session_state.qa_pairs = st.session_state.get("qa_pairs", 0) + 1

        # 질문일 때만 last_assistant_question 유지
        if followup.strip().endswith("?"):
            st.session_state.last_assistant_question = followup
            st.session_state.yesno_options = yn_opts if yn_opts else None
        else:
            st.session_state.last_assistant_question = None
            st.session_state.yesno_options = None
            
        if "진단을 진행하겠습니다" in followup:                       
            st.session_state.ready_to_diagnose = True

    # 조기 종료 플래그(가슴+통증+숨+식은땀)
    convo_text = " ".join([m["content"] for m in st.session_state.chat_messages[-8:]])
    strong_flags = all(flag in convo_text for flag in ["가슴", "통증", "숨"]) and "식은땀" in convo_text
    if strong_flags:
        st.session_state.ready_to_diagnose = True

# 진단 실행 (룰 기반 폴백)
def run_diagnosis() -> None:
    with st.spinner("진단 결과를 분석 중입니다…"):
        time.sleep(1.0)

        convo = " ".join([m["content"] for m in st.session_state.chat_messages])
        risk_score = 0
        if "가슴" in convo and "통증" in convo: risk_score += 3
        if "숨" in convo or "호흡" in convo: risk_score += 2
        if "식은땀" in convo: risk_score += 2
        if "실신" in convo: risk_score += 2
        if "복부" in convo and "통증" in convo: risk_score += 1
        if "발열" in convo or "열" in convo: risk_score += 1

        triage_result = "응급" if risk_score >= 6 else ("외래" if risk_score >= 3 else "가정")
        st.session_state.diagnosis["triage_level"] = triage_result
        st.session_state.diagnosis["summary"] = _generate_summary_from_conversation(st.session_state.chat_messages)

        hospitals = []
        if st.session_state.location_consent:
            if triage_result == "응급":
                hospitals = [
                    {"name": "A 병원 응급실", "distance_km": 0.8, "address": "서울특별시 동대문구 무학로 124", "phone": "02-123-4567", "doctors": 18, "beds": 42},
                    {"name": "B 병원 응급실", "distance_km": 1.2, "address": "서울특별시 성북구 고려대로 73", "phone": "02-678-9012"},
                    {"name": "C 병원 응급실", "distance_km": 2.0, "address": "서울특별시 중랑구 상봉로 31", "phone": "02-345-6789", "doctors": 14, "beds": 55},
                ]
            elif triage_result == "외래":
                hospitals = [
                    {"name": "C 의원", "distance_km": 0.5, "address": "서울특별시 강북구 도봉로 10", "phone": "02-222-1111", "doctors": 4, "beds": 6},
                    {"name": "D 내과", "distance_km": 0.9, "address": "서울특별시 강북구 삼양로 220", "phone": "02-333-2222", "doctors": 6, "beds": 8},
                    {"name": "E 가정의학과", "distance_km": 1.4, "address": "서울특별시 강북구 수유로 88", "phone": "02-444-3333", "doctors": 5, "beds": 10},
                ]
        st.session_state.diagnosis["hospitals"] = hospitals
