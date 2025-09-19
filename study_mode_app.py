# study_mode_app.py
import streamlit as st
import requests
import sqlite3
import json
import os
import random
from datetime import datetime, timedelta

# file parsing libs
import PyPDF2
from docx import Document

# ---------------------------
# CONFIG
# ---------------------------
st.set_page_config(page_title="📘 Study Mode Tutor (Full)", page_icon="📚", layout="wide")

# API key: prefer st.secrets, fall back to environment var
API_KEY = st.secrets.get("API_KEY", os.environ.get("API_KEY", None))
if not API_KEY:
    st.warning("API key not found. Set st.secrets['API_KEY'] or the environment variable API_KEY before using the app.")
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

# Database file for SRS
DB_PATH = "srs_cards.db"

# ---------------------------
# SYSTEM INSTRUCTIONS (Tutor Persona)
# ---------------------------
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
"""

# ---------------------------
# DB / SRS (SM-2) utilities
# ---------------------------
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
        );
    """)
    conn.commit()
    conn.close()

def add_card(question, answer):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    c.execute("INSERT INTO cards (question, answer, next_review) VALUES (?, ?, ?)", (question, answer, now))
    conn.commit()
    conn.close()

def get_due_cards(limit=10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    c.execute("SELECT id, question, answer, ef, interval, repetitions, next_review FROM cards WHERE next_review <= ? ORDER BY next_review ASC LIMIT ?", (now, limit))
    rows = c.fetchall()
    conn.close()
    return rows

def update_card_after_review(card_id, quality):
    # quality: 0..5
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT ef, interval, repetitions FROM cards WHERE id = ?", (card_id,))
    r = c.fetchone()
    if not r:
        conn.close()
        return
    ef, interval, repetitions = r
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
            interval = int(round(interval * ef)) if interval > 0 else int(round(6 * ef))
    next_review_dt = datetime.utcnow() + timedelta(days=interval)
    next_review = next_review_dt.isoformat()
    c.execute("UPDATE cards SET ef=?, interval=?, repetitions=?, next_review=? WHERE id=?", (ef, interval, repetitions, next_review, card_id))
    conn.commit()
    conn.close()

def count_cards():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM cards")
    n = c.fetchone()[0]
    conn.close()
    return n

init_db()

# ---------------------------
# File extract helper (pdf/docx/txt)
# ---------------------------
def extract_text_from_file(uploaded_file):
    if uploaded_file is None:
        return ""
    text = ""
    try:
        mime = uploaded_file.type
        if mime == "application/pdf":
            reader = PyPDF2.PdfReader(uploaded_file)
            for p in reader.pages:
                page_text = p.extract_text()
                if page_text:
                    text += page_text + "\n"
        elif mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = Document(uploaded_file)
            for para in doc.paragraphs:
                if para.text:
                    text += para.text + "\n"
        elif mime == "text/plain":
            text = uploaded_file.read().decode("utf-8")
        else:
            # fallback: try decode
            try:
                text = uploaded_file.read().decode("utf-8")
            except:
                text = ""
    except Exception as e:
        st.error(f"Could not read uploaded file: {e}")
    return text

# ---------------------------
# Gemini query helper (adds system instructions + mode context)
# ---------------------------
def query_gemini(task_prompt, file_context="", difficulty="Intermediate", study_mode="Practice", eli5=False, quick_answer=False, expect_json=False, json_key=None, timeout=60):
    """
    Compose a full prompt and call the Gemini endpoint.
    - expect_json: if True, instruct the model to output JSON and try to parse it.
    - json_key: optional top-level key expected (not required).
    """
    if not API_KEY:
        return "ERROR: API key is not configured."

    headers = {"Content-Type": "application/json"}
    params = {"key": API_KEY}

    mode_text = f"StudyMode: {study_mode}. Difficulty: {difficulty}. QuickAnswer: {'Yes' if quick_answer else 'No'}. ELI5: {'Yes' if eli5 else 'No'}."
    extra = ""
    if eli5:
        extra += "Use very simple analogies, short sentences, avoid jargon.\n"
    if quick_answer:
        extra += "Provide a short direct answer first, then offer to explain step-by-step only if asked.\n"

    # If expecting structured output, instruct JSON
    json_instruction = ""
    if expect_json:
        json_instruction = ("Output EXACTLY valid JSON with no surrounding explanation. "
                            "The top-level JSON should be an object. "
                            "If you are asked to produce flashcards, output like: "
                            "{\"flashcards\": [{\"q\":\"...\",\"a\":\"...\"}, ...]} "
                            "If you are asked to produce a quiz, output like: "
                            "{\"quiz\": [{\"q\":\"...\",\"options\": [\"a\",\"b\",\"c\",\"d\"], \"answerIndex\": 1, \"hint\":\"...\"}, ...]} \n")

    full_prompt = SYSTEM_INSTRUCTIONS + "\n\n" + mode_text + "\n\n" + extra + "\n\n"
    if file_context:
        full_prompt += "Use the following uploaded file content as context (use it when relevant):\n" + file_context[:4000] + "\n\n"
    if json_instruction:
        full_prompt += json_instruction + "\n\n"
    full_prompt += "Task: " + task_prompt

    data = {"contents": [{"role": "user", "parts": [{"text": full_prompt}]}]}

    try:
        resp = requests.post(API_URL, headers=headers, params=params, json=data, timeout=timeout)
    except requests.exceptions.RequestException as e:
        return f"ERROR: Request failed: {e}"

    if resp.status_code != 200:
        return f"ERROR: {resp.status_code} - {resp.text}"

    try:
        out = resp.json()
    except Exception:
        return f"ERROR: could not decode JSON response: {resp.text}"

    try:
        text = out["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return f"ERROR: unexpected response structure: {out}"

    if expect_json:
        # try parse JSON substring (model may add spaces/newlines). Find first { and last }.
        try:
            # Attempt direct parse first
            parsed = json.loads(text)
            return parsed
        except Exception:
            # fallback: try to extract JSON substring
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                snippet = text[start:end+1]
                try:
                    parsed = json.loads(snippet)
                    return parsed
                except Exception:
                    return {"_raw": text}
            else:
                return {"_raw": text}
    else:
        return text

# ---------------------------
# Session state init
# ---------------------------
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []  # list of (role, text)

if "file_text" not in st.session_state:
    st.session_state["file_text"] = ""

if "flashcards_local" not in st.session_state:
    st.session_state["flashcards_local"] = []  # list of dicts: {q,a,score}

if "quiz_local" not in st.session_state:
    st.session_state["quiz_local"] = []  # list of dicts: q,options,answerIndex,hint

# ---------------------------
# UI Layout
# ---------------------------
st.sidebar.header("Study Settings")
difficulty = st.sidebar.selectbox("Difficulty level (learner skill)", ["Beginner", "Intermediate", "Advanced"])
study_mode = st.sidebar.selectbox("Study Mode", ["Practice", "Exam"])
eli5 = st.sidebar.checkbox("Explain Like I'm 5 (ELI5)", value=False)
quick_answer = st.sidebar.checkbox("Quick Answer (direct first)", value=False)

st.sidebar.markdown("---")
section = st.sidebar.radio("App section", ["Tutor Chat", "Flashcards", "Quiz", "Review (SRS)", "Progress", "Demo Flow"])
st.sidebar.markdown("---")
uploaded_file = st.sidebar.file_uploader("Upload file (PDF, DOCX, TXT) — optional", type=["pdf", "docx", "txt"])
if uploaded_file is not None:
    text = extract_text_from_file(uploaded_file)
    st.session_state["file_text"] = text
    st.sidebar.success("File uploaded and processed — content added to context.")

# ---------------------------
# Section: Tutor Chat
# ---------------------------
if section == "Tutor Chat":
    st.header("💬 Tutor Chat")
    st.write("Ask a question, paste a problem, or ask for a hint/step-by-step/full solution.")
    # show chat history
    for role, txt in st.session_state["chat_history"]:
        if role == "user":
            st.chat_message("user").write(txt)
        else:
            st.chat_message("assistant").write(txt)

    user_msg = st.chat_input("Type your question or problem here...")
    if user_msg:
        st.session_state["chat_history"].append(("user", user_msg))
        st.chat_message("user").write(user_msg)

        extra_instructions = (
            "Behavior additions: after each small step present a short check-question, "
            "offer reflection question after full solutions, and if in Practice mode provide scaffolding. "
            "Only provide full solution if user explicitly asks 'full solution' or equivalent."
        )

        reply = query_gemini(
            task_prompt=user_msg,
            file_context=st.session_state["file_text"],
            difficulty=difficulty,
            study_mode=study_mode,
            eli5=eli5,
            quick_answer=quick_answer,
            extra_instructions=extra_instructions
        )
        st.session_state["chat_history"].append(("assistant", reply))
        st.chat_message("assistant").write(reply)

# ---------------------------
# Section: Flashcards
# ---------------------------
elif section == "Flashcards":
    st.header("🃏 Flashcards (generate from file or topic)")
    with st.form("flashcard_form"):
        topic = st.text_input("Topic (leave empty to use uploaded file content)")
        num = st.slider("Number of cards", 3, 20, 8)
        generate = st.form_submit_button("Generate Flashcards")
    if generate:
        if st.session_state["file_text"] and not topic:
            prompt = f"Create {num} concise Q&A flashcards from the uploaded content. Output JSON: {{\"flashcards\": [{{\"q\":\"...\",\"a\":\"...\"}}, ...]}} exactly."
            parsed = query_gemini(prompt, file_context=st.session_state["file_text"], difficulty=difficulty, study_mode=study_mode, eli5=eli5, expect_json=True)
        else:
            prompt = f"Create {num} concise Q&A flashcards about: {topic}. Output JSON: {{\"flashcards\": [{{\"q\":\"...\",\"a\":\"...\"}}, ...]}} exactly."
            parsed = query_gemini(prompt, difficulty=difficulty, study_mode=study_mode, eli5=eli5, expect_json=True)

        if isinstance(parsed, dict) and "flashcards" in parsed:
            created = 0
            for fc in parsed["flashcards"]:
                q = fc.get("q") or fc.get("Q") or ""
                a = fc.get("a") or fc.get("A") or ""
                if q and a:
                    add_card(q, a)  # persist to SRS DB
                    st.session_state["flashcards_local"].append({"q": q, "a": a, "score": 0})
                    created += 1
            st.success(f"Added {created} flashcards to your SRS deck.")
        else:
            # fallback: treat raw text as lines "Q: ... A: ..."
            raw = parsed.get("_raw") if isinstance(parsed, dict) else str(parsed)
            cards = []
            lines = [l.strip() for l in raw.splitlines() if l.strip()]
            q, a = None, None
            for line in lines:
                if line.lower().startswith("q:"):
                    q = line.split(":", 1)[1].strip()
                elif line.lower().startswith("a:"):
                    a = line.split(":", 1)[1].strip()
                if q and a:
                    add_card(q, a)
                    st.session_state["flashcards_local"].append({"q": q, "a": a, "score": 0})
                    q, a = None, None
            st.info("Flashcards created from raw text (fallback parsing).")

    # Interactive local flashcards with simple SRS priority (show lowest score)
    if st.session_state["flashcards_local"]:
        st.subheader("Practice (local session)")
        cards = st.session_state["flashcards_local"]
        min_score = min(c.get("score", 0) for c in cards)
        candidates = [i for i,c in enumerate(cards) if c.get("score",0)==min_score]
        idx = random.choice(candidates)
        card = cards[idx]
        st.markdown(f"**Q:** {card['q']}")
        if st.button("Show Answer"):
            st.info(card["a"])
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ I got it"):
                cards[idx]["score"] = cards[idx].get("score",0) + 1
                st.success("Great! Increased score.")
        with col2:
            if st.button("❌ I need practice"):
                cards[idx]["score"] = max(0, cards[idx].get("score",0) - 1)
                st.warning("No problem — we'll show this more often.")
        st.session_state["flashcards_local"] = cards

    # Show SRS deck count
    st.write(f"SRS deck size (persisted): {count_cards()} cards")

# ---------------------------
# Section: Quiz
# ---------------------------
elif section == "Quiz":
    st.header("📝 Quiz Generator (multiple-choice)")
    with st.form("quiz_form"):
        topic = st.text_input("Topic (leave empty to use uploaded file content)")
        n = st.slider("Number of quiz questions", 3, 12, 5)
        gen = st.form_submit_button("Generate Quiz")
    if gen:
        if st.session_state["file_text"] and not topic:
            prompt = f"Create {n} multiple-choice questions (A-D) based on the uploaded content. Output JSON: {{\"quiz\": [{{\"q\":\"...\",\"options\": [\"...\",\"...\",\"...\",\"...\"], \"answerIndex\": 0, \"hint\":\"...\"}}, ...]}} exactly."
            parsed = query_gemini(prompt, file_context=st.session_state["file_text"], difficulty=difficulty, study_mode=study_mode, eli5=eli5, expect_json=True)
        else:
            prompt = f"Create {n} multiple-choice questions (A-D) about {topic}. Output JSON: {{\"quiz\": [{{\"q\":\"...\",\"options\": [\"...\",\"...\",\"...\",\"...\"], \"answerIndex\": 0, \"hint\":\"...\"}}, ...]}} exactly."
            parsed = query_gemini(prompt, difficulty=difficulty, study_mode=study_mode, eli5=eli5, expect_json=True)

        if isinstance(parsed, dict) and "quiz" in parsed:
            st.session_state["quiz_local"] = parsed["quiz"]
            st.success("Quiz generated and loaded.")
        else:
            raw = parsed.get("_raw") if isinstance(parsed, dict) else str(parsed)
            st.error("Could not parse structured quiz JSON. Raw output preview below.")
            st.text_area("Raw model output", raw, height=300)

    # display quiz interactive
    if st.session_state["quiz_local"]:
        qlist = st.session_state["quiz_local"]
        # simple indexing controls
        if "quiz_idx" not in st.session_state:
            st.session_state["quiz_idx"] = 0
            st.session_state["quiz_score"] = 0
        idx = st.session_state["quiz_idx"]
        if idx >= len(qlist):
            st.success("Quiz finished!")
            st.write(f"Score: {st.session_state['quiz_score']} / {len(qlist)}")
            if st.button("Restart Quiz"):
                st.session_state["quiz_idx"] = 0
                st.session_state["quiz_score"] = 0
        else:
            item = qlist[idx]
            st.markdown(f"**Q {idx+1}:** {item.get('q')}")
            options = item.get("options") or item.get("choices") or []
            # ensure 4 options
            if len(options) < 2:
                st.error("Model returned insufficient options.")
            else:
                choice = st.radio("Pick an answer:", options, key=f"quiz_{idx}")
                if st.button("Submit Answer"):
                    correct_idx = item.get("answerIndex", None)
                    # support answer as text as fallback
                    correct_answer = None
                    if correct_idx is not None and isinstance(correct_idx, int) and 0 <= correct_idx < len(options):
                        correct_answer = options[correct_idx]
                    else:
                        # try read 'answer' text
                        maybe = item.get("answer")
                        if maybe:
                            correct_answer = maybe
                    if correct_answer and choice == correct_answer:
                        st.success("✅ Correct!")
                        st.session_state["quiz_score"] += 1
                        # mark success -> maybe reduce SRS priority for corresponding card
                    else:
                        st.error(f"❌ Incorrect. Correct answer: {correct_answer}")
                    # show hint button
                    hint = item.get("hint")
                    if hint:
                        if st.button("Show Hint"):
                            st.info(hint)
                    # next
                    if st.button("Next Question"):
                        st.session_state["quiz_idx"] += 1

# ---------------------------
# Section: Review (SRS)
# ---------------------------
elif section == "Review (SRS)":
    st.header("🔁 Spaced Repetition — Review Due Cards")
    due = get_due_cards(limit=10)
    if not due:
        st.info("No cards due right now. Nice work!")
    else:
        st.write(f"{len(due)} card(s) due for review")
        for card in due:
            cid, q, a, ef, interval, reps, next_rev = card
            st.markdown(f"**Q:** {q}")
            if st.button(f"Show answer (card {cid})"):
                st.markdown(f"**A:** {a}")
            quality = st.select_slider("How well did you recall this? (5=perfect, 0=complete blackout)", options=[0,1,2,3,4,5], key=f"quality_{cid}")
            if st.button(f"Submit review (card {cid})", key=f"submit_{cid}"):
                update_card_after_review(cid, int(quality))
                st.success("Saved review. Next review scheduled.")

# ---------------------------
# Section: Progress
# ---------------------------
elif section == "Progress":
    st.header("📈 Progress & Stats")
    total = count_cards()
    due_count = len(get_due_cards(limit=1000))
    st.metric("Total SRS cards", total)
    st.metric("Cards due now", due_count)
    st.subheader("Recent chat")
    for role, txt in st.session_state["chat_history"][-8:]:
        if role == "user":
            st.write(f"**You:** {txt}")
        else:
            st.write(f"**Tutor:** {txt}")

# ---------------------------
# Section: Demo Flow
# ---------------------------
elif section == "Demo Flow":
    st.header("▶️ Quick Demo Walkthrough")
    st.markdown("""
    1. Upload a short PDF/DOCX/TXT (or leave empty to try general prompts).  
    2. Choose Beginner / Practice / Exam and optionally ELI5.  
    3. Use Tutor Chat to ask a question. Try: `Solve 2x + 3 = 11` or `Explain variables`.  
    4. Generate Flashcards from file or topic, then open Review to practice.  
    5. Generate a Quiz and attempt questions.
    """)
    if st.button("Run sample chat prompt"):
        sample = "Solve 2x + 3 = 11 step-by-step (Practice, but ask check-questions)."
        st.session_state["chat_history"].append(("user", sample))
        st.chat_message("user").write(sample)
        resp = query_gemini(sample, file_context=st.session_state["file_text"], difficulty="Beginner", study_mode="Practice", eli5=True)
        st.session_state["chat_history"].append(("assistant", resp))
        st.chat_message("assistant").write(resp)

# ---------------------------
# Footer / helpers
# ---------------------------
st.sidebar.markdown("---")
st.sidebar.markdown("Made for study. Keep API key secure. For deployment: set secrets or env var `API_KEY`.")
