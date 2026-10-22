"""
tests/test_pipeline.py
-----------------------
Automated tests for the parts of the pipeline that can be verified
without live network access to an LLM or Whisper model download
(useful for CI / sandboxed environments). The LLM call itself is
mocked with realistic responses matching the assignment's example
outputs; everything downstream (JSON parsing, validation/sanitization,
database save/list/search, and CLI error handling) is exercised for
real.

Run with:  python -m pytest tests/ -v
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import database  # noqa: E402
import agent  # noqa: E402
from agent import extract_call_info, AgentError  # noqa: E402
from database import DatabaseError  # noqa: E402
from models import CallRecord  # noqa: E402
from speech_to_text import transcribe_audio, TranscriptionError  # noqa: E402


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    """Points the database module at a throwaway SQLite file for each test."""
    test_db_path = tmp_path / "test_calls.db"
    monkeypatch.setattr(database, "DB_PATH", test_db_path)
    database.init_db()
    return test_db_path


# --------------------------------------------------------------------------
# Database layer
# --------------------------------------------------------------------------

def test_save_and_list_calls(temp_db):
    record = CallRecord(
        caller_name="Sneha",
        intent="Interview Inquiry",
        callback_number="9008725671",
        transcript="Hello, my name is Sneha...",
    )
    saved = database.save_call(record)
    assert saved.id is not None
    assert saved.created_at is not None

    all_calls = database.list_calls()
    assert len(all_calls) == 1
    assert all_calls[0].caller_name == "Sneha"


def test_repeat_caller_creates_separate_records(temp_db):
    """Requirement: do not overwrite previous calls from the same caller."""
    for i in range(2):
        database.save_call(
            CallRecord(
                caller_name="Rahul",
                intent="Job Inquiry",
                callback_number="9876543210",
                transcript=f"Call number {i}",
            )
        )
    all_calls = database.list_calls()
    assert len(all_calls) == 2
    assert all_calls[0].id != all_calls[1].id


def test_save_call_rejects_empty_transcript(temp_db):
    with pytest.raises(DatabaseError):
        database.save_call(
            CallRecord(caller_name="Unknown", intent="General Inquiry",
                       callback_number="Not provided", transcript="   ")
        )


def test_search_calls_by_intent(temp_db):
    database.save_call(CallRecord("Sneha", "Interview Inquiry", "9008725671", "t1"))
    database.save_call(CallRecord("Rahul", "Job Inquiry", "9876543210", "t2"))

    results = database.search_calls(intent="Job")
    assert len(results) == 1
    assert results[0].caller_name == "Rahul"


def test_search_calls_no_filters_returns_all(temp_db):
    database.save_call(CallRecord("A", "General Inquiry", "Not provided", "t1"))
    database.save_call(CallRecord("B", "General Inquiry", "Not provided", "t2"))
    assert len(database.search_calls()) == 2


# --------------------------------------------------------------------------
# Agent (LLM extraction) layer - LLM call itself is mocked
# --------------------------------------------------------------------------

def _mock_response(json_text: str):
    """Builds a fake object shaped like the Anthropic SDK's response,
    with a .content[0].text attribute."""
    class _Block:
        def __init__(self, text):
            self.text = text

    class _Response:
        def __init__(self, text):
            self.content = [_Block(text)]

    return _Response(json_text)


def test_extract_call_info_complete_call():
    """Assignment Test Case 1."""
    transcript = ("Hello, my name is Sneha. I am calling regarding the interview "
                  "schedule. Please call me back on 9008725671.")
    fake_json = '{"caller_name": "Sneha", "intent": "Interview Inquiry", "callback_number": "9008725671"}'

    with patch.object(agent, "_call_llm", return_value=fake_json):
        record = extract_call_info(transcript)

    assert record.caller_name == "Sneha"
    assert record.intent == "Interview Inquiry"
    assert record.callback_number == "9008725671"


def test_extract_call_info_different_ordering():
    """Assignment section 5: info in any order."""
    transcript = "I'm calling about the interview. My name is Rahul and you can reach me at 9876543210."
    fake_json = '{"caller_name": "Rahul", "intent": "Interview Inquiry", "callback_number": "9876543210"}'

    with patch.object(agent, "_call_llm", return_value=fake_json):
        record = extract_call_info(transcript)

    assert record.caller_name == "Rahul"
    assert record.callback_number == "9876543210"


def test_extract_call_info_missing_name_and_number():
    """Assignment Test Case 3."""
    transcript = "Hello, I want to know more about your service."
    fake_json = '{"caller_name": "Unknown", "intent": "Service Inquiry", "callback_number": "Not provided"}'

    with patch.object(agent, "_call_llm", return_value=fake_json):
        record = extract_call_info(transcript)

    assert record.caller_name == "Unknown"
    assert record.callback_number == "Not provided"
    assert record.intent == "Service Inquiry"


def test_extract_call_info_handles_markdown_fenced_json():
    """LLMs sometimes wrap JSON in ```json fences despite instructions not to."""
    transcript = "Hi this is a test call."
    fake_json = '```json\n{"caller_name": "Unknown", "intent": "General Inquiry", "callback_number": "Not provided"}\n```'

    with patch.object(agent, "_call_llm", return_value=fake_json):
        record = extract_call_info(transcript)

    assert record.intent == "General Inquiry"


def test_extract_call_info_sanitizes_bad_phone_number():
    """If the model hallucinates a non-numeric 'phone number', we must not
    trust it - it should fall back to 'Not provided'."""
    transcript = "Hi, call me sometime maybe."
    fake_json = '{"caller_name": "Unknown", "intent": "General Inquiry", "callback_number": "sometime"}'

    with patch.object(agent, "_call_llm", return_value=fake_json):
        record = extract_call_info(transcript)

    assert record.callback_number == "Not provided"


def test_extract_call_info_rejects_invalid_json():
    transcript = "Hi there."
    with patch.object(agent, "_call_llm", return_value="not json at all"):
        with pytest.raises(AgentError):
            extract_call_info(transcript)


def test_extract_call_info_empty_transcript_raises():
    with pytest.raises(AgentError):
        extract_call_info("")


def test_extract_call_info_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(AgentError):
        agent._call_llm("some transcript")


# --------------------------------------------------------------------------
# Speech-to-text error handling (does not require the whisper model itself)
# --------------------------------------------------------------------------

def test_transcribe_missing_file_raises():
    with pytest.raises(TranscriptionError):
        transcribe_audio("audio/does_not_exist.wav")


def test_transcribe_unsupported_format_raises(tmp_path):
    bad_file = tmp_path / "call.txt"
    bad_file.write_text("not audio")
    with pytest.raises(TranscriptionError):
        transcribe_audio(str(bad_file))


def test_transcribe_empty_file_raises(tmp_path):
    empty_file = tmp_path / "call.wav"
    empty_file.touch()
    with pytest.raises(TranscriptionError):
        transcribe_audio(str(empty_file))
