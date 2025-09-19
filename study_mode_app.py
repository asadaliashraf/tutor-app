import streamlit as st
import requests
import json
import base64
import PyPDF2
import docx

API_KEY = "AIzaSyCvBc3KyBMush9se3QDqEdUTMqgkxpRRS0"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

# Page config
st.set_page_config(page_title="📘 Study Mode Tutor", page_icon="📚", layout="wide")

# Inject custom CSS for modern look
st.markdown("""
    <style>
    body {
        font-family: 'Segoe UI', sans-serif;
        background-color: #f8fafc;
    }
    .chat-bubble-user {
        background-color: #2563eb;
        color: white;
        padding: 10px 15px;
        border-radius: 15px;
        margin: 5px 0;
        max-width: 70%;
        margin-left: auto;
    }
    .chat-bubble-assistant {
        background-color: #e2e8f0;
        color: black;
        padding: 10px 15px;
        border-radius: 15px;
        margin: 5px 0;
        max-width: 70%;
        margin-right: auto;
    }
    .stButton>button {
        border-radius: 12px;
        background-color: #2563eb;
        color: white;
        font-weight: 600;
        padding: 8px 20px;
    }
    .stButton>button:hover {
        background-color: #1e40af;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📘 Study Mode Tutor")
st.caption("""
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
)

# Sidebar with study modes
study_mode = st.sidebar.radio("🎯 Select Study Mode", ["Beginner", "Practice", "Exam"])
st.sidebar.markdown("📂 You can also attach a file for context.")

# File upload
uploaded_file = st.sidebar.file_uploader("Upload PDF or DOCX", type=["pdf", "docx"])

file_text = ""
if uploaded_file:
    try:
        if uploaded_file.type == "application/pdf":
            reader = PyPDF2.PdfReader(uploaded_file)
            file_text = "".join([page.extract_text() for page in reader.pages])
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(uploaded_file)
            file_text = " ".join([p.text for p in doc.paragraphs])
        st.sidebar.success("✅ File uploaded successfully!")
    except Exception as e:
        st.sidebar.error(f"Could not read file: {e}")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "system", "content": """You are a patient, encouraging, and supportive study tutor operating in "Study Mode."  
        (system instructions here...)"""}
    ]

# Display chat history with custom bubbles
for msg in st.session_state["messages"]:
    if msg["role"] == "user":
        st.markdown(f"<div class='chat-bubble-user'>🙋‍♂️ {msg['content']}</div>", unsafe_allow_html=True)
    elif msg["role"] == "assistant":
        st.markdown(f"<div class='chat-bubble-assistant'>📘 {msg['content']}</div>", unsafe_allow_html=True)

# Chat input
user_input = st.chat_input("✏️ Ask me a question or type a problem...")

if user_input:
    st.session_state["messages"].append({"role": "user", "content": user_input})
    st.markdown(f"<div class='chat-bubble-user'>🙋‍♂️ {user_input}</div>", unsafe_allow_html=True)

    # Prepare request
    headers = {"Content-Type": "application/json"}
    params = {"key": API_KEY}

    context = st.session_state["messages"]
    if file_text:
        context.append({"role": "user", "content": f"Here’s study material to use:\n{file_text[:2000]}"})

    data = {
        "contents": [{"parts": [{"text": m["content"]}]} for m in context if m["role"] != "system"]
    }

    response = requests.post(API_URL, headers=headers, params=params, json=data)

    if response.status_code == 200:
        output = response.json()
        try:
            answer = output["candidates"][0]["content"]["parts"][0]["text"]
            st.session_state["messages"].append({"role": "assistant", "content": answer})
            st.markdown(f"<div class='chat-bubble-assistant'>📘 {answer}</div>", unsafe_allow_html=True)
        except Exception:
            st.error("⚠️ Unexpected response format")
            st.json(output)
    else:
        st.error(f"❌ Error {response.status_code}: {response.text}")
      # ================================
# Flashcards Generator
# ================================
st.subheader("🃏 Flashcards")

if st.button("Generate Flashcards"):
    headers = {"Content-Type": "application/json"}
    params = {"key": API_KEY}
    data = {
        "contents": [{
            "parts": [{"text": f"Generate 5 flashcards (Q/A format) from this material:\n{file_text or user_input}"}]
        }]
    }
    response = requests.post(API_URL, headers=headers, params=params, json=data)

    if response.status_code == 200:
        output = response.json()
        try:
            flashcards_text = output["candidates"][0]["content"]["parts"][0]["text"]
            st.session_state["flashcards"] = [
                {"front": q.strip(), "back": a.strip()}
                for q, a in (line.split(" - ") for line in flashcards_text.split("\n") if " - " in line)
            ]
        except Exception:
            st.error("⚠️ Unexpected flashcards format")
            st.json(output)
    else:
        st.error(f"❌ Error {response.status_code}: {response.text}")

# Display flashcards with flip functionality
if "flashcards" in st.session_state:
    for i, card in enumerate(st.session_state["flashcards"]):
        with st.expander(f"Flashcard {i+1}: {card['front']}"):
            st.info(card['back'])

# ================================
# Quiz Generator
# ================================
st.subheader("📝 Practice Quiz")

if st.button("Generate Quiz"):
    headers = {"Content-Type": "application/json"}
    params = {"key": API_KEY}
    data = {
        "contents": [{
            "parts": [{"text": f"Generate a 3-question multiple-choice quiz from this material. Include correct answer labels."}]
        }]
    }
    response = requests.post(API_URL, headers=headers, params=params, json=data)

    if response.status_code == 200:
        output = response.json()
        try:
            quiz_text = output["candidates"][0]["content"]["parts"][0]["text"]
            st.session_state["quiz"] = quiz_text.split("\n\n")  # separate questions
        except Exception:
            st.error("⚠️ Unexpected quiz format")
            st.json(output)
    else:
        st.error(f"❌ Error {response.status_code}: {response.text}")

# Display quiz
if "quiz" in st.session_state:
    for i, q in enumerate(st.session_state["quiz"]):
        st.markdown(f"**Q{i+1}:** {q}")
        answer = st.radio("Choose an answer:", ["A", "B", "C", "D"], key=f"quiz_{i}")
        if st.button(f"Check Q{i+1}", key=f"check_{i}"):
            st.success("✅ Correct!") if answer in q else st.error("❌ Try again!")

