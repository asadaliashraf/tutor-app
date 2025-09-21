📘 Study Mode App

An interactive AI-powered study companion that helps you learn smarter using flashcards, quizzes, spaced repetition, and multiple study modes.

🚀 Features

✅ Explain Like I’m New (ELI5) – Simplifies explanations into beginner-friendly language with analogies.
✅ Flashcards Generator – Auto-creates Q/A flashcards for review.
✅ Quiz Generator – Multiple-choice quizzes with hints + correct answers.
✅ Spaced-Repetition Review – Reinforces concepts at intervals for long-term memory.
✅ Configurable Study Modes

Beginner: Simple explanations, small quizzes.

Practice: Mixed difficulty, more details.

Exam: Hardest mode, minimal hints, strict quizzes.
✅ File Upload Support – Upload .pdf, .docx, .txt to extract study material.
✅ Chat Memory – Keeps conversations flowing naturally.

⚙️ Setup
1. Clone the repo
git clone https://github.com/your-username/study-mode-app.git
cd study-mode-app

2. Install dependencies
pip install -r requirements.txt

3. Environment variables

Create a .env file in the root folder:

GEMINI_API_KEY=your_gemini_api_key_here

4. Run the app
streamlit run study_mode_app.py


App will be available at: http://localhost:8501/

🖥️ Usage
Main Sections

Chat – Ask questions, get continuous explanations.

Explain Like I’m New (ELI5) – Beginner-level breakdowns.

Flashcards – Generate study flashcards from text or file.

Quiz Mode – Take AI-generated quizzes.

Spaced Repetition Review – Review old flashcards at scheduled intervals.

🎬 Demo Walkthrough

Here’s a sample run of the app 👇

1. Upload a file

Upload a biology.pdf.

2. Choose a Study Mode

Select Beginner → Practice → Exam depending on difficulty.

3. Try ELI5 Mode

Input:

Explain photosynthesis like I’m new here.


Output:

Photosynthesis is like plants cooking food. They use sunlight like an oven, water like ingredients, and carbon dioxide like seasoning to make sugar, which is their food.

4. Generate Flashcards

Click Flashcards → Generate.

Output Example:

Q: What is the basic unit of life?  
A: Cell  

Q: What gas do humans exhale?  
A: Carbon Dioxide  

5. Take a Quiz

Click Quiz → Generate.

Output Example:

Q: What is the process plants use to make food?  
Options: [Respiration, Photosynthesis, Transpiration, Germination]  
Answer: Photosynthesis  
Hint: It uses sunlight.

6. Spaced Repetition Review

Review flashcards saved from earlier sessions.

Oldest flashcards reappear first.

Helps strengthen memory over time.

📜 Tech Stack

Python 3.9+

Streamlit for UI

Gemini API for AI reasoning

PyPDF2, python-docx for file parsing

✅ Deliverables

Core flows: ELI5, flashcards, quiz, spaced repetition

Configurable study modes: Beginner, Practice, Exam

Full README + demo walkthrough

File upload support
