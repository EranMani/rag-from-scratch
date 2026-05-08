import asyncio
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pathlib import Path
from langchain_community.document_loaders import TextLoader
from rag.pipeline.indexer import ingest_documents
from app.auth.deps import get_current_user


router = APIRouter(prefix="/api", tags=["documents"])
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_SUFFIXES = {".txt", ".md"}


@router.post("/ingest")
async def ingest_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload a .txt or .md file and add it to the knowledge base"""
    safe_name = Path(file.filename).name          # strips all ../ and leading /
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid filename")

    if Path(safe_name).suffix.lower() not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="Only .txt and .md files are accepted")

    destination = (UPLOAD_DIR / safe_name).resolve()
    if not destination.is_relative_to(UPLOAD_DIR.resolve()):
        raise HTTPException(status_code=400, detail="Invalid filename")

    destination.write_bytes(await file.read())

    loader = TextLoader(str(destination), encoding="utf-8")
    docs = loader.load()
    count = await asyncio.to_thread(ingest_documents, docs)
    return {"status": "ok", "chunks_ingested": count, "filename": safe_name}
