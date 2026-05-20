# Commit 44 Spec — `phase-unlock-ui`
> **Project:** rag-from-scratch · **Assignee:** frontend (Aria) · **Load only for the active commit.**
> **Note:** Added in replan 2026-05-20 — Knowledge Profile sidebar must show the full curriculum shape (locked/unlocked phases) so novice users understand there is more ahead.

---

### Commit 44 — `phase-unlock-ui`

**Commit message:** `feat: locked/unlocked phase display and unlock celebration in Knowledge Profile sidebar`

**Body:**
Two UI changes to the Knowledge Profile sidebar that turn the gated curriculum from
an invisible system into a visible learning path.

**Change 1 — Overview tab: show all phases with locked/unlocked state**
The Knowledge Profile sidebar's Overview tab currently shows only the topics the user
can see based on their level. Change it to always show all three phases:

Phase 1 — Foundations (always visible, with progress)
Phase 2 — Core Components (locked with padlock if Phase 1 not passed; unlocked with progress when accessible)
Phase 3 — Production (locked with padlock if Phase 2 not passed; unlocked with progress when accessible)

Locked state visual treatment:
- Dimmed/grayed progress bar (use CSS opacity: 0.4 or a "locked" CSS class)
- Padlock icon beside the phase name
- Tooltip or subtitle: "Pass Phase 1 to unlock" / "Pass Phase 2 to unlock"
- Topics within a locked phase shown as greyed-out names without scores

Unlocked state:
- Full color progress bar showing mean score across phase topics
- Each topic shows its individual score or "Not yet started"

**Change 2 — Current tab: phase progression context**
The Current tab shows the active module + topic checklist. Add a small progress
indicator below the active topic list showing:
"Phase X of 3 — [N] topics complete, [M] to go before Phase X+1 unlocks"
This gives the user a map, not just a current position.

**Change 3 — Unlock celebration moment**
When the UI receives a profile update where mastery_level has just advanced
(e.g., "beginner" → "intermediate"), trigger a brief visual celebration:
- The newly unlocked phase in the Overview tab animates from locked to unlocked
  (CSS transition: opacity fade-in + padlock icon swap)
- A brief highlight on the newly accessible phase topics (green glow, 2–3 seconds)
- No modal or blocking overlay — the celebration is in-place, non-intrusive

Implementation note: the profile panel receives updated profile data from the API.
Compare the incoming mastery_level to the previously displayed level to detect
a gate crossing. Store the previous level in a ui_state variable.

**Scope hard limits (same as all UI commits):**
- Changes confined to `profile_panel()` and any helper functions it calls in `ui.py`
- No streaming logic, no auth handlers, no state changes outside the UI layer
- No new API calls — use the profile data already loaded by the existing panel

**Files touched:**
- `src/app/ui.py` — `profile_panel()` and UI helper functions only

**Depends on:** 43 (gate_just_passed signal in state; agent announcement sets context for the UI moment)
**Parallel with:** 45 (no shared files — RAG Specialist works in knowledge-base/)

**Testing — done when:**
- [ ] Novice user sees Phase 2 and Phase 3 as locked with padlock icons in Overview tab
- [ ] Intermediate user sees Phase 1 completed, Phase 2 unlocked, Phase 3 locked
- [ ] Expert user sees all three phases unlocked with full progress bars
- [ ] Unlock animation triggers when mastery_level advances in the profile data
- [ ] Locked topics within a locked phase are visible but grayed (not hidden)
- [ ] No layout regression on the Current tab topic checklist
