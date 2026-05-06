from fastapi import APIRouter, UploadFile, File
from pathlib import Path
from langchain_community.document_loaders import TextLoader
from rag.pipeline.indexer import ingest_documents


router = APIRouter(prefix="/api", tags=["documents"])
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/ingest")
async def ingest_file(file: UploadFile = File(...)):
    """Upload a .txt or .md file and add it to the knowledge base"""
    destination = UPLOAD_DIR / file.filename
    destination.write_bytes(await file.read())

    loader = TextLoader(str(destination), encoding="utf-8")
    docs = loader.load()
    count = ingest_documents(docs)
    return {"status": "ok", "chunks_ingested": count, "filename": file.filename}
