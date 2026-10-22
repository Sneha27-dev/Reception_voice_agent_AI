import json
import os
import re

from models import CallRecord, KNOWN_INTENTS

SYSTEM_PROMPT = f"""You are the Reception Agent for a small office.

Extract these three fields from the phone call transcript:

1. caller_name
2. intent
3. callback_number

Use these intent categories when appropriate:
{", ".join(KNOWN_INTENTS)}

Rules:
- Never invent information.
- If name is missing, use "Unknown".
- If phone number is missing, use "Not provided".
- If intent is unclear, use "General Inquiry".
- Return ONLY valid JSON.

JSON format:
{{"caller_name": "<name>", "intent": "<intent>", "callback_number": "<number>"}}
"""


class AgentError(Exception):
    pass


def _call_llm(transcript: str) -> str:
    try:
        from groq import Groq
    except ImportError as exc:
        raise AgentError(
            "Groq package is not installed. Run: pip install groq"
        ) from exc

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise AgentError(
            "GROQ_API_KEY is not set. Check your .env file."
        )

    model = os.getenv(
        "GROQ_MODEL",
        "llama-3.3-70b-versatile"
    )

    try:
        client = Groq(api_key=api_key)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": f"Transcript:\n{transcript}"
                }
            ],
            temperature=0,
            max_tokens=300
        )

    except Exception as exc:
        raise AgentError(
            f"Groq API error: {exc}"
        ) from exc

    if not response.choices:
        raise AgentError("Groq returned an empty response.")

    return response.choices[0].message.content.strip()


def _parse_llm_json(raw_text: str) -> dict:
    cleaned = raw_text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(
            r"^```(?:json)?",
            "",
            cleaned
        ).strip()

        cleaned = re.sub(
            r"```$",
            "",
            cleaned
        ).strip()

    try:
        return json.loads(cleaned)

    except json.JSONDecodeError as exc:
        raise AgentError(
            f"LLM response was not valid JSON: {raw_text}"
        ) from exc


_PHONE_DIGITS_RE = re.compile(r"\d")


def _sanitize_fields(data: dict) -> dict:

    defaults = CallRecord.unknown_defaults()

    caller_name = (
        str(data.get("caller_name") or "").strip()
        or defaults["caller_name"]
    )

    intent = (
        str(data.get("intent") or "").strip()
        or defaults["intent"]
    )

    callback_number = (
        str(data.get("callback_number") or "").strip()
        or defaults["callback_number"]
    )

    if callback_number != defaults["callback_number"]:

        digit_count = len(
            _PHONE_DIGITS_RE.findall(callback_number)
        )

        if digit_count < 7:
            callback_number = defaults["callback_number"]

    return {
        "caller_name": caller_name,
        "intent": intent,
        "callback_number": callback_number,
    }


def extract_call_info(transcript: str) -> CallRecord:

    if not transcript or not transcript.strip():
        raise AgentError(
            "Cannot process an empty transcript."
        )

    raw_response = _call_llm(transcript)

    parsed = _parse_llm_json(raw_response)

    clean = _sanitize_fields(parsed)

    return CallRecord(
        caller_name=clean["caller_name"],
        intent=clean["intent"],
        callback_number=clean["callback_number"],
        transcript=transcript.strip(),
    )