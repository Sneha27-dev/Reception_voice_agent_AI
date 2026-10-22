# Reception Voice Agent

A small, reliable, end-to-end AI agent that acts like a virtual receptionist:
it listens to (or reads) a caller's message, transcribes it, uses an LLM to
understand who called and why, and stores a structured record in SQLite.

```
Audio File / Text  ->  Speech-to-Text (Whisper)  ->  Transcript
                                                          |
                                                          v
                                              LLM Agent (Groq-hosted Llama model)
                                                          |
                                                          v
                                        {caller_name, intent, callback_number}
                                                          |
                                                          v
                                                   SQLite (calls.db)
                                                          |
                                                          v
                                              list_calls() / search_calls()
```

---

## 1. Project Structure

```
reception_voice_agent/
├── app.py                 # CLI entry point (process / list / search)
├── agent.py                # LLM "brain": system prompt + structured extraction
├── speech_to_text.py       # Whisper-based audio -> transcript
├── database.py             # All SQLite logic (save_call, list_calls, search_calls)
├── models.py                # CallRecord dataclass + shared constants
├── requirements.txt
├── .env.example
├── README.md
├── audio/                   # Sample test audio (generated with offline TTS)
│   ├── call_01.wav
│   ├── call_02.wav
│   └── call_03.wav
├── data/
│   └── calls.db             # Created automatically on first run
└── tests/
    └── test_pipeline.py     # Automated tests (DB + agent logic + error handling)
```

---

## 2. Installation

### Prerequisites
* Python 3.10+
* `ffmpeg` installed on your system (required by Whisper to decode audio)
  * macOS: `brew install ffmpeg`
  * Ubuntu/Debian: `sudo apt-get install ffmpeg`
  * Windows: [download from ffmpeg.org](https://ffmpeg.org/download.html) and add it to PATH

### Steps

```bash
# 1. Clone / unzip the project, then move into it
cd reception_voice_agent

# 2. (Recommended) create a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# then open .env and paste your real GROQ_API_KEY
```

The first time you run the app, Whisper will download its model file
(~140MB for the default "base" model) from OpenAI's servers - this requires
an internet connection once. After that it runs fully offline.

---

## 3. Running the Application

### Process a call from an audio file
```bash
python app.py process --audio audio/call_01.wav
```

### Process a call from raw text (skips speech-to-text)
Useful for quickly testing the LLM + database without needing an audio file:
```bash
python app.py process --text "Hello, my name is Sneha. I am calling regarding the interview schedule. Please call me back on 9876543210."
```

### View all stored calls
```bash
python app.py list
```

### Search stored calls
```bash
python app.py search --name Rahul
python app.py search --intent "Job Inquiry"
python app.py search --number 9876543210
python app.py search --date 2026-08-19
```

---

## 4. Example Input / Output

**Input (audio transcribed to):**
> "Hello, my name is Sneha. I am calling regarding the interview schedule. Please call me back on 9876543210."

**Console output:**
```
Transcribing audio: audio/call_01.wav
Transcript: Hello, my name is Sneha. I am calling regarding the interview schedule. Please call me back on 9876543210.

Extracting structured information with the LLM...
Saving call to database...

Call processed successfully:
ID:              1
Caller Name:     Sneha
Intent:          Interview Inquiry
Callback Number: 9876543210
Transcript:      Hello, my name is Sneha. I am calling regarding the interview schedule. Please call me back on 9876543210.
Created At:      2026-08-19 05:39:38
```

**Stored JSON-equivalent record:**
```json
{
  "caller_name": "Sneha",
  "intent": "Interview Inquiry",
  "callback_number": "9876543210"
}
```

---

## 5. Database Structure

Table `calls` in `data/calls.db`:

| Column          | Type    | Notes                                   |
|-----------------|---------|------------------------------------------|
| id              | INTEGER | Primary key, auto-increment              |
| caller_name     | TEXT    | "Unknown" if not stated                  |
| intent          | TEXT    | "General Inquiry" if unclear             |
| callback_number | TEXT    | "Not provided" if missing                |
| transcript      | TEXT    | Full transcript of the call              |
| created_at      | TEXT    | Timestamp, set automatically by SQLite   |

Example rows after processing the three sample calls:

```
ID | Name    | Intent             | Callback Number
--------------------------------------------------------
1  | Sneha   | Interview Inquiry  | 9876543210
2  | Rahul   | Job Inquiry        | 9876543210
3  | Unknown | Service Inquiry    | Not provided
```

Example direct SQL queries you can run against `data/calls.db`:
```sql
SELECT * FROM calls ORDER BY id DESC;
SELECT * FROM calls WHERE intent = 'Job Inquiry';
SELECT * FROM calls WHERE callback_number = 'Not provided';
```

---

## 6. Sample Audio / Test Data

`audio/call_01.wav`, `call_02.wav`, and `call_03.wav` are included and were
generated offline with `espeak-ng` (a free text-to-speech engine) reading
the exact transcripts from the assignment brief, so they can be transcribed
and used to demonstrate the pipeline immediately with no manual recording
needed.

To regenerate them yourself, or add more sample calls:
```bash
# Linux: sudo apt-get install espeak-ng
espeak-ng -v en -s 150 "Your sample call text here" -w audio/call_04.wav
```
Any real microphone recording (saved as .wav/.mp3/.m4a) will also work -
just point `--audio` at the file.

### The three required test cases

| # | Transcript | Expected Name | Expected Intent | Expected Number |
|---|---|---|---|---|
| 1 | "Hello, my name is Sneha. I am calling regarding the interview schedule. Please call me back on 9876543210." | Sneha | Interview Inquiry | 9876543210 |
| 2 | "Hi, this is Rahul. I want to know about the software engineer job opening. My number is 9876543210." | Rahul | Job Inquiry | 9876543210 |
| 3 | "Hello, I want to know more about your service." | Unknown | Service Inquiry | Not provided |

---

## 7. Testing

Automated tests cover the database layer, the LLM extraction/validation
logic (with the LLM call itself mocked so tests run without a live API key
or network access), and speech-to-text error handling:

```bash
python -m pytest tests/ -v
```

All 16 tests pass. They verify, among other things:
* The three required sample calls extract exactly the expected fields.
* A repeat caller creates a new row instead of overwriting the old one.
* Malformed/garbage LLM output (bad JSON, a non-numeric "phone number") is
  never trusted blindly - it falls back to the safe default values.
* Missing files, unsupported audio formats, empty audio, and empty
  transcripts all raise a clear error instead of crashing.

### Manual end-to-end test
```bash
python app.py process --audio audio/call_01.wav
python app.py process --audio audio/call_02.wav
python app.py process --audio audio/call_03.wav
python app.py list
```

---

## 8. Design Decisions and Tradeoffs

**Why Python** - the project and Whisper are supported by Python libraries, and the Groq SDK is used for the LLM call
Python-first, and its readability makes the project easy for a fresher to
explain in an interview.

**Why Whisper for speech-to-text** - it is free, runs locally (audio never
leaves the machine), handles accents and background noise well for its
size, and is the most common practical choice for a project like this. The
"base" model is used by default as a balance of speed and accuracy; this is
configurable via `WHISPER_MODEL` in `.env`.

**Why Groq-hosted Llama for the LLM** - the task is simple structured
extraction from a short transcript, so a small, fast, inexpensive model
(Llama 3.3) is sufficient; the API is a single HTTP call with no extra
infrastructure; and Groq provides an API for testing.
Swapping providers only requires editing `_call_llm()` in `agent.py` - the
rest of the app (parsing, validation, database, CLI) is provider-agnostic
because it only depends on getting back a JSON string.

**Why SQLite** - the project needs one small table with no concurrent
writers and no separate server to install; SQLite is a single file,
built into Python's standard library, and perfectly reproducible for an
evaluator (`data/calls.db` can just be inspected directly).

**Why one agent, not multiple** - the task (transcribe -> extract three
fields -> store -> retrieve) is a single linear pipeline with no need for
planning, delegation, or multiple specialized roles. A multi-agent system
would add coordination complexity without adding capability here.

**Why plain functions instead of a framework** - `save_call()` and
`list_calls()` are simple, well-defined operations. A tool-calling
framework or agent orchestration library would add a dependency and an
abstraction layer without making a two-tool pipeline more reliable.

**Current limitations**
* Processes uploaded/recorded audio files, not live telephone calls; a
  production version would connect a telephony provider (e.g. Twilio) that
  streams audio into the same `speech_to_text.py` -> `agent.py` pipeline.
* Whisper's "base" model is a good balance of speed/accuracy but will
  occasionally mishear uncommon names or noisy audio; a production system
  might use a larger model or a paid cloud STT API for higher accuracy.
* Phone number validation is a light sanity check (digit count), not full
  international phone number parsing.
* Single-process CLI, no concurrent multi-call handling; fine for a demo,
  not for a live call center.

**What could be improved in production**
* Real telephony integration (Twilio/Vonage) for live calls.
* A proper phone-number parser/validator (e.g. `phonenumbers` library).
* A web dashboard for receptionists to review calls instead of the CLI.
* Retry/backoff logic around the LLM API call for transient failures.
* Structured logging and metrics instead of print statements.

---

## 9. Testing and Edge Cases (with results)

| # | Case | How it's tested | Result |
|---|---|---|---|
| 1 | Complete call (name + intent + number) | `test_extract_call_info_complete_call` | Fields extracted correctly |
| 2 | Missing caller name | `test_extract_call_info_missing_name_and_number` | Falls back to "Unknown" |
| 3 | Missing callback number | `test_extract_call_info_missing_name_and_number` | Falls back to "Not provided" |
| 4 | Missing both name and number | Assignment Test Case 3, manually verified via CLI | Both defaults applied |
| 5 | Unknown intent | Sanitization defaults to "General Inquiry" | Verified via agent logic |
| 6 | Different ordering of information | `test_extract_call_info_different_ordering` | Extracted correctly regardless of order |
| 7 | Invalid/empty audio | `test_transcribe_empty_file_raises`, `test_transcribe_unsupported_format_raises` | Raises `TranscriptionError`, no crash |
| 8 | Multiple calls | `test_repeat_caller_creates_separate_records` | Separate rows created, none overwritten |
| 9 | Database retrieval | `test_save_and_list_calls`, manual `python app.py list` | Records saved and listed correctly |
| 10 | LLM/API failure | `test_extract_call_info_missing_api_key_raises`, `test_extract_call_info_rejects_invalid_json` | Raises `AgentError` with a clear message, CLI exits cleanly (no traceback) |

---

## 10. One-Minute Explanation (for a technical interview)

"This is a Reception Voice Agent that simulates a virtual receptionist. It
takes an audio recording of a caller - or raw text for quick testing -
transcribes it locally with OpenAI's Whisper model, then sends that
transcript to the Groq-hosted Llama model with a system prompt that tells it exactly what to
extract: the caller's name, their intent, and a callback number. The model
is instructed never to invent missing information and to use fixed
fallback values - 'Unknown', 'Not provided', 'General Inquiry' - when
something isn't stated. I don't fully trust the LLM's output either: there's
a validation layer that checks the JSON is well-formed and that anything
claiming to be a phone number actually looks like one before it's saved.
Every processed call becomes a new row in a local SQLite database, and
there's a small CLI to process calls, list everything stored, or search by
name, intent, number, or date. I kept it to a single agent with two or
three plain Python functions rather than a multi-agent framework, because
the task is a straightforward linear pipeline - the extra complexity
wouldn't have added any real capability."

---

## 11. Likely Interview Questions

**Q: Why didn't you let the LLM write directly to the database?**
A: Separation of concerns and safety. The LLM's only job is to return JSON;
`agent.py` validates and sanitizes that JSON (e.g. rejecting a "phone
number" with fewer than 7 digits) before `database.py` ever touches SQLite.
This means a bad or hallucinated LLM response can't corrupt the database
or execute unintended operations.

**Q: What happens if Whisper mishears a name?**
A: The system has no way to know the transcript itself is wrong - it can
only work with what it was given, same as a human receptionist mishearing
someone on a bad phone line. This is a known limitation, called out
explicitly in the README rather than hidden.

**Q: How do you stop the LLM from making up a caller's name?**
A: Two layers: the system prompt explicitly forbids inventing information
and specifies exact fallback strings, and `_sanitize_fields()` in `agent.py`
independently double-checks the response (e.g. discarding an
implausible phone number) rather than trusting the prompt alone.

**Q: Why SQLite instead of Postgres/MySQL?**
A: This project has one table, no concurrent writers, and needs to be
trivially reproducible for an evaluator - SQLite is a single file with zero
setup. A production call center handling many simultaneous calls would
likely move to Postgres for concurrent writes, but that would be
over-engineering for this project's actual requirements.

**Q: How would you scale this to real phone calls?**
A: Replace the audio-file input with a telephony webhook (e.g. Twilio Voice)
that streams call audio in; everything downstream - `speech_to_text.py`,
`agent.py`, `database.py` - stays the same, since they only depend on
getting an audio file or transcript, not on how the audio arrived.

**Q: What happens if the Groq API is down or the key is invalid?**
A: `_call_llm()` catches connection errors, authentication errors, and
general API errors separately and raises a single `AgentError` with a
clear message; `app.py` catches that and prints a clean error instead of a
raw traceback, so the whole application doesn't crash.

**Q: Why is `callback_number` sanity-checked by digit count instead of a
real phone number library?**
A: To keep the project at an appropriate scope for this assessment - a
digit-count check catches the obvious failure mode (the LLM returning
non-numeric text) without adding a new dependency. A production version
would use a proper library like `phonenumbers` for full validation and
formatting, and that's called out explicitly as a future improvement.

**Q: How did you test this without needing a live LLM call or a downloaded
Whisper model in restricted environments?**
A: The test suite mocks `agent._call_llm()` to return the LLM's exact JSON
output, which lets all the downstream logic - parsing, sanitization,
database writes, retrieval - be verified for real. Speech-to-text is
tested for its error-handling paths (missing file, bad format, empty
audio), which don't require the model itself. The CLI's `--text` flag also
lets a real end-to-end run be demonstrated without needing an audio file.
