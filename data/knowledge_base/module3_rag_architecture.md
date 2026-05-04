# Module 3: The RAG Architecture

## What Is RAG?
Retrieval-Augmented Generation is a framework that gives LLMs access to external knowledge at inference time. Instead of relying only on training data, the model retrieves relevant documents and uses them to generate accurate, grounded answers.

## The Three Pillars

### 1. Retrieval
- User asks a question
- The question is embedded into a vector
- The vector database finds the most similar document chunks
- Top-k chunks are returned (typically k=3 to 5)

### 2. Augmentation
- The retrieved chunks are injected into the prompt
- The LLM now has the facts it needs to answer correctly
- This is the "context" in the prompt template

### 3. Generation
- The LLM generates a response grounded in the retrieved context
- It can cite sources (metadata from chunks)
- It will say "I don't know" if no relevant chunks are found

## The LCEL Chain
In LangChain, the RAG pipeline is expressed as:

```
chain = {"context": retriever, "question": passthrough} | prompt | llm | parser
```

## RAG vs Alternatives

| Method | Best For | Pros | Cons |
|---|---|---|---|
| Prompt Engineering | Tone, rules | Fast | Limited by context window |
| Fine-Tuning | Style, patterns | Baked in | Slow, expensive, no citations |
| RAG | Dynamic facts | Up-to-date, cites sources | Setup complexity |

## Retrieval Quality
The most critical metric. If the wrong chunks are retrieved, the answer will be wrong even if the LLM is perfect. Measured by:
- Precision: Are retrieved chunks relevant?
- Recall: Are all relevant chunks retrieved?
