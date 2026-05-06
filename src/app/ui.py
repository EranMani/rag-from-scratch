import uuid
from nicegui import ui
from rag.chain import run_rag_pipeline


def create_session() -> dict:
    return {"session_id": str(uuid.uuid4()), "messages": []}


def setup_ui(fastapi_app):
    """Mount NiceGUI onto the existing FastAPI app."""

    @ui.page("/")
    def index():
        session = create_session()

        # Page styling
        ui.query("body").style("background:#0f172a; color:#e2e8f0; font-family:system-ui")

        # Header
        with ui.header().style("background:#1e293b; border-bottom:1px solid #334155; padding:1rem 2rem"):
            ui.label("Educational RAG System").style(
                "font-size:1.25rem; font-weight:600; color:#38bdf8"
            )
            ui.label(
                "Ask anything about RAG architecture, vector databases, LangChain, caching, or circuit breakers."
            ).style("font-size:0.8rem; color:#94a3b8; margin-top:0.25rem")

        # Chat scroll area
        with ui.column().style("flex:1; width:100%; max-width:900px; margin:0 auto; padding:1.5rem"):
            chat_area = ui.column().style("width:100%; gap:1rem")

            # Welcome message
            with chat_area:
                with ui.card().style(
                    "background:#1e293b; border:1px solid #334155; max-width:75%; border-radius:12px"
                ):
                    ui.markdown(
                        "Welcome! I am a RAG system that answers questions about how RAG systems work.\n\n"
                        "Try asking: **How does chunking work?** or **What is a circuit breaker?**"
                    )

        # Input bar
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

        # Send handler
        async def send():
            question = question_input.value.strip()
            if not question:
                return

            question_input.value = ""
            send_btn.disable()

            # Render human message immediately
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

            # Assistant response card
            with chat_area:
                with ui.card().style(
                    "background:#1e293b; border:1px solid #334155; max-width:75%; border-radius:12px"
                ):
                    ui.markdown(result["answer"])

                    # Meta badges
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

                    # Retrieved chunks (collapsed)
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

    ui.run_with(fastapi_app, mount_path="/", storage_secret="rag-secret-key")
