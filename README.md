📘 Study Mode Tutor

An interactive AI-powered tutor built with Streamlit + Gemini API.
It supports:

💬 Chat with memory (step-by-step tutoring)
🃏 Flashcards (with answers hidden until revealed)
📝 Quizzes (multiple choice with score tracking)
📎 File upload (PDF, DOCX, TXT) for study material
🎯 Study Modes: practice, exam, and ELI5 (explain like I’m new)
🎚️ Difficulty Levels: beginner, intermediate, advanced
📚 Spaced Repetition Review (future enhancement)
🚀 Setup Guide
1. Clone the repo
git clone https://github.com/asadaliashraf/tutor-app.git
cd study-mode-tutor
2. Install dependencies
pip install -r requirements.txt
requirements.txt should contain:
streamlit
requests
PyPDF2
python-docx
3. Set your Gemini API Key
In your terminal (or add to .env file):
export GEMINI_API_KEY="your_api_key_here"
On Windows (PowerShell):
$env:GEMINI_API_KEY="your_api_key_here"
4. Run the app
streamlit run study_mode_app.py
🖥️ Walkthrough / Demo Script
1. Open the app
You’ll see Study Mode Tutor with sidebar controls.
2. Upload a file (optional)
PDF, DOCX, or TXT supported.
Example: upload a short biology PDF to generate flashcards & quizzes.
3. Chat Section
Type a question: “Solve 2x + 3 = 11”.
The tutor will guide step-by-step with Socratic hints.
Try switching Mode → ELI5 for super-simple explanations.
4. Flashcards Section
Enter a topic (e.g., “photosynthesis”) and generate 5 flashcards.
Flip each card by clicking Show Answer.
5. Quiz Section
Enter a topic (or use your uploaded file).
Generate 5 multiple-choice questions.
Answer each and track your score.
6. SRS Review (coming soon 🚧)

This section will let you review past flashcards with spaced repetition scheduling.
