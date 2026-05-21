# MCQ Bank — langchain_fundamentals
# Topic: langchain_fundamentals
# Phase: 2 (Core Components)
# Questions: 11 (2 beginner, 4 intermediate, 3 advanced, 2 expert)
# Last updated: 2026-05-21 (Commit 45)

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
LCEL (LangChain Expression Language) uses lazy evaluation — the `|` operator constructs a computation graph by linking Runnable objects, but nothing is executed until `.invoke()`, `.stream()`, or `.batch()` is called. At the point of composition, no LLM call has been made, no prompt has been rendered, and no tokens have been consumed.

**Why A is wrong:** This is the most common misconception among developers coming from eager-evaluation frameworks. The `|` operator in Python is typically a bitwise OR — LCEL overloads it to mean "compose these Runnables." The intuition that "I connected them so they ran" is wrong. A practitioner who has not read the LCEL docs carefully will reach for A immediately.

**Why C is wrong:** Partial validation at composition time would be a reasonable design choice, but LangChain does not implement it. Variable mismatch in a prompt template only surfaces at `.invoke()` time. This option is plausible because other frameworks (e.g., Pydantic models) do validate at construction time — practitioners expect consistency with that pattern.

**Why D is wrong:** Sending connectivity checks at construction time would be a serious anti-pattern — it would make chain construction fail without network access and would leak API calls on every import. No production LLM framework does this. This distractor catches developers who assume LangChain is defensive by default.

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
`.as_retriever()` returns a `VectorStoreRetriever`, which inherits from `BaseRetriever` and implements the `Runnable` interface. As a Runnable, it takes a string query as input and returns a list of `Document` objects — not raw text, not IDs, not similarity scores. This makes it chainable with `|` in LCEL.

**Why A is wrong:** Option A describes the vector store's `.similarity_search()` method, which returns scores and raw results. The retriever abstraction wraps that into a standard Runnable interface. Practitioners who call `.similarity_search()` directly and then try `.as_retriever()` often confuse these two interfaces because they both do "similarity search."

**Why C is wrong:** `RetrievalQA` is a higher-level chain that includes the LLM generation step. `.as_retriever()` returns only the retrieval component. Developers who have only used `RetrievalQA` and have not decomposed the chain tend to conflate the whole chain with the retriever object.

**Why D is wrong:** The retriever returns `Document` objects, not document IDs or keyword match results. BM25-style retrieval returns IDs in some implementations, but the LangChain `BaseRetriever` contract always returns `List[Document]`. This option catches developers who assume keyword search behavior from the name "retriever."

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
`create_retrieval_chain` follows a strict sequential order: (1) the retriever is called with the input query and returns a list of Documents; (2) the retrieved documents and the original query are combined into a context dict; (3) the `combine_docs_chain` formats the documents, renders the prompt template, and calls the LLM; (4) the LLM returns a response.

**Why A is wrong:** Option A describes HyDE (Hypothetical Document Embeddings), a valid but non-default retrieval technique where an LLM generates a hypothetical answer first, then uses its embedding for retrieval. Practitioners who have read about HyDE and not carefully read `create_retrieval_chain`'s source tend to assume HyDE behavior is the default.

**Why C is wrong:** The `combine_docs_chain` cannot render its prompt before retrieval because the document context slot is empty. A developer who thinks of the chain as a template system (format first, fill later) reaches for C. The chain is actually a sequential data flow where each step depends on the output of the prior step.

**Why D is wrong:** Parallel retrieval and generation is architecturally impossible here — the LLM prompt requires the retrieved documents as input. Option D would describe a speculative execution pattern that LangChain does not implement in this chain. Developers familiar with async programming may expect parallelism where sequential dependency exists.

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
With a 4,096-token context window, `ConversationBufferMemory` will overflow for long conversations — the full verbatim history cannot fit. A hybrid strategy (summary for older turns + verbatim buffer for recent turns) retains precise information for recent turns (where specificity matters most) while compressing older turns into a summary that fits within the context budget.

**Why A is wrong:** Switching from `ConversationSummaryMemory` to `ConversationBufferMemory` makes the problem worse — a full verbatim buffer grows without bound and will overflow the 4,096-token window even faster. This option is plausible to someone who reads "stops referencing early information" and concludes "summaries are lossy, so switch to verbatim." The mechanism they have right; the solution direction they have exactly reversed.

**Why B is wrong:** Increasing the context window to 32,768 tokens solves today's problem but defers it — at 32,768 tokens, a 40–60 turn conversation will eventually overflow too. More critically, the question asks for a memory strategy change, not an infrastructure change. This option is a common engineering reflex: "just make the limit bigger," which sidesteps the architecture question.

**Why D is wrong:** Disabling memory eliminates the stated requirement. This is not a mitigation — it is abandonment of the feature. A practitioner who has had a bad experience with memory implementations might reach for D, but it does not address information loss; it removes memory entirely.

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
A `similarity_score_threshold` of 0.95 requires very high semantic similarity before a document qualifies — in practice, most queries will return empty results unless the corpus contains near-verbatim matches. When the retriever returns an empty list, `create_retrieval_chain` passes an empty context block to the `combine_docs_chain`. The LLM receives a prompt with no retrieved context and generates from its parametric training data instead — producing a plausible-sounding but ungrounded answer. No exception is raised because an empty list is a valid return value. The correct mitigations are: (1) lower the score threshold (e.g., 0.70–0.80) to allow more documents through, and (2) add explicit zero-result handling that logs the event and either raises an error, returns a "no relevant information found" response, or falls back to a different retrieval strategy.

**Why A is wrong:** The LLM is not malfunctioning — it is doing exactly what it was trained to do when given an empty context: generate a plausible response from parametric memory. Calling this an "LLM hallucination bug" obscures the real failure. Engineers who deploy without monitoring retrieval zero-result rates consistently misattribute retrieval failures as generation failures.

**Why B is wrong:** Prompt injection is a real threat but requires malicious content in retrieved documents. An empty retriever result produces no injection surface — there is no retrieved content to carry an attack. Framing empty retrieval as a security vulnerability confuses a configuration error with a threat model. Practitioners who have read about prompt injection but not seen retrieval failures may pattern-match incorrectly here.

**Why D is wrong:** An empty list adds essentially zero tokens to the prompt — it causes the opposite of context overflow. This option is wrong in both mechanism (empty list does not expand token count) and symptom (overflow would cause truncation errors, not plausible-sounding ungrounded responses). It catches developers who have only seen context overflow failures and associate "silent failure" with token limits.

---

## MCQ-6 — RunnablePassthrough and None propagation

**Difficulty:** intermediate
**Topic:** langchain_fundamentals

**Question:**
A developer builds an LCEL chain where `RunnablePassthrough()` is used to forward the original query through a parallel branch: `RunnableParallel({"context": retriever, "question": RunnablePassthrough()})`. During testing, a chain variant uses `RunnablePassthrough.assign(metadata=extract_metadata)` instead. Under what condition does `RunnablePassthrough` silently pass `None` rather than the input value, causing downstream failures with no raised exception?

**Options:**
A. When the input dictionary is missing the key that the downstream chain expects, `RunnablePassthrough` substitutes `None` for the missing key rather than raising a `KeyError`
B. When `.assign()` is used and the assigned function raises an unhandled exception, `RunnablePassthrough` catches the exception and returns `None` for that field instead of propagating the error
C. `RunnablePassthrough` never passes `None` — if the input is `None`, it raises a `ValidationError` before the chain continues
D. When `RunnablePassthrough()` is given a `None` input (e.g., the upstream step explicitly returns `None`), it passes `None` downstream without raising an error, silently corrupting any downstream step that expects a string

**Correct answer:** D

**Explanation:**
`RunnablePassthrough` is a transparent passthrough: it forwards whatever it receives, including `None`. If an upstream step returns `None` — for example, a chain branch that conditionally returns `None` on no-match — `RunnablePassthrough` passes `None` downstream. Downstream steps that call `.invoke(None)` and expect a string will either raise a `TypeError` or silently produce incorrect output depending on their implementation. No warning or exception comes from `RunnablePassthrough` itself. The failure is silent at the passthrough layer and only surfaces later in the chain, making it hard to trace to the upstream source.

**Why A is wrong:** `RunnablePassthrough` does not perform dictionary key lookup or substitution. It passes the entire input object as-is. Key-missing failures would come from a downstream step trying to access a missing key, not from the passthrough itself. This option describes a behavior pattern from Pydantic or TypedDict, not LCEL.

**Why B is wrong:** `.assign()` does not suppress exceptions from the assigned function. If `extract_metadata` raises, the exception propagates up the chain. The specific case of silent `None` occurs when the input to the passthrough itself is `None`, not when an assigned function errors.

**Why C is wrong:** `RunnablePassthrough` does not validate its input. It has no schema to enforce. This option would be correct if LCEL performed input validation at each step, but it does not — LCEL is a composition framework, and input validation is the responsibility of individual components.

---

## MCQ-7 — LangSmith trace coverage gaps

**Difficulty:** intermediate
**Topic:** langchain_fundamentals

**Question:**
A team enables LangSmith tracing on their LangChain RAG pipeline. After a production incident where the LLM returned a hallucinated answer, they examine the trace. The trace shows the retrieval step, the prompt sent to the LLM, and the LLM response. What would a LangSmith trace NOT capture that could be relevant to diagnosing why the LLM hallucinated?

**Options:**
A. The similarity scores of retrieved documents — LangSmith captures retrieval results but not the underlying similarity values
B. Custom Python functions called outside of a Runnable that transform retrieved documents before prompt construction — these execute outside the LCEL trace boundary and leave no record in the trace
C. The LLM's token usage — LangSmith does not record token counts for cost tracking
D. The system prompt content — LangSmith redacts system prompts by default to protect sensitive instructions

**Correct answer:** B

**Explanation:**
LangSmith traces instrument Runnable invocations in the LCEL graph. Any Python code that runs outside of a Runnable — such as a custom post-processing function that filters or transforms retrieved documents before they are inserted into the prompt — executes outside the trace boundary. If that function silently drops relevant documents or introduces errors, the trace shows the retrieval output and the final prompt, but contains no visibility into what happened between them. This is a common diagnosis gap: the trace looks clean, but a non-Runnable transformation step corrupted the context.

**Why A is wrong:** LangSmith does capture retrieval metadata including similarity scores when the retriever is instrumented. Similarity scores appear in the trace as part of the retriever step output. Practitioners who have not examined a retriever trace in detail assume it only shows document text.

**Why C is wrong:** LangSmith does record token usage — it is one of the primary cost-monitoring features of the platform. Token counts are visible per run and aggregable across sessions. This would be a reason to use LangSmith, not a limitation of it.

**Why D is wrong:** LangSmith does not redact system prompts by default. The full prompt (system prompt, retrieved context, user message) is visible in the trace. Some organizations configure redaction via environment variables, but this is not the default behavior.

---

## MCQ-8 — Memory not wired to chain

**Difficulty:** advanced
**Topic:** langchain_fundamentals

**Question:**
A developer creates a `ConversationBufferMemory` object and a `ConversationChain`. During code review, a senior engineer notes that the memory object is initialized but never passed to the chain: `memory = ConversationBufferMemory()` and `chain = LLMChain(llm=llm, prompt=prompt)` — memory is never set on the chain. What is the observable behavior of this system in production?

**Options:**
A. The chain raises a `MemoryNotConfigured` exception on the first multi-turn invocation
B. The chain operates statelessly — each invocation is independent, with no conversation history in the prompt. The memory object accumulates state internally but is never read or written by the chain, and no error is raised
C. The chain uses an implicit default memory (an empty `ConversationBufferMemory`) because LangChain initializes memory to a no-op buffer when none is provided
D. The first invocation succeeds with full history, but subsequent invocations fail because the disconnected memory object eventually runs out of buffer space

**Correct answer:** B

**Explanation:**
A `ConversationBufferMemory` instance is a Python object. Creating it and not attaching it to a chain means the chain has no reference to it. The `LLMChain` uses only the memory object passed to its `memory` parameter. Without that parameter, the chain runs statelessly: each `.invoke()` call processes only the current input, with no conversation history. No exception is raised because a stateless chain is valid. The disconnected memory object is garbage — it exists in memory but is never read or written. This failure mode is especially insidious because the system appears to work (it returns answers) but is not fulfilling the multi-turn use case it was designed for.

**Why A is wrong:** LangChain does not validate that memory is configured before running. There is no `MemoryNotConfigured` exception class. Developers who expect frameworks to enforce configuration completeness at runtime reach for this option, but LangChain's design philosophy allows stateless chains as a valid configuration.

**Why C is wrong:** LangChain does not initialize an implicit default memory. When `memory=None` (the default), the chain runs without any memory component — it does not substitute a no-op buffer. Developers who have worked with frameworks that use default/null object patterns (common in dependency injection) expect this behavior but it does not apply here.

**Why D is wrong:** This option invents a failure mode that does not exist. The disconnected memory object has no relationship to the chain and cannot affect its behavior — positively or negatively. The chain does not know the memory object exists. This distractor targets developers who reason that "eventually the disconnected object will cause a problem," which is intuitive but incorrect.

---

## MCQ-9 — get_relevant_documents vs. invoke deprecation

**Difficulty:** advanced
**Topic:** langchain_fundamentals

**Question:**
A production codebase calls `retriever.get_relevant_documents(query)` directly in several places. After upgrading LangChain from 0.1.x to 0.2.x, deprecation warnings appear in logs. A developer proposes replacing all calls with `retriever.invoke(query)`. Which statement correctly describes the behavioral difference between these two methods that the developer must account for?

**Options:**
A. `invoke()` returns a coroutine that must be awaited; `get_relevant_documents()` returns a list synchronously — the replacement requires switching to an async call path
B. `invoke()` passes the query through the full Runnable pipeline including any configured callbacks and middleware; `get_relevant_documents()` calls the underlying search directly, bypassing Runnable-layer instrumentation like LangSmith tracing
C. `invoke()` and `get_relevant_documents()` are identical in behavior — the deprecation is purely cosmetic for naming consistency
D. `invoke()` returns `Document` objects with normalized metadata; `get_relevant_documents()` returns raw strings — switching requires updating downstream code to handle `Document` objects

**Correct answer:** B

**Explanation:**
In LangChain 0.2.x, `get_relevant_documents()` is deprecated in favor of `invoke()`. The behavioral difference that matters is instrumentation: `invoke()` goes through the Runnable interface, which means LangSmith callbacks, middleware wrappers, and any configured tracing hooks are triggered. `get_relevant_documents()` calls the underlying retrieval logic more directly, bypassing some of the Runnable infrastructure. For a production system relying on LangSmith for observability, switching to `invoke()` is the correct move because it ensures traces capture retrieval calls consistently. The replacement itself is safe, but the developer must understand that `invoke()` is not a drop-in alias — it carries the full Runnable execution context.

**Why A is wrong:** Both `invoke()` and `get_relevant_documents()` have synchronous versions. There is a separate async method `ainvoke()` for async contexts. The synchronous `invoke()` returns a list directly, not a coroutine. Developers who conflate async/sync with the invoke API upgrade make this error.

**Why C is wrong:** The deprecation is not cosmetic. The behavioral difference in instrumentation coverage is the reason the deprecation exists — the LangChain team is consolidating execution paths onto the Runnable interface so all components are uniformly observable. Treating deprecation warnings as cosmetic is a common and costly mistake in production systems.

**Why D is wrong:** Both methods return `List[Document]` — the return type did not change. `get_relevant_documents()` already returned `Document` objects, not raw strings. This option would catch developers who have not inspected the return type of either method and assume deprecation implies a type change.

---

## MCQ-10 — LCEL with_fallbacks trigger condition

**Difficulty:** expert
**Topic:** langchain_fundamentals

**Question:**
A developer configures an LCEL chain with a fallback: `primary_chain.with_fallbacks([fallback_chain])`. During load testing, they observe that the fallback triggers for some requests but not others, even when the primary chain's LLM returns a successful HTTP 200 response. What is the most precise explanation for when `.with_fallbacks()` triggers?

**Options:**
A. `.with_fallbacks()` triggers whenever the primary chain's response latency exceeds a configurable timeout threshold, regardless of whether the response was valid
B. `.with_fallbacks()` triggers when the primary chain raises any exception — including output parser exceptions, validation errors, or any other exception thrown during execution — not only on LLM API failures
C. `.with_fallbacks()` triggers only on HTTP 4xx or 5xx errors from the LLM provider — it does not catch exceptions raised by Python code within the chain
D. `.with_fallbacks()` triggers on the first invocation failure and then permanently routes all subsequent requests to the fallback, regardless of whether the primary chain has recovered

**Correct answer:** B

**Explanation:**
`.with_fallbacks()` catches any exception raised during the primary chain's execution — not just network or API errors. If the output parser fails to parse the LLM's response (for example, the LLM returns text that does not conform to the expected JSON schema), a `OutputParserException` is raised, and the fallback triggers. This means a primary chain that successfully calls the LLM but whose output parser fails will route to the fallback. In load testing, this can manifest as intermittent fallback triggering when the LLM occasionally returns malformed output. The developer's assumption that "HTTP 200 means the primary chain succeeded" is wrong — success requires the full chain to complete without exception.

**Why A is wrong:** `.with_fallbacks()` does not implement timeout-based triggering natively. Latency monitoring is a separate concern handled by async timeouts or infrastructure-level circuit breakers, not by LCEL's fallback mechanism. A developer who associates "fallback" with "timeout handling" in distributed systems reaches for this option.

**Why C is wrong:** This is the mirror of the correct answer. The fallback catches exceptions from any part of the chain — Python exceptions, output parser errors, validation errors — not only HTTP-level failures. Restricting fallback to HTTP codes would make it far less useful as a reliability primitive.

**Why D is wrong:** `.with_fallbacks()` does not implement circuit-breaker state. It evaluates each invocation independently — the fallback is triggered per-call based on whether that call raises an exception. There is no "permanently route to fallback" behavior. Developers who know about circuit-breaker patterns assume LCEL's fallback includes circuit state, but it does not.

---

## MCQ-11 — RunnableParallel error propagation

**Difficulty:** expert
**Topic:** langchain_fundamentals

**Question:**
A production LCEL chain uses `RunnableParallel` to run two branches simultaneously: one calls a vector retriever and one calls a keyword retriever. Both results are merged downstream. During a production incident, the keyword retriever's backing service is down and raises a `ConnectionError`. What happens to the overall chain execution?

**Options:**
A. The chain continues with only the vector retriever's results — `RunnableParallel` treats branch failures as empty results and merges the available output
B. The chain raises the `ConnectionError` immediately, canceling both branches — even if the vector retriever has already returned results, the exception from one branch propagates and aborts the entire parallel step
C. `RunnableParallel` retries the failed branch up to 3 times before raising the exception, giving transient failures time to recover
D. The chain raises a `PartialResultError` containing the vector retriever's successful output alongside the `ConnectionError`, allowing downstream handlers to decide how to proceed

**Correct answer:** B

**Explanation:**
`RunnableParallel` does not implement fault isolation between branches. If any branch raises an exception, the exception propagates immediately and the entire `RunnableParallel` step fails. Even if other branches completed successfully, their results are discarded. There is no built-in behavior to treat a failed branch as an empty result or to return partial results. This is a critical operational property: a team that designs a hybrid retrieval pipeline using `RunnableParallel` must add explicit fault handling (e.g., wrapping each branch with `.with_fallbacks()` returning an empty list on error) or the failure of either retrieval source will take down the entire pipeline.

**Why A is wrong:** This is the most dangerous misconception. Developers who design parallel pipelines often assume resilience by default — "if one branch fails, use the other." `RunnableParallel` provides no such resilience. A system designed under this assumption will fail completely when any retrieval source goes down, which is a much worse outcome than the team expects.

**Why C is wrong:** `RunnableParallel` does not implement retry logic. Retries must be added explicitly, either by wrapping individual branches in a retry Runnable or by configuring retry at the LLM/retriever level. The assumption that parallel execution includes retry is a common projection from higher-level orchestration frameworks onto LCEL.

**Why D is wrong:** There is no `PartialResultError` in LangChain. The framework does not distinguish between full and partial failures in a parallel step. This option describes a sophisticated error-handling API that would be desirable but does not exist — it catches developers who assume production-grade frameworks implement this pattern.
