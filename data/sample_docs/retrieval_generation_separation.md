# Retrieval and Generation Separation

A clean RAG system keeps retrieval separate from generation. Retrieval finds
the most relevant chunks from local documents or a vector store. Generation then
uses those chunks as grounded context for the answer.

Separating these responsibilities makes the system easier to debug: if an
answer is weak, you can inspect whether retrieval found the right context before
changing the prompt or model.
