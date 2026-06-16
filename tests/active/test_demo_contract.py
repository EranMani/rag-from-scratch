from langchain_core.messages import AIMessage
from pathlib import PurePath

from rag_from_scratch import demo


class FakeJsonProfileModel:
    def invoke(self, messages):
        return AIMessage(
            content=(
                '{"updates": {'
                '"prior_knowledge": "understands LangGraph state machines", '
                '"current_interest": "LangChain chains", '
                '"communication_style": "prefers game-like explanations"'
                "}}"
            )
        )


def test_placeholder_openai_keys_are_not_treated_as_real_keys():
    assert not demo._has_real_openai_key("")
    assert not demo._has_real_openai_key("your_openai_api_key_here")
    assert not demo._has_real_openai_key("sk-...")
    assert demo._has_real_openai_key("sk-real-looking-key")


def test_sample_documents_are_bundled_and_have_metadata():
    docs = demo._load_sample_documents()

    assert len(docs) >= 3
    assert all(doc.page_content.strip() for doc in docs)
    assert all(PurePath(doc.metadata.get("source", "")).parts[:2] == ("data", "sample_docs") for doc in docs)
    assert {"LangGraph State Machines for RAG", "Session Knowledge Profile"} <= {
        doc.metadata["title"] for doc in docs
    }


def test_profile_update_json_fallback_extracts_changed_profile_fields():
    updates = demo._extract_profile_updates_with_json_prompt(
        FakeJsonProfileModel(),
        user_message="Switch to LangChain and explain it like a game.",
        answer="LangChain chains are like levels.",
        existing_profile={"communication_style": "prefers concise explanations"},
    )

    assert updates == {
        "prior_knowledge": "understands LangGraph state machines",
        "current_interest": "LangChain chains",
        "communication_style": "prefers game-like explanations",
    }


def test_preview_truncates_without_cutting_mid_word():
    preview = demo._preview("word " * 80)

    assert preview.endswith("...")
    assert len(preview) <= 220
    assert not preview.endswith(" ...")
