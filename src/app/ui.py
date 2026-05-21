import asyncio
import json
import uuid

import httpx
from nicegui import app, ui
from app.core.config import settings

_STAGE_LABELS = ["Retrieving context...", "Preparing your answer...", "Generating response..."]


def rag_icon(name: str, size: int = 18, color: str = "currentColor") -> str:
    _paths = {
        "send":          '<path d="M22 2 L11 13"/><path d="M22 2 l-7 20 -4 -9 -9 -4 z"/>',
        "search":        '<circle cx="11" cy="11" r="7"/><path d="M21 21 l-4.3 -4.3"/>',
        "arrow":         '<path d="M5 12 h14"/><path d="M13 6 l6 6 -6 6"/>',
        "down":          '<path d="M12 5 v14"/><path d="M6 13 l6 6 6 -6"/>',
        "chat":          '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
        "layers":        '<path d="M12 2 L2 7 l10 5 10 -5 z"/><path d="M2 17 l10 5 10 -5"/><path d="M2 12 l10 5 10 -5"/>',
        "target":        '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/>',
        "check":         '<path d="M20 6 L9 17 L4 12"/>',
        "code":          '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>',
        "user":          '<circle cx="12" cy="8" r="4"/><path d="M4 21 c0 -4.4 3.6 -8 8 -8 s8 3.6 8 8"/>',
        "settings":      '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
        "plus":          '<path d="M12 5 v14"/><path d="M5 12 h14"/>',
        "sparkle":       '<path d="M12 2 L13.5 10.5 L22 12 L13.5 13.5 L12 22 L10.5 13.5 L2 12 L10.5 10.5 Z"/>',
        "brain":         '<path d="M9 3 a3 3 0 0 0 -3 3 a3 3 0 0 0 -3 3 v3 a3 3 0 0 0 3 3 v3 a3 3 0 0 0 3 3 h0 a3 3 0 0 0 3 -3 V3 a0 0 0 0 0 0 0 z"/><path d="M15 3 a3 3 0 0 1 3 3 a3 3 0 0 1 3 3 v3 a3 3 0 0 1 -3 3 v3 a3 3 0 0 1 -3 3 h0 a3 3 0 0 1 -3 -3 V3 a0 0 0 0 1 0 0 z"/>',
        "stack":         '<rect x="3" y="3" width="18" height="6" rx="1.5"/><rect x="3" y="14" width="18" height="6" rx="1.5"/>',
        "check-circuit": '<path d="M3 12 h4 l2 -2 l2 2 h2"/><path d="M14 14 l2 2 l5 -7"/>',
    }
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true">{_paths.get(name, "")}</svg>'
    )


# Canonical module display names for topic_scores keys
_MODULE_LABELS: dict[str, str] = {
    "rag_fundamentals":          "RAG Fundamentals",
    "vector_databases":          "Vector Databases",
    "retrieval_methods":         "Retrieval Methods",
    "chunking_strategies":       "Chunking Strategies",
    "langchain":                 "LangChain",
    "production_patterns":       "Production Patterns",
    "embeddings_and_similarity": "Embeddings & Similarity",
    "rag_pipeline_architecture": "RAG Pipeline Architecture",
    "context_and_prompting":     "Context & Prompting",
    "evaluation_and_metrics":    "Evaluation & Metrics",
}

_PHASE_LABELS: dict[str, tuple[str, str]] = {
    "novice":        ("Phase 1", "Foundation"),
    "beginner":      ("Phase 1", "Foundation"),
    "intermediate":  ("Phase 2", "Core RAG"),
    "advanced":      ("Phase 3", "Advanced"),
    "expert":        ("Complete", "All phases"),
}

_PHASE_TOPICS: dict[str, list[str]] = {
    "novice":        ["embeddings_and_similarity", "rag_pipeline_architecture"],
    "beginner":      ["embeddings_and_similarity", "rag_pipeline_architecture"],
    "intermediate":  ["chunking_strategies", "vector_databases", "retrieval_methods", "context_and_prompting"],
    "advanced":      ["evaluation_and_metrics", "production_patterns"],
    "expert":        [],
}

_ADVANCE_MSG: dict[str, str] = {
    "novice":        "Each Phase 1 topic ≥ 0.70 to reach Phase 2",
    "beginner":      "Each Phase 1 topic ≥ 0.70 to reach Phase 2",
    "intermediate":  "Each Phase 2 topic ≥ 0.70 and average ≥ 0.75 to reach Phase 3",
    "advanced":      "Each Phase 3 topic ≥ 0.75 to become an expert",
    "expert":        "All phases complete — keep sharpening your skills",
}

_ALL_MODULES: list[dict] = [
    {"num": "01", "name": "Foundation", "topics": ["embeddings_and_similarity", "rag_pipeline_architecture"]},
    {"num": "02", "name": "Core RAG",   "topics": ["chunking_strategies", "vector_databases", "retrieval_methods", "context_and_prompting"]},
    {"num": "03", "name": "Advanced",   "topics": ["evaluation_and_metrics", "production_patterns"]},
]

_ACTIVE_MODULE_IDX: dict[str, int] = {
    "novice": 0, "beginner": 0, "intermediate": 1, "advanced": 2, "expert": 2,
}

_CURRICULUM_SEQUENCE: list[str] = [
    "embeddings_and_similarity",
    "rag_pipeline_architecture",
    "chunking_strategies",
    "vector_databases",
    "retrieval_methods",
    "context_and_prompting",
    "evaluation_and_metrics",
    "production_patterns",
]

_TOPIC_STARTER: dict[str, str] = {
    "embeddings_and_similarity": "How do embedding models turn text into vectors?",
    "rag_pipeline_architecture": "Walk me through a complete RAG pipeline.",
    "chunking_strategies":       "What chunking strategy works best for long documents?",
    "vector_databases":          "How does HNSW indexing make vector search fast?",
    "retrieval_methods":         "What's the difference between dense and sparse retrieval?",
    "context_and_prompting":     "How do I structure a RAG prompt to minimize hallucinations?",
    "evaluation_and_metrics":    "How do I measure retrieval quality in a RAG system?",
    "production_patterns":       "What are the biggest failure modes in production RAG?",
}

_NEXT_UNLOCK: dict[str, str] = {
    topic: _CURRICULUM_SEQUENCE[i + 1]
    for i, topic in enumerate(_CURRICULUM_SEQUENCE[:-1])
}

# Maps navigation chip display names → their parent module label.
# Used to render grouped module headers above the chips.
_CHIP_MODULE_GROUPS: list[tuple[str, tuple[str, ...]]] = [
    ("Foundation", ("Embeddings & Similarity", "RAG Pipeline Architecture")),
    ("Core RAG",   ("Chunking Strategies", "Vector Databases", "Retrieval Methods", "Context & Prompting")),
    ("Advanced",   ("Evaluation & Metrics", "Production Patterns")),
]


def _build_welcome_message(display_name: str | None, profile: dict | None) -> str:
    name = display_name or "there"

    if not profile:
        return (
            f"Welcome, **{name}**! I'm your RAG learning assistant.\n\n"
            "Ask me anything — or start here: **What is retrieval-augmented generation?**"
        )

    interaction_count: int = profile.get("interaction_count") or 0
    gaps: list = profile.get("gaps") or []
    strengths: list = profile.get("strengths") or []
    mastery_level: str = profile.get("mastery_level") or "novice"

    def _label(slug: str) -> str:
        return _MODULE_LABELS.get(slug, slug.replace("_", " ").title())

    def _starter(slug: str) -> str:
        return _TOPIC_STARTER.get(slug, "What would you like to explore today?")

    if interaction_count == 0 and mastery_level in ("novice", "beginner"):
        return (
            f"Ready to start, **{name}**? I'll build a picture of where you are as we go.\n\n"
            "Best first move: **What is retrieval-augmented generation?**"
        )

    if gaps:
        top_gap = gaps[0]
        return (
            f"Welcome back, **{name}**. **{_label(top_gap)}** came up as a weak spot last time — "
            f"today's a good time to close it.\n\n"
            f"Try: **{_starter(top_gap)}**"
        )

    if strengths:
        top_strength = strengths[0]
        next_slug = _NEXT_UNLOCK.get(top_strength)
        if next_slug:
            return (
                f"You have **{_label(top_strength)}** down solid, **{name}** — that's a real foundation. "
                f"**{_label(next_slug)}** is the natural next unlock.\n\n"
                f"Try: **{_starter(next_slug)}**"
            )
        return (
            f"You've worked through the full curriculum, **{name}**. "
            "At this point, sharpening the edges matters more than covering new ground.\n\n"
            f"Try: **{_starter(top_strength)}**"
        )

    # Fallback: mastery is known but gaps/strengths not yet populated —
    # recommend the first topic of their current phase.
    phase_topics = _PHASE_TOPICS.get(mastery_level, [])
    if phase_topics:
        rec_slug = phase_topics[0]
        phase_name = _PHASE_LABELS.get(mastery_level, ("", "your current phase"))[1]
        return (
            f"Welcome back, **{name}**. You're in **{phase_name}** — "
            f"that's where the real leverage is.\n\n"
            f"Try: **{_starter(rec_slug)}**"
        )

    return (
        f"Good to have you back, **{name}**. Your profile is still forming — "
        "the fastest way to build it is to start a conversation.\n\n"
        "Try: **What is retrieval-augmented generation?**"
    )



def create_session() -> dict:
    return {"session_id": str(uuid.uuid4()), "messages": []}


def setup_ui(fastapi_app):
    """Mount NiceGUI onto the existing FastAPI app."""

    def http() -> httpx.AsyncClient:
        return fastapi_app.state.internal_http_client

    def auth_headers() -> dict[str, str]:
        token = app.storage.user.get("access_token")
        if not token:
            return {}
        return {"Authorization": f"Bearer {token}"}

    async def verify_stored_bearer() -> bool:
        """True if access_token is present and /api/auth/me accepts it; clears stale auth on failure."""
        if not app.storage.user.get("access_token"):
            return False
        try:
            r = await http().get("/api/auth/me", headers=auth_headers())
            if r.status_code == 200:
                data = r.json()
                app.storage.user["user_id"] = data["user_id"]
                app.storage.user["email"] = data.get("email", "")
                app.storage.user["display_name"] = data.get("display_name", "")
                app.storage.user["is_admin"] = bool(data.get("is_admin", False))
                return True
        except Exception:
            pass
        for key in ("access_token", "user_id", "email", "display_name", "is_admin"):
            app.storage.user.pop(key, None)
        return False

    async def fetch_profile_email() -> None:
        try:
            r = await http().get("/api/auth/me", headers=auth_headers())
            if r.status_code == 200:
                data = r.json()
                app.storage.user["email"] = data.get("email", "")
                app.storage.user["display_name"] = data.get("display_name", "")
        except Exception:
            pass

    @ui.page("/login")
    async def login_page():
        if settings.allow_anonymous_chat or await verify_stored_bearer():
            ui.navigate.to("/")
            return

        ui.add_head_html('''<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
.rag-login-input .q-field__control { background: #0c0a1e !important; border-radius: 12px !important; min-height: 32px !important; }
.rag-login-input.q-field--outlined .q-field__control:before { border-color: #2e2558 !important; border-radius: 12px !important; transition: border-color 0.2s, box-shadow 0.2s; }
.rag-login-input.q-field--outlined:hover .q-field__control:before { border-color: rgba(236,72,153,0.4) !important; }
.rag-login-input.q-field--outlined.q-field--focused .q-field__control:before { border-color: #ec4899 !important; border-width: 2px !important; box-shadow: 0 0 0 3px rgba(236,72,153,0.15) !important; }
.rag-login-input:focus-within .q-field__control:before { border-color: #ec4899 !important; border-width: 2px !important; }
.rag-login-input .q-field__native { color: #ffffff !important; padding: 6px 1rem !important; min-height: unset !important; }
.rag-login-input .q-field__label { color: #94a3b8 !important; }
.rag-login-input .q-field__placeholder { color: #4a5568 !important; }
.auth-brand { display:flex; flex-direction:column; align-items:center; gap:0.5rem; padding-bottom:0.25rem; width:100%; }
.auth-tag { font-size:0.78rem; color:#94a3b8; text-align:center; }
.auth-sub { font-size:0.95rem; font-weight:600; color:#e2e8f0; text-align:center; width:100%; }
.auth-field-wrap { display:flex; flex-direction:column; gap:0.25rem; width:100%; }
.auth-field-label { font-size:0.82rem; font-weight:500; color:#e2e8f0; }
.auth-submit { width:100%; border-radius:999px !important; overflow:hidden !important; box-shadow:0 4px 24px rgba(236,72,153,0.35) !important; }
.auth-submit .q-btn__wrapper { background:linear-gradient(135deg,#f97316 0%,#ec4899 50%,#8b5cf6 100%) !important; border-radius:999px !important; min-height:48px !important; opacity:1 !important; }
.auth-submit .q-btn__content { color:white !important; font-weight:600 !important; font-size:1rem !important; }
.auth-swap { font-size:0.82rem; color:#64748b; text-align:center; width:100%; }
.auth-swap a { color:#f97316; cursor:pointer; text-decoration:none; }
.auth-swap a:hover { text-decoration:underline; }
</style>''')
        ui.query("body").style("background:radial-gradient(ellipse at 35% 0%, #2a1060 0%, #120e28 60%); color:#e2e8f0; font-family:'Inter',system-ui")
        ui.query(".nicegui-content").style("display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:100vh; padding:1rem; max-width:none")
        ui.query(".q-page").style("display:flex; flex-direction:column; align-items:center; justify-content:center; width:100%")
        with ui.column().style(
            "width:100%; max-width:420px; margin:0; padding:2rem; gap:1.25rem; "
            "background:linear-gradient(160deg, rgba(22,16,44,0.98) 0%, rgba(28,20,52,0.98) 100%); "
            "border:1px solid rgba(139,92,246,0.2); border-top:3px solid #f97316; border-radius:16px; "
            "backdrop-filter:blur(12px); box-shadow:0 8px 48px rgba(139,92,246,0.15)"
        ):
            with ui.column().classes("auth-brand").style("width:100%"):
                ui.html('<div style="width:48px;height:48px;border-radius:12px;background:linear-gradient(135deg,#f97316 0%,#ec4899 50%,#8b5cf6 100%);display:flex;align-items:center;justify-content:center;font-size:1.75rem;font-weight:800;color:white;font-family:Inter,system-ui">R</div>')
                ui.html('<span style="font-size:1.5rem;font-weight:700;letter-spacing:-0.02em;font-family:Inter,system-ui;background:linear-gradient(135deg,#f97316 0%,#ec4899 50%,#8b5cf6 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;line-height:1">RAG Tutor</span>')
                ui.html('<div class="auth-tag">Your AI-powered RAG learning assistant</div>')
            ui.html('<div class="auth-sub" style="width:100%">Sign in to continue your learning path</div>')
            ui.separator().style("border-color:rgba(139,92,246,0.2); margin:0.1rem 0")
            with ui.column().classes("auth-field-wrap"):
                ui.html('<span class="auth-field-label">Email address</span>')
                email = ui.input("").classes("rag-login-input w-full").props("outlined type=email")
            with ui.column().classes("auth-field-wrap"):
                ui.html('<span class="auth-field-label">Password</span>')
                password = ui.input(
                    "", password=True, password_toggle_button=True
                ).classes("rag-login-input w-full").props("outlined")

            async def do_login():
                try:
                    r = await http().post(
                        "/api/auth/login",
                        json={"email": email.value, "password": password.value},
                    )
                except Exception as e:
                    ui.notify(f"Network error: {e}", type="negative")
                    return
                if r.status_code != 200:
                    ui.notify("Invalid username/email or password", type="negative")
                    return
                data = r.json()
                app.storage.user["access_token"] = data["access_token"]
                app.storage.user["user_id"] = data["user_id"]
                await fetch_profile_email()
                ui.navigate.to("/")

            email.on("keydown.enter", do_login)
            password.on("keydown.enter", do_login)
            ui.button("Continue →", on_click=do_login).props("unelevated no-caps").style("background:linear-gradient(135deg,#f97316 0%,#ec4899 50%,#8b5cf6 100%) !important; color:white !important; width:100%; border-radius:999px; font-weight:600; min-height:48px; font-size:1rem; box-shadow:0 4px 24px rgba(236,72,153,0.45)")
            ui.html('<div class="auth-swap" style="width:100%">Don\'t have an account? <a href="/register">Create one →</a></div>')

    @ui.page("/register")
    async def register_page():
        if await verify_stored_bearer():
            ui.navigate.to("/")
            return

        ui.add_head_html('''<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
.rag-login-input .q-field__control { background: #0c0a1e !important; border-radius: 12px !important; min-height: 32px !important; }
.rag-login-input.q-field--outlined .q-field__control:before { border-color: #2e2558 !important; border-radius: 12px !important; transition: border-color 0.2s, box-shadow 0.2s; }
.rag-login-input.q-field--outlined:hover .q-field__control:before { border-color: rgba(139,92,246,0.4) !important; }
.rag-login-input.q-field--outlined.q-field--focused .q-field__control:before { border-color: #8b5cf6 !important; border-width: 2px !important; box-shadow: 0 0 0 3px rgba(139,92,246,0.15) !important; }
.rag-login-input:focus-within .q-field__control:before { border-color: #8b5cf6 !important; border-width: 2px !important; }
.rag-login-input .q-field__native { color: #ffffff !important; padding: 6px 1rem !important; min-height: unset !important; }
.rag-login-input .q-field__label { color: #94a3b8 !important; }
.rag-login-input .q-field__placeholder { color: #4a5568 !important; }
.auth-brand { display:flex; flex-direction:column; align-items:center; gap:0.5rem; padding-bottom:0.25rem; width:100%; }
.auth-tag { font-size:0.78rem; color:#94a3b8; text-align:center; }
.auth-sub { font-size:0.95rem; font-weight:600; color:#e2e8f0; text-align:center; width:100%; }
.auth-field-wrap { display:flex; flex-direction:column; gap:0.25rem; width:100%; }
.auth-field-label { font-size:0.82rem; font-weight:500; color:#e2e8f0; }
.auth-submit { width:100%; border-radius:999px !important; overflow:hidden !important; box-shadow:0 4px 24px rgba(236,72,153,0.35) !important; }
.auth-submit .q-btn__wrapper { background:linear-gradient(135deg,#f97316 0%,#ec4899 50%,#8b5cf6 100%) !important; border-radius:999px !important; min-height:48px !important; opacity:1 !important; }
.auth-submit .q-btn__content { color:white !important; font-weight:600 !important; font-size:1rem !important; }
.auth-swap { font-size:0.82rem; color:#64748b; text-align:center; width:100%; }
.auth-swap a { color:#8b5cf6; cursor:pointer; text-decoration:none; }
.auth-swap a:hover { text-decoration:underline; }
</style>''')
        ui.query("body").style("background:radial-gradient(ellipse at 65% 0%, #2a1060 0%, #120e28 60%); color:#e2e8f0; font-family:'Inter',system-ui")
        ui.query(".nicegui-content").style("display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:100vh; padding:1rem; max-width:none")
        ui.query(".q-page").style("display:flex; flex-direction:column; align-items:center; justify-content:center; width:100%")
        wrapper = ui.column().style(
            "width:100%; max-width:420px; margin:0; padding:2rem; gap:1.25rem; "
            "background:linear-gradient(160deg, rgba(22,16,44,0.98) 0%, rgba(28,20,52,0.98) 100%); "
            "border:1px solid rgba(139,92,246,0.2); border-top:3px solid #8b5cf6; border-radius:16px; "
            "backdrop-filter:blur(12px); box-shadow:0 8px 48px rgba(139,92,246,0.15)"
        )

        def show_success():
            name = display_name.value.strip() if display_name.value else None
            greeting = f"Welcome, {name}!" if name else "Welcome!"
            wrapper.clear()
            with wrapper:
                ui.label(greeting).style(
                    "font-size:1.35rem; font-weight:700; background:linear-gradient(135deg,#f97316,#ec4899);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text; text-align:center; width:100%"
                )
                ui.label("We're getting your account ready…").style(
                    "font-size:0.9rem; color:#94a3b8; text-align:center; width:100%"
                )
                with ui.row().style("justify-content:center; width:100%; padding:1rem 0"):
                    ui.spinner("dots", size="3rem", color="#f97316")
                ui.timer(2.5, lambda: ui.navigate.to("/"), once=True)

        with wrapper:
            with ui.column().classes("auth-brand").style("width:100%"):
                ui.html('<div style="width:48px;height:48px;border-radius:12px;background:linear-gradient(135deg,#f97316 0%,#ec4899 50%,#8b5cf6 100%);display:flex;align-items:center;justify-content:center;font-size:1.75rem;font-weight:800;color:white;font-family:Inter,system-ui">R</div>')
                ui.html('<span style="font-size:1.5rem;font-weight:700;letter-spacing:-0.02em;font-family:Inter,system-ui;background:linear-gradient(135deg,#f97316 0%,#ec4899 50%,#8b5cf6 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;line-height:1">RAG Tutor</span>')
                ui.html('<div class="auth-tag">Your AI-powered RAG learning assistant</div>')
            ui.html('<div class="auth-sub" style="width:100%">Create your account to start learning</div>')
            ui.separator().style("border-color:rgba(139,92,246,0.2); margin:0.1rem 0")
            with ui.column().classes("auth-field-wrap"):
                ui.html('<span class="auth-field-label">Display name</span>')
                display_name = ui.input("").classes("rag-login-input w-full").props("outlined")
            with ui.column().classes("auth-field-wrap"):
                ui.html('<span class="auth-field-label">Email address</span>')
                email = ui.input("").props("type=email outlined").classes("rag-login-input w-full")
            with ui.column().classes("auth-field-wrap"):
                ui.html('<span class="auth-field-label">Password</span>')
                password = ui.input("", password=True, password_toggle_button=True).classes(
                    "rag-login-input w-full"
                ).props("outlined")

            async def do_register():
                payload = {
                    "email": email.value,
                    "password": password.value,
                    "display_name": display_name.value or None,
                }
                try:
                    r = await http().post("/api/auth/register", json=payload)
                except Exception as e:
                    ui.notify(f"Network error: {e}", type="negative")
                    return
                if r.status_code != 200:
                    try:
                        detail = r.json().get("detail", r.text)
                    except Exception:
                        detail = r.text
                    ui.notify(str(detail), type="negative")
                    return
                data = r.json()
                app.storage.user["access_token"] = data["access_token"]
                app.storage.user["user_id"] = data["user_id"]
                await fetch_profile_email()
                show_success()

            display_name.on("keydown.enter", do_register)
            email.on("keydown.enter", do_register)
            password.on("keydown.enter", do_register)
            ui.button("Create account →", on_click=do_register).props("unelevated no-caps").style("background:linear-gradient(135deg,#f97316 0%,#ec4899 50%,#8b5cf6 100%) !important; color:white !important; width:100%; border-radius:999px; font-weight:600; min-height:48px; font-size:1rem; box-shadow:0 4px 24px rgba(236,72,153,0.45)")
            ui.html('<div class="auth-swap" style="width:100%">Already learning? <a href="/login">Sign in →</a></div>')

    @ui.page("/landing")
    def landing_page():
        ui.add_head_html('''<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
/* ---- Landing page namespace: rag-landing- ---- */
html { scroll-behavior: smooth; }
body { background: #120e28; color: #e2e8f0; font-family: "Inter", system-ui, sans-serif; margin: 0; }

.rag-landing-wrap {
  width: 100%;
  max-width: 100%;
  overflow-x: hidden;
  background: #120e28;
  box-sizing: border-box;
}

/* NAV */
.rag-landing-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 2.5rem;
  background: rgba(12,10,30,0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(139,92,246,0.12);
  position: sticky;
  top: 0;
  z-index: 100;
}
.rag-landing-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
}
.rag-landing-brand-mark {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(249,115,22,0.15) 0%, rgba(139,92,246,0.15) 100%);
  border: 1px solid rgba(249,115,22,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.9rem;
  color: #f97316;
  font-family: "Inter", system-ui;
}
.rag-landing-wordmark {
  font-size: 1.35rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, #f97316 0%, #ec4899 50%, #8b5cf6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1;
}
.rag-landing-nav-links {
  display: flex;
  gap: 2rem;
}
.rag-landing-nav-links a {
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  transition: color 0.2s;
  cursor: pointer;
}
.rag-landing-nav-links a:hover { color: #e2e8f0; }
@media (max-width: 767px) { .rag-landing-nav-links { display: none; } }

.rag-landing-btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: linear-gradient(135deg, #f97316 0%, #ec4899 50%, #8b5cf6 100%);
  color: #fff;
  border: none;
  border-radius: 999px;
  padding: 0.55rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 24px rgba(236,72,153,0.32), 0 0 0 1px rgba(249,115,22,0.4) inset;
  transition: box-shadow 0.2s, transform 0.15s;
  text-decoration: none;
  font-family: "Inter", system-ui;
}
.rag-landing-btn-primary:hover {
  box-shadow: 0 6px 32px rgba(236,72,153,0.55), 0 0 0 1px rgba(249,115,22,0.6) inset;
  transform: translateY(-1px);
}
.rag-landing-btn-primary.large {
  padding: 0.8rem 2rem;
  font-size: 1rem;
  border-radius: 999px;
}

.rag-landing-btn-ghost {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: transparent;
  color: #94a3b8;
  border: 1px solid rgba(139,92,246,0.3);
  border-radius: 999px;
  padding: 0.55rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: border-color 0.2s, color 0.2s;
  text-decoration: none;
  font-family: "Inter", system-ui;
}
.rag-landing-btn-ghost:hover { border-color: rgba(236,72,153,0.5); color: #e2e8f0; }
.rag-landing-btn-ghost.large {
  padding: 0.8rem 2rem;
  font-size: 1rem;
}

/* HERO */
.rag-landing-hero {
  position: relative;
  min-height: 580px;
  display: flex;
  align-items: center;
  padding: 5rem clamp(1.5rem, 5vw, 6rem) 4rem;
  overflow: hidden;
  background: radial-gradient(ellipse at 8% 92%, rgba(249,115,22,0.07) 0%, transparent 38%),
              radial-gradient(ellipse at 92% 8%, rgba(139,92,246,0.07) 0%, transparent 38%),
              #120e28;
}
.rag-landing-hero-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  opacity: 0.17;
  pointer-events: none;
}
.rag-landing-hero-content {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 4rem;
  width: 100%;
  box-sizing: border-box;
}
.rag-landing-hero-left {
  flex: 1;
  min-width: 0;
}
.rag-landing-eyebrow {
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #94a3b8;
  margin-bottom: 1.25rem;
}
.rag-landing-h1 {
  font-size: clamp(2.4rem, 4vw, 3.2rem);
  font-weight: 700;
  line-height: 1.08;
  letter-spacing: -0.03em;
  background: linear-gradient(135deg, #f97316 0%, #ec4899 50%, #8b5cf6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  color: #f97316;
  margin: 0 0 1.25rem;
}
.rag-landing-sub {
  font-size: 1rem;
  color: #94a3b8;
  max-width: 480px;
  line-height: 1.65;
  margin: 0 0 2rem;
}
.rag-landing-cta-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 1.25rem;
}
.rag-landing-social-proof {
  font-size: 0.78rem;
  color: #64748b;
  letter-spacing: 0.01em;
}

/* HERO MOCK */
.rag-landing-hero-mock {
  flex: 0 0 clamp(340px, 38%, 480px);
  background: linear-gradient(160deg, rgba(30,22,60,0.96) 0%, rgba(22,16,58,0.96) 100%);
  border: 1px solid rgba(139,92,246,0.22);
  border-radius: 16px;
  box-shadow: 0 8px 48px rgba(139,92,246,0.18), 0 0 0 1px rgba(249,115,22,0.06) inset;
  backdrop-filter: blur(8px);
  overflow: hidden;
}
@media (max-width: 768px) { .rag-landing-hero-mock { display: none; } }
.rag-landing-mock-title {
  padding: 0.6rem 1rem;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: #64748b;
  border-bottom: 1px solid rgba(139,92,246,0.12);
  background: rgba(12,10,30,0.6);
}
.rag-landing-mock-body {
  padding: 0.875rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.rag-landing-mock-bubble-user {
  align-self: flex-end;
  max-width: 82%;
  background: linear-gradient(135deg, #ea580c, #be185d);
  color: #fff0f6;
  border-radius: 14px 14px 3px 14px;
  padding: 0.6rem 0.75rem;
  font-size: 0.78rem;
  line-height: 1.4;
}
.rag-landing-mock-row-assistant {
  display: flex;
  gap: 0.5rem;
  align-items: flex-start;
}
.rag-landing-mock-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(249,115,22,0.2), rgba(139,92,246,0.2));
  border: 1px solid rgba(249,115,22,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.55rem;
  font-weight: 700;
  color: #f97316;
  flex-shrink: 0;
}
.rag-landing-mock-bubble-assistant {
  flex: 1;
  background: rgba(22,16,44,0.9);
  border: 1px solid rgba(139,92,246,0.18);
  border-radius: 3px 14px 14px 14px;
  padding: 0.6rem 0.75rem;
  font-size: 0.78rem;
  line-height: 1.45;
  color: #e2e8f0;
}
.rag-landing-mock-em { color: #e879f9; }
.rag-landing-mock-code {
  background: #16103a;
  border: 1px solid #2e2558;
  border-radius: 3px;
  padding: 0.1em 0.3em;
  font-size: 0.72rem;
  color: #e879f9;
  font-family: ui-monospace, monospace;
}
.rag-landing-mock-kc {
  background: rgba(139,92,246,0.08);
  border: 1px solid rgba(139,92,246,0.28);
  border-radius: 10px;
  padding: 0.6rem 0.75rem;
}
.rag-landing-mock-kc-label {
  font-size: 0.65rem;
  font-weight: 600;
  color: #a78bfa;
  margin-bottom: 0.35rem;
}
.rag-landing-mock-kc-q {
  font-size: 0.78rem;
  color: #e2e8f0;
  line-height: 1.4;
}

/* MARQUEE */
.rag-landing-marquee {
  width: 100%;
  overflow: hidden;
  background: rgba(12,10,30,0.7);
  backdrop-filter: blur(4px);
  border-top: 1px solid rgba(139,92,246,0.1);
  border-bottom: 1px solid rgba(139,92,246,0.1);
  padding: 0.875rem 0;
}
.rag-landing-marquee-track {
  display: flex;
  width: max-content;
  animation: rag-landing-marquee 30s linear infinite;
  white-space: nowrap;
}
.rag-landing-marquee-item {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #94a3b8;
  padding: 0 1rem;
}
.rag-landing-marquee-dot {
  color: #ec4899;
  padding: 0 0.25rem;
}
@keyframes rag-landing-marquee {
  0%   { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}

/* SECTIONS */
.rag-landing-section {
  width: 100%;
  box-sizing: border-box;
  padding: 5rem clamp(1.5rem, 5vw, 6rem);
}
.rag-landing-section-eyebrow {
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #94a3b8;
  margin-bottom: 1rem;
}
.rag-landing-h2 {
  font-size: clamp(1.75rem, 3vw, 2.4rem);
  font-weight: 700;
  line-height: 1.12;
  letter-spacing: -0.025em;
  color: #f8fafc;
  margin: 0 0 1.5rem;
}
.rag-landing-h2-gradient {
  background: linear-gradient(135deg, #f97316 0%, #ec4899 50%, #8b5cf6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  color: #f97316;
}

/* PROBLEM SECTION */
.rag-landing-problem-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 3.5rem;
  align-items: start;
}
@media (max-width: 767px) { .rag-landing-problem-grid { grid-template-columns: 1fr; } }
.rag-landing-body-p {
  font-size: 0.95rem;
  color: #94a3b8;
  line-height: 1.7;
  margin: 0 0 1rem;
}
.rag-landing-before-after {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.rag-landing-ba-card {
  background: linear-gradient(160deg, rgba(30,22,60,0.92) 0%, rgba(22,16,58,0.92) 100%);
  border: 1px solid #241d4a;
  border-radius: 12px;
  padding: 1.25rem;
  box-shadow: 0 4px 28px rgba(139,92,246,0.1);
}
.rag-landing-ba-card.bad  { border-top: 2px solid rgba(248,113,113,0.5); }
.rag-landing-ba-card.good { border-top: 2px solid rgba(249,115,22,0.5); }
.rag-landing-ba-tag {
  display: inline-block;
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  border-radius: 999px;
  padding: 0.2rem 0.65rem;
  margin-bottom: 0.75rem;
}
.rag-landing-ba-card.bad  .rag-landing-ba-tag { background: rgba(248,113,113,0.1); color: #f87171; border: 1px solid rgba(248,113,113,0.2); }
.rag-landing-ba-card.good .rag-landing-ba-tag { background: rgba(249,115,22,0.1);  color: #f97316; border: 1px solid rgba(249,115,22,0.2); }
.rag-landing-ba-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.rag-landing-ba-list li {
  font-size: 0.82rem;
  color: #94a3b8;
  padding-left: 1.1rem;
  position: relative;
  line-height: 1.4;
}
.rag-landing-ba-card.bad  .rag-landing-ba-list li::before { content: "×"; position: absolute; left: 0; color: #f87171; }
.rag-landing-ba-card.good .rag-landing-ba-list li::before { content: "✓"; position: absolute; left: 0; color: #4ade80; }

/* FEATURES SECTION */
.rag-landing-features {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
  margin-top: 1rem;
}
@media (max-width: 767px) { .rag-landing-features { grid-template-columns: 1fr; } }
.rag-landing-feature {
  background: linear-gradient(160deg, rgba(30,22,60,0.92) 0%, rgba(22,16,58,0.92) 100%);
  border: 1px solid #241d4a;
  border-radius: 14px;
  padding: 1.75rem 1.5rem;
  box-shadow: 0 4px 28px rgba(139,92,246,0.1);
  transition: box-shadow 0.2s, transform 0.2s;
}
.rag-landing-feature:hover {
  box-shadow: 0 8px 36px rgba(139,92,246,0.2);
  transform: translateY(-2px);
}
.rag-landing-feature-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: rgba(22,16,44,0.9);
  border: 1px solid rgba(139,92,246,0.2);
  margin-bottom: 1.25rem;
}
.rag-landing-feature h3 {
  font-size: 1.05rem;
  font-weight: 700;
  color: #f8fafc;
  margin: 0 0 0.6rem;
  letter-spacing: -0.01em;
}
.rag-landing-feature p {
  font-size: 0.875rem;
  color: #94a3b8;
  line-height: 1.6;
  margin: 0;
}

/* MODULES SECTION */
.rag-landing-modules {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.25rem;
  margin-top: 1rem;
}
@media (max-width: 900px)  { .rag-landing-modules { grid-template-columns: repeat(2,1fr); } }
@media (max-width: 600px)  { .rag-landing-modules { grid-template-columns: 1fr; } }
.rag-landing-module {
  background: linear-gradient(160deg, rgba(30,22,60,0.92) 0%, rgba(22,16,58,0.92) 100%);
  border: 1px solid #241d4a;
  border-radius: 12px;
  padding: 1.25rem;
  box-shadow: 0 4px 24px rgba(139,92,246,0.08);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.rag-landing-module-num {
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #64748b;
  font-family: ui-monospace, monospace;
}
.rag-landing-module-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: #e2e8f0;
  letter-spacing: -0.01em;
}
.rag-landing-module-desc {
  font-size: 0.8rem;
  color: #94a3b8;
  line-height: 1.5;
  flex: 1;
}
.rag-landing-module-bar-track {
  height: 4px;
  background: rgba(36,29,74,0.8);
  border-radius: 2px;
  overflow: hidden;
  margin-top: 0.25rem;
}
.rag-landing-module-bar-fill {
  height: 100%;
  border-radius: 2px;
  background: linear-gradient(90deg, #f97316 0%, #ec4899 55%, #8b5cf6 100%);
}

/* CTA FOOTER */
.rag-landing-cta-footer {
  text-align: center;
  padding: 6rem clamp(1.5rem, 5vw, 6rem);
  background: radial-gradient(ellipse at 50% 80%, rgba(249,115,22,0.06) 0%, transparent 60%),
              radial-gradient(ellipse at 50% 20%, rgba(139,92,246,0.06) 0%, transparent 60%),
              #120e28;
  border-top: 1px solid rgba(139,92,246,0.1);
}
.rag-landing-cta-footer .rag-landing-section-eyebrow { text-align: center; }
.rag-landing-cta-footer-body {
  font-size: 0.95rem;
  color: #94a3b8;
  max-width: 520px;
  margin: 0 auto 2rem;
  line-height: 1.7;
}
.rag-landing-cta-footer-sub {
  margin-top: 1.25rem;
  font-size: 0.82rem;
  color: #64748b;
}
.rag-landing-cta-footer-sub a {
  color: #e2e8f0;
  border-bottom: 1px solid rgba(236,72,153,0.4);
  padding-bottom: 1px;
  text-decoration: none;
  cursor: pointer;
}

/* SITE FOOTER */
.rag-landing-site-footer {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 2rem clamp(1.5rem, 5vw, 6rem);
  border-top: 1px solid rgba(139,92,246,0.1);
  background: #0c0a1e;
}
.rag-landing-site-footer-copy {
  font-size: 0.75rem;
  color: #64748b;
  letter-spacing: 0.03em;
}
/* Strip NiceGUI/Quasar container constraints — landing page only */
.nicegui-content { display: block !important; padding: 0 !important; max-width: 100% !important; width: 100% !important; margin: 0 !important; align-items: unset !important; justify-content: unset !important; }
.q-page { padding: 0 !important; }
.q-page-container { padding: 0 !important; width: 100% !important; max-width: 100% !important; }
#q-app, .q-layout { width: 100% !important; max-width: 100% !important; overflow-x: hidden !important; }

/* Custom scrollbar */
html { scrollbar-width: thin; scrollbar-color: #8b5cf6 #0c0a1e; }
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0c0a1e; }
::-webkit-scrollbar-thumb { background: linear-gradient(180deg, #f97316 0%, #ec4899 50%, #8b5cf6 100%); border-radius: 999px; }
::-webkit-scrollbar-thumb:hover { opacity: 0.85; }

/* Back-to-top button */
#rag-landing-totop {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  z-index: 999;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: linear-gradient(135deg, #f97316 0%, #ec4899 50%, #8b5cf6 100%);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 24px rgba(236,72,153,0.4), 0 0 0 1px rgba(249,115,22,0.3) inset;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.25s, transform 0.2s, box-shadow 0.2s;
  font-family: "Inter", system-ui;
}
#rag-landing-totop.rag-totop-visible {
  opacity: 1;
  pointer-events: auto;
}
#rag-landing-totop:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 32px rgba(236,72,153,0.6), 0 0 0 1px rgba(249,115,22,0.5) inset;
}
</style>''')

        ui.add_head_html('''<script>
document.addEventListener("DOMContentLoaded", function() {
  var canvas = document.getElementById("rag-particle-canvas");
  if (!canvas) return;
  var ctx = canvas.getContext("2d");
  var raf;
  var dpr = Math.min(window.devicePixelRatio || 1, 2);
  var colors = ["#f97316", "#ec4899", "#8b5cf6"];
  var density = 28;

  function resize() {
    var r = canvas.getBoundingClientRect();
    canvas.width = r.width * dpr;
    canvas.height = r.height * dpr;
    ctx.scale(dpr, dpr);
  }
  resize();
  window.addEventListener("resize", resize);

  function W() { return canvas.getBoundingClientRect().width; }
  function H() { return canvas.getBoundingClientRect().height; }

  var nodes = [];
  for (var i = 0; i < density; i++) {
    nodes.push({
      x: Math.random() * W(),
      y: Math.random() * H(),
      vx: (Math.random() - 0.5) * 0.18,
      vy: (Math.random() - 0.5) * 0.18,
      r: 1.5 + Math.random() * 2.5,
      c: colors[Math.floor(Math.random() * colors.length)]
    });
  }

  var LINK_DIST = 180;
  var t = 0;

  function draw() {
    var cw = W(), ch = H();
    ctx.clearRect(0, 0, cw, ch);
    t += 0.006;

    for (var i = 0; i < nodes.length; i++) {
      for (var j = i + 1; j < nodes.length; j++) {
        var a = nodes[i], b = nodes[j];
        var dx = a.x - b.x, dy = a.y - b.y;
        var d = Math.sqrt(dx*dx + dy*dy);
        if (d < LINK_DIST) {
          var alpha = (1 - d / LINK_DIST) * 0.5;
          var phase = (Math.sin(t * 1.2 + i * 0.4 + j * 0.3) + 1) / 2;
          var hue = phase < 0.5 ? "236,72,153" : "139,92,246";
          ctx.strokeStyle = "rgba(" + hue + "," + (alpha * 0.8) + ")";
          ctx.lineWidth = 0.6;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }
    }

    for (var k = 0; k < nodes.length; k++) {
      var n = nodes[k];
      n.x += n.vx; n.y += n.vy;
      if (n.x < -20) n.x = cw + 20; if (n.x > cw + 20) n.x = -20;
      if (n.y < -20) n.y = ch + 20; if (n.y > ch + 20) n.y = -20;

      var grad = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.r * 5);
      grad.addColorStop(0, n.c);
      grad.addColorStop(1, "transparent");
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.r * 5, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = n.c;
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
      ctx.fill();
    }

    if (!document.contains(canvas)) { return; }
    raf = requestAnimationFrame(draw);
  }
  draw();
});
</script>''')

        ui.add_head_html('''<script>
window.addEventListener("scroll", function() {
  var btn = document.getElementById("rag-landing-totop");
  if (!btn) return;
  if (window.scrollY > 320) {
    btn.classList.add("rag-totop-visible");
  } else {
    btn.classList.remove("rag-totop-visible");
  }
});
document.addEventListener("click", function(e) {
  if (e.target.closest("#rag-landing-totop")) {
    window.scrollTo({top: 0, behavior: "smooth"});
  }
});
</script>''')

        ui.query("body").style("background:#120e28; color:#e2e8f0; font-family:'Inter',system-ui; margin:0; padding:0")
        ui.query(".nicegui-content").style("display: block !important; padding: 0 !important; max-width: 100% !important; width: 100% !important; margin: 0 !important; align-items: unset !important; justify-content: unset !important")
        ui.query(".q-page").style("padding: 0 !important; min-height: unset !important")

        # Section A — Navbar
        ui.html('''<div class="rag-landing-wrap">
<nav class="rag-landing-nav">
  <a class="rag-landing-brand" href="/landing" style="text-decoration:none">
    <div class="rag-landing-brand-mark">R</div>
    <span class="rag-landing-wordmark">RAG Tutor</span>
  </a>
  <div class="rag-landing-nav-links">
    <a href="#problem">What It Solves</a>
    <a href="#how-it-works">How It Works</a>
    <a href="#curriculum">Curriculum</a>
  </div>
  <div style="display:flex;align-items:center;gap:0.625rem">
    <a class="rag-landing-btn-primary" href="/login">Sign in</a>
    <a class="rag-landing-btn-primary" href="/register">Start Learning Free
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12 h14"/><path d="M13 6 l6 6 -6 6"/></svg>
    </a>
  </div>
</nav>

<!-- Section B — Hero -->
<section class="rag-landing-hero">
  <canvas id="rag-particle-canvas" class="rag-landing-hero-canvas"></canvas>
  <div class="rag-landing-hero-content">
    <div class="rag-landing-hero-left">
      <div class="rag-landing-eyebrow">AI-NATIVE LEARNING SYSTEM</div>
      <h1 class="rag-landing-h1">Master RAG.<br>Ship with confidence.</h1>
      <p class="rag-landing-sub">RAG Tutor adapts to your level in real time — tracking your gaps, building on your strengths, and guiding you from fundamentals to production-grade systems.</p>
      <div class="rag-landing-cta-row">
        <a class="rag-landing-btn-primary large" href="/register">Start for Free
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12 h14"/><path d="M13 6 l6 6 -6 6"/></svg>
        </a>
        <a class="rag-landing-btn-ghost large" href="#how-it-works">See how it works
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 5 v14"/><path d="M6 13 l6 6 6 -6"/></svg>
        </a>
      </div>
      <div class="rag-landing-social-proof">No credit card required &nbsp;·&nbsp; Personalizes to your level instantly</div>
    </div>
    <!-- Hero mock — all inline styles, no shared class names with real chat page -->
    <div class="rag-landing-hero-mock">
      <div class="rag-landing-mock-title">LIVE &nbsp;·&nbsp; RAG TUTOR</div>
      <div class="rag-landing-mock-body">
        <div style="display:flex;justify-content:flex-end">
          <div class="rag-landing-mock-bubble-user">Why does cosine similarity outperform dot product for normalized embeddings?</div>
        </div>
        <div class="rag-landing-mock-row-assistant">
          <div class="rag-landing-mock-avatar">RT</div>
          <div class="rag-landing-mock-bubble-assistant">For unit-normalized vectors they&#39;re mathematically equivalent — same ranking, different scale. Where it matters is when norms <span class="rag-landing-mock-em">aren&#39;t</span> equal: dot product amplifies high-norm chunks. With <span class="rag-landing-mock-code">bge-large</span> embeddings you&#39;ll see a measurable shift on rare-token queries.</div>
        </div>
        <div class="rag-landing-mock-kc">
          <div class="rag-landing-mock-kc-label">&#10022; Knowledge Check</div>
          <div class="rag-landing-mock-kc-q">Which embedding model normalizes outputs by default?</div>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- Section C — Marquee -->
<div class="rag-landing-marquee" aria-hidden="true">
  <div class="rag-landing-marquee-track">
    <span class="rag-landing-marquee-item">RAG Fundamentals</span><span class="rag-landing-marquee-dot">·</span>
    <span class="rag-landing-marquee-item">Vector Databases</span><span class="rag-landing-marquee-dot">·</span>
    <span class="rag-landing-marquee-item">Retrieval Methods</span><span class="rag-landing-marquee-dot">·</span>
    <span class="rag-landing-marquee-item">Chunking Strategies</span><span class="rag-landing-marquee-dot">·</span>
    <span class="rag-landing-marquee-item">LangChain</span><span class="rag-landing-marquee-dot">·</span>
    <span class="rag-landing-marquee-item">Production Patterns</span><span class="rag-landing-marquee-dot">·</span>
    <span class="rag-landing-marquee-item">RAG Fundamentals</span><span class="rag-landing-marquee-dot">·</span>
    <span class="rag-landing-marquee-item">Vector Databases</span><span class="rag-landing-marquee-dot">·</span>
    <span class="rag-landing-marquee-item">Retrieval Methods</span><span class="rag-landing-marquee-dot">·</span>
    <span class="rag-landing-marquee-item">Chunking Strategies</span><span class="rag-landing-marquee-dot">·</span>
    <span class="rag-landing-marquee-item">LangChain</span><span class="rag-landing-marquee-dot">·</span>
    <span class="rag-landing-marquee-item">Production Patterns</span><span class="rag-landing-marquee-dot">·</span>
  </div>
</div>

<!-- Section D — Problem -->
<div class="rag-landing-section" id="problem">
  <div class="rag-landing-problem-grid">
    <div>
      <div class="rag-landing-section-eyebrow">THE PROBLEM</div>
      <h2 class="rag-landing-h2 rag-landing-h2-gradient">RAG is everywhere.<br>Understanding it deeply is rare.</h2>
      <p class="rag-landing-body-p">Most teams bolt together a LangChain tutorial and call it a RAG pipeline. Then they wonder why retrieval quality degrades, why hallucinations creep in at the edges, why their re-ranker makes things worse.</p>
      <p class="rag-landing-body-p">The real issues — chunking strategy, embedding model choice, index configuration, retrieval scoring, hybrid search, production caching — live in the space between the tutorial and the production system.</p>
      <p class="rag-landing-body-p">RAG Tutor closes that gap. Not with more documentation. With a tutor that knows exactly where you are and what you need next.</p>
    </div>
    <div class="rag-landing-before-after">
      <div class="rag-landing-ba-card bad">
        <span class="rag-landing-ba-tag">Without</span>
        <ul class="rag-landing-ba-list">
          <li>Hardcoded k=4. No re-rank.</li>
          <li>Fixed-size chunks. Lost context.</li>
          <li>Cosine, no hybrid. Rare tokens miss.</li>
          <li>No eval. Vibes-based shipping.</li>
          <li>Latency unknown. Caches absent.</li>
        </ul>
      </div>
      <div class="rag-landing-ba-card good">
        <span class="rag-landing-ba-tag">With RAG Tutor</span>
        <ul class="rag-landing-ba-list">
          <li>Adaptive k, learned per query class.</li>
          <li>Recursive chunking by doc structure.</li>
          <li>Hybrid BM25 + dense, with reranker.</li>
          <li>Recall@10 in CI. Regression alarms.</li>
          <li>Cache layers tuned to p50 latency.</li>
        </ul>
      </div>
    </div>
  </div>
</div>

<!-- Section E — Features -->
<div class="rag-landing-section" id="how-it-works" style="padding-top:2rem">
  <div class="rag-landing-section-eyebrow" style="text-align:center">HOW IT WORKS</div>
  <h2 class="rag-landing-h2" style="text-align:center;margin-bottom:3rem">Built different.</h2>
  <div class="rag-landing-features">
    <div class="rag-landing-feature">
      <div class="rag-landing-feature-icon">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#f97316" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M9 3 a3 3 0 0 0 -3 3 a3 3 0 0 0 -3 3 v3 a3 3 0 0 0 3 3 v3 a3 3 0 0 0 3 3 h0 a3 3 0 0 0 3 -3 V3 a0 0 0 0 0 0 0 z"/>
          <path d="M15 3 a3 3 0 0 1 3 3 a3 3 0 0 1 3 3 v3 a3 3 0 0 1 -3 3 v3 a3 3 0 0 1 -3 3 h0 a3 3 0 0 1 -3 -3 V3 a0 0 0 0 1 0 0 z"/>
        </svg>
      </div>
      <h3>Knows what you know</h3>
      <p>Every question you ask updates your knowledge profile. RAG Tutor adapts every response to your current mastery level — not a generic difficulty setting.</p>
    </div>
    <div class="rag-landing-feature">
      <div class="rag-landing-feature-icon">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#ec4899" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M12 2 L2 7 l10 5 10 -5 z"/>
          <path d="M2 17 l10 5 10 -5"/>
          <path d="M2 12 l10 5 10 -5"/>
        </svg>
      </div>
      <h3>From zero to production</h3>
      <p>Six modules cover every layer of the RAG stack — fundamentals, vector databases, retrieval methods, chunking, LangChain, and production patterns. In that order, for a reason.</p>
    </div>
    <div class="rag-landing-feature">
      <div class="rag-landing-feature-icon">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M3 12 h4 l2 -2 l2 2 h2"/>
          <path d="M14 14 l2 2 l5 -7"/>
        </svg>
      </div>
      <h3>Learns from your answers</h3>
      <p>After each response, RAG Tutor surfaces a knowledge check. Your answers train its model of you — so the next response is sharper, more targeted, more useful.</p>
    </div>
  </div>
</div>

<!-- Section F — Modules -->
<div class="rag-landing-section" id="curriculum">
  <div class="rag-landing-section-eyebrow">CURRICULUM</div>
  <h2 class="rag-landing-h2">Six modules. One coherent path.</h2>
  <p style="color:#94a3b8;max-width:520px;font-size:1rem;margin-bottom:2.25rem;line-height:1.6">Designed to build on each other — not to be consumed in isolation.</p>
  <div class="rag-landing-modules">
    <div class="rag-landing-module">
      <div class="rag-landing-module-num">01</div>
      <div class="rag-landing-module-title">RAG Fundamentals</div>
      <div class="rag-landing-module-desc">The architecture, the intuition, the why.</div>
      <div class="rag-landing-module-bar-track"><div class="rag-landing-module-bar-fill" style="width:92%"></div></div>
    </div>
    <div class="rag-landing-module">
      <div class="rag-landing-module-num">02</div>
      <div class="rag-landing-module-title">Vector Databases</div>
      <div class="rag-landing-module-desc">FAISS, Pinecone, Weaviate — and when to use each.</div>
      <div class="rag-landing-module-bar-track"><div class="rag-landing-module-bar-fill" style="width:71%"></div></div>
    </div>
    <div class="rag-landing-module">
      <div class="rag-landing-module-num">03</div>
      <div class="rag-landing-module-title">Retrieval Methods</div>
      <div class="rag-landing-module-desc">Semantic, keyword, hybrid, re-ranking.</div>
      <div class="rag-landing-module-bar-track"><div class="rag-landing-module-bar-fill" style="width:48%"></div></div>
    </div>
    <div class="rag-landing-module">
      <div class="rag-landing-module-num">04</div>
      <div class="rag-landing-module-title">Chunking Strategies</div>
      <div class="rag-landing-module-desc">The decision that breaks more pipelines than any other.</div>
      <div class="rag-landing-module-bar-track"><div class="rag-landing-module-bar-fill" style="width:32%"></div></div>
    </div>
    <div class="rag-landing-module">
      <div class="rag-landing-module-num">05</div>
      <div class="rag-landing-module-title">LangChain</div>
      <div class="rag-landing-module-desc">Chains, agents, and retrieval pipelines in code.</div>
      <div class="rag-landing-module-bar-track"><div class="rag-landing-module-bar-fill" style="width:12%"></div></div>
    </div>
    <div class="rag-landing-module">
      <div class="rag-landing-module-num">06</div>
      <div class="rag-landing-module-title">Production Patterns</div>
      <div class="rag-landing-module-desc">Caching, eval, observability, latency tuning.</div>
      <div class="rag-landing-module-bar-track"><div class="rag-landing-module-bar-fill" style="width:4%"></div></div>
    </div>
  </div>
</div>

<!-- Section G — CTA Footer -->
<div class="rag-landing-cta-footer">
  <div class="rag-landing-section-eyebrow" style="text-align:center">GET STARTED</div>
  <h2 class="rag-landing-h2 rag-landing-h2-gradient" style="font-size:clamp(2.2rem,4vw,3.2rem);margin-bottom:1.25rem">Start learning today.</h2>
  <p class="rag-landing-cta-footer-body">Your first session is free. No setup. No configuration. Just ask your first question and watch the system adapt.</p>
  <a class="rag-landing-btn-primary large" href="/register">Get Started
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12 h14"/><path d="M13 6 l6 6 -6 6"/></svg>
  </a>
  <div class="rag-landing-cta-footer-sub">Already have an account? <a href="/login">Sign in &#8594;</a></div>
</div>

<!-- Section H — Site Footer -->
<footer class="rag-landing-site-footer">
  <div style="display:flex;align-items:center;gap:8px">
    <div class="rag-landing-brand-mark" style="width:24px;height:24px;font-size:0.7rem">R</div>
    <span class="rag-landing-wordmark" style="font-size:1rem">RAG Tutor</span>
  </div>
  <div class="rag-landing-site-footer-copy">&#169; 2026 RAG Tutor &nbsp;·&nbsp; retrieve &nbsp;·&nbsp; augment &nbsp;·&nbsp; generate &nbsp;·&nbsp; master</div>
</footer>

<button id="rag-landing-totop" aria-label="Back to top">
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path d="M12 19V5"/><path d="M5 12l7-7 7 7"/>
  </svg>
</button>
</div>''')

    @ui.page("/")
    async def index():
        ui.add_head_html('''<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">''')
        ui.query("body").style("background:#120e28; color:#e2e8f0; font-family:'Inter',system-ui; overflow:hidden")

        ui.add_head_html("""
<style>
:root {
  --c-canvas: #120e28;
  --c-frame:  #0c0a1e;
  --c-sidebar:#16103a;
  --c-card:   #1e163c;
  --c-border: #241d4a;
  --c-warm:   #f97316;
  --c-coral:  #ec4899;
  --c-violet: #8b5cf6;
  --c-blue:   #38bdf8;
  --c-muted:  #94a3b8;
  --c-sunset: linear-gradient(135deg, #f97316, #ec4899, #8b5cf6);
  --c-surface-alt: #231848;
  --c-border-soft: rgba(139,92,246,0.18);
  --c-hairline:    rgba(255,255,255,0.04);
  --c-fg:          #e2e8f0;
  --c-fg-strong:   #f8fafc;
  --c-subtle:      #64748b;
  --c-neural:      #a78bfa;
  --g-sunset:      linear-gradient(135deg, #f97316 0%, #ec4899 50%, #8b5cf6 100%);
  --g-horizon:     linear-gradient(90deg, #f97316 0%, #ec4899 40%, #8b5cf6 70%, #38bdf8 100%);
  --g-card:        linear-gradient(160deg, rgba(30,22,60,0.92) 0%, rgba(22,16,58,0.92) 100%);
  --glow-card:     0 4px 28px rgba(139,92,246,0.12);
  --r-pill:        999px;
}
.nicegui-markdown h1,.nicegui-markdown h2,.nicegui-markdown h3{
  background:linear-gradient(135deg,#f97316,#ec4899);-webkit-background-clip:text;
  -webkit-text-fill-color:transparent;background-clip:text;
  font-weight:700;margin-top:1rem;margin-bottom:0.4rem}
.nicegui-markdown h1{font-size:1.4em}
.nicegui-markdown h2{font-size:1.2em}
.nicegui-markdown h3{font-size:1.05em}
.nicegui-markdown code{
  background:#16103a;font-family:ui-monospace,monospace;
  border:1px solid #2e2558;border-radius:4px;
  padding:0.1em 0.35em;font-size:0.875em;color:#e879f9}
.nicegui-markdown pre{
  background:#16103a;border:1px solid #2e2558;border-radius:6px;
  padding:0.75rem 1rem;overflow-x:auto;margin:0.5rem 0}
.nicegui-markdown pre code{border:none;padding:0;font-size:0.85em;color:#e2e8f0}
.nicegui-markdown ul,.nicegui-markdown ol{
  padding-left:1.5rem;margin:0.4rem 0}
.nicegui-markdown li{margin:0.2rem 0}
.q-tab-panels { background: #120e28 !important; }
.q-tab-panel  { background: #120e28 !important; padding: 0 !important; }
/* Pill-style tabs */
.rag-pill-tabs { background: transparent !important; border-bottom: none !important; min-height: auto !important; }
.rag-pill-tabs .q-tabs__content { background: var(--c-card,#1e163c); border-radius: 999px; padding: 4px; gap: 0; min-height: auto !important; }
.rag-pill-tabs .q-tab { padding: 7px 16px !important; border-radius: 999px !important; font-size: 12.5px !important; font-weight: 600 !important; color: var(--c-muted,#94a3b8) !important; min-height: auto !important; text-transform: none !important; }
.rag-pill-tabs .q-tab--active { color: #fff !important; background-image: linear-gradient(#0c0a1e,#0c0a1e),linear-gradient(90deg,#f97316,#ec4899,#8b5cf6) !important; background-origin: border-box !important; background-clip: padding-box,border-box !important; border: 1px solid transparent !important; box-shadow: 0 4px 18px rgba(236,72,153,0.20) !important; }
.rag-pill-tabs .q-tab__indicator { display: none !important; }
.rag-pill-tabs .q-tab__label { font-size: 12.5px; font-weight: 600; }
.q-table { background: #120e28 !important; color: #e2e8f0 !important; }
.q-table thead tr th { background: #16103a !important; color: #94a3b8 !important; font-size: 0.7rem; letter-spacing: 0.06em; border-bottom: 1px solid #241d4a !important; }
.q-table tbody tr td { border-bottom: 1px solid #1e163c !important; font-size: 0.82rem; }
.q-table tbody tr:hover td { background: #1e163c !important; }
@keyframes rag-pulse {
  0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
  40%            { opacity: 1;   transform: scale(1);   }
}
@keyframes rag-dot-color {
  0%   { background: #f97316; }
  33%  { background: #ec4899; }
  66%  { background: #8b5cf6; }
  100% { background: #f97316; }
}
.rag-thinking-dot {
  width: 7px; height: 7px; border-radius: 50%;
  display: inline-block;
  animation: rag-pulse 1.4s ease-in-out infinite, rag-dot-color 3s linear infinite;
}
.rag-thinking-dot:nth-child(2) { animation-delay: 0.2s, 1s; }
.rag-thinking-dot:nth-child(3) { animation-delay: 0.4s, 2s; }
.rag-thinking-label {
  font-size: 0.8rem;
  background: linear-gradient(135deg,#f97316,#ec4899);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text; font-style: italic; line-height: 1;
}
.q-header .q-btn:hover { color: #e2e8f0; transition: color 0.15s ease; }
.q-linear-progress { height: 4px !important; border-radius: 2px !important; }
.rag-mastery-chip {
  border-radius: 20px; padding: 0.2rem 0.75rem; font-size: 0.72rem;
  font-weight: 600; display: inline-block;
}
.rag-health-chip {
  border-radius: 20px; padding: 0.1rem 0.6rem; font-size: 0.7rem; display: inline-block;
}
.rag-brand-name {
  font-size: 1.35rem; font-weight: 700; letter-spacing: -0.02em;
  font-family: 'Inter', system-ui;
  background: linear-gradient(135deg, #f97316 0%, #ec4899 50%, #8b5cf6 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text; line-height: 1;
}

/* Layout engine */
html, body {
  height: 100vh !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
}
.q-layout {
  height: 100vh !important;
  display: flex !important;
  flex-direction: column !important;
  overflow: hidden !important;
}
.q-header {
  position: relative !important;
  flex-shrink: 0 !important;
}
.q-page-container {
  flex: 1 1 auto !important;
  min-height: 0 !important;
  display: flex !important;
  flex-direction: column !important;
  overflow: hidden !important;
  padding-top: 0 !important;
}
.q-page {
  padding: 0 !important;
  display: flex !important;
  flex-direction: column !important;
  height: 100% !important;
  min-height: 0 !important;
  overflow: hidden !important;
}
.nicegui-content {
  display: flex !important;
  flex-direction: column !important;
  height: 100% !important;
  min-height: 0 !important;
  overflow: hidden !important;
  padding: 0 !important;
}
.q-tab-panels {
  flex: 1 1 auto !important;
  min-height: 0 !important;
  overflow: hidden !important;
}
.q-panel {
  height: 100% !important;
  min-height: 0 !important;
  overflow: hidden !important;
}
.q-tab-panel {
  height: 100% !important;
  min-height: 0 !important;
  padding: 0 !important;
}
.rag-profile-sidebar .q-linear-progress {
  height: 4px !important; min-height: 4px !important;
  border-radius: 3px !important; flex-shrink: 0 !important; overflow: hidden !important;
}
.rag-profile-sidebar .q-linear-progress__track {
  background: rgba(36,29,74,0.6) !important; border: none !important;
  border-radius: 3px !important; opacity: 1 !important;
}
.rag-profile-sidebar .q-linear-progress__model {
  background: linear-gradient(90deg, #f97316, #ec4899, #8b5cf6, #38bdf8) !important;
  border-radius: 3px !important;
  box-shadow: 0 0 8px rgba(236,72,153,0.28) !important;
}
/* Mastery chip classes */
.mastery-chip {
  display:inline-flex; align-items:center; gap:8px; align-self:flex-start;
  padding:7px 14px; border-radius:999px;
  font-family:'Inter',system-ui; font-size:12px; font-weight:600;
  text-transform:uppercase; letter-spacing:0.08em;
}
.mastery-chip::before { content:""; width:6px; height:6px; border-radius:50%; display:inline-block; }
.mc-novice { background:rgba(148,163,184,0.10); color:#cbd5e1; border:1px solid rgba(148,163,184,0.28); }
.mc-novice::before { background:#94a3b8; }
.mc-intermediate { background:rgba(249,115,22,0.10); color:#fb923c; border:1px solid rgba(249,115,22,0.34); box-shadow:0 0 18px rgba(249,115,22,0.12); }
.mc-intermediate::before { background:#f97316; }
.mc-advanced { background:rgba(236,72,153,0.10); color:#f472b6; border:1px solid rgba(236,72,153,0.36); box-shadow:0 0 22px rgba(236,72,153,0.18); }
.mc-advanced::before { background:#ec4899; }
.mc-expert { background:rgba(139,92,246,0.12); color:#a78bfa; border:1px solid rgba(139,92,246,0.45); box-shadow:0 0 24px rgba(139,92,246,0.32),inset 0 0 14px rgba(139,92,246,0.10); }
.mc-expert::before { background:#8b5cf6; box-shadow:0 0 10px rgba(139,92,246,0.7); }

/* Chat input */
.rag-chat-input .q-field__control { background: transparent !important; border-radius: 0 !important; min-height: 36px !important; }
.rag-chat-input.q-field--outlined .q-field__control:before { border: none !important; box-shadow: none !important; }
.rag-chat-input .q-field__native { color: #e2e8f0 !important; padding: 0 !important; font-size: 14.5px !important; }
.rag-chat-input .q-field__placeholder { color: #64748b !important; }
.rag-chat-input .q-field__bottom { display: none !important; }

/* Send button — sunset gradient */
.rag-send-btn {
  background: linear-gradient(135deg, #f97316, #ec4899) !important;
  border-radius: 50% !important;
  width: 40px !important; height: 40px !important; min-width: 40px !important;
  flex-shrink: 0;
  box-shadow: 0 6px 28px rgba(236,72,153,0.55);
  transition: box-shadow 0.2s, transform 0.15s;
}
.rag-send-btn:not(.disabled):hover {
  box-shadow: 0 8px 36px rgba(236,72,153,0.75) !important;
  transform: scale(1.06) !important;
}
.rag-send-btn.disabled { opacity: 0.45 !important; box-shadow: none !important; cursor: not-allowed; }

/* MCQ option row hover */
.rag-mcq-row { transition: border-color 0.15s; }
.rag-mcq-row:hover { border-color: rgba(236,72,153,0.4) !important; }

/* Onboarding level row hover */
.rag-ob-level-row:hover { background: #2a1d56 !important; border-color: rgba(139,92,246,0.4) !important; transition: background 0.15s, border-color 0.15s; }

/* Chat bubble — strip p margins so label sits tight against text */
.rag-bubble-card .nicegui-markdown p:first-child { margin-top: 0 !important; }
.rag-bubble-card .nicegui-markdown p:last-child { margin-bottom: 0 !important; }
.rag-bubble-card .nicegui-markdown p { margin: 0.25em 0 !important; }

/* Sign out button — primary gradient pill with pink glow */
.rag-signout-btn.q-btn {
  background: linear-gradient(135deg, #f97316, #ec4899) !important;
  border-radius: 8px !important;
  padding: 0 14px !important;
  height: 32px !important;
  font-size: 0.75rem !important;
  font-weight: 600 !important;
  box-shadow: 0 4px 18px rgba(236,72,153,0.55) !important;
  transition: box-shadow 0.2s, transform 0.15s !important;
}
.rag-signout-btn.q-btn .q-btn__content { color: #fff !important; }
.rag-signout-btn.q-btn:hover { box-shadow: 0 6px 28px rgba(236,72,153,0.75) !important; transform: scale(1.04) !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #120e28; }
::-webkit-scrollbar-thumb { background: rgba(139,92,246,0.5); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(236,72,153,0.75); }
* { scrollbar-width: thin; scrollbar-color: rgba(139,92,246,0.6) #120e28; }

</style>
""")

        ui.add_head_html("""
<svg width="0" height="0" style="position:absolute;overflow:hidden">
  <defs>
    <linearGradient id="tg" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0" stop-color="#f97316"/>
      <stop offset="0.5" stop-color="#ec4899"/>
      <stop offset="1" stop-color="#8b5cf6"/>
    </linearGradient>
  </defs>
</svg>
""")

        ui.add_head_html("""
<style>
.sb-tabs{display:flex;gap:22px;border-bottom:1px solid rgba(255,255,255,0.07);margin-top:-4px;}
.sb-tab{position:relative;font-family:'Inter',system-ui,sans-serif;font-size:12.5px;font-weight:600;letter-spacing:0.02em;padding:8px 0 12px;background:transparent;border:0;cursor:pointer;color:#94a3b8;transition:color 160ms ease-out;user-select:none;outline:none;margin:0;}
.sb-tab:hover{color:#f8fafc;}
.sb-tab.active{color:#fb923c;}
.sb-tab.active::after{content:"";position:absolute;left:0;right:0;bottom:-1px;height:2px;border-radius:2px;background:linear-gradient(90deg,#f97316,#ec4899,#8b5cf6);box-shadow:0 0 12px rgba(236,72,153,0.45);}
</style>
""")

        ui.add_head_html("""
<style>
@keyframes rag-phase-unlock {
  0%   { box-shadow: 0 0 0 rgba(134,239,172,0); }
  40%  { box-shadow: 0 0 20px rgba(134,239,172,0.45); }
  100% { box-shadow: 0 0 0 rgba(134,239,172,0); }
}
.rag-phase-unlocked {
  animation: rag-phase-unlock 2.5s ease-out forwards;
}
</style>
""")

        bearer_ok = await verify_stored_bearer()
        can_use_chat = settings.allow_anonymous_chat or bearer_ok

        # Fetch profile once for the personalized welcome — sidebar re-fetches independently
        _welcome_profile: dict | None = None
        if bearer_ok:
            try:
                _r = await http().get("/api/profile/me", headers=auth_headers())
                if _r.status_code == 200:
                    _welcome_profile = _r.json()
            except Exception:
                pass

        # ---- Onboarding wizard ----
        _ob_step = [1]            # 1=self-report, 2=mcq, 3=result
        _ob_self_level = ["beginner"]
        _ob_answers: list = [[]]  # accumulates answers
        _ob_questions: list = [[]]
        _ob_placement: list = [{}]

        onboarding_dialog = ui.dialog().props("persistent")

        async def _ob_skip():
            try:
                await http().post(
                    "/api/onboarding/complete",
                    json={"level": _ob_self_level[0], "answers": [], "skipped": True},
                    headers=auth_headers(),
                )
            except Exception:
                pass
            onboarding_dialog.close()

        async def _ob_select_level(level: str):
            _ob_self_level[0] = level
            _ob_answers[0] = []
            try:
                r = await http().post(
                    "/api/onboarding/diagnostic",
                    json={"level": level},
                    headers=auth_headers(),
                )
                data = r.json() if r.status_code == 200 else {}
            except Exception:
                data = {}
            _ob_questions[0] = data.get("questions", [])
            _ob_step[0] = 2
            ob_step_content.refresh()

        async def _ob_select_answer(letter: str):
            _ob_answers[0].append(letter)
            n_questions = len(_ob_questions[0])
            if len(_ob_answers[0]) >= n_questions or len(_ob_answers[0]) >= 3:
                try:
                    r = await http().post(
                        "/api/onboarding/complete",
                        json={
                            "level": _ob_self_level[0],
                            "answers": _ob_answers[0],
                            "skipped": False,
                        },
                        headers=auth_headers(),
                    )
                    _ob_placement[0] = r.json() if r.status_code == 200 else {}
                except Exception:
                    _ob_placement[0] = {}
                _ob_step[0] = 3
            ob_step_content.refresh()

        def _ob_finish():
            onboarding_dialog.close()
            profile_panel.refresh()

        with onboarding_dialog:
            with ui.card().style(
                "background:linear-gradient(160deg,#1e163c,#16103a); "
                "border:1px solid rgba(139,92,246,0.3); border-top:3px solid #f97316; "
                "border-radius:16px; padding:28px 28px 24px; width:480px; max-width:94vw; "
                "box-shadow:0 8px 48px rgba(139,92,246,0.25); gap:0"
            ):
                @ui.refreshable
                def ob_step_content():
                    if _ob_step[0] == 1:
                        # Step 1: self-report
                        ui.label("Welcome to RAG Tutor!").style(
                            "font-size:1.2rem; font-weight:700; color:#f97316; margin-bottom:6px"
                        )
                        ui.label("How familiar are you with RAG systems?").style(
                            "font-size:0.9rem; color:#94a3b8; margin-bottom:20px"
                        )
                        _levels = [
                            ("beginner",     "Beginner",     "Just starting out"),
                            ("intermediate", "Intermediate", "Some experience"),
                            ("expert",       "Expert",       "I've built RAG systems"),
                        ]
                        for _lv, _lv_label, _lv_sub in _levels:
                            with ui.row().style(
                                "align-items:center; gap:12px; width:100%; "
                                "background:#231848; border:1px solid rgba(139,92,246,0.2); "
                                "border-radius:10px; padding:12px 14px; cursor:pointer; margin-bottom:8px"
                            ).classes("rag-ob-level-row").on(
                                "click",
                                lambda _e, _l=_lv: asyncio.ensure_future(_ob_select_level(_l))
                            ):
                                with ui.column().style("gap:2px; flex:1"):
                                    ui.label(_lv_label).style("font-size:0.9rem; font-weight:600; color:#f8fafc")
                                    ui.label(_lv_sub).style("font-size:0.78rem; color:#64748b")
                        ui.label("Skip for now").style(
                            "font-size:0.82rem; color:#64748b; text-align:right; "
                            "cursor:pointer; margin-top:8px; width:100%"
                        ).on("click", lambda: asyncio.ensure_future(_ob_skip()))

                    elif _ob_step[0] == 2:
                        # Step 2: diagnostic MCQ
                        questions = _ob_questions[0]
                        qi = len(_ob_answers[0])
                        total = min(len(questions), 3)

                        ui.label(f"Question {qi + 1} of {total}").style(
                            "font-size:0.72rem; font-weight:600; text-transform:uppercase; "
                            "letter-spacing:0.1em; color:#94a3b8; margin-bottom:12px"
                        )

                        if qi < len(questions):
                            raw_q = questions[qi]
                            raw_text = raw_q["text"] if isinstance(raw_q, dict) else raw_q
                            lines = raw_text.strip().splitlines()
                            q_text = lines[0] if lines else ""
                            opt_lines = [l for l in lines[1:] if len(l) >= 3 and l[0] in "ABCD" and l[1] == "."]

                            ui.label(q_text).style(
                                "font-size:0.9rem; color:#e2e8f0; line-height:1.5; margin-bottom:16px"
                            )

                            _letters = ["A", "B", "C", "D"]
                            for _li, _letter in enumerate(_letters):
                                _opt_text = opt_lines[_li][3:].strip() if _li < len(opt_lines) else ""
                                with ui.row().style(
                                    "align-items:center; gap:0; width:100%; margin-bottom:6px; "
                                    "background:#1a1238; border:1px solid rgba(139,92,246,0.2); "
                                    "border-radius:10px; overflow:hidden; cursor:pointer"
                                ).classes("rag-mcq-row").on(
                                    "click",
                                    lambda _e, _l=_letter: asyncio.ensure_future(_ob_select_answer(_l))
                                ):
                                    ui.label(_letter).style(
                                        "width:36px; min-width:36px; height:100%; min-height:42px; "
                                        "display:flex; align-items:center; justify-content:center; "
                                        "font-family:ui-monospace,monospace; font-size:11px; font-weight:700; "
                                        "color:#fff; flex-shrink:0; "
                                        "background:linear-gradient(135deg,#f97316,#ec4899,#8b5cf6)"
                                    )
                                    ui.label(_opt_text).style(
                                        "flex:1; padding:10px 14px; font-size:0.875rem; "
                                        "color:#e2e8f0; line-height:1.45"
                                    )

                        ui.label("Skip for now").style(
                            "font-size:0.82rem; color:#64748b; text-align:right; "
                            "cursor:pointer; margin-top:8px; width:100%"
                        ).on("click", lambda: asyncio.ensure_future(_ob_skip()))

                    else:
                        # Step 3: result
                        placement = _ob_placement[0]
                        confirmed = placement.get("confirmed_level", _ob_self_level[0])
                        correct = placement.get("correct_count", 0)
                        msg = placement.get("message", "")
                        phase_num, phase_name = _PHASE_LABELS.get(confirmed, ("Phase 1", "Foundation"))
                        phase_topics = _PHASE_TOPICS.get(confirmed, [])

                        with ui.row().style("align-items:center; gap:8px; margin-bottom:14px"):
                            ui.html(rag_icon("check-circuit", 20, "#22c55e"))
                            ui.label(f"You're placed at: {confirmed.capitalize()}").style(
                                "font-size:1.05rem; font-weight:700; color:#22c55e"
                            )

                        ui.label(f"You got {correct} out of 3 questions right.").style(
                            "font-size:0.875rem; color:#94a3b8; margin-bottom:4px"
                        )
                        if msg:
                            ui.label(msg).style("font-size:0.875rem; color:#94a3b8; margin-bottom:14px")

                        if phase_topics:
                            ui.label(f"You'll start with {phase_num} topics:").style(
                                "font-size:0.82rem; font-weight:600; color:#e2e8f0; margin-bottom:6px"
                            )
                            for _slug in phase_topics:
                                ui.label(f"· {_MODULE_LABELS.get(_slug, _slug.replace('_', ' ').title())}").style(
                                    "font-size:0.82rem; color:#94a3b8; margin-left:6px"
                                )
                        else:
                            ui.label("All phases complete — keep sharpening your skills.").style(
                                "font-size:0.82rem; color:#94a3b8; margin-bottom:6px"
                            )

                        ui.button("Start learning", on_click=_ob_finish).props("unelevated no-caps").style(
                            "background:linear-gradient(135deg,#f97316,#ec4899,#8b5cf6) !important; "
                            "color:white !important; width:100%; border-radius:999px; font-weight:600; "
                            "min-height:44px; font-size:0.95rem; box-shadow:0 4px 24px rgba(236,72,153,0.4); "
                            "margin-top:20px"
                        )

                ob_step_content()

        # Check onboarding status and open dialog if needed
        if bearer_ok:
            try:
                _ob_status = await http().get("/api/onboarding/status", headers=auth_headers())
                if _ob_status.status_code == 200 and _ob_status.json().get("needed"):
                    onboarding_dialog.open()
            except Exception:
                pass

        def logout():
            app.storage.user.clear()
            ui.navigate.to("/")

        with ui.header().style(
            "background:#0c0a1e; border-bottom:1px solid #241d4a; padding:0; position:relative; height:64px"
        ):
            with ui.row().style(
                "width:100%; height:100%; justify-content:space-between; align-items:center; padding:0 24px"
            ):
                # LEFT: brand + tabs
                with ui.row().style("align-items:center; gap:32px"):
                    with ui.row().style("align-items:center; gap:10px"):
                        ui.label("R").style(
                            "width:32px; height:32px; border-radius:8px; flex-shrink:0; "
                            "background: radial-gradient(120% 120% at 30% 25%, rgba(255,255,255,0.18), transparent 60%),"
                            "linear-gradient(135deg,#f97316,#ec4899,#8b5cf6); "
                            "display:inline-flex; align-items:center; justify-content:center; "
                            "font-family:'Inter',system-ui; font-weight:800; color:#fff; font-size:16px; "
                            "box-shadow:0 4px 18px rgba(236,72,153,0.35); letter-spacing:-0.02em"
                        )
                        ui.html('<span class="rag-brand-name">RAG Tutor</span>')
                    with ui.tabs().props("dense indicator-color=transparent").classes("rag-pill-tabs") as tabs:
                        chat_tab = ui.tab("Learn").props("no-caps")
                        admin_tab = ui.tab("System").props("no-caps")
                # RIGHT: user pill + sign out
                with ui.row().style("align-items:center; gap:14px"):
                    _user_store = {k: app.storage.user.get(k) for k in ("user_id", "email")}
                    uid = _user_store["user_id"]
                    if uid:
                        _email_val = _user_store["email"] or f"id …{uid[-8:]}"
                        _initials = _email_val.split("@")[0][:2].upper()
                        with ui.row().style(
                            "align-items:center; gap:6px; background:rgba(255,255,255,0.06); "
                            "border:1px solid #241d4a; border-radius:999px; "
                            "padding:3px 10px 3px 4px; font-family:Inter,system-ui"
                        ):
                            ui.label(_initials).style(
                                "width:22px; height:22px; border-radius:50%; "
                                "background:linear-gradient(135deg,#8b5cf6,#38bdf8); "
                                "color:white; font-size:0.6rem; font-weight:700; "
                                "display:flex; align-items:center; justify-content:center; flex-shrink:0"
                            )
                            ui.label(_email_val).style("font-size:0.72rem; color:#94a3b8")
                        ui.button("Sign out", on_click=logout).classes("rag-signout-btn").props("unelevated dense no-caps").style(
                            "background:linear-gradient(135deg,#f97316,#ec4899) !important; "
                            "box-shadow:0 4px 18px rgba(236,72,153,0.55) !important; "
                            "border-radius:8px !important; height:32px !important; "
                            "font-size:0.75rem !important; font-weight:600 !important"
                        )
                    elif settings.allow_anonymous_chat:
                        ui.label("Anonymous demo").style("font-size:0.75rem; color:#64748b")
                        ui.link("Sign in", "/login").classes("text-sky-400 text-sm")
                        ui.link("Register", "/register").classes("text-sky-400 text-sm")
            if not app.storage.user.get("is_admin", False):
                tabs.set_visibility(False)

        if not can_use_chat:
            ui.navigate.to("/landing")
            return

        session = create_session()

        with ui.tab_panels(tabs, value=chat_tab).classes("w-full").style(
            "flex:1; min-height:0; overflow:hidden"
        ):
            # ------------------------------------------------------------------ Chat tab
            with ui.tab_panel(chat_tab).style(
                "padding: 0; height: 100%; overflow: hidden; display: flex; flex-direction: column;"
            ):
                
                # 1. Main Content Container Row (Knowledge Profile & Messaging Space)
                # flex:1 forces it to consume every available layout pixel without ever bleeding over
                with ui.row().style("width: 100%; flex: 1; min-height: 0; gap: 0; overflow: hidden; align-items: stretch;"):
                    # --- Profile sidebar ---
                    _tab_state = ["Current"]
                    _prev_mastery: list = [None]

                    def _switch_tab(name: str) -> None:
                        _tab_state[0] = name
                        profile_panel.refresh()

                    _sidebar_shell = ui.element("div").style(
                        "width:320px; min-width:320px; flex:0 0 320px; height:100%; "
                        "background:#16103a; border-right:1px solid #241d4a; overflow:hidden"
                    )
                    @ui.refreshable
                    async def profile_panel():
                        with ui.column().classes("rag-profile-sidebar").style(
                            "width:320px; min-width:320px; flex:0 0 320px; height:100%; box-sizing:border-box; "
                            "background:#16103a; border-right:1px solid #241d4a; "
                            "box-shadow:inset 0 0 60px rgba(139,92,246,0.04); "
                            "padding:24px 22px; gap:0; overflow-y:auto; display:flex; flex-direction:column"
                        ):
                            headers = auth_headers()
                            if not headers:
                                ui.label("Sign in to track your progress.").style("font-size:0.8rem; color:#64748b")
                                return

                            try:
                                r = await http().get("/api/profile/me", headers=headers)
                                if r.status_code != 200:
                                    raise ValueError(f"status {r.status_code}")
                                profile = r.json()
                            except Exception:
                                ui.label("Profile unavailable.").style("font-size:0.8rem; color:#94a3b8")
                                return

                            mastery_raw = profile.get("mastery_level") or "novice"
                            mastery = mastery_raw if mastery_raw in {"novice", "beginner", "intermediate", "advanced", "expert"} else "novice"
                            _gate_crossed = _prev_mastery[0] is not None and mastery != _prev_mastery[0]
                            _prev_mastery[0] = mastery
                            topic_scores: dict = profile.get("topic_scores") or {}
                            interaction_count = profile.get("interaction_count", 0)
                            last_activity = profile.get("last_activity_at")

                            # Build modules list from _ALL_MODULES
                            active_idx = _ACTIVE_MODULE_IDX.get(mastery, 0)
                            modules = []
                            for i, m in enumerate(_ALL_MODULES):
                                is_locked = i > active_idx
                                topic_items = []
                                for slug in m["topics"]:
                                    score = topic_scores.get(slug)
                                    done = score is not None and score >= 0.70
                                    topic_items.append({
                                        "slug": slug,
                                        "name": _MODULE_LABELS.get(slug, slug.replace("_", " ").title()),
                                        "done": done,
                                    })
                                done_count = sum(1 for t in topic_items if t["done"])
                                modules.append({
                                    "num": m["num"],
                                    "name": m["name"],
                                    "topics": topic_items,
                                    "done_count": done_count,
                                    "locked": is_locked,
                                })
                            active_module = modules[active_idx]

                            # --- Mastery section (always shown) ---
                            with ui.column().style("gap:10px; margin-bottom:16px"):
                                ui.html(f'<span class="mastery-chip mc-{mastery}"><span class="dot"></span>{mastery.capitalize()}</span>')
                                _mastery_copy = {
                                    "novice":       "Just getting started — great time to build foundations.",
                                    "beginner":     "Just getting started — great time to build foundations.",
                                    "intermediate": "You've got the core. Time to go deeper.",
                                    "advanced":     "Strong foundations. Let's tackle production complexity.",
                                    "expert":       "You're in the top tier. Ask me anything.",
                                }
                                ui.label(_mastery_copy.get(mastery, _mastery_copy["novice"])).style(
                                    "font-family:'Inter',system-ui; font-size:12.5px; color:#94a3b8; line-height:1.5"
                                )

                            # --- Tab bar ---
                            active_tab = _tab_state[0]
                            with ui.element("div").classes("sb-tabs").style("margin-bottom:16px; flex-shrink:0"):
                                for tab_name in ("Current", "Overview"):
                                    tab_cls = "sb-tab active" if active_tab == tab_name else "sb-tab"
                                    ui.label(tab_name).classes(tab_cls).on(
                                        "click", lambda n=tab_name: _switch_tab(n)
                                    )

                            # --- Tab content ---
                            if active_tab == "Current":
                                # Current tab — active module + topics
                                done_count = active_module["done_count"]
                                total_count = len(active_module["topics"])
                                pct = (done_count / total_count * 100) if total_count else 0

                                with ui.element("div").style("display:flex; flex-direction:column; gap:0; flex:1; width:100%"):
                                    # cur-head
                                    with ui.element("div").style("display:flex; flex-direction:column; gap:4px; margin-bottom:14px; width:100%"):
                                        with ui.element("div").style("display:flex; gap:4px; align-items:baseline"):
                                            ui.label("Active module").style(
                                                "font-family:ui-monospace,monospace; font-size:10.5px; "
                                                "text-transform:uppercase; letter-spacing:0.1em; color:#94a3b8"
                                            )
                                            ui.label("·").style("color:#94a3b8; font-size:10.5px")
                                            ui.label(active_module["num"]).style(
                                                "font-family:ui-monospace,monospace; font-size:10.5px; "
                                                "text-transform:uppercase; letter-spacing:0.1em; color:#94a3b8"
                                            )
                                        ui.label(active_module["name"]).style(
                                            "font-family:'Inter',system-ui; font-size:15px; font-weight:700; "
                                            "color:#f8fafc; letter-spacing:-0.01em; line-height:1.3; margin:0"
                                        )

                                    # cur-progress
                                    with ui.element("div").style("display:flex; align-items:center; gap:10px; margin-bottom:16px; width:100%"):
                                        with ui.element("div").style(
                                            "flex:1; height:6px; background:rgba(36,29,74,0.6); "
                                            "border-radius:999px; overflow:hidden"
                                        ):
                                            ui.element("div").style(
                                                f"height:100%; width:{pct:.1f}%; "
                                                "background:linear-gradient(90deg,#f97316,#ec4899,#8b5cf6); "
                                                "box-shadow:0 0 10px rgba(236,72,153,0.35); border-radius:inherit"
                                            )
                                        ui.label(f"{done_count} / {total_count}").style(
                                            "font-family:ui-monospace,monospace; font-size:11.5px; color:#e2e8f0; "
                                            "letter-spacing:0.02em; min-width:38px; text-align:right"
                                        )

                                    # topic-list
                                    _any_score = any(topic_scores.get(t["slug"]) is not None for t in active_module["topics"])
                                    with ui.element("div").style("display:flex; flex-direction:column; gap:9px; width:100%"):
                                        for t in active_module["topics"]:
                                            score = topic_scores.get(t["slug"])
                                            score_text = f"{score:.0%}" if score is not None else "—"
                                            score_color = "#86efac" if t["done"] else ("#94a3b8" if score is not None else "#475569")
                                            name_color = "#e2e8f0" if t["done"] else "#94a3b8"
                                            with ui.element("div").style(
                                                "display:flex; align-items:center; gap:10px; "
                                                "font-family:'Inter',system-ui; font-size:12.5px; line-height:1.4"
                                            ):
                                                if t["done"]:
                                                    ui.html(
                                                        '<svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true" style="flex:0 0 14px">'
                                                        '<circle cx="8" cy="8" r="7" fill="url(#tg)"/>'
                                                        '<path d="M4.5 8.2 L7 10.6 L11.5 5.8" fill="none" stroke="#fff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'
                                                        '</svg>'
                                                    )
                                                else:
                                                    ui.html(
                                                        '<svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true" style="flex:0 0 14px;color:#475569">'
                                                        '<circle cx="8" cy="8" r="6.5" fill="none" stroke="currentColor" stroke-width="1.2"/>'
                                                        '<circle cx="8" cy="8" r="2" fill="currentColor"/>'
                                                        '</svg>'
                                                    )
                                                ui.label(t["name"]).style(f"color:{name_color}; flex:1")
                                                ui.label(score_text).style(
                                                    f"font-family:ui-monospace,monospace; font-size:11px; color:{score_color}"
                                                )
                                    if not _any_score:
                                        ui.label("Ask a question to start tracking your progress on this module.").style(
                                            "font-family:'Inter',system-ui; font-size:11px; color:#64748b; "
                                            "font-style:italic; margin-top:10px; line-height:1.5"
                                        )


                            else:
                                # Overview tab — all modules summary
                                completed_mods = sum(
                                    1 for m in modules
                                    if not m["locked"] and all(t["done"] for t in m["topics"])
                                )
                                total_mods = len(modules)
                                overall_pct = (completed_mods / total_mods * 100) if total_mods else 0

                                with ui.element("div").style("display:flex; flex-direction:column; gap:0; flex:1; width:100%"):
                                    # Overall progress summary card
                                    with ui.element("div").style(
                                        "padding:12px 14px; background:rgba(20,14,50,0.5); "
                                        "border:1px solid rgba(255,255,255,0.07); border-radius:8px; "
                                        "margin-bottom:18px; display:flex; flex-direction:column; gap:8px; width:100%"
                                    ):
                                        with ui.element("div").style("display:flex; justify-content:space-between; align-items:baseline; width:100%"):
                                            ui.label("Overall progress").style(
                                                "font-family:'Inter',system-ui; font-size:11px; font-weight:600; "
                                                "text-transform:uppercase; letter-spacing:0.1em; color:#94a3b8"
                                            )
                                            ui.label(f"{completed_mods} / {total_mods} modules").style(
                                                "font-family:ui-monospace,monospace; font-size:11px; color:#f8fafc"
                                            )
                                        with ui.element("div").style(
                                            "height:4px; background:rgba(36,29,74,0.6); "
                                            "border-radius:999px; overflow:hidden; width:100%"
                                        ):
                                            ui.element("div").style(
                                                f"height:100%; width:{overall_pct:.1f}%; "
                                                "background:linear-gradient(90deg,#f97316,#ec4899,#8b5cf6); "
                                                "border-radius:inherit"
                                            )

                                    # Phase lock labels keyed by module index
                                    _phase_labels: list[str] = ["Phase 1 — Foundations", "Phase 2 — Core Components", "Phase 3 — Production"]
                                    _phase_unlock_hints: list[str] = ["", "Pass Phase 1 to unlock", "Pass Phase 2 to unlock"]

                                    # Phase rows — locked/unlocked state
                                    with ui.element("div").style("display:flex; flex-direction:column; gap:14px; width:100%"):
                                        for phase_idx, m in enumerate(modules):
                                            is_locked = m["locked"]
                                            d = m["done_count"]
                                            total = len(m["topics"])
                                            pct = (d / total * 100) if total else 0

                                            # detect newly unlocked phase for celebration
                                            newly_unlocked = _gate_crossed and not is_locked and phase_idx == active_idx
                                            phase_extra_class = "rag-phase-unlocked" if newly_unlocked else ""

                                            block_opacity = "opacity:0.4;" if is_locked else ""
                                            block_style = (
                                                f"display:flex; flex-direction:column; gap:6px; width:100%; "
                                                f"border-radius:6px; padding:8px 10px; box-sizing:border-box; "
                                                f"background:rgba(20,14,50,0.35); {block_opacity}"
                                            )

                                            with ui.element("div").classes(phase_extra_class).style(block_style):
                                                # Phase header row
                                                with ui.element("div").style(
                                                    "display:flex; align-items:center; gap:8px; width:100%"
                                                ):
                                                    if is_locked:
                                                        ui.html(
                                                            '<svg width="12" height="14" viewBox="0 0 12 14" aria-hidden="true" style="flex:0 0 12px">'
                                                            '<rect x="2" y="6" width="8" height="7" rx="1.5" fill="#475569"/>'
                                                            '<path d="M3.5 6V4.5a2.5 2.5 0 0 1 5 0V6" fill="none" stroke="#475569" stroke-width="1.4" stroke-linecap="round"/>'
                                                            '</svg>'
                                                        )
                                                    ui.label(_phase_labels[phase_idx]).style(
                                                        "font-family:'Inter',system-ui; font-size:12px; font-weight:600; "
                                                        "color:" + ("#475569" if is_locked else "#e2e8f0") + "; flex:1"
                                                    )
                                                    if not is_locked:
                                                        ui.label(f"{d}/{total}").style(
                                                            "font-family:ui-monospace,monospace; font-size:11px; color:#94a3b8"
                                                        )

                                                # Unlock hint or progress bar
                                                if is_locked:
                                                    ui.label(_phase_unlock_hints[phase_idx]).style(
                                                        "font-family:'Inter',system-ui; font-size:11px; color:#475569; "
                                                        "font-style:italic; padding-left:20px"
                                                    )
                                                    # Topic names dimmed, no scores
                                                    with ui.element("div").style("display:flex; flex-direction:column; gap:4px; padding-left:20px; padding-top:2px"):
                                                        for t in m["topics"]:
                                                            ui.label(t["name"]).style(
                                                                "font-family:'Inter',system-ui; font-size:11.5px; color:#334155"
                                                            )
                                                else:
                                                    # Progress bar
                                                    with ui.element("div").style(
                                                        "height:3px; background:rgba(36,29,74,0.6); "
                                                        "border-radius:999px; overflow:hidden; width:100%"
                                                    ):
                                                        ui.element("div").style(
                                                            f"height:100%; width:{pct:.1f}%; "
                                                            "background:linear-gradient(90deg,#f97316,#ec4899,#8b5cf6); "
                                                            "border-radius:inherit"
                                                        )
                                                    # Topic list — structural map, no scores
                                                    with ui.element("div").style("display:flex; flex-direction:column; gap:4px; padding-top:2px"):
                                                        for t in m["topics"]:
                                                            ui.label(t["name"]).style(
                                                                "font-family:'Inter',system-ui; font-size:11.5px; "
                                                                "color:" + ("#86efac" if t["done"] else "#94a3b8")
                                                            )

                            # --- Stats footer (always shown) ---
                            with ui.column().style(
                                "gap:6px; padding-top:16px; margin-top:auto; "
                                "border-top:1px solid rgba(255,255,255,0.07); width:100%"
                            ):
                                with ui.row().style("justify-content:space-between; width:100%"):
                                    ui.label("questions asked").style(
                                        "font-family:ui-monospace,monospace; font-size:11px; color:#94a3b8"
                                    )
                                    ui.label(str(interaction_count)).style(
                                        "font-family:ui-monospace,monospace; font-size:11px; color:#e2e8f0; font-weight:500"
                                    )
                                if last_activity:
                                    last_str = (last_activity[:16].replace("T", " ") if len(last_activity) >= 16 else last_activity)
                                    with ui.row().style("justify-content:space-between; width:100%"):
                                        ui.label("last session").style(
                                            "font-family:ui-monospace,monospace; font-size:11px; color:#94a3b8"
                                        )
                                        ui.label(last_str).style(
                                            "font-family:ui-monospace,monospace; font-size:11px; color:#e2e8f0; font-weight:500"
                                        )

                    with _sidebar_shell:
                        await profile_panel()

                    # --- Chat column (scroll area + composer inside) ---
                    with ui.column().style("flex:1; min-height:0; overflow:hidden; position:relative; background:#120e28"):
                        # Scroll area — stops at bottom:108px, leaving room for the composer
                        with ui.column().classes("rag-scroll-area").style(
                            "position:absolute; top:0; left:0; right:0; bottom:108px; overflow-y:auto; "
                            "padding:32px 24px 24px; "
                            "background:radial-gradient(ellipse at 8% 92%, rgba(249,115,22,0.07) 0%, transparent 38%), "
                            "radial-gradient(ellipse at 92% 8%, rgba(139,92,246,0.07) 0%, transparent 38%), #120e28"
                        ):
                            chat_area = ui.column().style("max-width:760px; margin:0 auto; width:100%; gap:18px")
                            with chat_area:
                                with ui.card().style(
                                    "background:var(--c-card,#1e163c); border:1px solid var(--c-border,#241d4a); "
                                    "border-radius:12px; box-shadow:0 4px 28px rgba(139,92,246,0.12); "
                                    "backdrop-filter:blur(6px); padding:22px 24px"
                                ):
                                    _dn = app.storage.user.get("display_name") or None
                                    _welcome_msg = _build_welcome_message(_dn, _welcome_profile)
                                    ui.markdown(_welcome_msg).style(
                                        "font-size:0.9rem; color:#cbd5e1; line-height:1.6"
                                    )

                        # Composer — pinned to bottom, height ~108px
                        with ui.column().style(
                            "position:absolute; bottom:0; left:0; right:0; "
                            "padding:12px 24px 16px; "
                            "background:linear-gradient(0deg, #120e28 60%, transparent)"
                        ) as composer_wrap:
                            with ui.row().style(
                                "background:#231848; border:1px solid #241d4a; border-radius:16px; "
                                "padding:8px 8px 8px 16px; gap:10px; align-items:center; "
                                "max-width:760px; margin:0 auto; width:100%"
                            ) as composer_row:
                                question_input = ui.input(
                                    placeholder="Ask anything about RAG, embeddings, retrieval, LangChain…"
                                ).classes("rag-chat-input").props("outlined dense auto-grow").style("flex:1")
                                with ui.button().classes("rag-send-btn").props("unelevated").props('title="Send (Enter)"').style(
                                    "background:linear-gradient(135deg,#f97316,#ec4899) !important; "
                                    "border-radius:50%; width:40px; height:40px; min-width:40px; flex-shrink:0; "
                                    "display:inline-flex; align-items:center; justify-content:center; padding:0"
                                ) as send_btn:
                                    ui.html(rag_icon("send", 16, "#fff"))


            # ------------------------------------------------------------------ Admin tab
            with ui.tab_panel(admin_tab).style(
                "padding:0; overflow-y:auto; height:100%; background:#120e28"
            ):
                if not bearer_ok:
                    with ui.column().style("padding:2rem; gap:0.5rem"):
                        ui.label("Sign in to access admin panel.").style(
                            "font-size:0.9rem; color:#94a3b8"
                        )
                else:
                    current_uid = app.storage.user.get("user_id")

                    @ui.refreshable
                    async def admin_panel():
                        # Fetch users
                        try:
                            r_users = await http().get("/api/admin/users", headers=auth_headers())
                            if r_users.status_code != 200:
                                raise ValueError(f"status {r_users.status_code}")
                            users = r_users.json()
                        except Exception as exc:
                            users = []
                            users_error = str(exc)
                        else:
                            users_error = None

                        # Fetch aggregated service health (all dependencies + circuit breakers)
                        try:
                            r_health = await http().get("/api/health/services", headers=auth_headers())
                            health_data = r_health.json() if r_health.status_code == 200 else {}
                        except Exception:
                            health_data = {}

                        health_status = health_data.get("status", "unknown")
                        is_healthy = health_status.lower() == "healthy"

                        # ---- Page header strip ----
                        with ui.row().style(
                            "width:100%; background:#16103a; border-bottom:1px solid rgba(139,92,246,0.2); "
                            "padding:0.25rem .5rem; align-items:center; justify-content:space-between"
                        ):
                            with ui.column():
                                ui.label("Admin Dashboard").style(
                                    "font-size:1.1rem; font-weight:700; background:linear-gradient(135deg,#f97316,#ec4899);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text"
                                )
                            ui.button("Refresh", on_click=admin_panel.refresh).props("flat dense").style(
                                "color:#64748b"
                            )

                        # ---- Main content row ----
                        latest_join = "—"
                        if users:
                            raw_created = users[0].get("created_at") or ""
                            latest_join = raw_created[:10] if raw_created else "—"

                        with ui.row().style(
                            "width:100%; padding:1rem 2rem; gap:0; align-items:stretch; flex-wrap:wrap"
                        ):
                            # -- Left: Users table --
                            with ui.column().style("flex:1; min-width:280px; gap:0.6rem; padding-right:1.25rem"):
                                ui.label("Registered Users").style(
                                    "font-size:0.7rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.06em"
                                )

                                if users_error:
                                    ui.label(f"Could not load users: {users_error}").style(
                                        "font-size:0.85rem; color:#f87171"
                                    )
                                elif not users:
                                    ui.label("No registered users.").style(
                                        "font-size:0.85rem; color:#64748b; font-style:italic"
                                    )
                                else:
                                    columns = [
                                        {"name": "email", "label": "EMAIL", "field": "email", "align": "left"},
                                        {"name": "display_name", "label": "NAME", "field": "display_name", "align": "left"},
                                        {"name": "created_at", "label": "JOINED", "field": "created_at", "align": "left"},
                                        {"name": "actions", "label": "", "field": "id", "align": "right"},
                                    ]

                                    rows = []
                                    for user in users:
                                        raw_ca = user.get("created_at") or ""
                                        rows.append({
                                            "id": user["id"],
                                            "email": user["email"],
                                            "display_name": user.get("display_name") or "—",
                                            "created_at": raw_ca[:10] if raw_ca else "—",
                                            "is_self": user["id"] == current_uid,
                                        })

                                    table = ui.table(columns=columns, rows=rows).classes("w-full")
                                    table.add_slot("body-cell-actions", r"""
                                      <q-td :props="props">
                                        <q-btn v-if="props.row.is_self" flat dense disabled label="(you)"
                                               style="color:#64748b;font-size:0.75rem"/>
                                        <q-btn v-else flat dense label="Delete"
                                               style="color:#f87171;font-size:0.75rem"
                                               @click="$parent.$emit('delete', props.row)"/>
                                      </q-td>
                                    """)

                                    async def handle_delete(e):
                                        row = e.args
                                        uid = row["id"]
                                        email = row["email"]
                                        try:
                                            r = await http().delete(
                                                f"/api/admin/users/{uid}",
                                                headers=auth_headers(),
                                            )
                                            if r.status_code == 204:
                                                ui.notify(f"Deleted {email}", type="positive")
                                                admin_panel.refresh()
                                            elif r.status_code == 404:
                                                ui.notify("User not found", type="warning")
                                                admin_panel.refresh()
                                            else:
                                                ui.notify(f"Error {r.status_code}", type="negative")
                                        except Exception as exc:
                                            ui.notify(f"Network error: {exc}", type="negative")

                                    table.on("delete", handle_delete)

                            # Vertical divider
                            ui.element("div").style(
                                "width:1px; background:#1e3a5f; align-self:stretch; flex-shrink:0"
                            )

                            # -- Right: stat cards + system health --
                            with ui.column().style("flex:1; min-width:280px; gap:1rem; padding-left:1.25rem"):
                                # Stat cards — horizontal row
                                def stat_card(label_text, value_text, value_color, description, border_color="#ec4899"):
                                    with ui.column().style(
                                        "background:linear-gradient(135deg,#16103a,#1e163c); "
                                        f"border:1px solid #241d4a; border-top:2px solid {border_color}; border-radius:12px; "
                                        "padding:0.75rem 1rem; flex:1; gap:0.2rem"
                                    ):
                                        ui.label(label_text).style(
                                            "font-size:0.65rem; color:#64748b; letter-spacing:0.08em; text-transform:uppercase"
                                        )
                                        ui.label(value_text).style(
                                            f"font-size:1.4rem; font-weight:700; color:{value_color}"
                                        )
                                        ui.label(description).style(
                                            "font-size:0.7rem; color:#64748b"
                                        )

                                with ui.row().style("width:100%; gap:1rem; flex-wrap:wrap"):
                                    stat_card("USERS", str(len(users)), "#f97316", "registered", "#f97316")
                                    stat_card("LATEST JOIN", latest_join, "#ec4899", "most recent signup", "#ec4899")
                                    stat_card(
                                        "SYSTEM",
                                        "Healthy" if is_healthy else "Degraded",
                                        "#4ade80" if is_healthy else "#f87171",
                                        "all services",
                                        "#4ade80" if is_healthy else "#f87171",
                                    )

                                # System Health
                                with ui.column().style(
                                    "background:#16103a; border:1px solid rgba(139,92,246,0.2); border-radius:12px; "
                                    "padding:0.75rem 1rem; gap:0.6rem"
                                ):
                                    ui.label("SYSTEM HEALTH").style(
                                        "font-size:0.65rem; color:#64748b; letter-spacing:0.08em; text-transform:uppercase"
                                    )

                                    service_keys = ["api", "rag_pipeline", "vectorstore", "redis", "llm"]
                                    services_data = health_data.get("services", {})

                                    _chip_styles = {
                                        "healthy": "background:rgba(74,222,128,0.1);border:1px solid rgba(74,222,128,0.2);color:#4ade80",
                                        "ok": "background:rgba(74,222,128,0.1);border:1px solid rgba(74,222,128,0.2);color:#4ade80",
                                        "degraded": "background:rgba(251,191,36,0.1);border:1px solid rgba(251,191,36,0.2);color:#fbbf24",
                                        "unknown": "background:rgba(100,116,139,0.1);border:1px solid #475569;color:#64748b",
                                    }
                                    with ui.row().style("gap:0.75rem; flex-wrap:wrap"):
                                        for key in service_keys:
                                            svc_status = ""
                                            if services_data:
                                                svc_status = str(services_data.get(key, "")).lower()
                                            elif health_data:
                                                svc_status = health_status.lower() if key == "api" else "unknown"
                                            else:
                                                svc_status = "unknown"

                                            _norm = svc_status if svc_status in _chip_styles else "unknown"
                                            _chip_label = "Healthy" if _norm in ("healthy", "ok") else _norm.capitalize()

                                            with ui.column().style("align-items:center; gap:0.2rem"):
                                                ui.label(key.replace("_", " ").title()).style(
                                                    "font-size:0.7rem; color:#94a3b8"
                                                )
                                                ui.label(_chip_label).classes("rag-health-chip").style(
                                                    _chip_styles[_norm]
                                                )


                    await admin_panel()


        async def send_message(question: str):
            if not question:
                return

            send_btn.disable()

            with chat_area:
                _dn = app.storage.user.get("display_name") or app.storage.user.get("email", "You")
                _av = (_dn.split("@")[0] if "@" in _dn else _dn)[:2].upper()
                with ui.row().style("align-self:flex-end; gap:12px; align-items:flex-start"):
                    with ui.card().classes("rag-bubble-card").style(
                        "background:rgba(56,189,248,0.06); border:1px solid rgba(56,189,248,0.22); "
                        "border-radius:14px; word-break:break-word; overflow-wrap:break-word; overflow:hidden; "
                        "padding:12px 16px; max-width:600px"
                    ):
                        ui.label("YOU").style(
                            "font-family:ui-monospace,monospace; font-size:10px; color:#64748b; "
                            "text-transform:uppercase; letter-spacing:0.08em; margin-bottom:2px; "
                            "width:100%; text-align:right"
                        )
                        ui.label(question).style(
                            "font-size:14px; line-height:1.6; color:#e2e8f0; "
                            "word-break:break-word; overflow-wrap:break-word"
                        )
                    ui.label(_av).style(
                        "width:30px; height:30px; min-width:30px; border-radius:9px; flex-shrink:0; "
                        "background:linear-gradient(135deg,#8b5cf6,#38bdf8); "
                        "color:#fff; font-family:ui-monospace,monospace; font-size:11px; font-weight:700; "
                        "display:flex; align-items:center; justify-content:center"
                    )
                ui.run_javascript(
                    "var s=document.querySelector('.rag-scroll-area'); if(s) s.scrollTop=s.scrollHeight;"
                )

                stage_idx = [0]
                stage_active = [True]
                with ui.row().style(
                    "align-items:center; gap:12px; padding:4px 0"
                ) as thinking:
                    ui.label("RT").style(
                        "width:30px; height:30px; min-width:30px; border-radius:9px; flex-shrink:0; "
                        "background:linear-gradient(135deg,#f97316,#ec4899); "
                        "color:#fff; font-family:ui-monospace,monospace; font-size:11px; font-weight:700; "
                        "display:flex; align-items:center; justify-content:center; "
                        "box-shadow:0 0 14px rgba(236,72,153,0.32)"
                    )
                    ui.html('<span class="rag-thinking-dot"></span>'
                            '<span class="rag-thinking-dot"></span>'
                            '<span class="rag-thinking-dot"></span>')
                    _stage_label = ui.label(_STAGE_LABELS[0]).classes("rag-thinking-label")

                def _advance():
                    if not stage_active[0]:
                        return
                    stage_idx[0] = min(stage_idx[0] + 1, len(_STAGE_LABELS) - 1)
                    _stage_label.set_text(_STAGE_LABELS[stage_idx[0]])

                stage_timer = ui.timer(2.5, _advance)

            ui.update()
            await asyncio.sleep(0)

            # Pre-create the response card hidden; reveal on first token.
            with chat_area:
                with ui.row().style("align-self:flex-start; gap:12px; align-items:flex-start") as response_col:
                    ui.label("RT").style(
                        "width:30px; height:30px; min-width:30px; border-radius:9px; flex-shrink:0; "
                        "background:linear-gradient(135deg,#f97316,#ec4899); "
                        "color:#fff; font-family:ui-monospace,monospace; font-size:11px; font-weight:700; "
                        "display:flex; align-items:center; justify-content:center; "
                        "box-shadow:0 0 14px rgba(236,72,153,0.32)"
                    )
                    with ui.column().style("gap:6px; min-width:0; max-width:680px") as response_inner_col:
                        with ui.card().classes("rag-bubble-card").style(
                            "background:var(--c-card,#1e163c); border:1px solid rgba(236,72,153,0.22); "
                            "border-radius:14px; word-break:break-word; overflow-wrap:break-word; overflow:hidden; "
                            "box-shadow:0 4px 22px rgba(236,72,153,0.08); padding:12px 16px"
                        ):
                            ui.label("RAG TUTOR").style(
                                "font-family:ui-monospace,monospace; font-size:10px; color:#64748b; "
                                "text-transform:uppercase; letter-spacing:0.08em; margin-bottom:2px"
                            )
                            streaming_md = ui.markdown("").style("width:100%; word-break:break-word; overflow-wrap:break-word")
            response_col.set_visibility(False)

            ui.update()
            await asyncio.sleep(0)

            tokens: list[str] = []
            done_data: dict = {}
            result: dict = {"cache_hit": "miss", "chunks": [], "latency_ms": 0, "trace_id": "—"}
            first_token_received = [False]

            try:
                payload = {
                    "question": question,
                    "session_id": session["session_id"],
                }
                headers = auth_headers()
                async with http().stream(
                    "POST", "/api/chat", json=payload, headers=headers
                ) as resp:
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        raw = line[len("data: "):]
                        try:
                            event = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        if event.get("type") == "token":
                            if not first_token_received[0]:
                                first_token_received[0] = True
                                response_col.set_visibility(True)
                            tokens.append(event.get("content", ""))
                            streaming_md.content = "".join(tokens)
                            ui.update()
                            ui.run_javascript(
                                "var s=document.querySelector('.rag-scroll-area'); if(s) s.scrollTop=s.scrollHeight;"
                            )
                        elif event.get("type") == "done":
                            done_data = event

            except Exception as e:
                streaming_md.content = f"Error: {e}"
                ui.update()
            finally:
                stage_active[0] = False
                stage_timer.cancel()
                thinking.set_visibility(False)

            # Append debug info and knowledge check to the already-rendered response column.
            with response_inner_col:
                cache_color = "#14532d" if result["cache_hit"] != "none" else "#162032"
                with ui.expansion("Debug info").style(
                    "font-size:0.7rem; color:#64748b; margin-top:0.4rem; width:fit-content"
                ):
                    with ui.row().style("gap:0.5rem; flex-wrap:wrap; padding:0.25rem 0"):
                        user_level = done_data.get("user_level")
                        if user_level:
                            ui.badge(f"Tailored for {user_level}").style(
                                "background:#1e3a5f; color:#93c5fd; font-size:0.7rem"
                            )
                        ui.badge(f"cache: {result['cache_hit']}").style(
                            f"background:{cache_color}; color:#86efac; font-size:0.7rem"
                        )
                        ui.badge(f"{result['latency_ms']}ms").style(
                            "background:#0a1628; color:#64748b; font-size:0.7rem"
                        )
                        ui.badge(f"{len(result['chunks'])} chunks").style(
                            "background:#0a1628; color:#64748b; font-size:0.7rem"
                        )
                        ui.badge(f"trace: {result['trace_id']}").style(
                            "background:#0a1628; color:#64748b; font-size:0.7rem"
                        )

                if result["chunks"]:
                    with ui.expansion("Retrieved context", icon="search").style(
                        "font-size:0.75rem; color:#94a3b8; margin-top:0.5rem"
                    ):
                        for chunk in result["chunks"]:
                            source = chunk["source"].split("/")[-1]
                            with ui.card().style(
                                "background:#16103a; border-left:3px solid #8b5cf6; "
                                "padding:0.4rem 0.6rem; margin-top:0.3rem; border-radius:4px"
                            ):
                                ui.label(source).style(
                                    "font-weight:600; font-size:0.75rem; color:#a78bfa"
                                )
                                ui.label(chunk["content"] + "...").style(
                                    "font-size:0.75rem; color:#94a3b8"
                                )

                test_q = done_data.get("test_question")
                is_mcq = done_data.get("is_mcq", False)

                if test_q:
                    with ui.card().style(
                        "background:rgba(139,92,246,0.08); border:1px solid rgba(139,92,246,0.35); "
                        "box-shadow:0 0 16px rgba(139,92,246,0.2); width:fit-content; "
                        "border-radius:12px; padding:0.75rem 1rem; margin-top:0.75rem; "
                        "word-break:break-word; overflow-wrap:break-word; overflow:hidden"
                    ):
                        ui.label("Knowledge Check").style(
                            "font-size:0.7rem; font-weight:600; color:#a78bfa; margin-bottom:0.35rem"
                        )
                        # Show question line only (strip the A/B/C/D lines for MCQ)
                        _q_line = test_q.split("\n")[0] if is_mcq else test_q
                        ui.label(_q_line).style("font-size:0.875rem; color:#e2e8f0")

                # Render MCQ options inline, below the knowledge check card
                if is_mcq and test_q:
                    _opt_lines = [l for l in test_q.splitlines() if len(l) >= 3 and l[0] in "ABCD" and l[1] == "."]
                    with ui.column().style("gap:6px; margin-top:0.5rem") as _mcq_inline:
                        for _opt_line in _opt_lines:
                            _oletter = _opt_line[0]
                            _otext = _opt_line[3:].strip()
                            with ui.row().style(
                                "align-items:center; gap:0; width:100%; cursor:pointer; "
                                "background:#1a1238; border:1px solid rgba(139,92,246,0.2); "
                                "border-radius:10px; overflow:hidden"
                            ).classes("rag-mcq-row") as _orow:
                                ui.label(_oletter).style(
                                    "width:36px; min-width:36px; height:100%; min-height:42px; "
                                    "display:flex; align-items:center; justify-content:center; "
                                    "font-family:ui-monospace,monospace; font-size:11px; font-weight:700; "
                                    "color:#fff; flex-shrink:0; "
                                    "background:linear-gradient(135deg,#f97316,#ec4899,#8b5cf6)"
                                )
                                ui.label(_otext).style(
                                    "flex:1; padding:10px 14px; font-size:0.875rem; "
                                    "color:#e2e8f0; line-height:1.45"
                                )
                                async def _opt_click(_e, _t=_otext, _col=_mcq_inline):
                                    _col.set_visibility(False)
                                    await send_message(_t)
                                _orow.on("click", _opt_click)

                nav_chips = done_data.get("chips")
                if nav_chips:
                    _chip_names = {c["name"]: c for c in nav_chips}
                    with ui.column().style("gap:0.6rem; margin-top:0.75rem"):
                        ui.label("Choose a topic to explore:").style(
                            "font-size:0.72rem; color:#64748b; font-weight:500; letter-spacing:0.04em"
                        )
                        first_group = True
                        for _mod_label, _mod_topics in _CHIP_MODULE_GROUPS:
                            _group_chips = [_chip_names[t] for t in _mod_topics if t in _chip_names]
                            if not _group_chips:
                                continue
                            with ui.column().style(
                                f"gap:0.35rem; {'margin-top:0.25rem' if not first_group else ''}"
                            ):
                                ui.label(_mod_label).style(
                                    "font-size:0.65rem; font-weight:600; color:#475569; "
                                    "text-transform:uppercase; letter-spacing:0.1em; "
                                    "font-family:ui-monospace,monospace"
                                )
                                with ui.row().style("gap:0.5rem; flex-wrap:wrap"):
                                    for _chip in _group_chips:
                                        _cn = _chip["name"]
                                        _cd = _chip.get("description", "")
                                        _b = ui.button(_cn).props("no-caps unelevated").style(
                                            "font-size:0.78rem; background:rgba(139,92,246,0.1); "
                                            "color:#a78bfa; border:1px solid rgba(139,92,246,0.35); "
                                            "border-radius:999px; padding:0.25rem 0.85rem; "
                                            "font-family:Inter,system-ui; min-height:unset; box-shadow:none"
                                        )
                                        if _cd:
                                            _b.tooltip(_cd)
                                        async def _chip_click(_e, _t=_cn):
                                            await send_message(f"Tell me about {_t}")
                                        _b.on("click", _chip_click)
                            first_group = False
                        if len(nav_chips) < 8:
                            ui.label("You'll unlock more topics as you progress.").style(
                                "font-size:0.72rem; color:#475569; font-style:italic; margin-top:0.1rem"
                            )

            profile_panel.refresh()
            send_btn.enable()
            ui.update()
            ui.run_javascript(
                "var s=document.querySelector('.rag-scroll-area'); if(s) s.scrollTop=s.scrollHeight;"
            )

        async def send():
            question = question_input.value.strip()
            question_input.value = ""
            await send_message(question)

        send_btn.on_click(send)
        question_input.on("keydown.enter", send)

        if app.storage.user.get("user_id") and not app.storage.user.get("email"):
            await fetch_profile_email()

    ui.run_with(fastapi_app, mount_path="/", storage_secret=settings.nicegui_storage_secret)