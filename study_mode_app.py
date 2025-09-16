import streamlit as st
import requests
import PyPDF2
import docx as docx
from docx import Document

# ================== CONFIG ==================
API_KEY = "AIzaSyCvBc3KyBMush9se3QDqEdUTMqgkxpRRS0"  # 🔑 Replace with your Gemini API key
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

st.set_page_config(page_title="📘 Study Mode Tutor", page_icon="📚")
st.title("📘 Study Mode Tutor")
st.markdown("AI Tutor with Study Modes, File Upload, ELI5, Flashcards & Quiz!")

# ================== SESSION STATE ==================
if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "file_context" not in st.session_state:
    st.session_state["file_context"] = ""

# ================== SIDEBAR ==================
st.sidebar.header("⚙️ Options")
study_mode = st.sidebar.selectbox(
    "Choose Study Mode:",
    ["Beginner", "Practice", "Exam"]
)
eli5 = st.sidebar.checkbox("🍼 Explain Like I'm 5 (ELI5)")

task = st.sidebar.radio(
    "What would you like to do?",
    ["Chat", "Flashcards", "Quiz"]
)

# ================== FILE UPLOAD ==================
uploaded_file = st.file_uploader("📂 Upload study file (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])
if uploaded_file is not None:
    try:
        text = ""

        if uploaded_file.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            for page in pdf_reader.pages:
                text += page.extract_text() or ""

        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(uploaded_file)
            for para in doc.paragraphs:
                text += para.text + "\n"

        elif uploaded_file.type == "text/plain":
            text = uploaded_file.read().decode("utf-8")

        st.session_state["file_context"] = text
        st.success("✅ File uploaded and processed successfully!")

    except Exception as e:
        st.error(f"⚠️ Could not read file: {e}")

# ================== SYSTEM INSTRUCTIONS ==================
SYSTEM_INSTRUCTIONS = """
You are a patient, encouraging, and supportive study tutor operating in "Study Mode."
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
"""

# ================== HELPER FUNCTION ==================
def query_gemini(prompt):
    headers = {"Content-Type": "application/json"}
    params = {"key": API_KEY}

    # Combine context
    full_prompt = SYSTEM_INSTRUCTIONS + "\n\n"
    if st.session_state["file_context"]:
        full_prompt += "Context from uploaded file:\n" + st.session_state["file_context"][:4000] + "\n\n"
    full_prompt += f"Mode: {study_mode}\n"
    if eli5:
        full_prompt += "Explain in ELI5 style (super simple).\n\n"
    full_prompt += "Task: " + prompt

    data = {
        "contents": [{"role": "user", "parts": [{"text": full_prompt}]}]
    }

    response = requests.post(API_URL, headers=headers, params=params, json=data)

    if response.status_code == 200:
        try:
            output = response.json()
            return output["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            return f"⚠️ Unexpected response format: {response.json()}"
    else:
        return f"❌ Error {response.status_code}: {response.text}"

# ================== MAIN ==================
if task == "Chat":
    user_input = st.chat_input("✏️ Ask me a question...")
    if user_input:
        st.session_state["messages"].append({"role": "user", "content": user_input})
        st.chat_message("user").write(user_input)

        answer = query_gemini(user_input)
        st.session_state["messages"].append({"role": "assistant", "content": answer})
        st.chat_message("assistant").write(answer)

elif task == "Flashcards":
    if st.button("📌 Generate Flashcards"):
        answer = query_gemini("Create 10 flashcards (Q & A) from the content.")
        st.markdown(answer)

elif task == "Quiz":
    if st.button("📝 Generate Quiz"):
        answer = query_gemini("Create a 5-question multiple-choice quiz with answers.")
        st.markdown(answer)
elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
    doc = Document(uploaded_file)
    for para in doc.paragraphs:
        text += para.text + "\n"
