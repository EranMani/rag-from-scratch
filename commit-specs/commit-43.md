# Commit 43 Spec — `phase-unlock-agent`
> **Project:** rag-from-scratch · **Assignee:** ai-engineer (Nova) · **Load only for the active commit.**
> **Note:** Added in replan 2026-05-20 — phase unlock event is currently silent; learners receive no signal when they pass a gate.

---

### Commit 43 — `phase-unlock-agent`

**Commit message:** `feat: phase gate passage detection and in-chat unlock announcement`

**Body:**
The phase gate crossing is the motivational core of the curriculum. Currently it
is invisible — Phase 2 unlocks silently, the user has no idea. This commit makes
the agent aware of gate passage and announces it in-chat.

**Change 1 — AgentState: gate_just_passed field**
`src/agents/state.py`: add `gate_just_passed: str | None` field. Value is the phase
name that was just crossed ("phase_1", "phase_2", "phase_3") or `None`.

**Change 2 — update_profile_node: gate passage detection**
`src/agents/nodes/update_profile.py`: after calling `compute_topic_scores` and
`get_mastery_level`, compare the new mastery_level to the previous mastery_level
from the profile. If the level crossed a gate boundary (e.g., "beginner" → "intermediate",
"intermediate" → "advanced", "advanced" → "expert"), set `gate_just_passed` in the
returned state dict.

Gate crossing detection rules:
- "beginner" → "intermediate" or higher = phase_1 passed
- "intermediate" → "advanced" or higher = phase_2 passed
- "advanced" → "expert" = phase_3 passed

**Change 3 — generate_node: unlock announcement**
`src/agents/nodes/generate.py`: if `state.get("gate_just_passed")` is set, prepend
a structured unlock announcement to the agent's response before the normal answer.

Announcement content should:
- Celebrate the achievement explicitly ("You've passed Phase 1 — Foundations")
- Name the phase just completed and what it covered
- Introduce the phase now unlocked and its topics
- Be warm but not patronizing — this user just demonstrated real knowledge
- Be emitted ONCE (generate_node clears gate_just_passed after reading it by
  returning `{"gate_just_passed": None}` in its output)

Example Phase 1 → Phase 2 announcement:
  "You've completed Phase 1 — Foundations. Your scores on embeddings and RAG pipeline
  architecture are above the threshold. Phase 2 — Core Components — is now unlocked.
  You'll now encounter questions on chunking strategies, vector databases, retrieval
  methods, context and prompting, and LangChain fundamentals."

**Change 4 — generate_node: proximity feedback**
If `gate_just_passed` is None but any topic has a score between 0.60 and 0.69 (within
10 points of the 0.70 gate threshold), add a proximity signal to the adaptive context:
"[topic] is close to passing (score: X.XX). Reinforce where natural."
This is a system-context hint, not a user-visible message.

**Assignee:** Nova

**Files touched:**
- `src/agents/state.py` — add `gate_just_passed: str | None` field
- `src/agents/nodes/update_profile.py` — gate passage detection and state emission
- `src/agents/nodes/generate.py` — unlock announcement rendering + proximity hints

**Depends on:** 41 (gate logic must be correct before detecting gate passage)

**Testing — done when:**
- [ ] Profile transition from "beginner" → "intermediate" sets `gate_just_passed="phase_1"`
- [ ] Unlock announcement is present in the generated response on gate crossing
- [ ] `gate_just_passed` is cleared after generate_node reads it (no repeat announcements)
- [ ] User already at a level does not trigger spurious announcements on subsequent turns
- [ ] Proximity hint appears in system context when topic score is 0.60–0.69
- [ ] No announcement fires for passive-only score changes that don't cross a gate
