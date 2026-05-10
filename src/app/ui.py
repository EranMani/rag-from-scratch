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

# Benefit-oriented labels for user_level adaptation badge
_LEVEL_LABELS: dict[str, str] = {
    "beginner": "Simplified for clarity",
    "intermediate": "Standard depth",
    "advanced": "Full technical detail",
}


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
                return True
        except Exception:
            pass
        for key in ("access_token", "user_id", "email"):
            app.storage.user.pop(key, None)
        return False

    async def fetch_profile_email() -> None:
        try:
            r = await http().get("/api/auth/me", headers=auth_headers())
            if r.status_code == 200:
                app.storage.user["email"] = r.json().get("email", "")
        except Exception:
            pass

    @ui.page("/login")
    async def login_page():
        if not settings.allow_anonymous_chat:
            ui.navigate.to("/")
            return

        ui.query("body").style("background:#0f172a; color:#e2e8f0; font-family:system-ui")
        with ui.column().style(
            "width:100%; max-width:420px; margin:3rem auto; padding:1.5rem; gap:1rem"
        ):
            ui.label("Sign in").style("font-size:1.5rem; font-weight:600; color:#38bdf8")
            email = ui.input("Email").props("type=email").classes("w-full").style(
                "background:#1e293b; border:1px solid #334155; border-radius:8px"
            )
            password = ui.input(
                "Password", password=True, password_toggle_button=True
            ).classes("w-full").style(
                "background:#1e293b; border:1px solid #334155; border-radius:8px"
            )

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
                    ui.notify("Invalid email or password", type="negative")
                    return
                data = r.json()
                app.storage.user["access_token"] = data["access_token"]
                app.storage.user["user_id"] = data["user_id"]
                await fetch_profile_email()
                ui.navigate.to("/")

            ui.button("Login", on_click=do_login).style(
                "background:#0369a1; color:white; width:100%"
            )
            ui.link("Create an account", "/register").classes("text-sky-400 text-sm")
            ui.link("Back to chat", "/").classes("text-sky-400 text-sm")

    @ui.page("/register")
    async def register_page():
        if not settings.allow_anonymous_chat and await verify_stored_bearer():
            ui.navigate.to("/")
            return

        ui.query("body").style("background:#0f172a; color:#e2e8f0; font-family:system-ui")
        wrapper = ui.column().style(
            "width:100%; max-width:420px; margin:3rem auto; padding:1.5rem; gap:1rem"
        )

        def show_success():
            wrapper.clear()
            with wrapper:
                ui.label("You're signed in").style(
                    "font-size:1.35rem; font-weight:600; color:#38bdf8"
                )
                ui.label("Your account is ready. Continue to the chat when you like.").style(
                    "font-size:0.9rem; color:#94a3b8"
                )
                ui.button("Go to chat", on_click=lambda: ui.navigate.to("/")).style(
                    "background:#0369a1; color:white; width:100%"
                )

        with wrapper:
            ui.label("Register").style("font-size:1.5rem; font-weight:600; color:#38bdf8")
            email = ui.input("Email").props("type=email").classes("w-full").style(
                "background:#1e293b; border:1px solid #334155; border-radius:8px"
            )
            password = ui.input("Password", password=True, password_toggle_button=True).classes(
                "w-full"
            ).style("background:#1e293b; border:1px solid #334155; border-radius:8px")
            display_name = ui.input("Display name (optional)").classes("w-full").style(
                "background:#1e293b; border:1px solid #334155; border-radius:8px"
            )

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
                "background:#0369a1; color:white; width:100%"
            )
            ui.link("Already have an account? Sign in", "/").classes("text-sky-400 text-sm")

    @ui.page("/")
    async def index():
        ui.query("body").style("background:#0f172a; color:#e2e8f0; font-family:system-ui")

        bearer_ok = await verify_stored_bearer()
        can_use_chat = settings.allow_anonymous_chat or bearer_ok

        def logout():
            app.storage.user.clear()
            ui.navigate.to("/")

        with ui.header().style(
            "background:#1e293b; border-bottom:1px solid #334155; padding:1rem 2rem"
        ):
            with ui.row().style("width:100%; justify-content:space-between; align-items:flex-start"):
                with ui.column().style("gap:0.25rem"):
                    ui.label("Educational RAG System").style(
                        "font-size:1.25rem; font-weight:600; color:#38bdf8"
                    )
                    ui.label(
                        "Ask anything about RAG architecture, vector databases, LangChain, caching, or circuit breakers."
                    ).style("font-size:0.8rem; color:#94a3b8; margin-top:0.25rem")
                with ui.row().style("gap:0.75rem; align-items:center"):
                    uid = app.storage.user.get("user_id")
                    if uid:
                        label = app.storage.user.get("email") or f"id …{uid[-8:]}"
                        ui.label(label).style("font-size:0.75rem; color:#94a3b8")
                        ui.button("Log out", on_click=logout).props("flat dense").style(
                            "color:#94a3b8"
                        )
                    elif settings.allow_anonymous_chat:
                        ui.label("Anonymous demo").style("font-size:0.75rem; color:#64748b")
                        ui.link("Sign in", "/login").classes("text-sky-400 text-sm")
                        ui.link("Register", "/register").classes("text-sky-400 text-sm")

        if not can_use_chat:
            ui.navigate.to("/login")
            return

        session = create_session()

        # Outer row: profile sidebar (left) + chat area (right)
        with ui.row().style("width:100%; height:calc(100vh - 120px); gap:0; overflow:hidden"):

            # --- Profile sidebar ---
            @ui.refreshable
            async def profile_panel():
                with ui.column().style(
                    "width:280px; min-width:280px; height:100%; background:#1e293b; "
                    "border-right:1px solid #334155; padding:1rem; gap:0.75rem; overflow-y:auto"
                ):
                    ui.label("Knowledge Profile").style(
                        "font-size:0.9rem; font-weight:600; color:#38bdf8"
                    )

                    headers = auth_headers()
                    if not headers:
                        # Anonymous user — no profile to display
                        ui.label("Sign in to track your progress.").style(
                            "font-size:0.8rem; color:#64748b"
                        )
                        return

                    try:
                        r = await http().get("/api/profile/me", headers=headers)
                        if r.status_code != 200:
                            raise ValueError(f"status {r.status_code}")
                        profile = r.json()
                    except Exception:
                        ui.label("Profile unavailable.").style(
                            "font-size:0.8rem; color:#94a3b8"
                        )
                        return

                    # Mastery level — null-safe
                    mastery = profile.get("mastery_level") or "—"
                    ui.label(f"Level: {mastery.capitalize() if mastery != '—' else '—'}").style(
                        "font-size:0.8rem; color:#94a3b8"
                    )

                    topic_scores: dict = profile.get("topic_scores") or {}

                    if not topic_scores:
                        # Empty state for fresh users
                        ui.label("Start chatting to build your profile.").style(
                            "font-size:0.8rem; color:#64748b; font-style:italic"
                        )
                    else:
                        ui.label("Topic Scores").style(
                            "font-size:0.75rem; font-weight:600; color:#64748b; margin-top:0.25rem"
                        )
                        for slug, label in _MODULE_LABELS.items():
                            score: float = topic_scores.get(slug, 0.0)
                            with ui.column().style("gap:0.15rem; width:100%"):
                                ui.label(label).style("font-size:0.72rem; color:#94a3b8")
                                ui.linear_progress(value=score).style(
                                    "width:100%; height:6px"
                                ).props("color=sky-600 track-color=slate-700")

                    # Gaps tag list
                    gaps: list = profile.get("gaps") or []
                    if gaps:
                        ui.label("Gaps").style(
                            "font-size:0.75rem; font-weight:600; color:#64748b; margin-top:0.5rem"
                        )
                        with ui.row().style("flex-wrap:wrap; gap:0.3rem"):
                            for gap in gaps:
                                display = _MODULE_LABELS.get(gap, gap.replace("_", " ").title())
                                ui.badge(display).style(
                                    "background:#1e3a5f; color:#93c5fd; font-size:0.65rem; "
                                    "border-radius:4px; padding:0.1rem 0.4rem"
                                )

                    # Query count and last active
                    interaction_count = profile.get("interaction_count", 0)
                    last_activity = profile.get("last_activity_at")
                    ui.label(f"Queries: {interaction_count}").style(
                        "font-size:0.72rem; color:#64748b; margin-top:0.5rem"
                    )
                    if last_activity:
                        # Show date portion only for brevity
                        last_str = last_activity[:10] if len(last_activity) >= 10 else last_activity
                        ui.label(f"Last active: {last_str}").style(
                            "font-size:0.72rem; color:#64748b"
                        )

            await profile_panel()

            # --- Chat area ---
            with ui.column().style("flex:1; height:100%; overflow:hidden; position:relative"):
                with ui.column().style(
                    "flex:1; width:100%; max-width:900px; margin:0 auto; padding:1.5rem; "
                    "overflow-y:auto; height:calc(100% - 80px)"
                ):
                    chat_area = ui.column().style("width:100%; gap:1rem")

                    with chat_area:
                        with ui.card().style(
                            "background:#1e293b; border:1px solid #334155; max-width:75%; border-radius:12px"
                        ):
                            ui.markdown(
                                "Welcome! I am a RAG system that answers questions about how RAG systems work.\n\n"
                                "Try asking: **How does chunking work?** or **What is a circuit breaker?**"
                            )

                with ui.footer().style(
                    "background:#1e293b; border-top:1px solid #334155; padding:1rem 2rem"
                ):
                    with ui.row().style("width:100%; max-width:900px; margin:0 auto; gap:0.75rem"):
                        question_input = ui.input(
                            placeholder="Ask about RAG, vector databases, LangChain..."
                        ).style(
                            "flex:1; background:#0f172a; border:1px solid #334155; color:#e2e8f0; border-radius:8px"
                        )
                        send_btn = ui.button("Send").style(
                            "background:#0369a1; color:white; border-radius:8px"
                        )

        async def send():
            question = question_input.value.strip()
            if not question:
                return

            question_input.value = ""
            send_btn.disable()

            trusted_user_id = app.storage.user.get("user_id")

            with chat_area:
                with ui.card().style(
                    "background:#0369a1; color:#f0f9ff; max-width:75%; align-self:flex-end; border-radius:12px"
                ):
                    ui.label(question)

                stage_idx = [0]
                stage_active = [True]
                thinking = ui.label(_STAGE_LABELS[0]).style("color:#64748b; font-style:italic")

                def _advance():
                    if not stage_active[0]:
                        return
                    stage_idx[0] = min(stage_idx[0] + 1, len(_STAGE_LABELS) - 1)
                    thinking.set_text(_STAGE_LABELS[stage_idx[0]])

                stage_timer = ui.timer(2.5, _advance)

            ui.update()
            await asyncio.sleep(0)

            try:
                # Call the streaming /api/chat endpoint and collect SSE tokens.
                # The UI renders the complete answer after the stream finishes.
                payload = {
                    "question": question,
                    "session_id": session["session_id"],
                }
                headers = auth_headers()
                tokens: list[str] = []
                done_data: dict = {}
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
                            tokens.append(event.get("content", ""))
                        elif event.get("type") == "done":
                            done_data = event

                result = {
                    "answer": "".join(tokens),
                    "cache_hit": "miss",
                    "chunks": [],
                    "latency_ms": 0,
                    "trace_id": "—",
                }
            except Exception as e:
                result = {
                    "answer": f"Error: {e}",
                    "cache_hit": "none",
                    "chunks": [],
                    "latency_ms": 0,
                    "trace_id": "—",
                }
            finally:
                stage_active[0] = False
                stage_timer.cancel()
                thinking.delete()

            with chat_area:
                with ui.card().style(
                    "background:#1e293b; border:1px solid #334155; max-width:75%; border-radius:12px"
                ):
                    ui.markdown(result["answer"])

                    cache_color = "#14532d" if result["cache_hit"] != "none" else "#1e293b"
                    with ui.row().style("gap:0.5rem; margin-top:0.5rem; flex-wrap:wrap"):
                        ui.badge(f"cache: {result['cache_hit']}").style(
                            f"background:{cache_color}; color:#86efac; font-size:0.7rem"
                        )
                        ui.badge(f"{result['latency_ms']}ms").style(
                            "background:#0f172a; color:#94a3b8; font-size:0.7rem"
                        )
                        ui.badge(f"{len(result['chunks'])} chunks").style(
                            "background:#0f172a; color:#94a3b8; font-size:0.7rem"
                        )
                        ui.badge(f"trace: {result['trace_id']}").style(
                            "background:#0f172a; color:#94a3b8; font-size:0.7rem"
                        )
                        user_level = done_data.get("user_level")
                        if user_level:
                            ui.badge(_LEVEL_LABELS.get(user_level, f"Adapted for: {user_level}")).style(
                                "background:#1e3a5f; color:#93c5fd; font-size:0.7rem"
                            )

                    if result["chunks"]:
                        with ui.expansion("Retrieved context", icon="search").style(
                            "font-size:0.75rem; color:#94a3b8; margin-top:0.5rem"
                        ):
                            for chunk in result["chunks"]:
                                source = chunk["source"].split("/")[-1]
                                with ui.card().style(
                                    "background:#0f172a; border-left:3px solid #0369a1; "
                                    "padding:0.4rem 0.6rem; margin-top:0.3rem; border-radius:4px"
                                ):
                                    ui.label(source).style(
                                        "font-weight:600; font-size:0.75rem; color:#38bdf8"
                                    )
                                    ui.label(chunk["content"] + "...").style(
                                        "font-size:0.75rem; color:#94a3b8"
                                    )

            profile_panel.refresh()
            send_btn.enable()
            ui.update()

        send_btn.on_click(send)
        question_input.on("keydown.enter", send)

        if app.storage.user.get("user_id") and not app.storage.user.get("email"):
            await fetch_profile_email()

    ui.run_with(fastapi_app, mount_path="/", storage_secret=settings.nicegui_storage_secret)
