# 🎙️ Reception Voice Agent

An AI-powered virtual receptionist built using Python, OpenAI Whisper, Groq API, and SQLite. The application processes caller audio, converts speech into text, identifies the caller's name, purpose of calling, and callback number, and stores the information in a database.

## 🚀 Features

- **Speech-to-Text:** Converts audio recordings into text using OpenAI Whisper.
- **AI Information Extraction:** Uses a Groq-hosted Llama model to identify caller details from transcripts.
- **Call Management:** Stores caller information and transcripts in an SQLite database.
- **Search and Retrieval:** Lists and searches saved call records.
- **Input Validation:** Handles missing information and invalid responses with safe default values.
- **Sample Audio:** Includes sample recordings to demonstrate the workflow.

## 🛠️ Technologies Used

- Python
- OpenAI Whisper
- Groq API (Llama model)
- SQLite
- JSON
- pytest

## ⚙️ How It Works

1. The user provides an audio recording or text transcript.
2. Whisper converts the audio into text.
3. The AI model extracts the caller's name, intent, and callback number.
4. The application validates the extracted information.
5. The call details and transcript are saved in SQLite.
6. Users can list or search previously stored calls.

## 📁 Project Structure

```text
reception_voice_agent/
├── app.py
├── agent.py
├── speech_to_text.py
├── database.py
├── models.py
├── requirements.txt
├── .env.example
├── README.md
├── audio/
└── tests/
    └── test_pipeline.py
```

## 💻 Installation and Setup

**Prerequisites:** Python 3.10 or later and FFmpeg installed on your system.

1. Clone the repository:

```bash
git clone https://github.com/Sneha27-dev/reception-voice-agent.git
cd reception-voice-agent
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
```

On Windows:

```bash
venv\Scripts\activate
```

3. Install the required packages:

```bash
pip install -r requirements.txt
```

4. Create your environment configuration file by copying `.env.example` to `.env`.

5. Add your own Groq API key to `.env`:

```text
GROQ_API_KEY=your-groq-api-key-here
```

Never upload your real `.env` file or API key to GitHub.

## ▶️ Usage

Process an audio recording:

```bash
python app.py process --audio audio/call_01.wav
```

Process a text transcript:

```bash
python app.py process --text "Hello, my name is Rahul. I am calling about a job opening."
```

List saved calls:

```bash
python app.py list
```

Search call records:

```bash
python app.py search --name Rahul
```

Run automated tests:

```bash
python -m pytest tests/ -v
```

## 🎯 Example Use Case

A caller leaves a message asking about a job opportunity. The application transcribes the recording, extracts the caller's details, identifies the reason for the call, and stores the information for later reference.

## 🔮 Future Improvements

- Live telephone call integration
- Web dashboard for viewing and managing calls
- Improved phone number validation
- Multilingual speech support
- Better logging and error monitoring

## 👩‍💻 Author

**Sneha**

- GitHub: [Sneha27-dev](https://github.com/Sneha27-dev)
- LinkedIn: [Sneha](https://www.linkedin.com/in/sneha-557181312)

---

*This project demonstrates speech recognition, LLM-based information extraction, database management, and Python application development.*
