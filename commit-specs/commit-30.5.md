# Commit 30.5 — `ui-landing-raf-guard`

## Owner
Aria (frontend) — applied directly by Claude via Edit (exact file+line+content known; no agent invocation)

## Purpose
Resolve the Viktor BLOCKED finding deferred from Commit 30.
Add a DOM-guard check before `requestAnimationFrame(draw)` in the particle canvas animation to prevent the rAF loop from continuing after the canvas element has been removed from the DOM (e.g., on NiceGUI full-page reload/navigate).

## Scope
Single-line change in `src/app/ui.py`, `landing_page()` function, particle canvas `<script>` block.

## Change
**File:** `src/app/ui.py`

**Before:**
```javascript
    raf = requestAnimationFrame(draw);
  }
  draw();
```

**After:**
```javascript
    if (!document.contains(canvas)) { return; }
    raf = requestAnimationFrame(draw);
  }
  draw();
```

## Test Gate
- No automated test applicable — JS-only change in a NiceGUI `ui.html()` block; there are no JS unit tests in this project.
- Visual verification: particle canvas still animates normally on `/landing` page load.

## Quality Gates
- Viktor (required per protocol — resolves prior BLOCKED finding)
- Sage: not triggered — no user data, no auth, no external API
- Quinn: not triggered — no testable logic path
- Mira: not triggered — zero product-facing change

## Context
Viktor finding (C30): "The `draw()` rAF loop has no guard against the canvas being removed from the DOM. On NiceGUI full-page navigation, the canvas element is destroyed but the rAF callback continues firing indefinitely, holding a stale reference to a detached element. Add `if (!document.contains(canvas)) { return; }` before the `requestAnimationFrame(draw)` call."

Deferred from C30 per no-gate-fix-passes rule.
