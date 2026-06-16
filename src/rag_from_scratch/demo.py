"""Real Chroma + OpenAI demo for the canonical adaptive RAG flow.

Run from a fresh checkout with:
    python demo.py

Or, after installing the package / setting PYTHONPATH=src:
    python -m rag_from_scratch.demo

Required:
    OPENAI_API_KEY in .env or the shell environment.
"""

from __future__ import annotations

from pathlib import Path
import os
import shutil
import textwrap
from typing import Any

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DOCS_DIR = PROJECT_ROOT / "data" / "sample_docs"
DEMO_CHROMA_DIR = PROJECT_ROOT / "data" / "demo_chroma_db"
COLLECTION_NAME = "rag_from_scratch_demo"


class ProfileUpdate(BaseModel):
    """Structured profile signals extracted from a single user turn."""

    updates: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Stable learner-profile facts inferred from the user message. "
            "Use snake_case keys and short human-readable values."
        ),
    )


def run_demo() -> None:
    """Run the full two-turn demo with real embeddings, Chroma, and OpenAI."""

    load_dotenv(PROJECT_ROOT / ".env")
    _require_openai_key()

    model_name = os.getenv("MODEL_NAME") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
    embedding_model = (
        os.getenv("EMBEDDING_MODEL")
        or os.getenv("OPENAI_EMBEDDING_MODEL")
        or "text-embedding-3-small"
    )

    print("RAG From Scratch - Real Chroma/OpenAI Demo")
    print("=" * 44)
    print(f"Generation model: {model_name}")
    print(f"Embedding model:  {embedding_model}")
    print("Flow: Chroma retrieval -> OpenAI generation -> profile update -> profile reuse")

    vectorstore = _build_demo_vectorstore(embedding_model)
    llm = ChatOpenAI(model=model_name, temperature=0.2)
    profile_llm = ChatOpenAI(model=model_name, temperature=0).with_structured_output(
        ProfileUpdate,
        method="function_calling",
    )

    profile: dict[str, str] = {}
    history: list[dict[str, str]] = []
    user_messages = [
        "I understand basic RAG, but I am confused about why LangGraph is useful. Can you explain it briefly?",
        "How would that profile update change the next answer?",
        "Now let's switch to LangChain. I know LangGraph state machines now, and I want the explanation to feel more like a game with levels and mechanics.",
    ]

    for turn_number, user_message in enumerate(user_messages, start=1):
        retrieved_docs = vectorstore.similarity_search(user_message, k=2)
        answer = _generate_answer(
            llm=llm,
            user_message=user_message,
            retrieved_docs=retrieved_docs,
            profile=profile,
            history=history,
        )
        profile_before = dict(profile)
        profile_updates = _extract_profile_updates(profile_llm, user_message, answer, profile)
        profile.update(profile_updates)
        history.append({"user": user_message, "assistant": answer})
        _print_turn(
            turn_number,
            user_message,
            retrieved_docs,
            answer,
            profile_before,
            profile,
            profile_updates,
        )


def _build_demo_vectorstore(embedding_model: str) -> Chroma:
    """Create a fresh local Chroma collection from bundled sample docs."""

    if DEMO_CHROMA_DIR.exists():
        shutil.rmtree(DEMO_CHROMA_DIR)

    raw_docs = _load_sample_documents()
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=80,
        separators=["\n\n", "\n", ". ", " ", ""],
    ).split_documents(raw_docs)

    embeddings = OpenAIEmbeddings(model=embedding_model)
    return Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(DEMO_CHROMA_DIR),
    )


def _load_sample_documents() -> list[Document]:
    docs: list[Document] = []
    for path in sorted(SAMPLE_DOCS_DIR.glob("*.md")):
        content = path.read_text(encoding="utf-8").strip()
        if content:
            docs.append(
                Document(
                    page_content=content,
                    metadata={"source": str(path.relative_to(PROJECT_ROOT)), "title": _title_for(content, path)},
                )
            )
    if not docs:
        raise RuntimeError(f"No sample markdown files found in {SAMPLE_DOCS_DIR}")
    return docs


def _generate_answer(
    *,
    llm: ChatOpenAI,
    user_message: str,
    retrieved_docs: list[Document],
    profile: dict[str, str],
    history: list[dict[str, str]],
) -> str:
    context = "\n\n".join(
        f"Source: {doc.metadata.get('source', 'unknown')}\n{doc.page_content}"
        for doc in retrieved_docs
    )
    profile_text = _format_profile(profile)
    history_text = _format_history(history)

    messages = [
        SystemMessage(
            content=(
                "You are the assistant in a portfolio RAG demo. Answer using the retrieved "
                "context first. Be explicit when you are using the learner profile. Keep the "
                "answer concise, technical, and interview-readable.\n\n"
                f"Retrieved context:\n{context}\n\n"
                f"Current learner profile:\n{profile_text}\n\n"
                f"Session history:\n{history_text}"
            )
        ),
        HumanMessage(content=user_message),
    ]
    response = llm.invoke(messages)
    return str(response.content)


def _extract_profile_updates(
    profile_llm: Any,
    user_message: str,
    answer: str,
    existing_profile: dict[str, str],
) -> dict[str, str]:
    result = profile_llm.invoke(
        [
            SystemMessage(
                content=(
                    "Extract only durable learner-profile updates from this turn. "
                    "Capture communication preference, prior knowledge, and current technical interest "
                    "when the user states or strongly implies them. For example, 'explain it briefly' "
                    "means communication_style='prefers concise explanations'; 'I understand basic RAG' "
                    "means prior_knowledge='understands basic RAG'; asking about LangGraph means "
                    "current_interest='LangGraph state machines'. 'I know LangGraph state machines now' "
                    "means prior_knowledge='understands LangGraph state machines'; switching to LangChain "
                    "means current_interest='LangChain chains'; asking for an explanation like a game with "
                    "levels and mechanics means communication_style='prefers game-like explanations'. Return an empty object only when "
                    "there is no useful update. Do not repeat facts that already exist in the "
                    "current learner profile unless the new turn makes them more specific."
                )
            ),
            HumanMessage(
                content=(
                    f"Current learner profile:\n{_format_profile(existing_profile)}\n\n"
                    f"User message:\n{user_message}\n\n"
                    f"Assistant answer:\n{answer}\n\n"
                    "Profile update keys should be short snake_case names. Return only new or changed keys."
                )
            ),
        ]
    )
    if isinstance(result, ProfileUpdate):
        raw_updates = result.updates
    else:
        raw_updates = dict(result.get("updates", {}))
    return {
        key: value
        for key, value in raw_updates.items()
        if existing_profile.get(key) != value
    }


def _print_turn(
    turn_number: int,
    user_message: str,
    retrieved_docs: list[Document],
    answer: str,
    profile_before: dict[str, str],
    profile: dict[str, str],
    profile_updates: dict[str, str],
) -> None:
    print()
    print(f"Turn {turn_number}")
    print("-" * 44)
    print("User:")
    print(_wrap(user_message))
    print()
    print("Retrieved context from Chroma:")
    for doc in retrieved_docs:
        source = doc.metadata.get("source", "unknown")
        title = doc.metadata.get("title", "Untitled")
        print(f"- {title} ({source}): {_wrap(_preview(doc.page_content), width=100)}")
    print()
    print("Assistant generated by OpenAI:")
    print(_wrap(answer))
    print()
    print("Knowledge profile before update:")
    _print_profile(profile_before)
    print()
    print("Knowledge profile after update:")
    _print_profile(profile)
    print()
    print("Profile updates this turn:")
    if profile_updates:
        for key, value in profile_updates.items():
            print(f"- {key}: {value}")
    else:
        print("- none")


def _print_profile(profile: dict[str, str]) -> None:
    if profile:
        for key, value in profile.items():
            print(f"- {key}: {value}")
    else:
        print("- no profile signals yet")


def _require_openai_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(
            "OPENAI_API_KEY is required for the real demo. Add it to .env or export it "
            "in your shell, then run: python demo.py"
        )


def _title_for(content: str, path: Path) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return path.stem.replace("_", " ").title()


def _format_profile(profile: dict[str, str]) -> str:
    if not profile:
        return "No learner profile has been inferred yet."
    return "\n".join(f"- {key}: {value}" for key, value in profile.items())


def _format_history(history: list[dict[str, str]]) -> str:
    if not history:
        return "No prior turns."
    return "\n\n".join(
        f"User: {turn['user']}\nAssistant: {turn['assistant']}"
        for turn in history
    )


def _preview(content: str) -> str:
    compact = " ".join(line.strip("# ").strip() for line in content.splitlines() if line.strip())
    if len(compact) <= 220:
        return compact
    return compact[:217].rsplit(" ", 1)[0] + "..."


def _wrap(text: str, width: int = 88) -> str:
    return textwrap.fill(text, width=width, replace_whitespace=True, drop_whitespace=True)


if __name__ == "__main__":
    run_demo()
