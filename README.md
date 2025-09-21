📘 Study Mode Tutor

Your AI-powered study companion with tutoring, flashcards, quizzes, spaced repetition, and ELI5 explanations. Built with Streamlit and powered by Gemini API.

🚀 Features

Tutor Chat:

Friendly, Socratic teaching style.

Supports step-by-step guidance, hints, and full solutions.

New: Explain Like I’m New (ELI5) mode for ultra-simplified answers.

Flashcards Generator:

Upload a file (PDF, DOCX, or TXT) or enter a topic.

Automatically generate flashcards in Q/A format.

Practice with self-marking (✅ Got it / ❌ Need practice).

Quiz Generator:

Generate multiple-choice quizzes with hints.

Interactive answering and scoring.

Spaced Repetition Review (SRS):

Save flashcards into a review pool.

Revisit them later using a Leitner-style learning system.

Configurable Modes:

Difficulty: Beginner / Intermediate / Advanced.

Study Modes: Practice / Exam.

ELI5 toggle: explain everything in simple terms.

⚙️ Setup

Clone the repo

git clone https://github.com/asadaliashraf/tutor-app.git
cd study-mode-tutor


Create virtual environment & install dependencies

python -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows

pip install -r requirements.txt


Set your Gemini API Key

export GEMINI_API_KEY="your_api_key_here"   # macOS/Linux
setx GEMINI_API_KEY "your_api_key_here"     # Windows


Run the app

streamlit run study_mode_app.py

📝 Usage

Select your Study Mode and Difficulty from the sidebar.

Upload study material (PDF/DOCX/TXT) or type a topic.

Choose a section:

Tutor Chat → Ask questions, get guided answers.

Flashcards → Generate and practice cards.

Quiz → Test yourself with multiple-choice questions.

SRS Review → Strengthen long-term memory.

🎬 Demo Script / Walkthrough

Launch app with:

streamlit run study_mode_app.py


In sidebar, upload a sample PDF (e.g., biology notes).

Generate flashcards → Try practicing with them.

Switch to Quiz → Answer 5 auto-generated questions.

Try Tutor Chat with:

Explain photosynthesis like I’m new here.


You’ll see the ELI5 mode in action.

Add cards to SRS Review → Revisit them later for spaced repetition practice.
