# Troubleshooting

A running log of bugs, errors, and misconfigurations encountered during development — each entry includes the symptom, root cause, and fix so the same issue is never debugged twice.

---

### TRB-001 — `rag-chroma` container is unhealthy on startup

**Date:** 2026-05-11
**Component:** Docker / ChromaDB
**Symptom:** `dependency failed to start: container rag-chroma is unhealthy` when running `docker compose up -d`. The `app` and other services that depend on `chroma` fail to start.

**Root cause:** The `chromadb/chroma:latest` image does not include `curl`, `wget`, or any HTTP client binary. The health check used `CMD-SHELL` with `curl`, so every probe failed immediately with `curl: not found` (exit 1) — even though the ChromaDB server itself was healthy and responding on port 8000.

**Fix:** Replaced the `curl`-based health check with a raw TCP probe using bash's built-in `/dev/tcp` pseudo-device, which is available in the image. Applied to both `docker-compose.yml` and `docker-compose.prod.yml`.

```yaml
# Before (broken)
test: ["CMD-SHELL", "curl -sf http://localhost:8000/api/v1/heartbeat || exit 1"]

# After (fixed)
test: ["CMD-SHELL", "bash -c 'exec 3<>/dev/tcp/localhost/8000 && echo -e \"GET /api/v2/heartbeat HTTP/1.0\\r\\nHost: localhost\\r\\n\\r\\n\" >&3 && grep -q 200 <&3'"]
```

**Note:** The API path was also updated from `/api/v1/heartbeat` to `/api/v2/heartbeat` while fixing — ChromaDB 1.x still serves both, but v2 is the canonical path going forward.

---

### TRB-002 — Site redirects endlessly between `/` and `/login`

**Date:** 2026-05-11
**Component:** UI / Auth (`src/app/ui.py`)
**Symptom:** Opening the app in a browser causes an infinite redirect loop between the index page (`/`) and the login page (`/login`). The browser eventually shows an "ERR_TOO_MANY_REDIRECTS" error.

**Root cause:** The guard at the top of `login_page()` had an inverted condition:

```python
# Buggy — redirects to "/" when auth IS required
if not settings.allow_anonymous_chat:
    ui.navigate.to("/")
    return
```

When `allow_anonymous_chat = False` (auth required) and the user is unauthenticated:
1. `/` checks auth → not authenticated → redirects to `/login`
2. `/login` sees `not allow_anonymous_chat` is `True` → redirects back to `/`
3. Infinite loop.

**Fix:** Changed the guard to redirect to `/` only when the user genuinely has no reason to be on the login page — either anonymous access is allowed, or they are already authenticated.

```python
# Fixed — src/app/ui.py
if settings.allow_anonymous_chat or await verify_stored_bearer():
    ui.navigate.to("/")
    return
```

---

### TRB-003 — `RuntimeError: Found top level layout element "Footer" inside element "Column"`

**Date:** 2026-05-11
**Component:** UI / NiceGUI layout (`src/app/ui.py`)
**Symptom:** `RuntimeError: Found top level layout element "Footer" inside element "Column". Top level layout elements can not be nested but must be direct children of the page content.` — raised as soon as an authenticated user navigates to the chat page (`/`).

**Root cause:** NiceGUI enforces that `ui.footer()`, `ui.header()`, `ui.left_drawer()`, and `ui.right_drawer()` are **direct children of the page** — they cannot be nested inside any container. The `ui.footer()` (the chat input bar) was placed inside a `ui.column()`, which was itself inside a `ui.row()`:

```
ui.row()            ← outer layout row
  └── ui.column()   ← chat area wrapper
        └── ui.footer()   ← ILLEGAL — must be at page level
```

**Fix:** Moved `ui.footer()` out of all containers to sit as a direct page-level sibling of the outer `ui.row()`. Two height values were also corrected as a result:
- Outer `ui.row()`: `height:calc(100vh - 120px)` → `height:calc(100vh - 144px)` (now accounts for both header ~64px and footer ~80px)
- Inner chat scroll column: `height:calc(100% - 80px)` → `height:100%` (the 80px deduction was compensating for the footer being inside the column — no longer needed)

**Also fixed in the same pass:** `register_page()` guard was `if not settings.allow_anonymous_chat and await verify_stored_bearer()` — this allowed already-authenticated users to reach `/register` when anonymous chat was enabled. Simplified to `if await verify_stored_bearer()` to always redirect authenticated users away from the register page, consistent with the `login_page` guard.
