import streamlit as st
import requests
import json
import os
import random
import sqlite3
import PyPDF2
import docx
from datetime import date, datetime, timedelta

# -------------------------------
# CONFIG
# -------------------------------
API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCvBc3KyBMush9se3QDqEdUTMqgkxpRRS0")
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

st.set_page_config(page_title="📘 Study Tutor", page_icon="📚", layout="wide")
st.title("📘 Study Tutor")
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

# Spaced repetition deck
if "deck" not in st.session_state:
    st.session_state["deck"] = []  # {"q","a","interval","repetitions","next_review"}

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
IMPORTANT: Respond ONLY with valid JSON for Flashcards and Quizzes not for Chat. 
- Do not include explanations, markdown, or extra text.
- For flashcards: respond with a JSON array of objects { "q": "...", "a": "..." }.
- For quizes: respond with a JSON array of objects { "q": "...", "options": ["..."], "answerIndex": int }.
- Do not wrap in code blocks.
- For Chat do not use JSON 
- For tutor chat give hint only when user ask for hint
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

    # Add ELI5 mode toggle
    eli5_note = ""
    if st.session_state.get("eli5_mode"):
        eli5_note = "\nExplain this as if I'm completely new to the topic, using very simple words and examples."

    full_prompt = (
        f"{SYSTEM_INSTRUCTIONS}\n\n"
        f"Difficulty: {difficulty}\nMode: {mode}{eli5_note}\n\n"
        f"Context:\n{context}\n\n"
        f"User request:\n{task_prompt}"
    )

    data = {"contents": [{"role": "user", "parts": [{"text": full_prompt}]}]}

    try:
        response = requests.post(API_URL, headers=headers, params=params, json=data)
        response.raise_for_status()
        output = response.json()

        # Safely extract text
        candidates = output.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts and "text" in parts[0]:
                return parts[0]["text"]

        return f"⚠️ Unexpected response format: {json.dumps(output, indent=2)}"

    except Exception as e:
        return f"❌ Error: {str(e)}"
# -------------------------------
# SIDEBAR CONTROLS
# -------------------------------

st.sidebar.header("⚙️ Settings")
section = st.sidebar.radio("Choose Section", ["Tutor Chat", "Flashcards", "Quiz", "SRS Review"])
study_mode = st.sidebar.selectbox("Study Mode", ["practice", "exam"])
difficulty = st.sidebar.selectbox("Difficulty", ["beginner", "intermediate", "advanced"])
eli5_mode = st.sidebar.checkbox("🍼 Explain like I'm new here (ELI5 mode)")
uploaded_file = st.sidebar.file_uploader("📎 Upload a study file", type=["pdf", "docx", "txt"])
file_content = read_file(uploaded_file) if uploaded_file else ""
# -------------------------------
st.session_state["eli5_mode"] = eli5_mode
# SECTION: TUTOR CHAT
    # -------------------------------
# SECTION: TUTOR CHAT
    # -------------------------------
# SECTION: TUTOR CHAT
# -------------------------------
if section == "Tutor Chat":
    st.header("💬 Study Chat")

    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Show previous messages
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input bar
    user_input = st.chat_input("Type your message here...")

    if user_input:
        # Save user message
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Build full conversation for model context
        conversation_text = ""
        for msg in st.session_state.chat_history:
            role_label = "User" if msg["role"] == "user" else "Assistant"
            conversation_text += f"{role_label}: {msg['content']}\n"

        # Add ELI5 note if enabled
        extra_instruction = ""
        if st.session_state.get("eli5_mode"):
            extra_instruction = "\nExplain this as if I'm completely new to the topic, using very simple words and examples."

        # Query Gemini
        reply = query_gemini(
            task_prompt=conversation_text,
            context=file_content,
            mode=study_mode,
            difficulty=difficulty
        )

        # Save and display assistant message
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)

# -------------------------------
# SECTION: FLASHCARDS
# -------------------------------
if section == "Flashcards":
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

        # Save to SRS deck
        if st.button("💾 Save generated flashcards to SRS deck"):
            added = 0
            existing_qs = {c.get("q") for c in st.session_state["deck"]}
            for fc in st.session_state["flashcards_local"]:
                q_text = fc.get("q") or ""
                a_text = fc.get("a") or ""
                if not q_text or q_text in existing_qs:
                    continue
                card_obj = {
                    "q": q_text,
                    "a": a_text,
                    "interval": 1,
                    "repetitions": 0,
                    "next_review": date.today().isoformat()
                }
                st.session_state["deck"].append(card_obj)
                existing_qs.add(q_text)
                added += 1
            st.success(f"Saved {added} card(s) to SRS deck.")

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
        reply = query_gemini(
            f"Generate {n} multiple-choice quiz questions in JSON. Each with 'q','options','answerIndex'.",
            context=context
        )
        try:
            # Clean the response to avoid parsing issues
            cleaned_reply = reply.strip()
            qlist = json.loads(cleaned_reply)
            st.session_state["quiz_local"] = qlist
            st.session_state["quiz_idx"] = 0
            st.session_state["quiz_score"] = 0
        except Exception as e:
            st.error(f"⚠️ Could not parse quiz. Showing raw output.\nError: {e}")
            st.write(reply)

    if st.session_state.get("quiz_local"):
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
                    st.error(f"❌ Incorrect. Correct a
# -------------------------------
# SECTION: SRS REVIEW
# -------------------------------
elif section == "SRS Review":
    st.header("🔁 Spaced Repetition — Review Deck")

    if not st.session_state.get("deck"):
        st.info("Your SRS deck is empty. Generate flashcards and click 'Save generated flashcards to SRS deck' in the Flashcards section.")
    else:
        total = len(st.session_state["deck"])
        today = date.today()
        due_list = []
        for idx, c in enumerate(st.session_state["deck"]):
            try:
                nr_date = date.fromisoformat(c.get("next_review"))
            except Exception:
                nr_date = today
            if nr_date <= today:
                due_list.append((idx, c))

        st.subheader(f"Deck: {total} cards — {len(due_list)} due today")

        if not due_list:
            st.success("No cards due for review right now. 🎉")
        else:
            idx, card = due_list[0]
            st.markdown(f"**Q:** {card.get('q')}")
            if st.button("Show Answer", key=f"show_{idx}"):
                st.info(f"A: {card.get('a')}")

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("✅ Good", key=f"good_{idx}"):
                    reps = card.get("repetitions", 0) + 1
                    card["repetitions"] = reps
                    prev_interval = card.get("interval", 1)
                    if reps == 1:
                        new_interval = 1
                    elif reps == 2:
                        new_interval = 6
                    else:
                        new_interval = int(round(max(1, prev_interval * 2.5)))
                    card["interval"] = new_interval
                    card["next_review"] = (today + timedelta(days=new_interval)).isoformat()
                    st.session_state["deck"][idx] = card
                    st.experimental_rerun()
            with col2:
                if st.button("➕ Partial", key=f"partial_{idx}"):
                    reps = card.get("repetitions", 0) + 1
                    card["repetitions"] = reps
                    prev_interval = card.get("interval", 1)
                    new_interval = int(round(max(1, prev_interval * 1.5)))
                    card["interval"] = new_interval
                    card["next_review"] = (today + timedelta(days=new_interval)).isoformat()
                    st.session_state["deck"][idx] = card
                    st.experimental_rerun()
            with col3:
                if st.button("❌ Forgot", key=f"fail_{idx}"):
                    card["repetitions"] = 0
                    card["interval"] = 1
                    card["next_review"] = (today + timedelta(days=1)).isoformat()
                    st.session_state["deck"][idx] = card
                    st.experimental_rerun()

        st.markdown("---")
        if st.button("Export deck"):
            st.download_button("Download JSON", data=json.dumps(st.session_state["deck"], indent=2), file_name="srs_deck.json")
        if st.button("Clear deck"):
            st.session_state["deck"] = []
            st.experimental_rerun()















