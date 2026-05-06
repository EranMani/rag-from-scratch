from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from app.core.logging_config import logger
from app.core.metrics import LLM_CALLS
from rag.providers import get_provider
from rag.resilience.circuit_breaker import openai_cb


RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert on RAG (Retrieval-Augmented Generation) systems.
Answer questions using ONLY the provided context. If the context doesn't contain
the answer, say 'I don't have information about that in my knowledge base.'
Always cite which module the information comes from."""),
    ("human", """Context from knowledge base:
{context}

Question: {question}

Answer:"""),
])


def format_context(docs: list[Document]) -> str:
    """Combine retrieved chunks into a single context string with source lables"""
    parts = []
    # Run on all documents, fetch source from metadata and append to list
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "unknown")
        parts.append(f"[Source {i}: {source}]\n{doc.page_content}")

    # Convert parts to single context string
    return "\n\n---\n\n".join(parts)


def generate(question: str, docs: list[Document]) -> str:
    """
    Augment the prompt with retrieved docs and generate an answer
    Falls back to Ollama if OPENAI circuit breaker is OPEN
    """

    # Get the context as single string
    context = format_context(docs)
    # Get the LLM provider (OPENAI | OLLAMA)
    provider = get_provider() 
    llm = provider.get_llm()

    # LCEL chain: prompt | llm | parser
    chain = RAG_PROMPT | llm | StrOutputParser()

    try:
        response = chain.invoke({"context": context, "question": question})
        if provider.provider_name() == "openai":
            openai_cb.record_success()
        
        LLM_CALLS.labels(provider=provider.provider_name(), status="success").inc()
        logger.info(
            "Generation complete",
            extra={
                "provider": provider.provider_name(),
                "question": question[:80],
                "response_length": len(response),
            }
        )
        return response
    except Exception as e:
        if provider.provider_name() == "openai":
            openai_cb.record_failure()

        LLM_CALLS.labels(provider=provider.provider_name(),  status="error").inc()
        logger.error("Generation failed", extra={"error": str(e)})
        raise
