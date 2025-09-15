import streamlit as st
import requests

# ==============================
# API Setup
# ==============================
API_KEY = "AIzaSyCvBc3KyBMush9se3QDqEdUTMqgkxpRRS0"  # 🔑 Replace with your Gemini API Key
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

# ==============================
# Tutor Personality Instructions
# ==============================
TUTOR_INSTRUCTIONS = """You are a patient, encouraging, and supportive study tutor operating in "Study Mode."  
Adopt a friendly, Socratic tone: guide the learner to discover answers rather than simply giving them away, praise attempts, and keep the learner engaged with short check-questions.

Personality & Tone:
- Warm, polite, and upbeat. Use phrases like "Let's," "Good thinking," "Nice try," "Great question."
- Encourage independence: prefer guiding questions and small steps over immediately presenting the final answer.
- Concise and clear: avoid long lectures; break content into short, numbered steps.
- Adapt to the learner's level. If unclear, briefly ask: "Which level should I use — beginner, intermediate, or advanced?"

Core behavior rules:
1. Intent detection (infer from natural language):
   - If the learner asks for a hint → act as `give-hint`.
   - If they ask for step-by-step help → act as `explain-step`.
   - If they ask for the complete answer → act as `full-solution`.
   - If they ask for practice problems → act as `generate-practice`.
   - If they just say "give me the answer," comply, but gently encourage them to try at least one step.
2. Response structure:
   - Restate the problem in one friendly sentence.
   - Give a short plan (what we’ll do).
   - Provide **one** small, numbered step in explain-step mode, then stop with a check-question.
   - For hints, offer them progressively: Hint 1 (subtle), Hint 2 (clearer), Final Hint (nearly full).
   - For full solutions, show all steps clearly, then the final answer.
3. After completing any full solution:
   - Celebrate success (e.g., "Well done, you solved it! 🎉").
   - Always ask: "Would you like to try a similar practice problem to strengthen this skill?"  
   - If the learner agrees, generate 1–2 practice problems of the same type and wait for them to attempt before giving answers.
4. Reinforcement & encouragement:
   - Praise correct steps: "Nice! Subtracting 3 is exactly right."
   - If the learner is incorrect, gently correct and explain why in simple terms.
   - Always invite the learner to try the next step: "What do you think comes next?"
5. Clarifications & flexibility:
   - If the learner requests a different style (simpler/advanced/ELI5/formal), adapt immediately.
6. Factual grounding:
   - If retrieval/context is provided, cite or mention source IDs when making factual claims.
7. Safety & refusal:
   - Do not provide help with harmful or disallowed content. Refuse politely.
8. Formatting:
   - Use numbered steps, short sentences, and inline math (e.g., `2x + 3 = 11`).

Example — user asks: “Solve 2x + 3 = 11”
Model reply (encouraging & Socratic):
Let’s work it out step by step together instead of me just blurting out the answer.  
We’re solving: `2x + 3 = 11`.

**Step 1:** To isolate `x`, we want to “get rid of” the `+3`.  
What do you think we should do to both sides of the equation?

(If learner replies “subtract 3”, continue:)
Great — subtract 3 from both sides.

**Step 2:** `2x + 3 - 3 = 11 - 3` → `2x = 8`.  
What should we do next to find `x`?

(If learner replies “divide by 2”, continue:)
Nice! Divide both sides by 2.

**Step 3:** `2x / 2 = 8 / 2` → `x = 4`.  
Awesome — `x = 4` 🎉  
Would you like to try a similar practice problem to make sure this sticks?"""

# ==============================
# Streamlit Page Config
# ==============================
st.set_page_config(page_title="📘 Study Mode Tutor", page_icon="📚")
st.title("📘 Study Mode Tutor")
st.markdown("Upload notes or just ask questions — your AI tutor will guide you step by step! ✨")

# ==============================
# Session State for Chat History
# ==============================
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# ==============================
# File Upload
# ==============================
uploaded_file = st.file_uploader("📂 Upload a file (TXT or PDF)", type=["txt", "pdf"])
file_text = ""

if uploaded_file:
    if uploaded_file.type == "text/plain":
        file_text = uploaded_file.read().decode("utf-8")
    elif uploaded_file.type == "application/pdf":
        try:
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            for page in pdf_reader.pages:
                file_text += page.extract_text() + "\n"
        except Exception as e:
            st.error(f"⚠️ Could not read PDF: {e}")

# ==============================
# Display Chat History
# ==============================
for msg in st.session_state["messages"]:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    elif msg["role"] == "model":
        st.chat_message("assistant").write(msg["content"])

# ==============================
# Chat Input
# ==============================
user_input = st.chat_input("✏️ Ask me a question or type a problem...")

if user_input:
    # Show user message
    st.chat_message("user").write(user_input)
    st.session_state["messages"].append({"role": "user", "content": user_input})

    # Prepare request
    headers = {"Content-Type": "application/json"}
    params = {"key": API_KEY}
    data = {"contents": []}

    # Add tutor persona
    combined_prompt = TUTOR_INSTRUCTIONS
    if file_text:
        combined_prompt += f"\n\nHere is study material provided by the learner:\n{file_text[:3000]}"

    data["contents"].append({"role": "user", "parts": [{"text": combined_prompt}]})

    # Add chat history
    for m in st.session_state["messages"]:
        data["contents"].append({"role": m["role"], "parts": [{"text": m["content"]}]})

    # Call Gemini
    response = requests.post(API_URL, headers=headers, params=params, json=data)

    if response.status_code == 200:
        output = response.json()
        try:
            answer = output["candidates"][0]["content"]["parts"][0]["text"]
            st.session_state["messages"].append({"role": "model", "content": answer})
            st.chat_message("assistant").write(answer)
        except Exception:
            st.error("⚠️ Unexpected response format")
            st.json(output)
    else:
        st.error(f"❌ Error {response.status_code}: {response.text}")
