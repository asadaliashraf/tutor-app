import streamlit as st
import requests
import json
import os
import random
import sqlite3
import PyPDF2
import docx

# -------------------------------
# CONFIG
# -------------------------------
API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCvBc3KyBMush9se3QDqEdUTMqgkxpRRS0")
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

st.set_page_config(page_title="📘 Study Mode Tutor", page_icon="📚", layout="wide")
st.title("📘 Study Mode Tutor")
st.markdown("Your AI tutor with Study Mode, Flashcards, Quizzes & more 🚀")

# -------------------------------
# SESSION STATE
# -------------------------------
if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "flashcards_local" not in st.session_state:
    st.session_state["flashcards_local"] = []

if "quiz_local" not in st.session_state:
    st.session_state["quiz_local"] = []

# -------------------------------
# SYSTEM INSTRUCTIONS
# -------------------------------
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
   - Provide one small, numbered step in explain-step mode, then stop with a check-question.
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
Example:
User: "Solve 2x + 3 = 11"
Tutor: "Let's work it out step by step... Step 1: ... (then a check-question)."
IMPORTANT: Respond ONLY with valid JSON. 
- Do not include explanations, markdown, or extra text.
- For flashcards: respond with a JSON array of objects { "q": "...", "a": "..." }.
- For quizzes: respond with a JSON array of objects { "q": "...", "options": ["..."], "answerIndex": int }.
- Do not wrap in code blocks.
"""
# -------------------------------
# HELPERS
# -------------------------------
def read_file(uploaded_file):
    if uploaded_file is None:
        return ""
    if uploaded_file.type == "application/pdf":
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        return " ".join([p.extract_text() for p in pdf_reader.pages if p.extract_text()])
    elif uploaded_file.type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        doc = docx.Document(uploaded_file)
        return " ".join([p.text for p in doc.paragraphs])
    else:
        return uploaded_file.read().decode("utf-8")

def query_gemini(task_prompt, context="", mode="practice", difficulty="beginner"):
    headers = {"Content-Type": "application/json"}
    params = {"key": API_KEY}
    full_prompt = f"{SYSTEM_INSTRUCTIONS}\n\nDifficulty: {difficulty}\nMode: {mode}\n\nContext:\n{context}\n\nUser request:\n{task_prompt}"
    data = {
        "contents": [
            {"role": "user", "parts": [{"text": full_prompt}]}
        ]
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

# -------------------------------
# SIDEBAR CONTROLS
# -------------------------------
st.sidebar.header("⚙️ Settings")
section = st.sidebar.radio("Choose Section", ["Tutor Chat", "Flashcards", "Quiz", "SRS Review"])
study_mode = st.sidebar.selectbox("Study Mode", ["practice", "exam"])
difficulty = st.sidebar.selectbox("Difficulty", ["beginner", "intermediate", "advanced"])
uploaded_file = st.sidebar.file_uploader("📎 Upload a study file", type=["pdf", "docx", "txt"])
file_content = read_file(uploaded_file) if uploaded_file else ""

# -------------------------------
# SECTION: TUTOR CHAT
# -------------------------------
if section == "Tutor Chat":
    st.header("💬 Tutor Chat")
    user_msg = st.chat_input("Ask a question...")
    if user_msg:
        st.session_state["messages"].append({"role": "user", "content": user_msg})
        with st.spinner("Thinking..."):
            reply = query_gemini(user_msg, context=file_content, mode=study_mode, difficulty=difficulty)
        st.session_state["messages"].append({"role": "assistant", "content": reply})

    for msg in st.session_state["messages"]:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            st.chat_message("assistant").write(msg["content"])

# -------------------------------
# SECTION: FLASHCARDS
# -------------------------------
elif section == "Flashcards":
    st.header("🃏 Flashcards")
    with st.form("flash_form"):
        topic = st.text_input("Topic (leave empty to use uploaded file)")
        num = st.slider("Number of cards", 3, 20, 5)
        gen = st.form_submit_button("Generate Flashcards")

    if gen:
        context = file_content if not topic else topic
        reply = query_gemini(f"Generate {num} flashcards as JSON list with 'q' and 'a'.", context=context)
        try:
            cards = json.loads(reply)
            st.session_state["flashcards_local"] = cards
        except:
            st.error("⚠️ Could not parse flashcards. Showing raw output.")
            st.write(reply)

    if st.session_state["flashcards_local"]:
        if "flashcard_idx" not in st.session_state:
            st.session_state["flashcard_idx"] = 0
            st.session_state["show_answer"] = False

        cards = st.session_state["flashcards_local"]
        idx = st.session_state["flashcard_idx"]
        card = cards[idx]

        st.markdown(f"**Q:** {card['q']}")

        if not st.session_state["show_answer"]:
            if st.button("Show Answer"):
                st.session_state["show_answer"] = True
        else:
            st.info(card["a"])
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ I got it"):
                    st.session_state["flashcard_idx"] = (idx + 1) % len(cards)
                    st.session_state["show_answer"] = False
            with col2:
                if st.button("❌ I need practice"):
                    st.session_state["flashcard_idx"] = (idx + 1) % len(cards)
                    st.session_state["show_answer"] = False

# -------------------------------
# SECTION: QUIZ
# -------------------------------
elif section == "Quiz":
    st.header("📝 Quiz Generator")
    with st.form("quiz_form"):
        topic = st.text_input("Topic (leave empty to use uploaded file content)")
        n = st.slider("Number of questions", 3, 10, 5)
        gen = st.form_submit_button("Generate Quiz")

    if gen:
        context = file_content if not topic else topic
        reply = query_gemini(f"Generate {n} multiple-choice quiz questions in JSON. Each with 'q','options','answerIndex'.", context=context)
        try:
            qlist = json.loads(reply)
            st.session_state["quiz_local"] = qlist
            st.session_state["quiz_idx"] = 0
            st.session_state["quiz_score"] = 0
        except:
            st.error("⚠️ Could not parse quiz. Showing raw output.")
            st.write(reply)

    if st.session_state["quiz_local"]:
        idx = st.session_state.get("quiz_idx", 0)
        qlist = st.session_state["quiz_local"]

        if idx >= len(qlist):
            st.success(f"Quiz finished! Score: {st.session_state['quiz_score']} / {len(qlist)}")
            if st.button("Restart Quiz"):
                st.session_state["quiz_idx"] = 0
                st.session_state["quiz_score"] = 0
        else:
            item = qlist[idx]
            st.markdown(f"**Q {idx+1}:** {item.get('q')}")
            options = item.get("options", [])
            choice = st.radio("Pick an answer:", options, key=f"quiz_choice_{idx}")

            if st.button("Submit Answer", key=f"submit_{idx}"):
                correct_idx = item.get("answerIndex", None)
                correct_answer = options[correct_idx] if isinstance(correct_idx, int) else None
                if choice == correct_answer:
                    st.success("✅ Correct!")
                    st.session_state["quiz_score"] += 1
                else:
                    st.error(f"❌ Incorrect. Correct answer: {correct_answer}")

            if st.button("Next Question", key=f"next_{idx}"):
                st.session_state["quiz_idx"] += 1

# -------------------------------
# SECTION: SRS REVIEW
# -------------------------------
elif section == "SRS Review":
    st.header("📚 Spaced Repetition Review")
    st.info("Future enhancement: review flashcards with scheduling.")


