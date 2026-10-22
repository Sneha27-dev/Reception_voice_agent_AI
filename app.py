"""
app.py
------
Command-line entry point for the Reception Voice Agent.

Usage examples:

    python app.py process --audio audio/call_01.wav
    python app.py process --text "Hi, my name is Rahul, call me on 9876543210"
    python app.py list
    python app.py search --name Rahul
    python app.py search --intent "Job Inquiry"

A CLI is sufficient for this project (see README) - the goal is a
working agent, not a frontend.
"""

import argparse
import sys

from dotenv import load_dotenv

import database
from agent import AgentError, extract_call_info
from database import DatabaseError
from speech_to_text import TranscriptionError, transcribe_audio

load_dotenv()


def process_call(audio_path: str | None, text: str | None) -> int:
    """Runs one call through the full pipeline: audio -> transcript ->
    LLM extraction -> save to database. Returns an exit code."""
    try:
        if audio_path:
            print(f"Transcribing audio: {audio_path}")
            transcript = transcribe_audio(audio_path)
        else:
            transcript = text.strip() if text else ""
            if not transcript:
                print("Error: --text was empty.", file=sys.stderr)
                return 1

        print(f"Transcript: {transcript}\n")

        print("Extracting structured information with the LLM...")
        record = extract_call_info(transcript)

        print("Saving call to database...")
        saved = database.save_call(record)

        print("\nCall processed successfully:")
        _print_record(saved)
        return 0

    except TranscriptionError as exc:
        print(f"Speech-to-text error: {exc}", file=sys.stderr)
        return 1
    except AgentError as exc:
        print(f"LLM agent error: {exc}", file=sys.stderr)
        return 1
    except DatabaseError as exc:
        print(f"Database error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - last-resort guard so the CLI never crashes with a raw traceback
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1


def list_all_calls() -> int:
    try:
        calls = database.list_calls()
    except DatabaseError as exc:
        print(f"Database error: {exc}", file=sys.stderr)
        return 1

    if not calls:
        print("No calls stored yet.")
        return 0

    print(f"{len(calls)} call(s) found:\n")
    for record in calls:
        _print_record(record)
        print("-" * 60)
    return 0


def search(args: argparse.Namespace) -> int:
    try:
        results = database.search_calls(
            caller_name=args.name,
            intent=args.intent,
            callback_number=args.number,
            date=args.date,
        )
    except DatabaseError as exc:
        print(f"Database error: {exc}", file=sys.stderr)
        return 1

    if not results:
        print("No matching calls found.")
        return 0

    print(f"{len(results)} matching call(s):\n")
    for record in results:
        _print_record(record)
        print("-" * 60)
    return 0


def _print_record(record) -> None:
    print(f"ID:              {record.id}")
    print(f"Caller Name:     {record.caller_name}")
    print(f"Intent:          {record.intent}")
    print(f"Callback Number: {record.callback_number}")
    print(f"Transcript:      {record.transcript}")
    print(f"Created At:      {record.created_at}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reception Voice Agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    process_parser = subparsers.add_parser("process", help="Process one call")
    group = process_parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--audio", help="Path to an audio file (wav/mp3/m4a/flac/ogg/webm)")
    group.add_argument("--text", help="Raw transcript text (skips speech-to-text; useful for testing)")

    subparsers.add_parser("list", help="List all stored calls")

    search_parser = subparsers.add_parser("search", help="Search stored calls")
    search_parser.add_argument("--name", help="Filter by caller name (partial match)")
    search_parser.add_argument("--intent", help="Filter by intent (partial match)")
    search_parser.add_argument("--number", help="Filter by callback number (partial match)")
    search_parser.add_argument("--date", help="Filter by date, format YYYY-MM-DD")

    return parser


def main() -> int:
    database.init_db()

    parser = build_parser()
    args = parser.parse_args()

    if args.command == "process":
        return process_call(audio_path=args.audio, text=args.text)
    if args.command == "list":
        return list_all_calls()
    if args.command == "search":
        return search(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
