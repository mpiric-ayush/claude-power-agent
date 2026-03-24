import streamlit as st
from anthropic import Anthropic
import os

st.set_page_config(page_title="Claude Power Agent", page_icon="⚡", layout="wide")
st.title("⚡ Claude Power Agent")
st.caption("Dynamic Role Engine • Claude Opus 4.6 / Sonnet 4.6 • Full Control")

# ====================== SIDEBAR CONFIG ======================
with st.sidebar:
    st.header("🔧 Configuration")
    
    # API Key
    api_key = st.text_input(
        "Anthropic API Key (Claude Pro / Max)",
        type="password",
        value=os.getenv("ANTHROPIC_API_KEY", ""),
        help="Your key is never stored or sent anywhere except to Anthropic."
    )
    
    if not api_key:
        st.warning("👉 Enter your API key to activate the agent")
        st.stop()
    
    client = Anthropic(api_key=api_key)
    
    # Model selection (latest March 2026 models)
    model = st.selectbox(
        "Model",
        options=["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
        index=0,  # defaults to the most powerful Opus 4.6
        help="Opus 4.6 = maximum intelligence | Sonnet 4.6 = best balance"
    )
    
    # Default System Role = Your full Claude Power Agent definition
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
   - You can instantly switch to any new role the user defines (e.g., "Now act as a Senior Python Architect" or "Become a World-Class Research Analyst").
   - Support any domain: coding, writing, analysis, strategy, creative work, research, teaching, etc.
   - If the user wants a completely different agent, treat the new System Role as the new foundation.

### Response Style Guidelines
- Match the tone, depth, and style required by the current System Role.
- Default to professional, clear, and highly actionable unless the role specifies otherwise.
- For technical tasks: provide explanations, code examples, and edge cases.
- For creative tasks: be imaginative yet grounded.
- Always end responses in a way that invites continuation or next steps when appropriate.

You are now activated as Claude Power Agent."""

    # Persistent System Role
    if "system_role" not in st.session_state:
        st.session_state.system_role = DEFAULT_SYSTEM_ROLE
    
    system_role = st.text_area(
        "System Role (editable)",
        value=st.session_state.system_role,
        height=400,
        help="This is your agent's brain. Change it anytime — the agent will instantly adapt."
    )
    st.session_state.system_role = system_role  # sync back to session state
    
    # Advanced settings
    with st.expander("⚙️ Advanced Settings"):
        temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.05)
        max_tokens = st.slider("Max Tokens", 256, 8192, 4096, 256)
    
    st.divider()
    
    # Quick actions
    if st.button("🔄 Reset Chat (keep System Role)", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    if st.button("🔄 Reset to Default Role", use_container_width=True):
        st.session_state.system_role = DEFAULT_SYSTEM_ROLE
        st.success("System Role restored to full Claude Power Agent")
        st.rerun()

# ====================== MAIN CHAT ======================
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
if user_prompt := st.chat_input("Type your prompt here... (the agent will execute it under the current System Role)"):
    
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)
    
    # Generate assistant response with streaming
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            with client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=st.session_state.system_role,
                messages=st.session_state.messages,
            ) as stream:
                for chunk in stream:
                    if chunk.type == "content_block_delta":
                        full_response += chunk.delta.text
                        message_placeholder.markdown(full_response + "▌")
            
            # Final clean response
            message_placeholder.markdown(full_response)
            
            # Save to history
            st.session_state.messages.append({"role": "assistant", "content": full_response})
        
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.info("Check your API key and quota.")

st.caption("Built as your personal **Claude Power Agent** — fully dynamic, role-based, and ready for anything.")