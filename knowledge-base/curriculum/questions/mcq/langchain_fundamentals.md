# MCQ Bank — langchain_fundamentals
# Topic: langchain_fundamentals
# Phase: 2 (Core Components)
# Questions: 5 (2 beginner, 2 intermediate, 1 advanced)
# Last updated: 2026-05-20 (Commit 40)

---

## MCQ-1 — LCEL lazy evaluation

**Difficulty:** beginner
**Topic:** langchain_fundamentals

**Question:**
A developer writes the following LangChain code: `chain = prompt | llm | output_parser`. At this point, no `.invoke()` has been called. What has happened?

**Options:**
A. The prompt template has been rendered, the LLM has been called, and the output parser has processed the response
B. A directed execution graph has been constructed, but no component has run and no LLM token has been consumed
C. The prompt template has been validated for variable names, but the LLM and output parser have not yet been called
D. LangChain has sent a test request to the LLM API to verify connectivity, but has not yet processed any user input

**Correct answer:** B

**Explanation:**
LCEL (LangChain Expression Language) uses lazy evaluation — the `|` operator constructs a computation graph by linking Runnable objects, but nothing is executed until `.invoke()`, `.stream()`, or `.batch()` is called. At the point of composition, no LLM call has been made, no prompt has been rendered, and no tokens have been consumed. Option A is incorrect — execution requires an explicit `.invoke()` call. Option C is incorrect — no validation of prompt variables occurs at composition time; variable mismatch errors surface only at execution time. Option D is incorrect — LangChain does not send test requests on chain construction.

---

## MCQ-2 — The retriever interface

**Difficulty:** beginner
**Topic:** langchain_fundamentals

**Question:**
What does calling `.as_retriever()` on a LangChain vector store return, and what does that object accept as input and produce as output when invoked?

**Options:**
A. A `VectorStore` object that accepts embedding vectors as input and returns similarity scores as output
B. A `BaseRetriever` Runnable that accepts a string query as input and returns a list of `Document` objects as output
C. A `RetrievalQA` chain that accepts a question string and returns a formatted answer string
D. A `SearchIndex` object that accepts keyword terms as input and returns matching document IDs as output

**Correct answer:** B

**Explanation:**
`.as_retriever()` returns a `VectorStoreRetriever`, which inherits from `BaseRetriever` and implements the `Runnable` interface. As a Runnable, it takes a string query as input and returns a list of `Document` objects — not raw text, not IDs, not similarity scores. This makes it chainable with `|` in LCEL. Option A incorrectly describes the vector store's internal similarity search, not the retriever abstraction. Option C describes a higher-level chain, not the retriever itself. Option D describes keyword search behavior and incorrect return types.

---

## MCQ-3 — Execution order in `create_retrieval_chain`

**Difficulty:** intermediate
**Topic:** langchain_fundamentals

**Question:**
When `create_retrieval_chain(retriever, combine_docs_chain).invoke({"input": "What is BM25?"})` is called, which of the following correctly describes the execution order?

**Options:**
A. The LLM generates a hypothetical answer first, then the retriever uses that answer to find relevant documents, then the final answer is generated
B. The retriever is called first with the query, then the retrieved documents and query are passed to the combine_docs_chain, which renders a prompt and calls the LLM
C. The combine_docs_chain is called first to format the prompt structure, then the retriever fills in the context slot, then the LLM is called
D. The retriever and LLM are called in parallel — retrieval and generation happen simultaneously and results are merged

**Correct answer:** B

**Explanation:**
`create_retrieval_chain` follows a strict sequential order: (1) the retriever is called with the input query and returns a list of Documents; (2) the retrieved documents and the original query are combined into a context dict; (3) the `combine_docs_chain` formats the documents, renders the prompt template, and calls the LLM; (4) the LLM returns a response. Option A describes HyDE (Hypothetical Document Embeddings), a specific retrieval technique that is not the default behavior of `create_retrieval_chain`. Option C is incorrect — the chain cannot format a prompt before retrieval because the context block is empty until retrieval completes. Option D is incorrect — retrieval must complete before generation because the LLM needs the retrieved documents as context.

---

## MCQ-4 — Choosing between memory types

**Difficulty:** intermediate
**Topic:** langchain_fundamentals

**Question:**
A customer support chatbot handles conversations that regularly reach 40–60 turns. The LLM context window is 4,096 tokens. The team notices that after turn 20, the assistant stops referencing information from the early part of the conversation. Which memory configuration change would best address this while minimizing information loss from very recent turns?

**Options:**
A. Switch from `ConversationSummaryMemory` to `ConversationBufferMemory` to retain the full verbatim history
B. Increase the LLM context window to 32,768 tokens and keep `ConversationBufferMemory`
C. Switch to a hybrid strategy: `ConversationSummaryMemory` for turns older than N, with a verbatim buffer for the most recent N turns
D. Disable memory entirely and rely on the user to restate relevant context in each turn

**Correct answer:** C

**Explanation:**
With a 4,096-token context window, `ConversationBufferMemory` will overflow for long conversations — the full verbatim history cannot fit. A hybrid strategy (summary for older turns + verbatim buffer for recent turns) retains precise information for recent turns (where specificity matters most) while compressing older turns into a summary that fits within the context budget. Option A makes the overflow problem worse, not better — a full verbatim buffer grows without bound. Option B addresses the constraint but was not asked (context window size is a deployment infrastructure decision, not a memory strategy decision), and 32,768 tokens is still finite. Option D abandons the memory requirement entirely, which does not address information loss — it eliminates memory as a feature.

---

## MCQ-5 — Silent failure modes

**Difficulty:** advanced
**Topic:** langchain_fundamentals

**Question:**
A LangChain RAG pipeline is in production. The vector store contains 10,000 documents, but the retriever is configured with `search_type="similarity_score_threshold"` and `score_threshold=0.95`. For many user queries, the retriever returns an empty list. No exception is raised. The LLM generates a response that sounds plausible but is completely unsupported by any retrieved document. Which statement best describes this failure and its correct mitigation?

**Options:**
A. This is an LLM hallucination bug. The fix is to use a different LLM with lower hallucination rates
B. This is a prompt injection vulnerability. The empty retriever result allows the LLM's parametric knowledge to override the system prompt grounding instruction
C. This is a silent retrieval failure. The score threshold is too restrictive, causing the retriever to return no documents. The chain continues with empty context, and the LLM generates from its parametric knowledge without raising an error. Mitigation: lower the score threshold, add a post-retrieval check that logs and handles zero-result cases explicitly
D. This is a context window overflow. An empty document list causes LangChain to exceed the context limit, triggering silent truncation of the system prompt

**Correct answer:** C

**Explanation:**
A `similarity_score_threshold` of 0.95 requires very high semantic similarity before a document qualifies — in practice, most queries will return empty results unless the corpus contains near-verbatim matches. When the retriever returns an empty list, `create_retrieval_chain` passes an empty context block to the `combine_docs_chain`. The LLM receives a prompt with no retrieved context and generates from its parametric training data instead — producing a plausible-sounding but ungrounded answer. No exception is raised because an empty list is a valid return value. The correct mitigations are: (1) lower the score threshold (e.g., 0.70–0.80) to allow more documents through, and (2) add explicit zero-result handling that logs the event and either raises an error, returns a "no relevant information found" response, or falls back to a different retrieval strategy. Option A misidentifies the root cause — the LLM is behaving correctly given the empty context it received. Option B incorrectly frames this as a security issue. Option D is incorrect — an empty list does not cause context overflow.
