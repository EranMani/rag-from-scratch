from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum


class Role(StrEnum):
    USER = "human"
    AI = "assistant"


@dataclass
class Message:
    role: Role
    content: str


class SessionMemory:
    """
    In memory conversation buffer per session
    Stores full message history - grows unbounded
    """

    def __init__(self) -> None:
        self._sessions: dict[str, list[Message]] = defaultdict(list)

    def add_human(self, session_id: str, content: str):
        self._sessions[session_id].append(Message(role=Role.USER, content=content))

    def add_assistant(self, session_id: str, content: str):
        self._sessions[session_id].append(Message(role=Role.AI, content=content))

    def get_history(self, session_id: str) -> list[Message]:
        return self._sessions[session_id]

    def format_history(self, session_id: str) -> str:
        """Format as a string to inject into prompts"""
        messages = self._sessions[session_id]
        # Show the 10 latest messages for token cost and context optimization
        return "\n".join(f"{m.role.upper()}: {m.content}" for m in messages[-10:])

    def clear(self, session_id: str):
        self._sessions[session_id] = []

    
session_memory = SessionMemory()
