import json
import os
import re
import textwrap
import time
import uuid
from datetime import datetime

import streamlit as st

try:
    from anthropic import Anthropic
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "Missing dependency `anthropic`. Install app dependencies with "
        "`pip install -r requirements.txt` before running or deploy with a platform "
        "that installs Python requirements."
    ) from exc

try:
    from pypdf import PdfReader
except Exception:
    try:
        from PyPDF2 import PdfReader
    except Exception:
        PdfReader = None


st.set_page_config(page_title="Claude Power Agent", page_icon="C", layout="wide")


DEFAULT_SYSTEM_ROLE = """You are **Claude Power Agent** — an extremely capable, adaptive, and intelligent AI agent built for maximum usefulness and precision.

### Core Architecture & Operating Principles
You operate as a **modular, role-based agent** with the following high-level design:

1. **Dynamic Role Engine**
   - You will fully embody whatever role, personality, expertise level, or behavior is defined in the **System Role** provided at the start of the conversation.
   - The System Role is your "brain configuration". You must strictly follow it and never contradict or ignore it.

2. **User Prompt as Task Layer**
   - Every user message is a specific task, question, or instruction that you must execute **within the boundaries of the current System Role**.
   - Treat the user prompt as the primary goal while staying 100% in character.

3. **Reasoning & Execution Framework** (Always use this internally)
   - **Step 1: Understand Context** — Analyze the full conversation history, the System Role, and the current user prompt.
   - **Step 2: Plan** — Think step-by-step about the best approach to fulfill the request.
   - **Step 3: Execute** — Deliver the highest quality response possible.
   - **Step 4: Self-Check** — Verify accuracy, usefulness, clarity, and alignment with the System Role.
   - **Step 5: Adapt** — If the user changes the System Role mid-conversation, instantly reconfigure yourself to the new role for all future responses.

4. **Key Behavioral Rules**
   - Be truthful, precise, and never hallucinate.
   - Think deeply and show clear reasoning when complex problems are involved.
   - Ask clarifying questions if the user prompt is ambiguous — but only after acknowledging the request.
   - Maximize helpfulness and creativity while staying within the defined role.
   - Use structured output (markdown, tables, bullet points, code blocks, etc.) whenever it improves clarity.
   - Maintain conversation memory — refer to previous messages when relevant.

5. **Flexibility & Meta Capabilities**
   - You can instantly switch to any new role the user defines.
   - Support any domain: coding, writing, analysis, strategy, creative work, research, teaching, etc.
   - If the user wants a completely different agent, treat the new System Role as the new foundation.

### Response Style Guidelines
- Match the tone, depth, and style required by the current System Role.
- Default to professional, clear, and highly actionable unless the role specifies otherwise.
- For technical tasks: provide explanations, code examples, and edge cases.
- For creative tasks: be imaginative yet grounded.
- Always end responses in a way that invites continuation or next steps when appropriate.

You are now activated as Claude Power Agent."""

STARTER_PROMPTS = [
    "Summarize this topic like an executive advisor and give me an action plan.",
    "Review my idea critically and tell me the risks, gaps, and next steps.",
    "Act as a senior software architect and design the best approach for this feature.",
    "Read my uploaded PDF and extract the key decisions, deadlines, and action items.",
]


def apply_custom_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #efefe8;
            --bg-strong: #e4e4dc;
            --panel: rgba(255, 255, 251, 0.78);
            --panel-strong: rgba(255, 255, 255, 0.92);
            --ink: #000000;
            --muted: #3f3f3f;
            --line: rgba(0, 0, 0, 0.12);
            --accent: #000000;
            --accent-soft: #f5f5ef;
            --success: #0f5132;
        }

        html, body, [class*="css"], [data-testid="stAppViewContainer"], [data-testid="stMarkdownContainer"] {
            font-family: "Times New Roman", Times, serif !important;
            color: var(--ink);
        }

        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at top left, rgba(0, 0, 0, 0.04), transparent 28%),
                radial-gradient(circle at bottom right, rgba(0, 0, 0, 0.06), transparent 30%),
                linear-gradient(180deg, #f3f3ed 0%, #e8e8df 100%);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #e8e8e0 0%, #dcdcd3 100%);
            border-right: 1px solid var(--line);
        }

        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2rem;
        }

        .app-shell {
            background:
                linear-gradient(135deg, rgba(255, 255, 252, 0.95) 0%, rgba(241, 241, 235, 0.84) 100%);
            border: 1px solid var(--line);
            border-radius: 28px;
            padding: 1.4rem;
            box-shadow: 0 24px 60px rgba(0, 0, 0, 0.08);
            margin-bottom: 1rem;
        }

        .hero-grid {
            display: grid;
            grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.9fr);
            gap: 1rem;
            align-items: stretch;
        }

        .hero-panel {
            background: rgba(255, 255, 255, 0.38);
            border: 1px solid rgba(0, 0, 0, 0.08);
            border-radius: 24px;
            padding: 1.1rem 1.2rem;
            backdrop-filter: blur(8px);
        }

        .eyebrow {
            display: inline-block;
            background: #000000;
            color: #ffffff;
            padding: 0.28rem 0.62rem;
            border-radius: 999px;
            font-size: 0.8rem;
            letter-spacing: 0.03em;
            margin-bottom: 0.75rem;
        }

        .hero-title {
            font-size: 2.35rem;
            font-weight: 700;
            margin: 0;
            color: #000000;
            line-height: 1.05;
        }

        .hero-subtitle {
            color: #222222;
            font-size: 1rem;
            margin-top: 0.55rem;
            max-width: 52rem;
        }

        .status-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.8rem;
            margin-top: 1rem;
        }

        .status-card {
            background: rgba(255, 255, 255, 0.7);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 0.85rem 1rem;
        }

        .status-label {
            color: #525252;
            font-size: 0.85rem;
            margin-bottom: 0.2rem;
        }

        .status-value {
            color: #000000;
            font-size: 1.2rem;
            font-weight: 700;
        }

        .starter-card {
            background: rgba(255, 255, 255, 0.74);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 0.8rem 1rem;
            margin-bottom: 0.75rem;
        }

        .section-title {
            font-size: 1.05rem;
            color: #000000;
            margin-bottom: 0.5rem;
            font-weight: 700;
        }

        [data-testid="stChatMessage"] {
            background: rgba(255, 255, 255, 0.74);
            border: 1px solid rgba(0, 0, 0, 0.08);
            border-radius: 22px;
            padding: 0.5rem 0.7rem;
            margin-bottom: 0.8rem;
            box-shadow: 0 10px 26px rgba(0, 0, 0, 0.04);
        }

        .chat-meta {
            color: var(--muted);
            font-size: 0.88rem;
            margin-bottom: 0.5rem;
        }

        .upload-note {
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid rgba(0, 0, 0, 0.08);
            border-radius: 14px;
            padding: 0.75rem 0.9rem;
            color: #000000;
            margin-bottom: 0.8rem;
        }

        .saved-chat {
            background: rgba(255,255,255,0.5);
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 0.7rem 0.85rem;
            margin-bottom: 0.55rem;
        }

        .saved-chat small {
            color: var(--muted);
        }

        .stButton > button, .stDownloadButton > button {
            border-radius: 12px;
            border: 1px solid #000000;
            background: #000000;
            color: #ffffff !important;
            font-weight: 700;
            transition: all 0.2s ease;
        }

        .stButton > button *, .stDownloadButton > button * {
            color: #ffffff !important;
            fill: #ffffff !important;
        }

        .stButton > button:hover, .stDownloadButton > button:hover {
            background: #1a1a1a;
            color: #ffffff !important;
            border-color: #1a1a1a;
            box-shadow: 0 8px 18px rgba(0, 0, 0, 0.16);
        }

        .stButton > button:hover *, .stDownloadButton > button:hover * {
            color: #ffffff !important;
            fill: #ffffff !important;
        }

        .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div,
        .stNumberInput input {
            background: rgba(255, 255, 255, 0.92);
            border-color: rgba(0, 0, 0, 0.16);
            color: #000000;
        }

        .hero-visual {
            min-height: 272px;
            border-radius: 24px;
            border: 1px solid rgba(0, 0, 0, 0.08);
            background:
                linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(231, 231, 224, 0.9)),
                radial-gradient(circle at 20% 20%, rgba(0, 0, 0, 0.08), transparent 24%);
            position: relative;
            overflow: hidden;
        }

        .hero-visual::before {
            content: "";
            position: absolute;
            inset: 22px;
            border-radius: 20px;
            background:
                radial-gradient(circle at 50% 50%, rgba(0, 0, 0, 0.92) 0 8%, transparent 9%),
                radial-gradient(circle at 24% 28%, rgba(0, 0, 0, 0.9) 0 4%, transparent 5%),
                radial-gradient(circle at 76% 24%, rgba(0, 0, 0, 0.9) 0 4%, transparent 5%),
                radial-gradient(circle at 20% 76%, rgba(0, 0, 0, 0.9) 0 4%, transparent 5%),
                radial-gradient(circle at 80% 78%, rgba(0, 0, 0, 0.9) 0 4%, transparent 5%),
                linear-gradient(90deg, transparent 0 19%, rgba(0, 0, 0, 0.2) 19.4% 20.1%, transparent 20.5% 49.5%, rgba(0, 0, 0, 0.2) 49.9% 50.6%, transparent 51% 79.2%, rgba(0, 0, 0, 0.2) 79.6% 80.3%, transparent 80.7% 100%),
                linear-gradient(180deg, transparent 0 24%, rgba(0, 0, 0, 0.2) 24.4% 25.1%, transparent 25.5% 49.5%, rgba(0, 0, 0, 0.2) 49.9% 50.6%, transparent 51% 74.2%, rgba(0, 0, 0, 0.2) 74.6% 75.3%, transparent 75.7% 100%);
            opacity: 0.95;
        }

        .hero-visual::after {
            content: "AGENT";
            position: absolute;
            bottom: 18px;
            right: 22px;
            color: rgba(0, 0, 0, 0.7);
            font-size: 2rem;
            font-weight: 700;
            letter-spacing: 0.18em;
        }

        @media (max-width: 980px) {
            .hero-grid {
                grid-template-columns: 1fr;
            }

            .status-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def make_chat(title: str = "New conversation") -> dict:
    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "messages": [],
        "created_at": now_stamp(),
        "updated_at": now_stamp(),
    }


def init_state() -> None:
    if "system_role" not in st.session_state:
        st.session_state.system_role = DEFAULT_SYSTEM_ROLE
    if "conversations" not in st.session_state:
        first_chat = make_chat("Strategy session")
        st.session_state.conversations = [first_chat]
        st.session_state.current_chat_id = first_chat["id"]
    if "pending_prompt" not in st.session_state:
        st.session_state.pending_prompt = ""
    if "uploaded_pdf" not in st.session_state:
        st.session_state.uploaded_pdf = None


def current_chat() -> dict:
    for chat in st.session_state.conversations:
        if chat["id"] == st.session_state.current_chat_id:
            return chat
    fallback = st.session_state.conversations[0]
    st.session_state.current_chat_id = fallback["id"]
    return fallback


def create_chat(title: str = "New conversation") -> None:
    chat = make_chat(title)
    st.session_state.conversations.insert(0, chat)
    st.session_state.current_chat_id = chat["id"]


def switch_chat(chat_id: str) -> None:
    st.session_state.current_chat_id = chat_id


def delete_chat(chat_id: str) -> None:
    if len(st.session_state.conversations) == 1:
        st.warning("At least one conversation must remain.")
        return
    st.session_state.conversations = [
        chat for chat in st.session_state.conversations if chat["id"] != chat_id
    ]
    if st.session_state.current_chat_id == chat_id:
        st.session_state.current_chat_id = st.session_state.conversations[0]["id"]


def infer_title(messages: list[dict]) -> str:
    for message in messages:
        if message["role"] == "user":
            cleaned = re.sub(r"\s+", " ", message["content"]).strip()
            return cleaned[:42] + ("..." if len(cleaned) > 42 else "")
    return "New conversation"


def update_chat_metadata(chat: dict) -> None:
    chat["updated_at"] = now_stamp()
    if chat["messages"]:
        chat["title"] = infer_title(chat["messages"])


def render_message(role: str, content: str) -> None:
    with st.chat_message(role):
        st.markdown(content)


def pdf_extract_text(uploaded_file) -> tuple[str, str]:
    if PdfReader is None:
        return "", "PDF reading library not installed. Install `pypdf` or `PyPDF2` to extract content."

    try:
        reader = PdfReader(uploaded_file)
        pages = []
        for index, page in enumerate(reader.pages):
            page_text = (page.extract_text() or "").strip()
            if page_text:
                pages.append(f"[Page {index + 1}]\n{page_text}")
        text = "\n\n".join(pages).strip()
        if not text:
            return "", "The PDF was uploaded, but no extractable text was found."
        return text, f"Loaded {len(reader.pages)} pages from `{uploaded_file.name}`."
    except Exception as exc:
        return "", f"Unable to read the PDF: {exc}"


def escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def generate_simple_pdf(title: str, body: str) -> bytes:
    lines = [title, ""]
    for raw_line in body.splitlines():
        wrapped = textwrap.wrap(raw_line, width=92) or [""]
        lines.extend(wrapped)

    page_width = 612
    page_height = 792
    margin = 50
    line_height = 15
    max_lines = int((page_height - 2 * margin) / line_height)

    pages = [lines[i:i + max_lines] for i in range(0, len(lines), max_lines)] or [[]]
    objects: list[bytes] = []

    def add_object(payload: bytes) -> int:
        objects.append(payload)
        return len(objects)

    font_id = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman >>")
    page_ids = []

    for page_lines in pages:
        content_lines = ["BT", "/F1 12 Tf", f"{margin} {page_height - margin} Td"]
        for idx, line in enumerate(page_lines):
            escaped = escape_pdf_text(line)
            if idx == 0:
                content_lines.append(f"({escaped}) Tj")
            else:
                content_lines.append(f"0 -{line_height} Td")
                content_lines.append(f"({escaped}) Tj")
        content_lines.append("ET")
        stream = "\n".join(content_lines).encode("latin-1", errors="replace")
        content_id = add_object(
            f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream"
        )
        page_id = add_object(
            (
                "<< /Type /Page /Parent PAGES_ID 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
            ).encode("latin-1")
        )
        page_ids.append(page_id)

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    pages_id = add_object(
        f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("latin-1")
    )

    for page_id in page_ids:
        objects[page_id - 1] = objects[page_id - 1].replace(b"PAGES_ID", str(pages_id).encode("ascii"))

    catalog_id = add_object(f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("latin-1"))

    buffer = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(buffer))
        buffer.extend(f"{idx} 0 obj\n".encode("ascii"))
        buffer.extend(obj)
        buffer.extend(b"\nendobj\n")

    xref_start = len(buffer)
    buffer.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    buffer.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        buffer.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    buffer.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF"
        ).encode("ascii")
    )
    return bytes(buffer)


def build_transcript(chat: dict) -> str:
    chunks = [f"{chat['title']}", f"Updated: {chat['updated_at']}", ""]
    for message in chat["messages"]:
        role = message["role"].upper()
        chunks.append(f"{role}\n{message['content']}\n")
    return "\n".join(chunks)


def export_json(chat: dict) -> bytes:
    payload = {
        "title": chat["title"],
        "created_at": chat["created_at"],
        "updated_at": chat["updated_at"],
        "messages": chat["messages"],
        "system_role": st.session_state.system_role,
        "uploaded_pdf": st.session_state.uploaded_pdf,
    }
    return json.dumps(payload, indent=2).encode("utf-8")


def inject_uploaded_pdf_context(prompt: str) -> str:
    uploaded_pdf = st.session_state.uploaded_pdf
    if not uploaded_pdf or not uploaded_pdf.get("text"):
        return prompt

    pdf_context = uploaded_pdf["text"][:18000]
    return (
        f"{prompt}\n\n"
        f"Use this uploaded PDF as reference when relevant.\n"
        f"PDF file: {uploaded_pdf['name']}\n"
        f"PDF extracted text:\n{pdf_context}"
    )


def render_saved_chats() -> None:
    st.markdown("### Conversation History")
    ordered = sorted(
        st.session_state.conversations,
        key=lambda item: item["updated_at"],
        reverse=True,
    )
    for chat in ordered:
        st.markdown(
            f"""
            <div class="saved-chat">
                <div><strong>{chat["title"]}</strong></div>
                <small>{chat["updated_at"]}</small>
            </div>
            """,
            unsafe_allow_html=True,
        )
        left, right = st.columns([4, 1])
        with left:
            if st.button(
                f"Open",
                key=f"open_{chat['id']}",
                use_container_width=True,
            ):
                switch_chat(chat["id"])
                st.rerun()
        with right:
            if st.button(
                "X",
                key=f"delete_{chat['id']}",
                use_container_width=True,
            ):
                delete_chat(chat["id"])
                st.rerun()


def render_sidebar() -> tuple[Anthropic, str, float, int]:
    with st.sidebar:
        st.header("Agent Workspace")

        if st.button("New Conversation", use_container_width=True):
            create_chat("New conversation")
            st.rerun()

        render_saved_chats()
        st.divider()

        st.subheader("Configuration")
        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            value=os.getenv("ANTHROPIC_API_KEY", ""),
            help="Sent only to Anthropic for live model responses.",
        )
        if not api_key:
            st.warning("Enter your API key to activate the agent.")
            st.stop()
        client = Anthropic(api_key=api_key)

        model = st.selectbox(
            "Model",
            options=["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
            index=0,
        )

        with st.expander("System Role", expanded=False):
            st.session_state.system_role = st.text_area(
                "System Role",
                value=st.session_state.system_role,
                height=320,
            )
            if st.button("Reset Default Role", use_container_width=True):
                st.session_state.system_role = DEFAULT_SYSTEM_ROLE
                st.rerun()

        with st.expander("Advanced", expanded=False):
            temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.05)
            max_tokens = st.slider("Max Tokens", 256, 8192, 4096, 256)

        st.divider()
        st.subheader("PDF Tools")
        uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
        if uploaded_file is not None:
            extracted_text, status = pdf_extract_text(uploaded_file)
            st.info(status)
            st.session_state.uploaded_pdf = {
                "name": uploaded_file.name,
                "text": extracted_text,
                "uploaded_at": now_stamp(),
            }
        if st.session_state.uploaded_pdf:
            st.caption(
                f"Attached PDF: {st.session_state.uploaded_pdf['name']} "
                f"({st.session_state.uploaded_pdf['uploaded_at']})"
            )
            if st.button("Remove PDF Context", use_container_width=True):
                st.session_state.uploaded_pdf = None
                st.rerun()

        st.divider()
        st.subheader("Chat Actions")
        current = current_chat()
        transcript = build_transcript(current)
        st.download_button(
            "Download TXT",
            data=transcript.encode("utf-8"),
            file_name=f"{current['title'].replace(' ', '_').lower()}.txt",
            mime="text/plain",
            use_container_width=True,
        )
        st.download_button(
            "Download JSON",
            data=export_json(current),
            file_name=f"{current['title'].replace(' ', '_').lower()}.json",
            mime="application/json",
            use_container_width=True,
        )
        st.download_button(
            "Download PDF",
            data=generate_simple_pdf(current["title"], transcript),
            file_name=f"{current['title'].replace(' ', '_').lower()}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
        if st.button("Reset Current Chat", use_container_width=True):
            current["messages"] = []
            update_chat_metadata(current)
            st.rerun()

    return client, model, temperature, max_tokens


def render_header(chat: dict, model: str) -> None:
    total_messages = len(chat["messages"])
    user_messages = len([msg for msg in chat["messages"] if msg["role"] == "user"])
    assistant_messages = len([msg for msg in chat["messages"] if msg["role"] == "assistant"])
    pdf_status = st.session_state.uploaded_pdf["name"] if st.session_state.uploaded_pdf else "None"

    st.markdown('<div class="app-shell">', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="hero-grid">
            <div class="hero-panel">
                <div class="eyebrow">Agent Workspace</div>
                <p class="hero-title">{chat["title"]}</p>
                <div class="hero-subtitle">
                    Minimal, professional chat workspace with memory, role control, PDF context, and export tools.
                    The visual direction is now much closer to a premium agent interface: lighter surfaces, stronger
                    black typography, quieter chrome, and focused action controls. Model: {model}
                </div>
                <div class="status-grid">
                    <div class="status-card">
                        <div class="status-label">Messages</div>
                        <div class="status-value">{total_messages}</div>
                    </div>
                    <div class="status-card">
                        <div class="status-label">User Turns</div>
                        <div class="status-value">{user_messages}</div>
                    </div>
                    <div class="status-card">
                        <div class="status-label">Assistant Turns</div>
                        <div class="status-value">{assistant_messages}</div>
                    </div>
                    <div class="status-card">
                        <div class="status-label">Attached PDF</div>
                        <div class="status-value">{pdf_status[:18] + ("..." if len(pdf_status) > 18 else "")}</div>
                    </div>
                </div>
            </div>
            <div class="hero-visual"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def render_starters() -> None:
    if current_chat()["messages"]:
        return

    st.markdown('<div class="section-title">Quick Start</div>', unsafe_allow_html=True)
    for idx, prompt in enumerate(STARTER_PROMPTS):
        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(f'<div class="starter-card">{prompt}</div>', unsafe_allow_html=True)
        with col2:
            if st.button("Use", key=f"starter_{idx}", use_container_width=True):
                st.session_state.pending_prompt = prompt
                st.rerun()


def stream_response(client: Anthropic, model: str, max_tokens: int, temperature: float, prompt: str) -> str:
    chat = current_chat()
    enriched_prompt = inject_uploaded_pdf_context(prompt)
    chat["messages"].append({"role": "user", "content": prompt})
    update_chat_metadata(chat)

    render_message("user", prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        try:
            api_messages = []
            for message in chat["messages"][:-1]:
                api_messages.append({"role": message["role"], "content": message["content"]})
            api_messages.append({"role": "user", "content": enriched_prompt})

            with client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=st.session_state.system_role,
                messages=api_messages,
            ) as stream:
                for chunk in stream:
                    if chunk.type == "content_block_delta":
                        full_response += chunk.delta.text
                        message_placeholder.markdown(full_response + "▌")

            message_placeholder.markdown(full_response)
            chat["messages"].append({"role": "assistant", "content": full_response})
            update_chat_metadata(chat)
            return full_response
        except Exception as exc:
            message_placeholder.error(f"Error: {exc}")
            st.info("Check the API key, model access, or quota.")
            chat["messages"].pop()
            update_chat_metadata(chat)
            return ""


def main() -> None:
    apply_custom_theme()
    init_state()
    client, model, temperature, max_tokens = render_sidebar()
    chat = current_chat()

    render_header(chat, model)

    if st.session_state.uploaded_pdf:
        st.markdown(
            (
                f'<div class="upload-note"><strong>PDF attached:</strong> '
                f'{st.session_state.uploaded_pdf["name"]}. '
                f'The agent can use it as context for summaries, extraction, and analysis.</div>'
            ),
            unsafe_allow_html=True,
        )

    render_starters()

    for message in chat["messages"]:
        render_message(message["role"], message["content"])

    prompt = st.session_state.pending_prompt or st.chat_input(
        "Ask anything, analyze a PDF, continue a previous conversation, or give the agent a new role..."
    )
    if st.session_state.pending_prompt:
        st.session_state.pending_prompt, prompt = "", st.session_state.pending_prompt

    if prompt:
        stream_response(client, model, max_tokens, temperature, prompt)
        time.sleep(0.1)
        st.rerun()

    st.caption(
        "Built as a polished agent workspace with better UI, conversation history, PDF upload and export, and role-based control."
    )


if __name__ == "__main__":
    main()
