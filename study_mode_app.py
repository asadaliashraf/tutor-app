# study_mode_app.py
import streamlit as st
import requests
import sqlite3
import json
import os
from datetime import datetime, timedelta

# File reading libraries
import PyPDF2
from docx import Document

# ---------------------
# CONFIG
# ---------------------
# Use Streamlit secrets in production:
# st.secrets["API_KEY"] = "AIza..."
API_KEY = st.secrets.get("API_KEY", os.environ.get("API_KEY", "AIzaSyCvBc3KyBMush9se3QDqEdUTMqgkxpRRS0"))
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

DB_PATH = "srs.db"

# ---------------------
# SYSTEM INSTRUCTIONS (Tutor Persona)
# ---------------------
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
# ---------------------
# DB: SRS (SM-2 style) helper functions
# ---------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            ef REAL DEFAULT 2.5,
            interval INTEGER DEFAULT 0,
            repetitions INTEGER DEFAULT 0,
            next_review TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_card(question, answer):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    next_review = datetime.utcnow().isoformat()
    c.execute("INSERT INTO cards (question, answer, next_review) VALUES (?, ?, ?)", (question, answer, next_review))
    conn.commit()
    conn.close()

def get_due_cards():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    c.execute("SELECT id, question, answer, ef, interval, repetitions, next_review FROM cards WHERE next_review <= ? ORDER BY next_review ASC", (now,))
    rows = c.fetchall()
    conn.close()
    return rows

def update_card_after_review(card_id, quality):
    """
    SM-2 algorithm update.
    quality: 0..5 (5 perfect recall, 0 complete blackout)
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT ef, interval, repetitions FROM cards WHERE id = ?", (card_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return
    ef, interval, repetitions = row
    # Update EF
    ef = max(1.3, ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    if quality < 3:
        repetitions = 0
        interval = 1
    else:
        repetitions += 1
        if repetitions == 1:
            interval = 1
        elif repetitions == 2:
            interval = 6
        else:
            interval = int(round(interval * ef))
    next_review_dt = datetime.utcnow() + timedelta(days=interval)
    next_review = next_review_dt.isoformat()
    c.execute("UPDATE cards SET ef=?, interval=?, repetitions=?, next_review=? WHERE id=?", (ef, interval, repetitions, next_review, card_id))
    conn.commit()
    conn.close()

# Initialize DB
init_db()

# ---------------------
# Utility: extract text from upload
# ---------------------
def extract_text_from_file(uploaded_file):
    if not uploaded_file:
        return ""
    t = ""
    try:
        if uploaded_file.type == "application/pdf":
            reader = PyPDF2.PdfReader(uploaded_file)
            for page in reader.pages:
                t += (page.extract_text() or "") + "\n"
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = Document(uploaded_file)
            for p in doc.paragraphs:
                t += p.text + "\n"
        elif uploaded_file.type == "text/plain":
            t = uploaded_file.read().decode("utf-8")
    except Exception as e:
        st.error(f"Could not read file: {e}")
    return t

# ---------------------
# Gemini API query helper (wraps system + context)
# ---------------------
def query_gemini_with_system(task_prompt, file_context="", study_mode="Practice", eli5=False, quick_answer=False, extra_instructions=""):
    headers = {"Content-Type": "application/json"}
    params = {"key": API_KEY}
    # Compose behavior instructions: system + mode-specific tweaks
    mode_instructions = f"Study Mode: {study_mode}. QuickAnswer: {'Yes' if quick_answer else 'No'}. ELI5: {'Yes' if eli5 else 'No'}."
    full_prompt = SYSTEM_INSTRUCTIONS + "\n\n" + mode_instructions + "\n\n"
    if eli5:
        full_prompt += "If possible, prefer analogies and extremely simple language. Keep sentences short.\n\n"
    if quick_answer:
        full_prompt += "If QuickAnswer is enabled, produce a short direct answer first; then offer an optional short step-by-step if user requests.\n\n"
    if file_context:
        full_prompt += "Context from user file (use this to inform answers):\n" + file_context[:4000] + "\n\n"
    if extra_instructions:
        full_prompt += extra_instructions + "\n\n"
    # Add the actual task
    full_prompt += "Task: " + task_prompt
    data = {"contents": [{"role": "user", "parts": [{"text": full_prompt}]}]}
    resp = requests.post(API_URL, headers=headers, params=params, json=data, timeout=60)
    if resp.status_code == 200:
        j = resp.json()
        try:
            return j["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            return f"⚠️ Unexpected response format: {j}"
    else:
        return f"❌ Error {resp.status_code}: {resp.text}"

# ---------------------
# Streamlit UI
# ---------------------
st.set_page_config(page_title="Study Mode Tutor (SRS)", page_icon="📚", layout="wide")
st.title("📘 Study Mode Tutor — SRS, Adaptive Quizzes & Study Modes")

# Sidebar controls
st.sidebar.header("Settings")
study_mode = st.sidebar.selectbox("Choose study mode", ["Beginner", "Practice", "Exam"])
eli5 = st.sidebar.checkbox("Explain Like I'm 5 (ELI5)", value=False)
quick_answer = st.sidebar.checkbox("Quick Answer (skip scaffolding)", value=False)
task = st.sidebar.radio("App section", ["Tutor Chat", "Flashcards", "Quiz", "Review (SRS)", "Progress"])

# File upload (global context)
uploaded_file = st.sidebar.file_uploader("Upload file (PDF/DOCX/TXT) for context", type=["pdf", "docx", "txt"])
if uploaded_file:
    st.session_state["file_text"] = extract_text_from_file(uploaded_file)
    st.sidebar.success("File loaded. The tutor will use it as context.")

# initialize file_text
if "file_text" not in st.session_state:
    st.session_state["file_text"] = ""

# Chat history init
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []  # list of (role, text)

# ---------- Tutor Chat ----------
if task == "Tutor Chat":
    st.subheader("Tutor Chat — step-by-step, Socratic guidance")
    # Display history
    for role, text in st.session_state["chat_history"]:
        if role == "user":
            st.chat_message("user").write(text)
        else:
            st.chat_message("assistant").write(text)
    # Input
    user_q = st.chat_input("Ask your question (or paste a problem):")
    if user_q:
        st.session_state["chat_history"].append(("user", user_q))
        st.chat_message("user").write(user_q)

        # Add knowledge-check & reflection behavior by instructing the model
        # We'll add an instruction so model asks a short check question after each step,
        # and adds a reflection prompt at the end of full solutions.
        extra_instructions = (
            "Behavior additions:\n"
            "- After presenting each small step, ask a short check-question (1 sentence) to keep student engaged.\n"
            "- If a full solution is requested, include a short reflection prompt at the end (e.g., 'Why does this step work?').\n"
            "- When in Beginner mode, provide more scaffolding and hints; Practice mode be balanced; Exam mode give minimal hints.\n"
            "- Occasionally ask multiple-choice quick-checks (1 question) to test understanding before moving on.\n"
            "Stop after each step and wait for user's next message unless the user explicitly asked for 'full solution'."
        )

        # Send to model
        answer = query_gemini_with_system(
            task_prompt=user_q,
            file_context=st.session_state["file_text"],
            study_mode=study_mode,
            eli5=eli5,
            quick_answer=quick_answer,
            extra_instructions=extra_instructions
        )
        st.session_state["chat_history"].append(("assistant", answer))
        st.chat_message("assistant").write(answer)

# ---------- Flashcards ----------
elif task == "Flashcards":
    st.subheader("Flashcards — generate Q&A from file or a topic")
    topic = st.text_input("Optional topic (leave empty to use uploaded file):")
    count = st.slider("Number of flashcards to create", 3, 20, 8)
    if st.button("Generate Flashcards"):
        if st.session_state["file_text"] and not topic:
            prompt = f"Create {count} concise Q&A flashcards from the uploaded content. Format as 'Q: ...' then 'A: ...' on next line."
        else:
            prompt = f"Create {count} concise Q&A flashcards about: {topic}. Use clear, short Q&A pairs."
        cards_text = query_gemini_with_system(prompt, file_context=st.session_state["file_text"], study_mode=study_mode, eli5=eli5)
        st.markdown("**Generated flashcards:**")
        st.markdown(cards_text)
        # Parse and add to DB: simple parsing Q: / A:
        lines = [l.strip() for l in cards_text.splitlines() if l.strip()]
        q,a = None,None
        for line in lines:
            if line.startswith("Q:") or line.startswith("q:"):
                q = line.partition(":")[2].strip()
            elif line.startswith("A:") or line.startswith("a:"):
                a = line.partition(":")[2].strip()
            if q and a:
                add_card(q,a)
                q,a = None,None
        st.success("Flashcards added to your review deck (SRS).")

    if st.button("Show review deck size"):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM cards")
        total = c.fetchone()[0]
        conn.close()
        st.info(f"You have {total} cards in the deck.")

# ---------- Quiz ----------
elif task == "Quiz":
    st.subheader("Adaptive Quiz Generator")
    topic = st.text_input("Optional topic (leave empty to use uploaded file):")
    num_q = st.slider("Number of questions", 3, 12, 5)
    if st.button("Generate Adaptive Quiz"):
        # Determine difficulty from recent SRS performance
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT AVG(repetitions) FROM cards")
        row = c.fetchone()
        avg_rep = row[0] or 0
        conn.close()
        # adapt difficulty
        if avg_rep >= 3:
            difficulty_hint = "Make these questions slightly harder than average."
        elif avg_rep >= 1:
            difficulty_hint = "Make these questions medium difficulty."
        else:
            difficulty_hint = "Make these questions easier and include helpful hints."
        if st.session_state["file_text"] and not topic:
            prompt = f"Create {num_q} multiple choice questions (A-D) based on the uploaded content. {difficulty_hint} Include correct answer immediately after each question for grading."
        else:
            prompt = f"Create {num_q} multiple choice questions (A-D) about {topic}. {difficulty_hint} Include correct answer immediately after each question."
        q_text = query_gemini_with_system(prompt, file_context=st.session_state["file_text"], study_mode=study_mode, eli5=eli5)
        st.markdown(q_text)
        # Optionally parse and store? (we'll leave as display)

# ---------- Review (SRS) ----------
elif task == "Review (SRS)":
    st.subheader("Spaced Repetition — Review Due Cards")
    due = get_due_cards()
    if not due:
        st.info("No cards due right now. Good job! 🎉")
    else:
        st.write(f"{len(due)} card(s) due for review.")
        for row in due:
            card_id, q, a, ef, interval, reps, next_review = row
            st.markdown(f"**Q:** {q}")
            if st.button(f"Show answer (card {card_id})"):
                st.markdown(f"**A:** {a}")
                # After showing answer, ask user for quality feedback
                quality = st.select_slider("How well did you recall this? (5=perfect, 0=complete blackout)", options=[0,1,2,3,4,5], value=5, key=f"q_{card_id}")
                if st.button(f"Submit review (card {card_id})", key=f"submit_{card_id}"):
                    update_card_after_review(card_id, int(quality))
                    st.success("Review recorded. The card's next review has been scheduled.")

# ---------- Progress ----------
elif task == "Progress":
    st.subheader("Progress & Stats")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM cards")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM cards WHERE next_review <= ?", (datetime.utcnow().isoformat(),))
    due = c.fetchone()[0]
    conn.close()
    st.metric("Total cards in deck", total)
    st.metric("Cards due now", due)
    st.markdown("Recent chat history:")
    for role, txt in st.session_state["chat_history"][-6:]:
        if role == "user":
            st.write(f"**You:** {txt}")
        else:
            st.write(f"**Tutor:** {txt}")

# Footer / help
st.sidebar.markdown("---")
st.sidebar.markdown("Need a quick demo? See README or press the 'Demo' button below to walk through a sample flow.")
if st.sidebar.button("Demo"):
    # small demo walk-through
    st.info("Demo flow: Upload a small PDF -> Choose Beginner -> Ask 'Explain variables' -> Generate 5 flashcards -> Review deck.")

