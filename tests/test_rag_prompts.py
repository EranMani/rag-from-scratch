"""
Tests for Commit 17 — adaptive-prompt-templates.

Three spec gates:

Gate 1: All 5 mastery level keys present in PROMPT_TEMPLATES.
Gate 2: DEFAULT_PROMPT matches existing generate_node RAG_PROMPT behavior
        (same constraint text, {context} variable, produces a SystemMessage).
Gate 3: `from agents.prompts import PROMPT_TEMPLATES, DEFAULT_PROMPT` works
        without error.

Design notes:
- No LLM calls. All assertions are structural / content-based.
- ChatPromptTemplate.format_messages(context=...) is used to verify that the
  {context} variable resolves correctly for every template.
- Gate 2 checks behavioral equivalence with the inline SystemMessage in
  generate_node: "Answer using ONLY the provided context" constraint must be
  present verbatim in the DEFAULT_PROMPT system message.
"""

from __future__ import annotations

import pytest
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

# ---------------------------------------------------------------------------
# Gate 3 — import smoke test (must pass before any other gate can run)
# ---------------------------------------------------------------------------

from agents.prompts import PROMPT_TEMPLATES, DEFAULT_PROMPT  # noqa: E402


# ---------------------------------------------------------------------------
# Gate 1 — all 5 mastery level keys present
# ---------------------------------------------------------------------------

EXPECTED_LEVELS = {"novice", "beginner", "intermediate", "advanced", "expert"}


class TestGate1AllLevelKeysPresent:
    def test_prompt_templates_is_dict(self) -> None:
        assert isinstance(PROMPT_TEMPLATES, dict)

    def test_all_five_keys_present(self) -> None:
        assert set(PROMPT_TEMPLATES.keys()) == EXPECTED_LEVELS

    def test_novice_key_present(self) -> None:
        assert "novice" in PROMPT_TEMPLATES

    def test_beginner_key_present(self) -> None:
        assert "beginner" in PROMPT_TEMPLATES

    def test_intermediate_key_present(self) -> None:
        assert "intermediate" in PROMPT_TEMPLATES

    def test_advanced_key_present(self) -> None:
        assert "advanced" in PROMPT_TEMPLATES

    def test_expert_key_present(self) -> None:
        assert "expert" in PROMPT_TEMPLATES

    def test_each_value_is_chat_prompt_template(self) -> None:
        for level, template in PROMPT_TEMPLATES.items():
            assert isinstance(template, ChatPromptTemplate), (
                f"PROMPT_TEMPLATES['{level}'] is {type(template)}, expected ChatPromptTemplate"
            )

    def test_no_extra_keys(self) -> None:
        assert set(PROMPT_TEMPLATES.keys()) - EXPECTED_LEVELS == set()

    def test_each_template_accepts_context_variable(self) -> None:
        """Every template must format without error when given a context string."""
        for level, template in PROMPT_TEMPLATES.items():
            messages = template.format_messages(context="test context")
            assert len(messages) >= 1, f"PROMPT_TEMPLATES['{level}'].format_messages returned empty list"

    def test_each_template_produces_system_message(self) -> None:
        for level, template in PROMPT_TEMPLATES.items():
            messages = template.format_messages(context="ctx")
            assert isinstance(messages[0], SystemMessage), (
                f"PROMPT_TEMPLATES['{level}'] first message is {type(messages[0])}, expected SystemMessage"
            )

    def test_each_template_embeds_context_in_output(self) -> None:
        sentinel = "UNIQUE_CONTEXT_SENTINEL_XYZ"
        for level, template in PROMPT_TEMPLATES.items():
            messages = template.format_messages(context=sentinel)
            assert sentinel in messages[0].content, (
                f"PROMPT_TEMPLATES['{level}'] did not embed context in system message"
            )

    def test_each_template_has_rag_constraint(self) -> None:
        """All templates must include the core factual constraint."""
        for level, template in PROMPT_TEMPLATES.items():
            messages = template.format_messages(context="ctx")
            assert "ONLY the provided context" in messages[0].content, (
                f"PROMPT_TEMPLATES['{level}'] missing 'ONLY the provided context' constraint"
            )


# ---------------------------------------------------------------------------
# Gate 2 — DEFAULT_PROMPT matches existing generate_node RAG_PROMPT behavior
# ---------------------------------------------------------------------------

class TestGate2DefaultPromptBehavior:
    def test_default_prompt_is_chat_prompt_template(self) -> None:
        assert isinstance(DEFAULT_PROMPT, ChatPromptTemplate)

    def test_default_prompt_accepts_context_variable(self) -> None:
        messages = DEFAULT_PROMPT.format_messages(context="some context")
        assert len(messages) >= 1

    def test_default_prompt_first_message_is_system_message(self) -> None:
        messages = DEFAULT_PROMPT.format_messages(context="ctx")
        assert isinstance(messages[0], SystemMessage)

    def test_default_prompt_embeds_context(self) -> None:
        sentinel = "SENTINEL_DEFAULT_CONTEXT"
        messages = DEFAULT_PROMPT.format_messages(context=sentinel)
        assert sentinel in messages[0].content

    def test_default_prompt_contains_rag_constraint(self) -> None:
        """Must match the core constraint from the inline generate_node SystemMessage."""
        messages = DEFAULT_PROMPT.format_messages(context="ctx")
        assert "ONLY the provided context" in messages[0].content

    def test_default_prompt_references_rag_domain(self) -> None:
        """The system message must reference RAG systems as the expert domain."""
        messages = DEFAULT_PROMPT.format_messages(context="ctx")
        assert "RAG" in messages[0].content

    def test_default_prompt_is_not_in_prompt_templates(self) -> None:
        """DEFAULT_PROMPT is a separate object — not aliased to any level in the dict."""
        for level, template in PROMPT_TEMPLATES.items():
            assert template is not DEFAULT_PROMPT, (
                f"PROMPT_TEMPLATES['{level}'] is the same object as DEFAULT_PROMPT"
            )

    def test_get_with_unknown_level_returns_default(self) -> None:
        """Commit 18 usage pattern: unknown level falls back to DEFAULT_PROMPT."""
        result = PROMPT_TEMPLATES.get("unknown_level", DEFAULT_PROMPT)
        assert result is DEFAULT_PROMPT

    def test_get_with_none_returns_default(self) -> None:
        result = PROMPT_TEMPLATES.get(None, DEFAULT_PROMPT)  # type: ignore[call-overload]
        assert result is DEFAULT_PROMPT


# ---------------------------------------------------------------------------
# Gate 3 — package-level import (validated by the import at the top of this file)
# ---------------------------------------------------------------------------

class TestGate3ImportWorks:
    def test_prompt_templates_imported(self) -> None:
        """PROMPT_TEMPLATES is importable from agents.prompts (top-level package)."""
        assert PROMPT_TEMPLATES is not None

    def test_default_prompt_imported(self) -> None:
        """DEFAULT_PROMPT is importable from agents.prompts (top-level package)."""
        assert DEFAULT_PROMPT is not None

    def test_module_import_from_submodule(self) -> None:
        """Direct submodule import path also works."""
        from agents.prompts.rag import PROMPT_TEMPLATES as PT, DEFAULT_PROMPT as DP
        assert PT is PROMPT_TEMPLATES
        assert DP is DEFAULT_PROMPT
