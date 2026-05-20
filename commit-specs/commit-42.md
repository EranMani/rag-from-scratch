# Commit 42 Spec — `rag-specialist-persona`
> **Project:** rag-from-scratch · **Assignee:** claude · **Load only for the active commit.**
> **Note:** Added in replan 2026-05-20 — new RAG Specialist agent persona to produce practitioner-depth curriculum content.

---

### Commit 42 — `rag-specialist-persona`

**Commit message:** `feat: add RAG Specialist agent persona and interface contract with Lara`

**Body:**
Creates the RAG Specialist agent — a build-time practitioner persona whose job is to
deepen the knowledge-base content that the existing graph nodes consume. This agent
is NOT a runtime graph node. It authors files. The graph is unchanged.

**Why this agent is needed:**
Lara (curriculum specialist) owns curriculum structure — topic definitions, phase gates,
learning objectives, and question format. Her ceiling is pedagogically sound but
surface-level content. She can write "explain what cosine similarity is" but not
"your production RAG system shows faithfulness=0.6 and context precision=0.9 — diagnose
the three most likely failure modes." The second question requires someone who has
debugged this failure mode in a live system.

The RAG Specialist fills that gap. Its primary output is additional MCQ questions and
open-ended questions written from operational experience, plus practitioner-depth
"why wrong" explanations in each MCQ answer field. Secondary output: knowledge-base
documents with "this is what actually breaks in production" depth.

**Agent domain:**
- Owns: `knowledge-base/curriculum/questions/` (question depth within Lara's structure)
- Never touches: `src/`, any Lara-owned structure files (curriculum-map.md, gates.md,
  topic-slugs.json — those remain Lara's)
- Interface contract: the slug file format (established by Lara) is the contract.
  The Specialist writes to that format; Lara owns the format definition.

**Agent identity file contents (`.claude/agents/rag-specialist.md`):**
The file must define:
- Role: practitioner-depth RAG content author
- Domain: `knowledge-base/curriculum/questions/` only
- Expertise framing: operational RAG systems, production failure modes, LangChain
  pipeline debugging, embedding model version management, retrieval quality at scale
- Content standards: every question must reflect a real failure mode or a
  distinction that only matters in production; no exam-prep recall questions
- Collaboration with Lara: Lara provides topic structure; Specialist fills depth
- Collaboration with Nova: Nova flags which topics score poorly in user sessions
  (session_history in user profiles) — that data informs where to add harder questions

**Files touched:**
- `.claude/agents/rag-specialist.md` (new)
- `AGENTS.md` (add RAG Specialist entry)

**Depends on:** 40 (LangChain topic must exist — Specialist needs to fill it)

**Testing — done when:**
- [ ] `.claude/agents/rag-specialist.md` exists and follows the established agent identity format
- [ ] `AGENTS.md` contains a RAG Specialist entry with domain and interface described
- [ ] Agent file clearly states it never touches src/ or Lara's structure files
