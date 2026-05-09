# Commit 13 Spec — `langgraph-assessment-llm`
> **Project:** rag-from-scratch · **Assignee:** Nova · **Load only for the active commit.**

---

### Commit 13 — `langgraph-assessment-llm`

**Commit message:** `feat: assessment_node LLM integration with structured output parsing`

**Body:**
Replaces the stub in `assess_node` with a real LLM call that extracts topic
understanding from the user's question and the generated answer.

Uses `.with_structured_output(AssessmentOutput)` (LangChain's structured output
interface) — NOT `StrOutputParser`. This ensures the LLM returns a validated
`AssessmentOutput` object. If parsing fails, the node catches the exception,
sets `assessment_error: True`, and the graph takes the fallback edge cleanly.

Assessment prompt evaluates:
- Which knowledge base modules are referenced in this interaction
- What the user's apparent understanding level is for each module
- What gaps are visible from the question asked

The assessment is a second LLM call per user turn. It runs on the same provider
as `generate_node` (OpenAI primary, Ollama fallback via circuit breaker).

**Assignee:** Nova (`nova.nodegraph@gmail.com`)

**Files touched:**
- `src/agents/nodes/assess.py` (replace stub with real implementation)

**Depends on:** 12

**Testing — done when:**
- [ ] `assess_node` with a question about "vector databases" returns `topic_scores_delta` with `vector_databases` key set
- [ ] LLM parse failure sets `assessment_error: True` and does not raise
- [ ] `user_level` in returned state is one of the valid mastery level strings
- [ ] Assessment call uses `get_provider()` — inherits circuit breaker fallback
