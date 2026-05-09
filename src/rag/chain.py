import time
import uuid
from langchain_core.documents import Document
from app.core.logging_config import logger
from rag.pipeline.retriever import retrieve
from rag.pipeline.generator import generate
from rag.cache.redis_cache import cache
from rag.memory.conversation import session_memory


def run_rag_pipeline(
    question: str,
    session_id: str = None,
    user_id: str = None,
) -> dict:
    """
    Full RAG pipeline:
    1. Check query cache
    2. Retrieve relevant chunks (semantic or BM25 fallback)
    3. Check LLM response cache
    4. Generate answer (with circuit breaker protection)
    5. Store in caches and memory

    Returns a dict with the answer and debug metadata
    """

    start = time.perf_counter()
    trace_id = str(uuid.uuid4())[:8]
    session_id = session_id or "default"

    logger.info(
        "RAG pipeline start",
        extra={"trace_id": trace_id, "question": question[:80], "session_id": session_id}
    )

    # ======== STEP1 - Query cache check ===============
    # Known gap: cache key is question only — does not include session_id or
    # conversation history. A repeated question in an active session may be
    # served from this cache, bypassing history injection entirely. Accepted
    # for Commits 03–16; cache key is extended in Commit 17 (adds user_level).
    # History is never incorporated into the cache key — this is a permanent
    # known limitation. See DECISIONS.md: "Conversation history not included
    # in LLM cache key".
    cached_answer = cache.get_query(question)
    if cached_answer:
        latency = round((time.perf_counter() - start) * 1000)
        logger.info("Served from query cache", extra={"trace_id": trace_id, "latency_ms": latency})
        return {
            "answer": cached_answer,
            "cache_hit": "query",
            "chunks": [],
            "latency_ms": latency,
            "trace_id": trace_id,
        }

    # ======== STEP2 - Retrieve relevant chunks ========
    docs: list[Document] = retrieve(question, k=4)

    # ======== STEP2b - Load conversation history ======
    # format_history() is called AFTER retrieve() so history influences
    # generation only, not retrieval — this is intentional per design.
    conversation_history = session_memory.format_history(session_id)

    # ======== STEP3 - LLM cache check =================
    prompt_key = question + "".join(d.page_content[:100] for d in docs)
    cached_response = cache.get_llm_response(prompt_key)

    if cached_response:
        answer = cached_response
        cache_hit = "llm"
    else:
        # ======== STEP4 - Generate ====================
        answer = generate(question, docs, conversation_history)
        cache.set_llm_response(prompt_key, answer)
        cache_hit = "none"

    # ======== STEP5 - Store in query cache + memory ===
    cache.set_query(question, answer)
    session_memory.add_human(session_id, question)
    session_memory.add_assistant(session_id, answer)

    latency = round((time.perf_counter() - start) * 1000)
    logger.info(
        "RAG pipeline complete",
        extra={
            "trace_id": trace_id,
            "latency_ms": latency,
            "cache_hit": cache_hit,
            "chunks_retrieved": len(docs),
        }
    )

    return {
        "answer": answer,
        "cache_hit": cache_hit,
        "chunks": [{"content": d.page_content[:200], "source": d.metadata.get("source", "")} for d in docs],
        "latency_ms": latency,
        "trace_id": trace_id,
    }
