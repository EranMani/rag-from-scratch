# Question Bank: `chunking_strategies`
# Phase: 2 — Core Components
# Maintained by: Lara (RAG Curriculum Specialist)
# Last updated: 2026-05-23 (Commit 51)

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

---

## Q12 — What chunking does in a RAG pipeline

**Difficulty:** novice

**Question:**
What is the purpose of chunking a document before indexing it in a RAG system?
Why can't the full document be used as a single unit?

**Correct answer criteria:**
- Chunking splits a document into smaller pieces so each piece can be embedded and
  retrieved independently
- Embedding models have a maximum token input — most accept 512 to 8192 tokens. A
  100-page document exceeds this limit and cannot be embedded as a single unit
- Even when the embedding model can handle a full document, the resulting embedding
  represents an average of the entire document's content. That average vector cannot
  represent any specific topic within the document well, so retrieval quality degrades
- Smaller chunks allow retrieval to return the specific passage that answers the query,
  rather than an entire document that happens to contain the answer somewhere

**Partial credit criteria:**
- Identifies the token limit constraint but does not explain why embedding a full
  document produces poor retrieval even when the limit allows it
- Identifies that chunking enables more targeted retrieval but cannot connect it to
  how embeddings work

**Incorrect / no-credit criteria:**
- Believes chunking is only for storage or cost reasons, not a functional retrieval requirement
- Claims full documents can be used as retrieval units with no quality impact
- Cannot explain what an embedding represents

---

## Q13 — What a chunk boundary is

**Difficulty:** novice

**Question:**
What is a chunk boundary in document chunking? Give one example of a natural chunk
boundary and one example of an artificial chunk boundary.

**Correct answer criteria:**
- A chunk boundary is the point in a document where one chunk ends and the next begins
- Natural chunk boundary: a point that corresponds to a meaningful content division —
  a paragraph break, a section header, a sentence end, or a question-and-answer
  separator. Splitting here preserves each chunk as a semantically complete unit
- Artificial chunk boundary: a point determined by a fixed rule unrelated to content —
  for example, splitting every 500 tokens regardless of where sentences or paragraphs
  fall. This may cut mid-sentence or mid-argument, leaving both adjacent chunks
  with incomplete meaning

**Partial credit criteria:**
- Correctly defines chunk boundary and gives one example type but not both
- Gives both example types but cannot explain what makes one natural and one artificial

**Incorrect / no-credit criteria:**
- Describes a chunk boundary as the same as a file boundary or page break
- Cannot distinguish natural from artificial boundaries
- Claims all chunk boundaries are equivalent in quality

---

## Q14 — What chunking strategy to use for a simple FAQ document

**Difficulty:** novice

**Question:**
You have a FAQ document where each question-and-answer pair is separated by a blank line.
Each Q&A pair is between 50 and 150 tokens. What chunking strategy would you use, and why?

**Correct answer criteria:**
- Split at blank line boundaries — one chunk per Q&A pair. Each pair is already a
  semantically complete unit: the question defines what the chunk is about and the answer
  provides the retrievable information
- This avoids splitting a question from its answer or merging two unrelated Q&A pairs into
  one chunk
- Fixed-size chunking would be inappropriate here because it would disrespect the natural
  boundaries — it might split a 100-token Q&A pair in half or merge two pairs together

**Partial credit criteria:**
- Recommends splitting at natural boundaries but cannot explain why fixed-size is inappropriate
  for this specific document structure
- Correctly identifies the chunking strategy but does not justify it against the alternative

**Incorrect / no-credit criteria:**
- Recommends fixed-size chunking without acknowledging the natural Q&A pair structure
- Recommends embedding the entire FAQ as one unit
- Cannot identify that the blank-line boundary corresponds to a meaningful content boundary

---

## Q15 — High overlap and context recall degradation

**Difficulty:** intermediate

**Question:**
You set chunk overlap to 60% of chunk size (300 tokens overlap on 500-token chunks) to ensure no content is lost at chunk boundaries. After re-indexing, RAGAS context_recall drops from 0.82 to 0.67 despite faithfulness remaining stable. Explain the mechanism causing the recall drop and describe what you would change.

**Correct answer criteria:**
- High overlap creates near-duplicate chunks: chunk N (tokens 1–500) and chunk N+1 (tokens 201–700) share 300 tokens. Their embedding vectors are very similar because they represent largely the same content
- At retrieval time, top-K slots fill with near-identical chunks: if a query matches the shared 300-token region, both chunk N and chunk N+1 score high and both occupy retrieval slots. With top-5 retrieval, 2–3 slots may be consumed by near-duplicates of the same passage
- Context recall drops because the top-5 result set is no longer diverse — it covers a narrow portion of the document rather than the 5 most distinct relevant passages. Information from other parts of the document that would have answered other sub-questions is crowded out
- Fix: reduce overlap to 10–20% (50–100 tokens on 500-token chunks). Alternatively, add a post-retrieval deduplication step that removes chunks with cosine similarity above a threshold (e.g., 0.95) before passing context to the LLM

**Partial credit criteria:**
- Correctly identifies that high overlap creates near-duplicate chunks but does not connect this to how top-K retrieval fills result slots with redundant content
- Identifies the recall mechanism but proposes only increasing top-K as the fix without recognizing that more slots would also fill with near-duplicates

**Incorrect / no-credit criteria:**
- Attributes the recall drop to the embedding model being confused by repeated content
- Recommends increasing overlap further to "ensure more coverage"
- Cannot explain the connection between chunk duplication and retrieval slot crowding

**Follow-up probe:**
"If you add post-retrieval deduplication, what threshold would you use to distinguish a near-duplicate chunk from a genuinely different chunk covering a related topic, and how would you set that threshold empirically?"
