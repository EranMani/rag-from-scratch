# Module 4: Data Preparation and Chunking

## Why Chunking Is Critical
You cannot embed a 500-page document as a single vector — it would lose all precision. The vector would represent everything and nothing specifically. Chunking breaks documents into focused, searchable pieces.

## The Precision Problem
Without chunking: a query for "remote work" might return an entire 50-page handbook. The LLM context window fills up, most content is irrelevant, and the answer degrades.

With chunking: the same query returns a specific 300-character paragraph about remote work policy.

## Chunking Strategies

### Fixed-Size Chunking
Split text into equal-length pieces (e.g., 500 characters each). Fast and simple but can break sentences mid-thought.

### Sentence/Paragraph-Based
Split at grammatical boundaries — periods, newlines, double newlines. Preserves meaning. Used by RecursiveCharacterTextSplitter in LangChain.

### RecursiveCharacterTextSplitter (LangChain)
Tries splitting on: `["\n\n", "\n", " ", ""]` in order. Falls through to the next separator if chunks are still too large. Best general-purpose splitter.

## Chunk Overlap
The most important chunking parameter. If "Dogs are allowed" ends Chunk A and "on Fridays" starts Chunk B, the meaning is lost without overlap.

Overlap copies the last N characters of Chunk A to the start of Chunk B, ensuring no sentence gets split across chunks without context.

- Typical overlap: 50–200 characters
- Rule of thumb: 10–20% of chunk size

## Parameters in This System
- `chunk_size`: 500 characters (focused and precise)
- `chunk_overlap`: 100 characters (20% overlap)
- Splitter: RecursiveCharacterTextSplitter
