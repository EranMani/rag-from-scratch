# Question Bank: `langchain_fundamentals`
# Phase: 2 — Core Components
# Maintained by: Lara (RAG Curriculum Specialist)
# Last updated: 2026-05-21 (Commit 45)

---

## Q1 — LCEL pipe syntax and chain composition

**Difficulty:** novice

**Question:**
Explain what the `|` operator does in LangChain Expression Language (LCEL). What types
of objects can be connected with `|`, and what does it mean for a chain to be "composed"
vs. "executed"?

**Correct answer criteria:**
- The `|` operator in LCEL connects Runnable objects into a chain — the output of the
  left-hand component becomes the input to the right-hand component.
- Valid components are any objects implementing the `Runnable` interface: prompt templates,
  LLMs, chat models, output parsers, retrievers, and custom Runnables.
- Composition with `|` is lazy — it creates a directed graph of operations but does not
  execute anything. Execution is deferred until `.invoke()`, `.stream()`, or `.batch()` is called.
- This lazy evaluation means you can compose chains, store them, pass them as arguments,
  and add further components before any LLM call or retrieval operation is made.

**Partial credit criteria:**
- Correctly describes `|` as chaining components and identifies that output flows from left
  to right, but does not explain the lazy evaluation / deferred execution distinction.
- Explains lazy evaluation correctly but cannot name more than one type of compatible Runnable.

**Incorrect / no-credit criteria:**
- Describes `|` as a Python bitwise OR operator with no connection to LCEL semantics.
- Believes the chain is executed immediately when components are composed with `|`.
- Cannot explain what types of objects are connected by `|`.

**Follow-up probe (if partial):**
"If I write `chain = prompt | llm | parser` and never call `.invoke()`, what has happened?
Has the LLM been called? Has any token been consumed?"

---

## Q2 — The retriever interface and `.as_retriever()`

**Difficulty:** novice

**Question:**
What does `.as_retriever()` return when called on a LangChain vector store, and what
parameters does it accept? How does the returned object connect to a chain?

**Correct answer criteria:**
- `.as_retriever()` returns a `VectorStoreRetriever` object, which implements the
  `Runnable` interface (specifically `BaseRetriever`).
- Key parameters: `search_type` (e.g., `"similarity"`, `"mmr"`, `"similarity_score_threshold"`),
  and `search_kwargs` (a dict with keys like `k` for number of results, `score_threshold`
  for threshold-based retrieval, `fetch_k` for MMR candidate pool size).
- The returned retriever connects to a chain via `|` because it implements `Runnable` —
  it takes a string query as input and returns a list of `Document` objects as output.
- The retriever is the component that bridges the vector store (storage layer) to the
  chain (orchestration layer) — the chain never calls the vector store directly.

**Partial credit criteria:**
- Correctly states that `.as_retriever()` returns a retriever and that it connects via `|`,
  but cannot name more than one `search_type` or explain `search_kwargs`.
- Can explain the `k` parameter and `search_type` but does not explain what the retriever
  returns (list of Documents) or how it sits between the vector store and the chain.

**Incorrect / no-credit criteria:**
- Believes `.as_retriever()` returns raw text rather than `Document` objects.
- Cannot explain how the retriever connects to a chain.
- Confuses the retriever with the vector store itself.

---

## Q3 — Tracing `create_retrieval_chain` from query to response

**Difficulty:** intermediate

**Question:**
Walk through the execution of `create_retrieval_chain(retriever, combine_docs_chain)`
when `.invoke({"input": "What is chunking?"})` is called. Name each component that is
called, in order, and describe what it receives and what it passes to the next component.

**Correct answer criteria:**
1. The retriever is called first — it receives the query string `"What is chunking?"` and
   returns a list of `Document` objects (the retrieved chunks).
2. The input dict and retrieved documents are merged into a new context dict — typically
   `{"input": "...", "context": [Document, ...]}`.
3. The `combine_docs_chain` (usually a `StuffDocumentsChain` or an LCEL chain) receives this
   dict. It formats the documents into a string context, injects them into the prompt template,
   and passes the rendered prompt to the LLM.
4. The LLM generates a response; the output parser (if any) processes the raw LLM output into
   the final answer.
5. `create_retrieval_chain` wraps these steps and returns a dict containing both the answer
   and the source documents under standard keys (`"answer"`, `"context"`).

**Partial credit criteria:**
- Correctly identifies the retriever-first ordering and the final LLM call, but omits or
  misstates the intermediate document-formatting step.
- Describes the steps in the right order but cannot explain what is passed between components
  (treats it as a black box at one or more steps).

**Incorrect / no-credit criteria:**
- Believes the LLM is called before retrieval.
- Cannot describe what the retriever returns or what the `combine_docs_chain` receives.
- Describes only two steps (retrieve + generate) with no mention of document formatting.

**Follow-up probe (if partial):**
"What key in the output dict contains the retrieved source documents, and why does returning
them matter for a production system?"

---

## Q4 — Memory types and their tradeoffs

**Difficulty:** intermediate

**Question:**
Compare `ConversationBufferMemory` and `ConversationSummaryMemory`. What does each store,
when is each the better choice, and what happens to each when the conversation history
grows long enough to exceed the context limit?

**Correct answer criteria:**
- `ConversationBufferMemory` stores the full verbatim history of all prior messages (human
  and AI turns) as a list or formatted string. It is appropriate for short conversations
  where precise phrasing matters (e.g., the user may reference an exact previous statement).
- `ConversationSummaryMemory` stores a compressed summary of the conversation so far, using
  an LLM to progressively summarize as new turns are added. It is appropriate for long
  conversations where the exact wording of old turns is less important than the overall context.
- `ConversationBufferMemory` at context limit: the raw history exceeds the context window.
  The developer must handle this — options include truncating old turns (losing information)
  or switching to a summary or windowed memory strategy. LangChain does not handle this
  automatically — silence is the failure mode (the chain silently truncates or errors).
- `ConversationSummaryMemory` at context limit: the summary itself can grow, but at a much
  slower rate than the raw buffer. The risk is information loss through progressive
  summarization — details from early turns may be abstracted away. Each new turn also
  incurs an additional LLM call for summarization.

**Partial credit criteria:**
- Correctly describes what each stores and a valid use case for each, but does not address
  what happens when the context limit is exceeded.
- Correctly describes the context-limit behavior for one memory type but not the other.

**Incorrect / no-credit criteria:**
- Believes LangChain manages context window limits automatically for either memory type.
- Cannot explain the mechanism by which `ConversationSummaryMemory` compresses history.
- Describes both memory types as storing "conversation history" without distinguishing
  verbatim storage from summarized storage.

---

## Q5 — Silent failure modes in a LangChain pipeline

**Difficulty:** advanced

**Question:**
A LangChain RAG pipeline is returning answers that are consistently unhelpful but raises
no exceptions. Identify at least three distinct places where a LangChain pipeline can fail
silently, explain the mechanism behind each failure, and describe how you would surface
each failure for diagnosis.

**Correct answer criteria:**
Any three of the following, each with mechanism and detection strategy:

1. Retriever returning empty results — if the query produces no matches (e.g., score
   threshold too high, no relevant chunks in the index), the retriever returns an empty
   list. The chain continues with an empty context block. The LLM generates a response
   from the empty context — typically "I don't have information on that" or, worse, a
   hallucinated answer. Detection: log `len(retrieved_docs)` after every retrieval call;
   alert when it is zero.

2. Prompt template variable mismatch — if a prompt template references a variable name
   (e.g., `{context}`) but the chain passes a differently-named key (e.g., `"retrieved_context"`),
   LangChain may silently pass an empty string or raise a KeyError that gets swallowed
   depending on configuration. The LLM receives a prompt with missing context. Detection:
   validate template variable names against the chain's input schema at startup; log
   rendered prompts in debug mode.

3. Chain swallowing exceptions — LCEL chains and LangChain v0.1-era chains may catch and
   suppress internal exceptions (e.g., LLM API timeout, parser failure), returning a
   fallback value or `None` instead of propagating the error. The caller sees a response
   with no indication that a failure occurred. Detection: configure verbose logging (`verbose=True`)
   or add a custom error callback via `callbacks=[...]`; use `.with_fallbacks()` deliberately
   and log when a fallback is invoked.

4. Output parser silently dropping content — if the LLM returns text that does not match
   the expected output format (e.g., JSON expected but prose returned), some parsers return
   a partial result or empty object instead of raising. Detection: add validation after
   parsing; log raw LLM output alongside parsed output so mismatches are visible.

5. Memory not wired to the chain — if memory is instantiated but not passed to the chain
   correctly, each call runs without any conversation history, even though the developer
   expects continuity. The chain compiles without error; no exception is raised. Detection:
   inspect `chain.memory` at runtime; add a test turn that refers to a previous turn and
   verify the reference is understood.

**Partial credit criteria:**
- Identifies three failure modes but provides a detection strategy for only one or two.
- Provides mechanisms and detection for two failure modes, not three.

**Incorrect / no-credit criteria:**
- Identifies fewer than two distinct failure modes.
- Lists failure modes without explaining the mechanism (e.g., "retriever might fail" without
  explaining why it would fail silently and what the observable symptom is).
- Suggests only "add error handling" as a detection strategy without identifying specific
  instrumentation points.

---

## Q6 — LCEL lazy evaluation and its implications

**Difficulty:** intermediate

**Question:**
A developer writes: `chain = prompt | llm`. Then they change the system prompt template
and write: `chain = chain | output_parser`. Later, they call `chain.invoke({"question": "..."})`.
Explain what LCEL's lazy evaluation means for this sequence, and describe one practical
implication for streaming and one for error handling.

**Correct answer criteria:**
- Lazy evaluation: each `|` operation constructs a node in an execution graph but does
  not run any code. Neither `prompt`, `llm`, nor `output_parser` is called at composition
  time. The full chain is only executed when `.invoke()`, `.stream()`, or `.batch()` is called.
- Streaming implication: because the chain is a graph rather than an eagerly evaluated
  pipeline, LCEL can stream token-by-token from the LLM to the output parser without
  materializing the full LLM response in memory first. Components downstream of the LLM
  receive chunks as they arrive, enabling true streaming responses. Eager evaluation would
  require the full LLM response before the parser could run.
- Error handling implication: because errors only surface at `.invoke()` time (not at
  composition time), a misconfigured chain — e.g., a prompt template that references a
  variable not provided by the chain's input — will not raise an error until the chain is
  actually executed. This makes startup validation important: call `.input_schema` or run
  a test invoke to catch schema mismatches early.

**Partial credit criteria:**
- Correctly explains lazy evaluation (no execution at composition) but covers only one of
  the two implications (streaming or error handling), not both.
- Describes both implications but conflates eager and lazy evaluation or cannot explain
  why lazy evaluation enables streaming.

**Incorrect / no-credit criteria:**
- Believes composition with `|` executes each component in sequence immediately.
- Cannot explain any practical implication of lazy evaluation for either streaming or errors.

---

## Q7 — Choosing memory strategy for a long-running assistant

**Difficulty:** advanced

**Question:**
You are building a customer support assistant that handles conversations of up to 50 turns.
The LLM you are using has an 8,192-token context window. The average turn is 200 tokens.
At 50 turns, the raw conversation history would be approximately 10,000 tokens — exceeding
the context window. Design a memory strategy that handles this constraint. Explain which
LangChain memory component(s) you would use, what tradeoffs your design accepts, and what
you would instrument to detect memory-related quality degradation.

**Correct answer criteria:**
- The learner must identify that 50 turns × 200 tokens = ~10,000 tokens exceeds the 8,192
  context window and that a raw buffer strategy will not work.
- Viable strategies (any one, fully reasoned):
  - `ConversationSummaryMemory`: compress older turns into a rolling summary. The tradeoff
    is that specific facts from early turns (e.g., customer's account number mentioned in
    turn 2) may be lost in progressive summarization. Each new turn incurs an additional
    LLM call for summarization.
  - `ConversationBufferWindowMemory` (windowed buffer): keep only the last N turns verbatim.
    The tradeoff is that information from turns outside the window is completely lost — the
    assistant has no memory of earlier conversation.
  - Hybrid: keep a rolling summary of turns older than N, and a verbatim buffer of the
    last N turns. More complex but retains recent precision and longer-term context.
- Instrumentation: log the token count of the memory string injected into each prompt;
  alert when it approaches the context window budget; log whether the assistant references
  facts from early turns correctly (a quality signal for summary accuracy).

**Partial credit criteria:**
- Correctly identifies the context overflow problem and proposes a valid strategy, but
  does not address the tradeoffs accepted by that strategy.
- Addresses tradeoffs but does not propose instrumentation for detecting quality degradation.

**Incorrect / no-credit criteria:**
- Proposes `ConversationBufferMemory` as the solution without addressing the context overflow.
- Cannot calculate that 50 × 200 = 10,000 tokens exceeds the context window.
- Does not propose any instrumentation for detecting memory-related quality issues.

---

## Q8 — Debugging a pipeline with no visible errors

**Difficulty:** advanced

**Question:**
A LangChain RAG pipeline has been deployed. Users report that answers are sometimes
accurate and sometimes completely unrelated to the question. No exceptions appear in the
logs. The pipeline uses a vector store retriever, a stuff-documents chain, and GPT-4.
Describe your systematic diagnostic process — which components you would inspect first,
what signals you would look for, and what instrumentation you would add if it is not
already present.

**Correct answer criteria:**
- Start at the retriever: log `retrieved_docs` for failing queries. If the retriever returns
  empty results or irrelevant documents, the problem is in retrieval (wrong embedding model,
  score threshold too restrictive, index contains wrong content).
- Inspect the rendered prompt: log the full prompt string sent to the LLM for failing
  queries. If the prompt contains empty or misformatted context, the problem is in the
  chain assembly (variable name mismatch, document formatting error).
- Check the LLM output before parsing: log raw LLM completions. If the completions are
  reasonable but the final answer is wrong, the problem is in the output parser or
  post-processing step.
- Instrumentation to add: LangChain callbacks (`callbacks=[MyLoggingCallback()]`) that
  log on_retriever_end (documents returned), on_llm_start (prompt sent), and on_llm_end
  (completion received). These three hooks cover the full pipeline at the component level
  without modifying chain logic.
- Cross-reference accurate vs. inaccurate answers: look for a pattern (query type, query
  length, topic domain) that predicts failure — this narrows which component is responsible.

**Partial credit criteria:**
- Proposes checking the retriever and the LLM prompt, but does not describe specific
  LangChain instrumentation (callbacks) or a method for cross-referencing patterns.
- Describes the callback mechanism correctly but does not suggest which specific hooks
  to attach or what signals to extract from them.

**Incorrect / no-credit criteria:**
- Proposes only restarting the service or checking API rate limits.
- Cannot identify the retriever as the first diagnostic target.
- Does not distinguish between retrieval failures and generation failures as separate
  diagnostic hypotheses.

---

## Q9 — Diagnosing silent empty context in a LangChain chain

**Difficulty:** advanced

**Question:**
A LangChain RAG chain is returning answers that are consistently vague and non-specific,
but no exceptions are raised and the chain completes successfully. A colleague suspects
the LLM is receiving an empty context block. Describe the exact diagnostic procedure to
confirm or rule out empty context, identify three mechanisms by which a LangChain chain
can silently pass empty context to the LLM, and specify the instrumentation change that
would surface this in production automatically.

**Correct answer criteria:**
- Diagnostic procedure:
  1. Enable LangChain verbose logging (`verbose=True` on the chain or chain components)
     and run a failing query. Inspect the rendered prompt sent to the LLM in the output.
  2. Alternatively, attach a callback: `callbacks=[CustomLoggingCallback()]` that
     implements `on_llm_start(serialized, prompts, **kwargs)` and logs the raw prompt string.
  3. Confirm whether the context block in the logged prompt is empty or populated.

- Mechanism 1 — Retriever returning empty list: if the retriever finds no results (score
  threshold too high, index empty, embedding model producing out-of-distribution query
  vectors), it returns `[]`. The chain passes this empty list through the document
  formatter, which produces an empty string. No error is raised. Detection: log
  `len(docs)` in an `on_retriever_end` callback.

- Mechanism 2 — Variable name mismatch in the prompt template: the prompt template
  expects `{context}` but the chain's RunnablePassthrough passes the key as
  `"retrieved_context"` or `"documents"`. The template renders with an empty string for
  the missing variable (or raises a KeyError that a try/except swallows). Detection:
  validate chain input/output schema at startup using `.input_schema` and `.output_schema`.

- Mechanism 3 — Document formatter producing empty string: the `format_docs` function
  (or `StuffDocumentsChain` format method) is passed `Document` objects but the `.page_content`
  attribute is empty because the text was not properly stored at indexing time. The
  formatter produces whitespace or an empty string. Detection: log the document text
  lengths in `on_retriever_end`.

- Production instrumentation: register a LangChain callback that logs on_retriever_end
  (chunk count and first 100 characters of each chunk's content), on_llm_start (prompt
  length and first/last 100 characters), and emits a metric/alert when chunk count is
  zero or prompt length is below a threshold.

**Partial credit criteria:**
- Identifies the diagnostic procedure and one mechanism, with a correct instrumentation
  approach for that mechanism only
- Identifies all three mechanisms but does not describe how to surface them in production
  (only describes manual debugging steps)

**Incorrect / no-credit criteria:**
- Recommends only restarting the service or checking API connectivity
- Cannot identify any mechanism that would cause silent empty context
- Describes "print the output" as the diagnostic procedure without identifying LangChain-
  specific instrumentation points (callbacks, verbose mode)

---

## Q10 — Migrating ConversationalRetrievalChain to LCEL with preserved memory

**Difficulty:** advanced

**Question:**
You have a production RAG assistant built on `ConversationalRetrievalChain`. The team
wants to migrate to LCEL for better streaming support and traceability. Describe the
specific behavioral differences you must account for when replacing
`ConversationalRetrievalChain` with an LCEL equivalent, with focus on memory handling.
What fails silently if you compose the LCEL chain without explicitly replicating
the memory behavior?

**Correct answer criteria:**
- ConversationalRetrievalChain behavior: the chain automatically retrieves conversation
  history from its memory component, condenses the history + current question into a
  standalone question (via a separate LLM call), and uses the condensed question as the
  retrieval query. This "question condensation" step is not present in a basic LCEL chain.

- What fails silently without question condensation: follow-up queries that reference
  previous turns ("And what about the second option you mentioned?") are passed directly
  to the retriever as-is. The retriever embeds a query that contains pronouns and
  implicit references with no context, producing irrelevant or empty retrieval results.
  No error is raised — the chain completes with a bad context block.

- What must be explicitly replicated in LCEL:
  1. A conversation history store (e.g., `ChatMessageHistory` with `RunnableWithMessageHistory`)
  2. A question condensation step: a sub-chain that takes (chat_history, current_question)
     and generates a standalone, self-contained retrieval query before calling the retriever
  3. The retrieval step using the condensed question
  4. The final generation step using original history + retrieved context

- Key LCEL-specific note: `RunnableWithMessageHistory` handles session-scoped history
  persistence, but the question condensation logic must be authored explicitly as a
  sub-chain — it is not automatically provided by any LCEL primitive.

**Partial credit criteria:**
- Correctly identifies that question condensation is missing and explains why it matters
  for follow-up queries, but cannot describe the full LCEL component list needed to
  replicate the behavior
- Lists the required components correctly but cannot explain what fails silently if
  question condensation is omitted

**Incorrect / no-credit criteria:**
- Claims `RunnableWithMessageHistory` alone replicates `ConversationalRetrievalChain`
  behavior (memory persistence is not the same as question condensation)
- Cannot identify the question condensation step as the critical difference
- Describes the migration as straightforward with no behavioral differences to account for

---

## Q11 — LangSmith traces show tool calls succeeding but final answer is wrong

**Difficulty:** advanced

**Question:**
A LangSmith trace for a failing query shows: (1) the retriever tool called successfully
and returned 5 chunks with similarity scores 0.81–0.89, (2) the LLM tool called
successfully and returned a completion, (3) no errors or exceptions anywhere in the trace.
Yet the final answer is factually wrong in a way that contradicts the retrieved chunks.
Walk through the four diagnostic hypotheses you would investigate using the trace data
alone, before making any code changes.

**Correct answer criteria:**
The learner should demonstrate how to use LangSmith trace anatomy (inputs/outputs at each
step) to isolate the failure:

- Hypothesis 1 — Context not reaching the LLM: expand the LLM tool node in the trace
  and inspect the actual prompt input. Verify that the retrieved chunks appear in the
  context block. If the prompt shows an empty or truncated context block despite
  the retriever returning 5 chunks, there is a document formatting or variable binding
  failure between the retriever output and the prompt template input.

- Hypothesis 2 — Prompt template rendering error: the rendered prompt in the LLM input
  may show context present but malformatted (e.g., `[Document(page_content='...')]` as a
  Python repr string rather than clean text). This happens when `format_docs` is missing
  from the chain and documents are passed as raw objects. The LLM receives a technical
  string it was not designed to reason over.

- Hypothesis 3 — Retrieved chunks do not contain the correct answer despite high
  similarity scores: expand each retrieved document in the trace. High cosine similarity
  does not guarantee the chunk contains the specific fact needed — it means the chunk is
  topically related. If the answer requires a specific numerical value, date, or name that
  is absent from all 5 chunks, the failure is retrieval quality, not generation.

- Hypothesis 4 — LLM output truncation: inspect the token count and stop reason in the
  LLM node output. If the completion was stopped by a length limit (stop_reason="length"
  rather than "stop"), the answer may have been cut off mid-reasoning. The truncated
  portion that was generated but not returned may have contained the correct answer.

**Partial credit criteria:**
- Identifies three of four hypotheses with correct LangSmith trace inspection steps
- Identifies all four hypotheses but describes only generic debugging (not trace-specific
  inspection steps)

**Incorrect / no-credit criteria:**
- Recommends code changes before exhausting trace-based diagnostics
- Cannot identify more than one hypothesis
- Describes only "check the retrieval quality" without specifying what to inspect
  in the trace and what signal confirms or rules out each hypothesis
