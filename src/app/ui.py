import uuid

import httpx
from nicegui import app, ui
from app.core.config import settings
from rag.chain import run_rag_pipeline


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
        if not settings.allow_annonymous_chat:
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
        if not settings.allow_annonymous_chat and await verify_stored_bearer():
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
        can_use_chat = settings.allow_annonymous_chat or bearer_ok

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
                    elif settings.allow_annonymous_chat:
                        ui.label("Anonymous demo").style("font-size:0.75rem; color:#64748b")
                        ui.link("Sign in", "/login").classes("text-sky-400 text-sm")
                        ui.link("Register", "/register").classes("text-sky-400 text-sm")

        if not can_use_chat:
            with ui.column().style(
                "width:100%; max-width:420px; margin:2rem auto; padding:1.5rem; gap:1rem"
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
            return

        session = create_session()

        with ui.column().style("flex:1; width:100%; max-width:900px; margin:0 auto; padding:1.5rem"):
            chat_area = ui.column().style("width:100%; gap:1rem")

            with chat_area:
                with ui.card().style(
                    "background:#1e293b; border:1px solid #334155; max-width:75%; border-radius:12px"
                ):
                    ui.markdown(
                        "Welcome! I am a RAG system that answers questions about how RAG systems work.\n\n"
                        "Try asking: **How does chunking work?** or **What is a circuit breaker?**"
                    )

        with ui.footer().style("background:#1e293b; border-top:1px solid #334155; padding:1rem 2rem"):
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

                thinking = ui.label("Thinking...").style("color:#64748b; font-style:italic")

            ui.update()

            try:
                result = run_rag_pipeline(
                    question=question,
                    session_id=session["session_id"],
                    user_id=trusted_user_id,
                )
            except Exception as e:
                result = {
                    "answer": f"Error: {e}",
                    "cache_hit": "none",
                    "chunks": [],
                    "latency_ms": 0,
                    "trace_id": "—",
                }

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

            send_btn.enable()
            ui.update()

        send_btn.on_click(send)
        question_input.on("keydown.enter", send)

        if app.storage.user.get("user_id") and not app.storage.user.get("email"):
            await fetch_profile_email()

    ui.run_with(fastapi_app, mount_path="/", storage_secret="rag-secret-key")
