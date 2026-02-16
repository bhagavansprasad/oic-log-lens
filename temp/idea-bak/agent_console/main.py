import streamlit as st
from agent_core.agent import Agent

# ----------------------------
# Page config
# ----------------------------
st.set_page_config(
    page_title="AuraWings.AI",
    layout="wide",
    initial_sidebar_state="expanded"
)

agent = Agent()

# ----------------------------
# Global CSS
# ----------------------------
st.markdown("""
<style>
body { background-color: #f7f9fb; }

section[data-testid="stSidebar"] {
    background-color: #0f172a;
    color: white;
}
section[data-testid="stSidebar"] * { color: white; }

.config-card {
    background-color: white;
    border-radius: 12px;
    padding: 1rem;
    box-shadow: 0 0 0 1px #e5e7eb;
    margin-bottom: 1rem;
}

.title { font-size: 36px; font-weight: 700; }
.subtitle { font-size: 16px; color: #6b7280; }
</style>
""", unsafe_allow_html=True)

# =====================================================
# SIDEBAR (Dummy)
# =====================================================
with st.sidebar:
    st.markdown("### 🪽 **AuraWings.AI**")
    st.button("➕ New chat", use_container_width=True)

    st.markdown("---")
    st.markdown("**Conversations**")
    st.write("• Invoice queries")
    st.write("• Fusion errors")
    st.write("• SQL help")

    st.markdown("---")
    st.button("→ Sign In", use_container_width=True)

# =====================================================
# MAIN LAYOUT
# =====================================================
left, center, right = st.columns([1, 3, 1])

# =====================================================
# CENTER – REAL CHAT
# =====================================================
with center:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    st.markdown("<div style='text-align:center;margin-top:40px'>", unsafe_allow_html=True)
    st.markdown("<div class='title'>What can I help with?</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='subtitle'>Ask about Aura Fusion SQL, reports, or optimizations.</div>",
        unsafe_allow_html=True
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Render chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.json(msg["content"])

    # REAL INPUT → REAL AGENT
    user_input = st.chat_input("Search By Invoice ID...")

    if user_input:
        # Show user message
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })

        with st.chat_message("user"):
            st.write(user_input)

        # Call REAL backend
        with st.spinner("Thinking..."):
            try:
                response = agent.handle(user_input)
            except Exception as e:
                response = {"error": str(e)}

        # Show assistant response
        st.session_state.messages.append({
            "role": "assistant",
            "content": response
        })

        with st.chat_message("assistant"):
            st.json(response)

# =====================================================
# RIGHT – Dummy Smart Connectivity Panel
# =====================================================
with right:
    st.markdown("### ✨ Smart Connectivity")

    with st.container():
        st.markdown("<div class='config-card'>", unsafe_allow_html=True)
        st.markdown("**Instance Setup**")

        st.text_input("Environment Nickname (e.g.)")
        st.text_input("Instance URL (FA-XXXX.Auracloud)")
        st.text_input("Username")
        st.text_input("Password", type="password")

        col1, col2 = st.columns(2)
        with col1:
            st.selectbox("Environment", ["TEST", "DEV", "PROD"])
        with col2:
            st.selectbox("Source System", ["Aura Fusion"])

        # Dummy buttons
        st.button("💾 Save Config", use_container_width=True)
        st.button("🔍 Find SSO", use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

    with st.container():
        st.markdown("<div class='config-card'>", unsafe_allow_html=True)
        st.markdown("**Fusion Pipelines**")
        st.selectbox(
            "Create Data Model",
            ["Invoice Model", "Supplier Model", "Payments Model"]
        )
        st.markdown("</div>", unsafe_allow_html=True)
