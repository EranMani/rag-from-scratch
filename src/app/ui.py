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
                return True
        except Exception:
            pass
        for key in ("access_token", "user_id", "email", "display_name"):
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
        if await verify_stored_bearer():
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
        ui.query("body").style("background:#0f172a; color:#e2e8f0; font-family:system-ui; overflow:hidden")

        ui.add_head_html("""
<style>
.nicegui-markdown h1,.nicegui-markdown h2,.nicegui-markdown h3{
  color:#38bdf8;font-weight:600;margin-top:1rem;margin-bottom:0.4rem}
.nicegui-markdown h1{font-size:1.4em}
.nicegui-markdown h2{font-size:1.2em}
.nicegui-markdown h3{font-size:1.05em}
.nicegui-markdown code{
  background:#0f172a;font-family:ui-monospace,monospace;
  border:1px solid #334155;border-radius:4px;
  padding:0.1em 0.35em;font-size:0.875em}
.nicegui-markdown pre{
  background:#0f172a;border:1px solid #334155;border-radius:6px;
  padding:0.75rem 1rem;overflow-x:auto;margin:0.5rem 0}
.nicegui-markdown pre code{border:none;padding:0;font-size:0.85em}
.nicegui-markdown ul,.nicegui-markdown ol{
  padding-left:1.5rem;margin:0.4rem 0}
.nicegui-markdown li{margin:0.2rem 0}
.q-tab-panels { background: #0f172a !important; }
.q-tab-panel  { background: #0f172a !important; padding: 0 !important; }
.q-tab { color: #64748b !important; font-size: 0.85rem; font-weight: 500; }
.q-tab--active { color: #38bdf8 !important; }
.q-tabs { background: #1e293b !important; border-bottom: 1px solid #334155; }
.q-tab__indicator { background: #38bdf8 !important; }
.q-table { background: #0f172a !important; color: #e2e8f0 !important; }
.q-table thead tr th { background: #1e293b !important; color: #64748b !important; font-size: 0.7rem; letter-spacing: 0.06em; border-bottom: 1px solid #334155 !important; }
.q-table tbody tr td { border-bottom: 1px solid #1e293b !important; font-size: 0.82rem; }
.q-table tbody tr:hover td { background: #1e293b !important; }
</style>
""")

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

        with ui.tabs().classes("w-full") as tabs:
            chat_tab = ui.tab("Chat")
            admin_tab = ui.tab("Admin")

        with ui.tab_panels(tabs, value=chat_tab).classes("w-full").style(
            "height:calc(100vh - 168px); overflow:hidden"
        ):
            # ------------------------------------------------------------------ Chat tab
            with ui.tab_panel(chat_tab).style("padding:0; height:100%; overflow:hidden"):
                with ui.row().style("width:100%; height:100%; gap:0; overflow:hidden"):

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

                            mastery = profile.get("mastery_level") or "—"
                            ui.label(f"Level: {mastery.capitalize() if mastery != '—' else '—'}").style(
                                "font-size:0.8rem; color:#94a3b8"
                            )

                            topic_scores: dict = profile.get("topic_scores") or {}

                            if not topic_scores:
                                ui.label("Start chatting to build your profile.").style(
                                    "font-size:0.8rem; color:#64748b; font-style:italic"
                                )
                            else:
                                ui.label("Topic Scores").style(
                                    "font-size:0.75rem; font-weight:600; color:#64748b; margin-top:0.25rem"
                                )
                                for slug, label in _MODULE_LABELS.items():
                                    score: float = topic_scores.get(slug, 0.0)
                                    with ui.column().style("gap:0.4rem; width:100%"):
                                        ui.label(label).style("font-size:0.72rem; color:#94a3b8")
                                        ui.linear_progress(value=score).style(
                                            "width:100%; height:10px"
                                        ).props("color=sky-600 track-color=slate-700")

                            gaps: list = profile.get("gaps") or []
                            if gaps:
                                ui.label("Gaps").style(
                                    "font-size:0.75rem; font-weight:600; color:#64748b; margin-top:0.5rem"
                                )
                                with ui.row().style("flex-wrap:wrap; gap:0.3rem"):
                                    for gap in gaps:
                                        display = _MODULE_LABELS.get(gap, gap.replace("_", " ").title())
                                        ui.badge(display).style(
                                            "background:#1e3a5f; color:#bfdbfe; font-size:0.75rem; "
                                            "border-radius:4px; padding:0.25rem 0.6rem"
                                        )

                            interaction_count = profile.get("interaction_count", 0)
                            last_activity = profile.get("last_activity_at")
                            ui.label(f"Queries: {interaction_count}").style(
                                "font-size:0.72rem; color:#64748b; margin-top:0.5rem"
                            )
                            if last_activity:
                                last_str = (last_activity[:16].replace("T", " ") if len(last_activity) >= 16 else last_activity)
                                ui.label(f"Last active: {last_str}").style(
                                    "font-size:0.72rem; color:#64748b"
                                )

                    await profile_panel()

                    # --- Chat area ---
                    with ui.column().style("flex:1; height:100%; overflow:hidden; position:relative"):
                        with ui.column().style(
                            "flex:1; width:100%; max-width:900px; margin:0 auto; padding:1.5rem; "
                            "padding-bottom:90px; overflow-y:auto; height:100%"
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

            # ------------------------------------------------------------------ Admin tab
            with ui.tab_panel(admin_tab).style(
                "padding:0; overflow-y:auto; height:100%; background:#0f172a"
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

                        # Fetch health
                        try:
                            r_health = await http().get("/api/health", headers=auth_headers())
                            health_data = r_health.json() if r_health.status_code == 200 else {}
                        except Exception:
                            health_data = {}

                        health_status = health_data.get("status", "unknown")
                        is_healthy = health_status.lower() in ("healthy", "ok")

                        # ---- Page header strip ----
                        with ui.row().style(
                            "width:100%; background:#1e293b; border-bottom:1px solid #334155; "
                            "padding:1.25rem 2rem; align-items:center; justify-content:space-between"
                        ):
                            with ui.column().style("gap:0.2rem"):
                                ui.label("Admin Dashboard").style(
                                    "font-size:1.1rem; font-weight:600; color:#38bdf8"
                                )
                                ui.label("System overview & user management").style(
                                    "font-size:0.78rem; color:#64748b"
                                )
                            ui.button("Refresh", on_click=admin_panel.refresh).props("flat dense").style(
                                "color:#64748b"
                            )

                        # ---- Stat cards row ----
                        latest_join = "—"
                        if users:
                            raw_created = users[0].get("created_at") or ""
                            latest_join = raw_created[:10] if raw_created else "—"

                        with ui.row().style(
                            "width:100%; padding:1.5rem 2rem 0; gap:1rem; flex-wrap:wrap"
                        ):
                            # Card helper
                            def stat_card(label_text, value_text, value_color, description):
                                with ui.column().style(
                                    "background:#1e293b; border:1px solid #334155; border-radius:12px; "
                                    "padding:1rem 1.25rem; min-width:160px; flex:1; gap:0.2rem"
                                ):
                                    ui.label(label_text).style(
                                        f"font-size:0.65rem; color:#64748b; letter-spacing:0.08em; text-transform:uppercase"
                                    )
                                    ui.label(value_text).style(
                                        f"font-size:1.6rem; font-weight:700; color:{value_color}"
                                    )
                                    ui.label(description).style(
                                        "font-size:0.7rem; color:#64748b"
                                    )

                            stat_card("USERS", str(len(users)), "#38bdf8", "registered")
                            stat_card("LATEST JOIN", latest_join, "#a78bfa", "most recent signup")
                            stat_card(
                                "SYSTEM",
                                "Healthy" if is_healthy else "Degraded",
                                "#4ade80" if is_healthy else "#f87171",
                                "all services",
                            )
                            stat_card("STACK", "RAG · LLM · SQLite", "#fb923c", "core components")

                        # ---- Two-column content area ----
                        with ui.row().style(
                            "width:100%; padding:1.5rem 2rem; gap:1.5rem; align-items:flex-start; flex-wrap:wrap"
                        ):
                            # -- Left column: user table --
                            with ui.column().style("flex:2; min-width:400px; gap:0.75rem"):
                                # Section header
                                with ui.row().style("align-items:center; gap:0.5rem"):
                                    ui.label("Registered Users").style(
                                        "font-size:0.7rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.06em"
                                    )
                                    ui.badge(str(len(users))).style(
                                        "background:#1e3a5f; color:#38bdf8; font-size:0.72rem; border-radius:4px; padding:0.15rem 0.5rem"
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

                                    async def handle_delete(row):
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

                                    table.on("delete", lambda e: asyncio.ensure_future(handle_delete(e.args)))

                            # -- Right column: health + monitoring --
                            with ui.column().style("flex:1; min-width:280px; gap:0"):

                                # Card 1: System Health
                                with ui.column().style(
                                    "background:#1e293b; border:1px solid #334155; border-radius:12px; "
                                    "padding:1rem 1.25rem; gap:0.5rem"
                                ):
                                    ui.label("SYSTEM HEALTH").style(
                                        "font-size:0.65rem; color:#64748b; letter-spacing:0.08em; text-transform:uppercase"
                                    )

                                    service_keys = ["api", "rag_pipeline", "vectorstore", "redis", "llm"]
                                    services_data = health_data.get("services", {})

                                    for key in service_keys:
                                        svc_status = ""
                                        if services_data:
                                            svc_status = str(services_data.get(key, "")).lower()
                                        elif health_data:
                                            # flat health response — treat top-level status for api
                                            svc_status = health_status.lower() if key == "api" else "unknown"
                                        else:
                                            svc_status = "unknown"

                                        if svc_status in ("healthy", "ok"):
                                            dot_color = "#4ade80"
                                        elif svc_status == "degraded":
                                            dot_color = "#fbbf24"
                                        else:
                                            dot_color = "#f87171"

                                        with ui.row().style(
                                            "display:flex; align-items:center; gap:0.5rem; padding:0.25rem 0"
                                        ):
                                            ui.label("●").style(f"color:{dot_color}; font-size:0.7rem")
                                            ui.label(key.replace("_", " ").title()).style(
                                                "font-size:0.8rem; color:#94a3b8"
                                            )

                                # Card 2: Monitoring placeholder
                                with ui.column().style(
                                    "background:#1e293b; border:1px dashed #334155; border-radius:12px; "
                                    "padding:1rem 1.25rem; gap:0.6rem; margin-top:1rem"
                                ):
                                    ui.label("MONITORING").style(
                                        "font-size:0.65rem; color:#64748b; letter-spacing:0.08em; text-transform:uppercase"
                                    )
                                    ui.label(
                                        "Grafana & Prometheus dashboards will be embedded here after deployment."
                                    ).style("font-size:0.8rem; color:#64748b; font-style:italic")
                                    with ui.row().style("gap:0.5rem; flex-wrap:wrap; margin-top:0.25rem"):
                                        for tag in ("Grafana", "Prometheus"):
                                            ui.label(tag).style(
                                                "background:#0f172a; color:#64748b; border:1px solid #334155; "
                                                "border-radius:4px; padding:0.2rem 0.6rem; font-size:0.72rem"
                                            )

                    await admin_panel()

        # Footer — input bar, hidden when Admin tab is active
        footer = ui.footer().style(
            "background:#1e293b; border-top:1px solid #334155; padding:1rem 2rem"
        )
        with footer:
            with ui.row().style("width:100%; max-width:900px; margin:0 auto; gap:0.75rem"):
                question_input = ui.input(
                    placeholder="Ask about RAG, vector databases, LangChain..."
                ).style(
                    "flex:1; background:#0f172a; border:1px solid #334155; color:#e2e8f0; border-radius:8px"
                )
                send_btn = ui.button("Send").style(
                    "background:#0369a1; color:white; border-radius:8px"
                )

        tabs.on("update:model-value", lambda e: footer.set_visibility(e.args == "Chat"))

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
                        "background:#0369a1; color:#f0f9ff; width:fit-content; align-self:flex-end; "
                        "border-radius:12px; word-break:break-word; overflow-wrap:break-word; overflow:hidden"
                    ):
                        ui.label(question).style("word-break:break-word; overflow-wrap:break-word; max-width:100%")

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
                # Collect SSE tokens from streaming /api/chat; render complete answer after stream.
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
                thinking.set_visibility(False)

            with chat_area:
                with ui.column().style("align-self:flex-start; max-width:75%; gap:0.2rem"):
                    ui.label("RAG Assistant").style("font-size:0.7rem; color:#64748b")
                    with ui.card().style(
                        "background:#1e293b; border:1px solid #334155; width:fit-content; "
                        "border-radius:12px; word-break:break-word; overflow-wrap:break-word; overflow:hidden"
                    ):
                        ui.markdown(result["answer"]).style("width:100%; word-break:break-word; overflow-wrap:break-word")

                    cache_color = "#14532d" if result["cache_hit"] != "none" else "#1e293b"
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
                                "background:#0f172a; color:#64748b; font-size:0.7rem"
                            )
                            ui.badge(f"{len(result['chunks'])} chunks").style(
                                "background:#0f172a; color:#64748b; font-size:0.7rem"
                            )
                            ui.badge(f"trace: {result['trace_id']}").style(
                                "background:#0f172a; color:#64748b; font-size:0.7rem"
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

                    test_q = done_data.get("test_question")
                    if test_q:
                        with ui.card().style(
                            "background:#1e3a5f; border:1px solid #3b82f6; width:fit-content; "
                            "border-radius:12px; padding:0.75rem 1rem; margin-top:0.75rem; "
                            "word-break:break-word; overflow-wrap:break-word; overflow:hidden"
                        ):
                            ui.label("Knowledge Check").style(
                                "font-size:0.7rem; font-weight:600; color:#60a5fa; margin-bottom:0.35rem"
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
