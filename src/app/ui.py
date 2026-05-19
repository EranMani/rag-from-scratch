import asyncio
import json
import uuid

import httpx
from nicegui import app, ui
from app.core.config import settings

_STAGE_LABELS = ["Retrieving context...", "Preparing your answer...", "Generating response..."]

# Canonical module display names for topic_scores keys
_MODULE_LABELS: dict[str, str] = {
    "rag_fundamentals": "RAG Fundamentals",
    "vector_databases": "Vector Databases",
    "retrieval_methods": "Retrieval Methods",
    "chunking_strategies": "Chunking Strategies",
    "langchain": "LangChain",
    "production_patterns": "Production Patterns",
}


def _build_welcome_message(display_name: str | None, profile: dict | None) -> str:
    name = display_name or "there"

    if not profile:
        return (
            f"Welcome, **{name}**! I'm your RAG learning assistant.\n\n"
            "Ask me anything about RAG architecture — or try: **How does chunking work?**"
        )

    interaction_count: int = profile.get("interaction_count") or 0
    gaps: list = profile.get("gaps") or []
    strengths: list = profile.get("strengths") or []
    mastery_level: str = profile.get("mastery_level") or "novice"

    def _label(slug: str) -> str:
        return _MODULE_LABELS.get(slug, slug.replace("_", " ").title())

    if interaction_count == 0:
        return (
            f"Welcome to your RAG learning journey, **{name}**! "
            "I'll adapt to your level as we go.\n\n"
            "Start by asking anything — or try: **What is retrieval-augmented generation?**"
        )

    if gaps:
        gap_labels = [_label(g) for g in gaps[:2]]
        gap_str = " and ".join(f"**{l}**" for l in gap_labels)
        suffix = "more" if len(gaps) > 2 else ""
        return (
            f"Hey **{name}**! I see you have gaps in {gap_str}"
            + (f" and {len(gaps) - 2} more topic{'s' if len(gaps) - 2 > 1 else ''}" if suffix else "")
            + f". Want to work on those today?\n\n"
            f"You've had **{interaction_count}** {'session' if interaction_count == 1 else 'sessions'} so far — keep it up!"
        )

    if strengths:
        strength_labels = [_label(s) for s in strengths[:2]]
        strength_str = " and ".join(f"**{l}**" for l in strength_labels)
        if mastery_level in ("advanced", "expert"):
            return (
                f"Welcome back, **{name}**! You've mastered {strength_str}. "
                "Ready to dive into advanced patterns?\n\n"
                f"**{interaction_count}** {'session' if interaction_count == 1 else 'sessions'} completed — impressive!"
            )
        return (
            f"Welcome back, **{name}**! You're strong in {strength_str}. "
            "Want to go deeper or explore a new topic?\n\n"
            f"**{interaction_count}** {'session' if interaction_count == 1 else 'sessions'} and counting!"
        )

    return (
        f"Welcome back, **{name}**! You've had **{interaction_count}** "
        f"{'session' if interaction_count == 1 else 'sessions'} — your profile is building up.\n\n"
        "What would you like to explore today?"
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
.rag-login-input .q-field__control { background: #0c0a1e !important; border-radius: 10px !important; }
.rag-login-input.q-field--outlined .q-field__control:before { border-color: #2e2558 !important; border-radius: 10px !important; transition: border-color 0.2s, box-shadow 0.2s; }
.rag-login-input.q-field--outlined:hover .q-field__control:before { border-color: rgba(236,72,153,0.4) !important; }
.rag-login-input.q-field--outlined.q-field--focused .q-field__control:before { border-color: #ec4899 !important; box-shadow: 0 0 0 3px rgba(236,72,153,0.15); }
.rag-login-input .q-field__native { color: #ffffff !important; padding-left: 1rem !important; padding-right: 1rem !important; }
.rag-login-input .q-field__label { color: #94a3b8 !important; }
.rag-login-input .q-field__placeholder { color: #4a5568 !important; }
</style>''')
        ui.query("body").style("background:radial-gradient(ellipse at 35% 0%, #2a1060 0%, #120e28 60%); color:#e2e8f0; font-family:'Inter',system-ui")
        with ui.column().style(
            "width:100%; max-width:420px; margin:3rem auto; padding:2rem; gap:1.25rem; "
            "background:linear-gradient(160deg, rgba(22,16,44,0.98) 0%, rgba(28,20,52,0.98) 100%); "
            "border:1px solid rgba(139,92,246,0.2); border-top:3px solid #f97316; border-radius:16px; "
            "backdrop-filter:blur(12px); box-shadow:0 8px 48px rgba(139,92,246,0.15)"
        ):
            with ui.row().style("align-items:center; gap:0.625rem"):
                ui.html('''<svg width="36" height="36" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs><linearGradient id="lg-login" x1="0" y1="0" x2="28" y2="28" gradientUnits="userSpaceOnUse">
    <stop offset="0%" stop-color="#f97316"/><stop offset="50%" stop-color="#ec4899"/><stop offset="100%" stop-color="#8b5cf6"/>
  </linearGradient></defs>
  <path d="M10 6L4 14L10 22" stroke="url(#lg-login)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M18 6L24 14L18 22" stroke="url(#lg-login)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M15 8L13 20" stroke="url(#lg-login)" stroke-width="2" stroke-linecap="round" opacity="0.7"/>
</svg>''')
                ui.html('<span style="font-size:1.5rem;font-weight:700;letter-spacing:-0.02em;font-family:Inter,system-ui;background:linear-gradient(135deg,#f97316 0%,#ec4899 50%,#8b5cf6 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;line-height:1">RAG Tutor</span>')
            ui.label("Your AI-powered RAG learning assistant").style("font-size:1rem; color:#94a3b8; font-weight:500; margin-top:-0.25rem")
            ui.label("Sign in to your account").style("font-size:0.78rem; color:#64748b; margin-top:-0.5rem")
            ui.separator().style("border-color:rgba(139,92,246,0.2); margin:0.1rem 0")
            email = ui.input("Username or Email").classes("rag-login-input w-full").props("outlined")
            password = ui.input(
                "Password", password=True, password_toggle_button=True
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

            ui.button("Login", on_click=do_login).style(
                "background:linear-gradient(135deg,#ea580c,#be185d) !important; color:white; width:100%; border-radius:10px; font-weight:600; box-shadow:0 4px 20px rgba(190,24,93,0.4)"
            )
            ui.link("Create a new account", "/register").classes("text-pink-400 text-sm")

    @ui.page("/register")
    async def register_page():
        if await verify_stored_bearer():
            ui.navigate.to("/")
            return

        ui.add_head_html('''<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
.rag-login-input .q-field__control { background: #0c0a1e !important; border-radius: 10px !important; }
.rag-login-input.q-field--outlined .q-field__control:before { border-color: #2e2558 !important; border-radius: 10px !important; transition: border-color 0.2s, box-shadow 0.2s; }
.rag-login-input.q-field--outlined:hover .q-field__control:before { border-color: rgba(236,72,153,0.4) !important; }
.rag-login-input.q-field--outlined.q-field--focused .q-field__control:before { border-color: #8b5cf6 !important; box-shadow: 0 0 0 3px rgba(139,92,246,0.15); }
.rag-login-input .q-field__native { color: #ffffff !important; padding-left: 1rem !important; padding-right: 1rem !important; }
.rag-login-input .q-field__label { color: #94a3b8 !important; }
.rag-login-input .q-field__placeholder { color: #4a5568 !important; }
</style>''')
        ui.query("body").style("background:radial-gradient(ellipse at 65% 0%, #2a1060 0%, #120e28 60%); color:#e2e8f0; font-family:'Inter',system-ui")
        wrapper = ui.column().style(
            "width:100%; max-width:420px; margin:3rem auto; padding:2rem; gap:1.25rem; "
            "background:linear-gradient(160deg, rgba(22,16,44,0.98) 0%, rgba(28,20,52,0.98) 100%); "
            "border:1px solid rgba(139,92,246,0.2); border-top:3px solid #8b5cf6; border-radius:16px; "
            "backdrop-filter:blur(12px); box-shadow:0 8px 48px rgba(139,92,246,0.15)"
        )

        def show_success():
            wrapper.clear()
            with wrapper:
                ui.label("You're signed in").style(
                    "font-size:1.35rem; font-weight:600; background:linear-gradient(135deg,#f97316,#ec4899);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text"
                )
                ui.label("Your account is ready. Continue to the chat when you like.").style(
                    "font-size:0.9rem; color:#94a3b8"
                )
                ui.button("Go to chat", on_click=lambda: ui.navigate.to("/")).style(
                    "background:linear-gradient(135deg,#ea580c,#be185d); color:white; width:100%; box-shadow:0 4px 20px rgba(190,24,93,0.35)"
                )

        with wrapper:
            with ui.row().style("align-items:center; gap:0.625rem"):
                ui.html('''<svg width="36" height="36" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs><linearGradient id="lg-reg" x1="0" y1="0" x2="28" y2="28" gradientUnits="userSpaceOnUse">
    <stop offset="0%" stop-color="#f97316"/><stop offset="50%" stop-color="#ec4899"/><stop offset="100%" stop-color="#8b5cf6"/>
  </linearGradient></defs>
  <path d="M10 6L4 14L10 22" stroke="url(#lg-reg)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M18 6L24 14L18 22" stroke="url(#lg-reg)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M15 8L13 20" stroke="url(#lg-reg)" stroke-width="2" stroke-linecap="round" opacity="0.7"/>
</svg>''')
                ui.html('<span style="font-size:1.5rem;font-weight:700;letter-spacing:-0.02em;font-family:Inter,system-ui;background:linear-gradient(135deg,#f97316 0%,#ec4899 50%,#8b5cf6 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;line-height:1">RAG Tutor</span>')
            ui.label("Your AI-powered RAG learning assistant").style("font-size:1rem; color:#94a3b8; font-weight:500; margin-top:-0.25rem")
            ui.label("Create your account").style("font-size:0.78rem; color:#64748b; margin-top:-0.5rem")
            ui.separator().style("border-color:rgba(139,92,246,0.2); margin:0.1rem 0")
            email = ui.input("Email").props("type=email outlined").classes("rag-login-input w-full")
            password = ui.input("Password", password=True, password_toggle_button=True).classes(
                "rag-login-input w-full"
            ).props("outlined")
            display_name = ui.input("Display name (optional)").classes("rag-login-input w-full").props("outlined")

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

            ui.button("Create account", on_click=do_register).style(
                "background:linear-gradient(135deg,#ea580c,#be185d) !important; color:white; width:100%; border-radius:10px; font-weight:600; box-shadow:0 4px 20px rgba(190,24,93,0.4)"
            )
            ui.link("Already have an account? Sign in", "/login").classes("text-pink-400 text-sm")

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
.q-tab { color: #64748b !important; font-size: 0.85rem; font-weight: 500; }
.q-tab--active { color: #f97316 !important; }
.q-tabs { background: #0c0a1e !important; border-bottom: 1px solid rgba(139,92,246,0.2); }
.q-tab__indicator { background: linear-gradient(90deg,#f97316,#ec4899) !important; height: 3px !important; }
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
.rag-header-accent::after {
  content: '';
  position: absolute;
  bottom: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(90deg, #f97316 0%, #ec4899 40%, #8b5cf6 70%, #38bdf8 100%);
  box-shadow: 0 0 16px rgba(236,72,153,0.5);
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
}
.nicegui-header.rag-header-accent {
  gap: 0 !important;
  padding: 0 !important;
}
.rag-profile-sidebar .q-linear-progress {
  height: 8px !important;
  min-height: 8px !important;
  border-radius: 4px !important;
  flex-shrink: 0 !important;
  overflow: hidden !important;
}
.rag-profile-sidebar .q-linear-progress__track {
  background: rgba(22, 14, 44, 0.85) !important;
  border: 1px solid rgba(46, 37, 88, 0.8) !important;
  opacity: 1 !important;
  border-radius: 4px !important;
}
.rag-profile-sidebar .q-linear-progress__model {
  background: linear-gradient(90deg, #f97316 0%, #ec4899 55%, #8b5cf6 100%) !important;
  border-radius: 4px !important;
  transition: transform 0.5s cubic-bezier(0.4,0,0.2,1) !important;
}

/* Chat input */
.rag-chat-input .q-field__control { background: #1e1642 !important; border-radius: 14px !important; min-height: 52px !important; }
.rag-chat-input.q-field--outlined .q-field__control:before { border-color: rgba(236,72,153,0.35) !important; border-radius: 14px !important; transition: border-color 0.2s, box-shadow 0.2s; }
.rag-chat-input.q-field--outlined:hover .q-field__control:before { border-color: rgba(236,72,153,0.6) !important; }
.rag-chat-input.q-field--outlined.q-field--focused .q-field__control:before { border-color: #ec4899 !important; box-shadow: 0 0 0 3px rgba(236,72,153,0.18), 0 0 16px rgba(236,72,153,0.12); }
.rag-chat-input .q-field__native { color: #e2e8f0 !important; padding: 0 1rem !important; }
.rag-chat-input .q-field__placeholder { color: #8b7aaa !important; }

/* Send button — sunset gradient */
.rag-send-btn {
  background: linear-gradient(135deg, #ea580c 0%, #be185d 100%) !important;
  border-radius: 14px !important;
  width: 52px !important; height: 52px !important; min-width: 52px !important;
  flex-shrink: 0;
  box-shadow: 0 0 0 1px rgba(236,72,153,0.3), 0 4px 20px rgba(236,72,153,0.35), 0 0 32px rgba(249,115,22,0.15);
  transition: box-shadow 0.2s, transform 0.15s;
}
.rag-send-btn:not(.disabled):hover {
  box-shadow: 0 0 0 1px rgba(236,72,153,0.5), 0 4px 28px rgba(236,72,153,0.55), 0 0 40px rgba(249,115,22,0.25) !important;
  transform: scale(1.06) !important;
  transition: box-shadow 0.15s, transform 0.15s;
}
.rag-send-btn.disabled { opacity: 0.3 !important; box-shadow: none !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #120e28; }
::-webkit-scrollbar-thumb { background: rgba(139,92,246,0.5); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(236,72,153,0.75); }
* { scrollbar-width: thin; scrollbar-color: rgba(139,92,246,0.6) #120e28; }

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

        def logout():
            app.storage.user.clear()
            ui.navigate.to("/")

        with ui.header().classes("rag-header-accent").style(
            "background:#0c0a1e; position:relative; padding:0"
        ):
            # Restored standard paddings here — no more calculated vertical shifting or big gaps
            with ui.row().style("width:100%; justify-content:space-between; align-items:center; padding:1rem 2rem"):
                with ui.column().style("gap:0"):
                    with ui.row().style("align-items:center; gap:10px"):
                        ui.html('''<svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="rag-brand-icon-grad" x1="0" y1="0" x2="28" y2="28" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#f97316"/>
      <stop offset="100%" stop-color="#fb923c"/>
    </linearGradient>
  </defs>
  <path d="M10 6L4 14L10 22" stroke="url(#rag-brand-icon-grad)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M18 6L24 14L18 22" stroke="url(#rag-brand-icon-grad)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M15 8L13 20" stroke="url(#rag-brand-icon-grad)" stroke-width="2" stroke-linecap="round" opacity="0.7"/>
</svg>''')
                        ui.html('<span class="rag-brand-name">RAG Tutor</span>')
                with ui.row().style("gap:0.75rem; align-items:center"):
                    _user_store = {k: app.storage.user.get(k) for k in ("user_id", "email")}
                    uid = _user_store["user_id"]
                    if uid:
                        label = _user_store["email"] or f"id …{uid[-8:]}"
                        ui.label(label).style(
                            "font-size:0.7rem; color:#94a3b8; background:rgba(255,255,255,0.06); "
                            "border:1px solid rgba(249,115,22,0.15); border-radius:999px; "
                            "padding:3px 10px; font-family:Inter,system-ui"
                        )
                        ui.button("Log out", on_click=logout).props("flat dense").style(
                            "color:#64748b; font-size:0.75rem"
                        )
                    elif settings.allow_anonymous_chat:
                        ui.label("Anonymous demo").style("font-size:0.75rem; color:#64748b")
                        ui.link("Sign in", "/login").classes("text-sky-400 text-sm")
                        ui.link("Register", "/register").classes("text-sky-400 text-sm")

            with ui.tabs().classes("w-full") as tabs:
                chat_tab = ui.tab("Chat")
                admin_tab = ui.tab("Admin")
            if not app.storage.user.get("is_admin", False):
                tabs.set_visibility(False)

        if not can_use_chat:
            ui.navigate.to("/login")
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
                    @ui.refreshable
                    async def profile_panel():
                        with ui.column().classes("rag-profile-sidebar").style(
                            "width:280px; min-width:280px; flex:0 0 280px; "
                            "height:100%; box-sizing:border-box; "
                            "background:linear-gradient(180deg,rgba(249,115,22,0.05) 0%,rgba(139,92,246,0.05) 100%),#16103a; border-right:2px solid rgba(236,72,153,0.2); "
                            "padding:1rem; gap:1rem; overflow-y:auto"
                        ):
                            ui.label("Knowledge Profile").style("font-size:0.9rem; font-weight:700; background:linear-gradient(135deg,#f97316,#ec4899);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text")

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

                            mastery = profile.get("mastery_level") or "novice"
                            _mastery_styles = {
                                "novice": "background:rgba(100,116,139,0.15);color:#94a3b8;border:1px solid rgba(100,116,139,0.3)",
                                "intermediate": "background:rgba(249,115,22,0.12);color:#f97316;border:1px solid rgba(249,115,22,0.35);box-shadow:0 0 8px rgba(249,115,22,0.2)",
                                "advanced": "background:rgba(236,72,153,0.12);color:#ec4899;border:1px solid rgba(236,72,153,0.35);box-shadow:0 0 8px rgba(236,72,153,0.2)",
                                "expert": "background:linear-gradient(135deg,rgba(249,115,22,0.1),rgba(139,92,246,0.1));color:#a78bfa;border:1px solid rgba(139,92,246,0.4);box-shadow:0 0 12px rgba(139,92,246,0.25)",
                            }
                            _chip_style = _mastery_styles.get(mastery, _mastery_styles["novice"])
                            ui.label(mastery.capitalize()).classes("rag-mastery-chip").style(_chip_style)

                            topic_scores: dict = profile.get("topic_scores") or {}

                            if not topic_scores:
                                ui.label("Start chatting to build your profile.").style("font-size:0.8rem; color:#64748b; font-style:italic")
                            else:
                                ui.label("Topic Scores").style("font-size:0.82rem; font-weight:600; color:#64748b; margin-top:0.25rem")
                                for slug, label in _MODULE_LABELS.items():
                                    score: float = topic_scores.get(slug, 0.0)
                                    with ui.column().style("gap:0.4rem; width:100%"):
                                        with ui.row().style("justify-content:space-between; align-items:center; width:100%"):
                                            ui.label(label).style("font-size:0.8rem; color:#94a3b8")
                                            ui.label(f"{int(score * 100)}%").style("font-size:0.8rem; color:#64748b; font-family:ui-monospace,monospace")
                                        ui.linear_progress(value=score, show_value=False).style("width:100%").props("color=deep-orange-400 track-color=blue-grey-900")

                            interaction_count = profile.get("interaction_count", 0)
                            last_activity = profile.get("last_activity_at")
                            ui.label(f"Queries: {interaction_count}").style("font-size:0.78rem; color:#64748b; margin-top:0.5rem")
                            if last_activity:
                                last_str = (last_activity[:16].replace("T", " ") if len(last_activity) >= 16 else last_activity)
                                ui.label(f"Last active: {last_str}").style("font-size:0.78rem; color:#64748b")

                    await profile_panel()

                    # --- Chat message log box viewport ---
                    with ui.column().style("flex:1; height:100%; min-height:0; overflow:hidden; position:relative; background:#120e28"):
                        with ui.column().style("position:absolute; top:0; left:0; right:0; bottom:0; overflow-y:auto; padding:1.5rem; background:radial-gradient(ellipse at 8% 92%, rgba(249,115,22,0.07) 0%, transparent 38%), radial-gradient(ellipse at 92% 8%, rgba(139,92,246,0.07) 0%, transparent 38%), radial-gradient(ellipse at 50% 50%, rgba(236,72,153,0.03) 0%, transparent 60%), #120e28"):
                            chat_area = ui.column().style("width:100%; gap:1rem")

                            with chat_area:
                                with ui.card().style("background:rgba(22,16,44,0.9); border:1px solid rgba(139,92,246,0.2); max-width:75%; border-radius:4px 20px 20px 20px; box-shadow:0 4px 28px rgba(139,92,246,0.12); backdrop-filter:blur(6px); padding:1rem 1.25rem"):
                                    _dn = app.storage.user.get("display_name") or app.storage.user.get("email")
                                    ui.markdown(_build_welcome_message(_dn, _welcome_profile))

                # 2. Input Container Control Footer Row Panel
                # Clean, top-down stacking. No absolute hacks needed anymore.
                with ui.row().style(
                    "width: 100%; flex-shrink: 0; "
                    "padding: 1rem 2rem; gap: 0.75rem; align-items: center; "
                    "background: linear-gradient(180deg, rgba(249,115,22,0.08) 0%, rgba(236,72,153,0.06) 50%, rgba(139,92,246,0.05) 100%), #231848; "
                    "border-top: 2px solid transparent; border-image: linear-gradient(90deg,#f97316,#ec4899,#8b5cf6) 1; "
                    "box-shadow: 0 -12px 40px rgba(236,72,153,0.2), 0 -4px 12px rgba(249,115,22,0.1); "
                    "box-sizing: border-box;"
                ):
                    question_input = ui.input(
                        placeholder="Ask about RAG, vector databases, LangChain..."
                    ).classes("rag-chat-input").props("outlined auto-grow").style("flex:1")
                    send_btn = ui.button(icon="send").classes("rag-send-btn").props("unelevated").style("color:white; font-size:1.1rem").props("color=orange")

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


        async def send():
            question = question_input.value.strip()
            if not question:
                return

            question_input.value = ""
            send_btn.disable()

            with chat_area:
                _dn = app.storage.user.get("display_name") or app.storage.user.get("email", "You")
                with ui.column().style("align-self:flex-end; max-width:75%; gap:0.2rem"):
                    ui.label(_dn).style(
                        "font-size:0.7rem; color:#64748b; text-align:right; align-self:flex-end"
                    )
                    with ui.card().style(
                        "background:linear-gradient(135deg,#ea580c,#be185d); color:#fff0f6; width:fit-content; align-self:flex-end; "
                        "border-radius:20px 20px 4px 20px; word-break:break-word; overflow-wrap:break-word; overflow:hidden; "
                        "box-shadow:0 4px 20px rgba(190,24,93,0.35); padding:0.75rem 1rem"
                    ):
                        ui.label(question).style("word-break:break-word; overflow-wrap:break-word; max-width:100%")

                stage_idx = [0]
                stage_active = [True]
                with ui.row().style(
                    "align-items:center; gap:0.5rem; padding:0.3rem 0"
                ) as thinking:
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
                with ui.column().style("align-self:flex-start; max-width:75%; gap:0.2rem") as response_col:
                    ui.label("RAG Assistant").style("font-size:0.7rem; color:#64748b")
                    with ui.card().style(
                        "background:rgba(22,16,44,0.9); border:1px solid rgba(139,92,246,0.2); width:fit-content; "
                        "border-radius:4px 20px 20px 20px; word-break:break-word; overflow-wrap:break-word; overflow:hidden; "
                        "box-shadow:0 4px 24px rgba(139,92,246,0.12); backdrop-filter:blur(6px); padding:0.75rem 1rem"
                    ):
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
            with response_col:
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
                if test_q:
                    with ui.card().style(
                        "background:rgba(139,92,246,0.08); border:1px solid rgba(139,92,246,0.35); "
                        "box-shadow:0 0 16px rgba(139,92,246,0.2); width:fit-content; "
                        "border-radius:12px; padding:0.75rem 1rem; margin-top:0.75rem; "
                        "word-break:break-word; overflow-wrap:break-word; overflow:hidden"
                    ):
                        ui.label("✦ Knowledge Check").style(
                            "font-size:0.7rem; font-weight:600; color:#a78bfa; margin-bottom:0.35rem"
                        )
                        ui.label(test_q).style("font-size:0.875rem; color:#e2e8f0")

            profile_panel.refresh()
            send_btn.enable()
            ui.update()

        send_btn.on_click(send)
        question_input.on("keydown.enter", send)

        if app.storage.user.get("user_id") and not app.storage.user.get("email"):
            await fetch_profile_email()

    ui.run_with(fastapi_app, mount_path="/", storage_secret=settings.nicegui_storage_secret)