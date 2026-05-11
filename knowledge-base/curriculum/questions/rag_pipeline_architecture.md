# Question Bank: `rag_pipeline_architecture`
# Phase: 1 — Foundations
# Maintained by: Lara (RAG Curriculum Specialist)
# Last updated: 2026-05-11 (Commit 22)

---

## Q1 — The two phases of RAG

**Difficulty:** beginner

**Question:**
RAG architectures are commonly described as having two distinct phases. Name them, briefly
describe what happens in each, and explain why they are kept separate.

**Correct answer criteria:**
- Phase 1 is indexing (also called ingestion or offline phase): raw documents are loaded,
  split into chunks, embedded, and stored in a vector database
- Phase 2 is querying (also called retrieval or online phase): the user query is embedded,
  nearest-neighbor search retrieves relevant chunks, and those chunks are injected into
  the LLM prompt for generation
- They are kept separate because indexing is expensive (embedding all documents) and done
  in advance; querying must be fast (milliseconds) and happens in real time

**Partial credit criteria:**
- Correctly names both phases but describes only one with accuracy
- Describes what happens in both phases but cannot explain why they're separated

**Incorrect / no-credit criteria:**
- Describes RAG as a single unified pipeline where the LLM searches documents in real time
- Conflates the two phases into one continuous process
- Names the phases incorrectly in a way that suggests fundamental confusion

---

## Q2 — Drawing the pipeline

**Difficulty:** beginner

**Question:**
List every component in a minimal RAG pipeline in order, for both the indexing phase and
the query phase. Use component names (e.g., "document loader," "text splitter"), not
framework names.

**Correct answer criteria:**
**Indexing phase (in order):**
1. Document loader — reads raw source documents
2. Text splitter / chunker — splits documents into chunks
3. Embedding model — converts chunks to vectors
4. Vector store — stores vectors (and associated text) for retrieval

**Query phase (in order):**
1. Embedding model — converts user query to a vector
2. Vector store / retriever — finds top-K nearest vectors to the query
3. Prompt template — combines retrieved chunks with the user question
4. LLM — generates the final answer from the constructed prompt

**Partial credit criteria:**
- Lists most components but omits one (e.g., forgets the prompt template, or lists
  the embedding model only for one phase)
- Lists all components but not in correct order (e.g., puts embedding before splitting)

**Incorrect / no-credit criteria:**
- Lists fewer than 5 of the 8 components
- Describes the LLM as directly searching the vector store
- Omits the vector store entirely

---

## Q3 — What context injection actually means

**Difficulty:** beginner

**Question:**
In RAG, what does "context injection" mean? Where in the pipeline does it happen, and
what exactly is being injected into what?

**Correct answer criteria:**
- Context injection is the step where retrieved document chunks are inserted into the LLM
  prompt alongside the user's question
- It happens at the prompt template stage — after retrieval and before generation
- The chunks (text passages from the document corpus) are injected into a structured
  prompt template, typically as a "Context:" section, so the LLM generates an answer
  grounded in those specific passages rather than purely from its training data
- The LLM never directly accesses the vector store — it only sees what the prompt template
  places in its input window

**Partial credit criteria:**
- Describes context injection as "giving the LLM information" without specifying that
  it is the retrieved chunks injected via the prompt template
- Correctly describes the mechanism but states the LLM searches for context itself

**Incorrect / no-credit criteria:**
- Describes context injection as fine-tuning the LLM with the documents
- Claims the LLM directly queries the vector database
- Confuses context injection with the embedding process

---

## Q4 — Tracing a retrieval failure

**Difficulty:** intermediate

**Question:**
A user asks a question and the RAG system returns an incorrect answer. Your investigation
reveals that the retrieved chunks were all from the wrong section of the document corpus.
Which stage of the pipeline most likely failed, and what are three possible causes?

**Correct answer criteria:**
- The retrieval stage failed (the vector store returned semantically incorrect nearest
  neighbors)
- Three possible causes (any three of the following are acceptable):
  1. Poor chunking — relevant content was split across chunk boundaries, leaving no
     single chunk containing a complete, searchable answer
  2. Embedding mismatch — the query and document chunks were not embedded with the same
     model, or the model does not represent the query's semantic space well
  3. Insufficient top-K — not enough chunks were retrieved to include the relevant one;
     the correct chunk ranked 6th but only K=5 was retrieved
  4. Metadata pollution — the vector store contains many near-duplicate or off-topic
     chunks from an unrelated document set that ranked higher
  5. Query representation failure — the user query is ambiguous or contains vocabulary
     not well-represented in the embedding model

**Partial credit criteria:**
- Correctly identifies the retrieval stage but only names one or two causes
- Names three causes but attributes the failure to the wrong pipeline stage

**Incorrect / no-credit criteria:**
- Attributes the failure to the LLM generation stage (the chunks were wrong before
  the LLM ever saw them)
- Cannot identify the retrieval stage as the failure point
- Lists causes that are unrelated to retrieval (e.g., "the LLM hallucinated")

**Follow-up probe:**
"If the retrieved chunks were correct but the answer was still wrong — which stage would
you investigate next, and why?"

---

## Q5 — RAG vs. fine-tuning

**Difficulty:** intermediate

**Question:**
Your team is deciding between RAG and fine-tuning an LLM to answer questions about your
company's internal documentation. List two scenarios where RAG is the better choice and
one scenario where fine-tuning is more appropriate. Justify each.

**Correct answer criteria:**
- RAG better for:
  1. Documentation that changes frequently — RAG retrieves from an updatable index;
     fine-tuned models require expensive retraining when documents change
  2. When you need the LLM to cite specific source passages — RAG can return the exact
     retrieved chunks alongside the answer; fine-tuning bakes knowledge into weights
     without attributable source
  3. (Acceptable alternative): Large document corpora that exceed what fine-tuning
     can memorize — RAG accesses documents at query time, not from memorized weights
- Fine-tuning better for:
  1. Changing the model's behavior, tone, or output format (e.g., always respond in a
     specific structured format) — style/format adjustments are not addressable by RAG
  2. (Acceptable alternative): Teaching the model domain-specific reasoning patterns
     or terminology that appears so frequently that memorizing it reduces inference cost

**Partial credit criteria:**
- Two correct RAG scenarios but fine-tuning scenario is weak or incorrect
- Identifies the distinction in principle (freshness vs. behavior) but cannot give
  concrete scenarios

**Incorrect / no-credit criteria:**
- Claims fine-tuning is always better for domain-specific tasks
- Claims RAG eliminates the need for fine-tuning in all cases
- Cannot identify any scenario where fine-tuning is appropriate

---

## Q6 — The role of the prompt template

**Difficulty:** intermediate

**Question:**
Why does a RAG system need a prompt template? What specific things must a well-designed
RAG prompt template always include, and what happens if the template is missing or
poorly designed?

**Correct answer criteria:**
- The prompt template structures the LLM's input so it knows the role of each piece of
  information: "this is context from my documents" vs. "this is the user's question"
- A well-designed template must include:
  1. A system instruction that tells the LLM to answer from the provided context
     (and what to do when context is insufficient)
  2. A clearly delimited context block containing the retrieved chunks
  3. The user's question
  4. (Optional but good practice) An output format directive
- Without a template (or with a poor one): the LLM may blend context with world knowledge,
  ignore relevant passages, hallucinate answers not supported by context, or fail to
  signal when it cannot answer

**Partial credit criteria:**
- Describes the template as "putting context and question together" without explaining
  what the system instruction component does
- Lists the required components but cannot explain what breaks when the template is missing

**Incorrect / no-credit criteria:**
- Describes the template as optional formatting preference
- Cannot name the components that must be present
- Claims the LLM knows how to use context without being instructed

---

## Q7 — Index freshness

**Difficulty:** intermediate

**Question:**
Your RAG system was indexed over your product documentation last month. A critical product
feature was updated this week, but users are receiving answers based on the old documentation.
What is this problem called, and what are two architectural approaches to prevent it?

**Correct answer criteria:**
- This is called index staleness (or stale index / index drift)
- Approach 1: incremental indexing — a change-detection mechanism (webhook, file watcher,
  database trigger) detects document updates and re-embeds only the changed chunks,
  replacing the stale vectors in the index
- Approach 2: scheduled full re-indexing — the entire corpus is re-indexed on a cadence
  (hourly, daily) to ensure freshness within an acceptable staleness window
- (Acceptable alternative): Document versioning with metadata timestamps, combined with
  a retrieval filter that excludes chunks from outdated document versions

**Partial credit criteria:**
- Correctly identifies index staleness but only describes one approach to prevent it
- Describes incremental vs. scheduled re-indexing without explaining how detection works

**Incorrect / no-credit criteria:**
- Describes the solution as fine-tuning the LLM with new information
- Claims the LLM will automatically learn about new documentation
- Cannot identify the staleness problem or any architectural response to it

---

## Q8 — Retrieval failure vs. generation failure

**Difficulty:** advanced

**Question:**
You are debugging a RAG system that is producing wrong answers. Describe a diagnostic
procedure that would allow you to definitively determine whether the failure is in the
retrieval stage (wrong chunks returned) or the generation stage (correct chunks returned,
wrong answer generated). What would you look for in each case?

**Correct answer criteria:**
- Step 1: Inspect the retrieved chunks directly — log or display the exact chunks that
  were passed to the LLM for the failing query
- Step 2: Manual evaluation — a human (or automated evaluator) judges whether the correct
  answer is present in the retrieved chunks
  - If the answer IS in the chunks and the LLM still answered wrong: generation failure
    (the LLM ignored context, hallucinated, or misread the passage)
  - If the answer is NOT in the chunks: retrieval failure (the wrong chunks were returned)
- For retrieval failure: investigate embedding quality, chunking strategy, top-K setting,
  and query representation
- For generation failure: investigate prompt template design, context ordering, LLM
  instruction following, and whether the answer requires multi-chunk synthesis

**Partial credit criteria:**
- Describes checking the retrieved chunks but does not specify how to distinguish
  retrieval vs. generation failure
- Identifies retrieval vs. generation as distinct failure modes but cannot describe
  a concrete diagnostic procedure

**Incorrect / no-credit criteria:**
- Diagnoses by examining the final LLM output only (without checking intermediate stages)
- Cannot distinguish retrieval failures from generation failures as distinct categories
- Recommends only switching LLMs or embedding models without diagnostic steps

**Follow-up probe:**
"If the retrieved chunks contain the correct information but the LLM still answers
incorrectly, what three things would you change first in the prompt template?"
