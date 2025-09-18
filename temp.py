import streamlit as st
import time
import re
from typing import List, Optional, Dict, Tuple

# (OpenAI/ft_model_id 부분은 그대로 유지)

# ---------------- 한국어 엔티티/슬롯 추출 ----------------
_duration_pat = re.compile(r"(\d+)\s*(분|시간|시간대|일|주|개월)")    
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

def _extract_entities(text: str) -> Dict[str, str]:
    """사용자 발화에서 부위/기간/강도/주요증상/동반증상 등을 추출"""    
    t = text.strip()

    # 부위
    region = None
    for key, kws in _region_map.items():
        if any(kw in t for kw in kws):
            region = key
            break

    # 기간
    duration = None
    m = _duration_pat.search(t)
    if m:
        duration = f"{m.group(1)}{m.group(2)}"

    # 강도(느낌) 키워드 스캔
    severity = None
    for w in _severity_words:
        if w in t:
            severity = w
            break

    # 주요/동반 증상 분류
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


# ---------------- 맞춤 후속 질문 선택 ----------------
def _choose_followup(ents: Dict[str, str], context_topics: List[str]) -> Tuple[str, List[str]]:
    """엔티티와 직전 문맥을 바탕으로 구체적 후속 질문과 Yes/No 옵션(있으면)을 반환"""    
    region, duration, severity, ms, assoc = (ents[k] for k in ["region", "duration", "severity", "main_symptom", "assoc"])

    # 1) 가슴+통증 → 시간/방사통/유발요인
    if (ms == "통증" and (region == "가슴" or "가슴" in context_topics)):
        if not duration:
            q = "가슴 통증은 언제부터 시작되었나요? 대략 몇 분/시간 정도 지속되었는지 알려주세요."
            return q, []    
        q = "통증이 움직이거나 숨쉴 때 더 심해지나요?"
        return q, ["네. 더 심해집니다.", "아니요. 비슷합니다."]    

    # 2) 호흡 문제 → 호흡 곤란 정도/안정시 여부
    if ms == "호흡곤란/호흡불편" or "호흡" in context_topics:
        q = "안정 시에도 숨이 차신가요?"    
        return q, ["네. 안정 시에도 숨이 찹니다.", "아니요. 활동 시에만 숨이 찹니다."]    

    # 3) 복부 통증 → 위치 구체화
    if ms == "통증" and (region == "복부" or "복부" in context_topics):
        q = "복부의 어느 부위가 더 아프신가요? 상복부/하복부/우측/좌측 중 선택해주세요."
        return q, []    

    # 4) 위장관 증상 → 구토/설사/혈변 여부
    if ms == "위장관 증상" or any(w in context_topics for w in ["기침", "복부"]):
        q = "구토나 설사가 동반되나요?"
        return q, ["네. 있습니다.", "아니요. 없습니다."]    

    # 5) 동반증상 기반 추가 확인
    if "식은땀" in assoc:
        q = "식은땀이 지금도 계속 나시나요?"
        return q, ["네. 계속 납니다.", "아니요. 지금은 없습니다."]    

    # 기본: 너무 포괄적인 재질문 대신, 사용자의 답변을 반영한 구체요청
    q = "지금 불편하신 부위와 증상을 한 번 더 구체적으로 말씀해주실 수 있을까요? 예) '가슴 중앙이 조이고 30분째 심함'"    
    return q, []    


# ---------------- 공감/요약 응답 생성 ----------------
def _format_ack(text: str, ents: Dict[str, str]) -> str:
    """사용자 답변을 반영한 공감형 요약 문장 생성"""    
    bits = []
    if ents["region"]:
        bits.append(ents["region"])
    if ents["main_symptom"]:
        bits.append(ents["main_symptom"])
    if ents["duration"]:
        bits.append(ents["duration"])
    if ents["severity"]:
        bits.append(ents["severity"])
    if ents["assoc"]:
        bits.append(ents["assoc"])

    noted = " / ".join(bits) if bits else "말씀해주신 내용"
    return f"알겠습니다. {noted}으로 이해했습니다."    


# ---------------- 기존 토픽 탐지(문맥 보강용) ----------------
def _detect_topics(text: str) -> List[str]:
    t = text.lower()
    topics = []
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


def _yesno_options_for(question: str) -> List[str]:
    q = question
    if "숨" in q or "호흡" in q:
        return ["네. 숨쉬기 힘듭니다.", "아니요. 괜찮습니다."]
    if "쓰러" in q or "의식" in q:
        return ["네. 쓰러졌습니다.", "아니요. 쓰러지지 않았습니다."]
    if "땀" in q:
        return ["네. 식은땀이 있습니다.", "아니요. 식은땀은 없습니다."]
    if "통증" in q:
        return ["네. 통증이 있습니다.", "아니요. 통증은 없습니다."]
    if "구토" in q or "설사" in q:
        return ["네. 있습니다.", "아니요. 없습니다."]
    return []    : 기본값은 빠른응답 없음


def _is_closed_question(q: str) -> bool:
    return any(tok in q for tok in ["인가요", "있나요", "하셨나요", "합니까", "되나요", "않나요"])    


# ---------------- 요약 생성기(기존) ----------------
def _generate_summary_from_conversation(messages: List[dict]) -> str:
    text = " ".join(m.get("content", "") for m in messages)
    found = []
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


# ---------------- 대화 응답 생성 (개선) ----------------
def simulate_model_response(prompt: str) -> None:
    """사용자 자유 입력을 반영해 공감+요약 후 맞춤 질문으로 진행"""    
    with st.chat_message("assistant"):
        with st.spinner("응답을 생성 중입니다…"):
            time.sleep(0.8)    : UX 미세 조정
            ents = _extract_entities(prompt)    
            ack = _format_ack(prompt, ents)     

            # 최근 문맥 토픽(마지막 3개 메시지)로 보강
            recent = " ".join([m["content"] for m in st.session_state.chat_messages[-3:]])
            context_topics = _detect_topics(recent + " " + prompt)    

            followup, yn_opts = _choose_followup(ents, context_topics)    

            # 최종 응답: 공감 → 요약 → 후속질문
            response = f"{ack} {followup}"    
            st.write(response)    

    # 기록 및 상태 갱신
    st.session_state.chat_messages.append({"role": "assistant", "content": response})    

    # Q/A 페어 카운트 (질문이 실제로 있을 때만 증가)
    if "?" in response:
        st.session_state.qa_pairs = st.session_state.get("qa_pairs", 0) + 1    

    # 빠른응답 옵션 세팅
    if _is_closed_question(followup) and yn_opts:
        st.session_state.last_assistant_question = followup    
        st.session_state.yesno_options = yn_opts              
    else:
        st.session_state.last_assistant_question = followup    
        st.session_state.yesno_options = None                  

    # 조기 종료 플래그(가슴+통증+식은땀+호흡)
    convo_text = " ".join([m["content"] for m in st.session_state.chat_messages[-8:]])
    strong_flags = all(flag in convo_text for flag in ["가슴", "통증", "숨"]) and "식은땀" in convo_text
    if strong_flags:
        st.session_state.ready_to_diagnose = True    


# -------- run_diagnosis()는 이전 버전 그대로 사용 (요약 자동 생성 포함) --------
