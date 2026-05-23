# Question Bank: `chunking_strategies`
# Phase: 2 — Core Components
# Maintained by: Lara (RAG Curriculum Specialist)
# Last updated: 2026-05-11 (Commit 22)

---

## Q1 — Fixed-size vs. semantic chunking

**Difficulty:** novice

**Question:**
Explain the difference between fixed-size chunking and semantic chunking. Give one
concrete example of a document type where each approach is more appropriate.

**Correct answer criteria:**
- Fixed-size chunking: splits documents into chunks of a fixed token or character count,
  regardless of content boundaries. Simple and fast, but may split mid-sentence or
  mid-paragraph
- Semantic chunking: splits at natural content boundaries — sentence boundaries, paragraph
  breaks, section headers, or semantic coherence boundaries — preserving meaning within
  each chunk
- Fixed-size example: log files, streaming data, or any corpus where content boundaries
  are uniform and meaning is locally self-contained (each log entry stands alone)
- Semantic example: legal contracts, research papers, or technical documentation where
  splitting mid-clause or mid-argument destroys the chunk's usability as a retrieval unit

**Partial credit criteria:**
- Correctly distinguishes the two approaches but cannot give a concrete example for each
- Gives examples but reverses which approach suits which document type

**Incorrect / no-credit criteria:**
- Describes both approaches as equivalent with no tradeoffs
- Believes fixed-size is always inferior and should never be used
- Cannot explain what "semantic boundary" means

---

## Q2 — Chunk overlap mechanics

**Difficulty:** novice

**Question:**
What is chunk overlap in a RAG chunking strategy? Why does it exist, and what is the
typical risk of setting overlap too high?

**Correct answer criteria:**
- Chunk overlap is the number of tokens (or characters) shared between consecutive chunks —
  chunk N ends with the same N tokens that chunk N+1 begins with
- It exists to preserve continuity: without overlap, content that spans a chunk boundary
  (a sentence that starts in chunk N and ends in chunk N+1) would be split, making neither
  chunk contain a complete, retrievable unit of meaning
- Risk of too-high overlap: redundancy and storage bloat — if overlap is 50% of chunk size,
  you are storing every piece of content twice, doubling index size and potentially
  returning near-duplicate chunks in retrieval results

**Partial credit criteria:**
- Correctly explains what overlap is but cannot explain why it exists
- Explains the purpose but does not identify the risk of excessive overlap

**Incorrect / no-credit criteria:**
- Describes overlap as a mistake or bug to be avoided
- Claims overlap causes retrieval failures (mild overlap improves retrieval; excessive
  overlap causes redundancy, not failures)
- Cannot describe the mechanism of overlap at all

---

## Q3 — Token budget constraints

**Difficulty:** intermediate

**Question:**
You are chunking a 200-page legal document for a RAG system. Your embedding model has a
512-token maximum input. Your prompt template uses 400 tokens for instructions and context
framing, and you retrieve top-5 chunks. Describe how you would think through the chunk
size constraint in this scenario.

**Correct answer criteria:**
- The embedding model limit (512 tokens) sets the hard upper bound for chunk size —
  chunks exceeding 512 tokens will be truncated during embedding, losing content
- The context window constraint: 400 tokens (template) + 5 chunks × chunk_size must fit
  within the LLM's context window. If using a model with a 4096-token window, that leaves
  approximately (4096 - 400) / 5 = ~739 tokens per chunk — but the embedding model caps
  at 512, so 512 is the binding constraint for chunk size
- Recommended chunk size: 256–400 tokens to stay safely under the 512-token embedding
  limit while leaving room for overlap
- The learner should recognize that two separate limits apply (embedding model limit and
  LLM context window limit) and correctly identify which is binding

**Partial credit criteria:**
- Identifies the embedding model token limit as the constraint but ignores the LLM context
  window calculation
- Sets up the math correctly but arrives at an incorrect binding constraint
- Identifies both constraints but cannot explain which is binding in this scenario

**Incorrect / no-credit criteria:**
- Does not account for the embedding model's maximum input limit
- Believes chunk size is a free parameter independent of model constraints
- Ignores the LLM context window completely

---

## Q4 — Domain-specific chunking strategies

**Difficulty:** intermediate

**Question:**
You are building a RAG system over a large Markdown-formatted technical documentation site
with headers like `## Installation`, `### Configuration`, and `## API Reference`. Describe
a chunking strategy tailored to this document structure and explain why it would outperform
naive fixed-size chunking.

**Correct answer criteria:**
- Header-based (hierarchical) chunking: split at Markdown heading boundaries, keeping
  each section as a self-contained chunk. A chunk begins at a header and ends just before
  the next header of equal or higher level
- This preserves document structure: each chunk is a semantically complete unit (e.g.,
  one API endpoint's documentation, one configuration option), rather than an arbitrary
  slice of text
- Why it outperforms fixed-size: a fixed-size chunker might split "## API Reference"
  header text from its body, or split a parameter table across two chunks, making both
  retrieval and generation worse. Header-based chunks are naturally self-contained and
  likely to match user intent
- Optionally: metadata can be added to each chunk (e.g., the section path
  "Installation > Docker Setup") to help retrieval models contextualize short chunks

**Partial credit criteria:**
- Recommends header-based splitting but cannot explain why it outperforms fixed-size
  for this specific document type
- Correctly identifies the structural advantage but cannot describe the implementation
  mechanism

**Incorrect / no-credit criteria:**
- Recommends fixed-size chunking without any domain-specific adaptation
- Recommends sentence splitting (ignores the document's header structure)
- Cannot explain the connection between chunk structure and retrieval quality

---

## Q5 — Context-free chunks and the "orphaned chunk" problem

**Difficulty:** intermediate

**Question:**
A chunking strategy produces the following chunk:
  "It was introduced in version 3.2 and deprecated in version 4.0."
This chunk retrieves highly in response to a query about version compatibility.
Explain the retrieval and generation problem this chunk creates, and describe how you
would fix the chunking strategy to prevent it.

**Correct answer criteria:**
- The problem: this chunk has no self-contained context — "It" is a pronoun with no
  referent in the chunk. The chunk cannot stand alone; without the preceding context,
  neither the retrieval model nor the LLM knows what "it" refers to
- This is the "orphaned chunk" or "context-free chunk" problem — the chunk scored well
  because of keyword match, but it is useless without the surrounding context
- Fix 1: use larger chunks (increase chunk size to include the antecedent)
- Fix 2: use chunk overlap to carry the preceding sentence(s) into the next chunk
- Fix 3: prepend the document title, section header, or a context summary to each chunk
  (document-level metadata injection)

**Partial credit criteria:**
- Identifies that "it" is problematic but describes it only as a grammar issue, not
  a retrieval/generation failure mode
- Recommends overlap as a fix but cannot explain why it solves this specific problem

**Incorrect / no-credit criteria:**
- Says the chunk is fine because it matched the query
- Cannot identify that the pronoun without antecedent creates a context failure
- Recommends only changing the query rather than the chunking strategy

**Follow-up probe:**
"If you prepend the section header to every chunk, what new risk does that introduce
for very short sections?"

---

## Q6 — Chunk size and retrieval precision tradeoff

**Difficulty:** intermediate

**Question:**
Explain the tradeoff between using very small chunks (50–100 tokens) versus very large
chunks (800–1000 tokens) in a RAG system. Under what circumstances might each extreme be
appropriate?

**Correct answer criteria:**
- Very small chunks:
  - Advantage: high precision — a small chunk is less likely to contain off-topic content,
    so when it retrieves, it's very targeted
  - Disadvantage: low context — a 50-token chunk may lack enough surrounding text for the
    embedding model to judge relevance accurately; the LLM may not have enough context to
    formulate a complete answer from a single small chunk
  - Appropriate when: searching for specific factual snippets (dates, names, figures)
    in highly structured documents
- Very large chunks:
  - Advantage: self-contained — each chunk contains a complete argument, section, or
    explanation, giving the LLM full context
  - Disadvantage: retrieval noise — a large chunk may contain both relevant and
    irrelevant content; the embedding represents the average, diluting the relevance signal
  - Appropriate when: document sections are naturally long and queries require broad context

**Partial credit criteria:**
- Describes one extreme correctly but cannot characterize the other
- States "medium chunk size is always best" without articulating the tradeoffs at the extremes

**Incorrect / no-credit criteria:**
- Claims one extreme is always better than the other with no qualification
- Cannot identify any retrieval quality implication of chunk size

---

## Q7 — Chunking code files

**Difficulty:** advanced

**Question:**
You are building a code search RAG system over a large Python codebase. Describe why
naive fixed-size or paragraph-based chunking is inappropriate for code, and propose
a more suitable chunking strategy with specific boundary rules.

**Correct answer criteria:**
- Fixed-size chunking fails because: it splits across function or class boundaries —
  a chunk may contain half a function definition, which is neither independently
  semantically complete nor a valid unit of code
- Paragraph-based fails because: code "paragraphs" (blank-line-separated blocks) do
  not correspond to semantic units — blank lines in code separate logical groups, but
  a function with a blank line between parameter blocks would be incorrectly split
- Better strategy: AST-based (Abstract Syntax Tree) chunking — split at function,
  method, or class boundaries using the code's parse tree, not textual heuristics
- Each chunk should include: the full function/method signature, its docstring, the
  full body, and optionally the enclosing class name as metadata
- This ensures each chunk is a syntactically complete, independently meaningful unit

**Partial credit criteria:**
- Identifies that code requires different chunking but cannot describe AST-based
  or function-boundary chunking specifically
- Correctly describes the chunking rule but does not include the rationale for
  why textual strategies fail

**Incorrect / no-credit criteria:**
- Recommends sentence splitting for code
- Believes fixed-size chunking is adequate for code with a small enough chunk size
- Cannot identify what makes code structurally different from prose

---

## Q8 — Parent-child chunking (multi-level retrieval)

**Difficulty:** advanced

**Question:**
Describe the parent-child chunking strategy. What problem does it solve that single-level
chunking does not, and what are the implementation requirements for using it?

**Correct answer criteria:**
- Parent-child chunking: create two levels of chunks from the same document — a small
  "child" chunk (50–150 tokens) for high-precision retrieval, and a larger "parent"
  chunk (500–1000 tokens) that contains the child as a sub-section
- At retrieval time: the system retrieves the child chunks (high precision), but passes
  the corresponding parent chunks to the LLM (full context)
- Problem solved: single-level chunking forces a choice between retrieval precision
  (small chunks) and generation context (large chunks). Parent-child provides both:
  small chunks for precise retrieval, large chunks for rich generation context
- Implementation requirements: the index must store chunk-to-parent mappings; the
  retrieval step must include a parent-lookup stage after initial retrieval; parent chunks
  must be stored separately (not just as a second embedding) because they need to be
  fetched by ID, not by similarity

**Partial credit criteria:**
- Describes the two-level structure but cannot explain what problem it solves compared
  to single-level chunking
- Correctly identifies the problem it solves but cannot describe the implementation
  (child retrieval → parent fetch)

**Incorrect / no-credit criteria:**
- Describes parent-child as simply having two different chunk sizes in the same index
- Cannot explain why the parent chunk needs to be fetched separately (not retrieved)
- Believes the LLM uses both child and parent chunks simultaneously

---

## Q9 — Mixed-content corpus chunking strategy

**Difficulty:** advanced

**Question:**
You are indexing a developer documentation corpus that contains three content types in
the same files: API reference sections (structured, terse, parameter-by-parameter),
narrative explanation sections (prose paragraphs describing concepts), and embedded code
examples (Python and bash snippets). Describe a chunking strategy that handles the
different semantic boundaries of each content type, and explain the operational tradeoff
you accept at index time.

**Correct answer criteria:**
- API reference sections: chunk at the parameter or endpoint boundary — each parameter
  definition or endpoint description is a self-contained retrieval unit. Splitting mid-
  parameter table or across two parameters produces orphaned chunks that lack context.
  Header-based splitting (e.g., at `####` level) approximates this if the docs are well-
  structured; otherwise a custom parser that identifies parameter blocks is required
- Narrative sections: sentence-aware or paragraph-based chunking with overlap. Prose
  meaning flows across sentence boundaries, so hard splits without overlap produce
  context-free chunks. Chunk size of 200–400 tokens with 50-token overlap handles most
  explanatory paragraphs
- Code examples: treat each code block as an atomic unit — never split a code snippet
  across two chunks. Include the prose sentence immediately before the code block in the
  same chunk as context (the sentence typically describes what the code does). AST-based
  splitting is ideal but regex-based code fence detection (```` ``` ````) is a practical
  approximation
- Operational tradeoff at index time: content-type-aware chunking requires a pre-processing
  pass to classify each section by type before applying the appropriate splitter. This
  adds pipeline complexity (a classifier or rule-based parser) and increases index build
  time. The tradeoff is index build latency and maintenance overhead in exchange for
  substantially better chunk coherence

**Partial credit criteria:**
- Correctly describes the chunking approach for two of three content types but does not
  address the operational cost of type-aware chunking
- Identifies the operational tradeoff correctly but proposes the same chunking strategy
  for all three content types

**Incorrect / no-credit criteria:**
- Recommends fixed-size chunking for all content types with no content-type adaptation
- Cannot identify that code blocks must never be split across chunk boundaries
- Describes the operational tradeoff as purely a storage cost rather than a pipeline
  complexity cost

---

## Q10 — Parent-document retrieval: when is the overhead justified?

**Difficulty:** advanced

**Question:**
You are considering switching from standard fixed-size chunking (400-token chunks indexed
and retrieved directly) to parent-document retrieval (100-token child chunks for retrieval,
500-token parent chunks returned to the LLM). Describe the problem parent-document
retrieval solves, when the overhead is justified, and what the failure mode is when the
parent document is too large.

**Correct answer criteria:**
- Problem it solves: standard chunking forces a single chunk size to serve two different
  goals simultaneously — small enough for precise retrieval (the embedding captures a
  focused semantic unit) and large enough to provide the LLM with complete, contextually
  rich text for generation. These goals are in tension: at 400 tokens, chunks are often
  too large for precise retrieval but too small for complete answers. Parent-document
  retrieval decouples retrieval precision from generation context by using different
  chunk sizes for each purpose
- When justified: when you observe that retrieval precision is high (top-1 chunk is
  usually the right chunk) but generation quality is poor because individual chunks lack
  sufficient context to produce a complete answer. Also justified when documents have
  natural hierarchical structure (e.g., a paragraph is the retrieval unit, the section
  is the generation unit)
- Failure mode when parent is too large: if the parent chunk is 2,000+ tokens, the LLM's
  context window fills quickly (5 parents × 2,000 tokens = 10,000 tokens consumed by
  context alone), forcing a reduction in the number of results returned. Worse, a very
  large parent likely contains content unrelated to the child that triggered its retrieval —
  the parent-child precision advantage evaporates when the parent is so large it is
  effectively a full document

**Partial credit criteria:**
- Correctly describes the precision-context tension that parent-document retrieval solves
  but does not address when the overhead is justified
- Identifies the large-parent failure mode but describes it only as a storage problem,
  not a context window and relevance dilution problem

**Incorrect / no-credit criteria:**
- Describes parent-document retrieval as simply indexing two chunk sizes and letting the
  retriever choose between them
- Claims the approach is always better than standard chunking with no conditions
- Cannot identify any failure mode

---

## Q11 — Evaluating chunk size optimality without full re-indexing

**Difficulty:** advanced

**Question:**
Your production RAG system was indexed with 300-token chunks six months ago. You suspect
the chunk size may no longer be optimal but re-indexing 2 million documents is expensive.
What offline signals can you use to evaluate whether your current chunk size is causing
retrieval or generation quality problems, and what are the limitations of each signal?

**Correct answer criteria:**
- Signal 1: context_precision from RAGAS evaluation on a query sample. Low precision
  (many retrieved chunks are partially off-topic) suggests chunks are too large — the
  embedding represents an average of multiple topics, diluting the relevance signal.
  Limitation: RAGAS requires a ground truth test set, which may be stale or insufficient
  to cover all query types
- Signal 2: faithfulness score on queries that should have a single-source answer. If
  faithfulness is low despite context_recall being high, individual chunks may be too
  small — the answer is spread across multiple chunks, and the LLM is struggling to
  synthesize across them. Limitation: faithfulness is affected by prompt quality and LLM
  behavior, not just chunking, so a low faithfulness score is not a definitive chunking
  signal
- Signal 3: manual inspection of retrieved chunks for a sample of failing queries.
  Count how often the correct answer is split across two adjacent chunks (orphaned
  boundary problem) vs. how often a single chunk contains excess irrelevant material.
  Limitation: this is labor-intensive and subject to selection bias in which queries you
  inspect; it does not scale beyond a few hundred examples
- Signal 4: chunk utilization in generation. Use an LLM to judge which retrieved chunks
  were actually used in generating the answer. If fewer than 50% of retrieved chunks are
  utilized, chunks may be too large (noise) or top-K is too high. Limitation: this adds
  inference cost and requires a reliable utilization evaluator

**Partial credit criteria:**
- Identifies two valid signals but does not articulate the limitation of either
- Correctly describes limitations for three signals but proposes only one concrete signal

**Incorrect / no-credit criteria:**
- Recommends re-indexing with a different chunk size as the only evaluation method
  (the question specifically asks for signals that avoid full re-indexing)
- Cannot identify any metric that would indicate chunk size is suboptimal
- Describes all signals as definitive rather than acknowledging their limitations
