import streamlit as st
import html, re   
from callbacks import next_step
from utils import simulate_model_response, run_diagnosis
from state import initialize_state

CHAT_CSS = """
<style>
.chat-wrap {border-radius:16px; padding:12px 12px 4px; background:#fafafa; border:1px solid #eee;}
.chat-row {display:flex; margin:8px 0; align-items:flex-end;}
.chat-row.left {justify-content:flex-start;}
.chat-row.right {justify-content:flex-end;}
.avatar {width:28px; height:28px; border-radius:50%; display:flex; align-items:center; justify-content:center; margin:0 6px; font-size:16px;}
.avatar.assistant {background:#e9ecef;}
.avatar.user {background:#2b6cb0; color:#fff;}
.bubble {max-width:78%; padding:10px 14px; border-radius:18px; line-height:1.45; word-break:break-word;}
.bubble.assistant {background:#f1f3f5; color:#111; border-top-left-radius:6px;}
.bubble.user {background:#2b6cb0; color:#fff; border-top-right-radius:6px;}
.quick-row {display:flex; gap:8px; margin:8px 0 2px;}
.inputbar {display:flex; gap:8px; align-items:center; margin-top:12px;}
.inputbar .send {width:100%; padding:9px 12px; border-radius:12px; border:1px solid #ddd;}
</style>
"""

def _esc(t: str) -> str:
    return html.escape(t).replace("\n", "<br>")

def _is_meaningful(text: str) -> bool:
    if text is None:
        return False
    t = text.replace("\u00A0", " ").replace("\u200B", "").replace("\u200C", "").replace("\u200D", "").replace("\uFEFF", "")
    t = t.strip()
    if not t:
        return False
    only_punc = re.sub(r"[.,;:·•–—\-_|*~'\"()\[\]{}!?]+", "", t)
    return bool(only_punc.strip())

def _prune_empty_messages() -> None:
    msgs = []
    for m in st.session_state.chat_messages:
        role = m.get("role", "assistant")
        content = (m.get("content") or "")
        if not _is_meaningful(content):
            continue
        msgs.append({"role": role, "content": content.strip()})
    st.session_state.chat_messages = msgs

def _render_chat() -> None:
    st.markdown(CHAT_CSS, unsafe_allow_html=True)
    st.markdown("<div class='chat-wrap'>", unsafe_allow_html=True)
    for msg in st.session_state.chat_messages:
        content = (msg.get("content") or "")
        if not _is_meaningful(content):   
            continue
        role = msg.get("role", "assistant")
        side = "right" if role == "user" else "left"
        bcls = "user" if role == "user" else "assistant"
        avatar = "🧑" if role == "user" else "🤖"
        st.markdown(
            f"<div class='chat-row {side}'>"
            f"<div class='avatar {bcls}'>{avatar}</div>"
            f"<div class='bubble {bcls}'>{_esc(content)}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

def display() -> None:
    initialize_state()

    # 상단 환자 정보
    info = st.session_state.patient_info
    history_str = ", ".join(info.get("history", [])) if info.get("history") else "과거력 없음"
    st.subheader(f"{info['gender']} / {info['age']}세 / {history_str}")

    # 빈/의미없는 말풍선 정리 후 렌더
    _prune_empty_messages()   
    _render_chat()

    # --- 예/아니오 빠른 응답 ---
    last_q = st.session_state.get("last_assistant_question")
    yesno_opts = st.session_state.get("yesno_options")
    if last_q and yesno_opts:
        cols = st.columns(len(yesno_opts))
        def _on_yesno(opt: str):
            st.session_state.chat_messages.append({"role": "user", "content": opt})
            simulate_model_response(opt)
            # 콜백에서 rerun 호출하지 않음(경고 방지)   
        for i, opt in enumerate(yesno_opts):
            cols[i].button(opt, key=f"yn_{i}", on_click=_on_yesno, args=(opt,))

    # --- 입력 콜백 ---
    def _on_send():
        text = (st.session_state.get("free_input") or "").strip()
        if not text:
            return
        st.session_state.chat_messages.append({"role": "user", "content": text})
        st.session_state.free_input = ""  # 안전: 콜백 내부
        simulate_model_response(text)
        # 콜백에서는 rerun 호출 안 함   

    # 입력 바
    c1, c2 = st.columns([4, 1])
    with c1:
        st.text_input("증상을 입력하세요", key="free_input", label_visibility="collapsed")
    with c2:
        st.button("전송", use_container_width=True, on_click=_on_send)

    # --- 자동/수동 진단 ---
    pair_count = st.session_state.get("qa_pairs", 0)
    should_autorun = st.session_state.get("ready_to_diagnose", False) or pair_count >= 9

    if should_autorun:
        if not st.session_state.get("_diag_banner", False):
            st.session_state.chat_messages.append({"role": "assistant", "content": "진단을 진행하겠습니다."})
            st.session_state._diag_banner = True
        run_diagnosis()
        next_step()
        st.rerun() 

    if pair_count >= 10 and not should_autorun:
        if st.button("진단 결과 확인", type="primary", use_container_width=True):
            run_diagnosis()
            next_step()
            st.rerun()   
