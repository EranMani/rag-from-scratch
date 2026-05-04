# Module 1: The Core Problem in Information Retrieval

## The Semantic Gap
The fundamental challenge is the semantic gap — the difference between how humans phrase questions and how computers store data. A search for "clothing rules" fails to find a document titled "Dress Code" in a traditional SQL database because exact match is required.

## SQL Limitations
- Exact match failure: LIKE queries require precise formatting
- No concept of meaning — only character comparison
- Cannot understand that "remote work" and "work from home" are the same

## Keyword Search Methods
- **TF-IDF**: Term Frequency-Inverse Document Frequency. Scores words by how often they appear in a doc vs the whole corpus. Common words score low.
- **BM25**: Improved TF-IDF. Adds length normalization and saturation — a word appearing 100 times is not 10x better than one appearing 10 times. Used as fallback in this system.

## LLM Memory and Context Window
Large Language Models have a knowledge cutoff date — their training data has a fixed endpoint. They cannot know about events after training or private company data.

The context window is the LLM's short-term memory:
- Small models: 2,000–4,000 tokens (~1,500–3,000 words)
- Large models: up to 1 million tokens (but expensive and slow)
- FIFO eviction: oldest messages are dropped when the window fills

## Why This Matters for RAG
RAG solves both problems: it bridges the semantic gap using vector embeddings, and extends LLM memory by retrieving relevant context at query time rather than storing everything in the context window.
