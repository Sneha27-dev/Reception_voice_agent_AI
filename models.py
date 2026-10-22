"""
models.py
---------
Simple data model for a processed call.

We use a plain dataclass instead of an ORM because the project only has
one table and one shape of record. An ORM would add a dependency and a
layer of abstraction that this project does not need (see README ->
"Why simple Python tools/functions are sufficient").
"""

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class CallRecord:
    """Structured representation of a single processed call.

    id and created_at are filled in by the database (SQLite) when the
    record is saved, so they default to None / empty until then.
    """

    caller_name: str
    intent: str
    callback_number: str
    transcript: str
    id: Optional[int] = None
    created_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def unknown_defaults() -> dict:
        """The exact fallback values the assignment requires when a field
        cannot be confidently extracted. Centralised here so agent.py and
        database.py always agree on the same strings."""
        return {
            "caller_name": "Unknown",
            "intent": "General Inquiry",
            "callback_number": "Not provided",
        }


# The fixed set of intents the agent is encouraged to classify calls into.
# The LLM is told about this list but is allowed to fall back to
# "General Inquiry" if nothing fits - it is guidance, not a hard constraint,
# because callers phrase things in many different ways.
KNOWN_INTENTS = [
    "Interview Inquiry",
    "Job Inquiry",
    "Appointment",
    "Complaint",
    "Service Inquiry",
    "Information Request",
    "General Inquiry",
]
