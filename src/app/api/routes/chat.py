import uuid
from fastapi import APIRouter
from pydantic import BaseModel
from app.core.metrics import REQUEST_COUNT, REQUEST_LATENCY
from rag.chain import run_rag_pipeline

router = APIRouter(prefix="/api", tags=["chat"])



class ChatRequest(BaseModel):
    question: str
    session_id: str = None
    user_id: str = None


class ChatResponse(BaseModel):
    answer: str
    cache_hit: str
    chunks: list[dict]
    latency_ms: int
    trace_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    with REQUEST_LATENCY.labels(endpoint="/chat").time():
        result = run_rag_pipeline(
            question=body.question,
            session_id=body.session_id or str(uuid.uuid4()),
            user_id=body.user_id
        )
    REQUEST_COUNT.labels(endpoint="/chat", status="success").inc()
    return ChatResponse(**result)