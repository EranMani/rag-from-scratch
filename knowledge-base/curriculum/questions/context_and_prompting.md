# Question Bank: `context_and_prompting`
# Phase: 2 — Core Components
# Maintained by: Lara (RAG Curriculum Specialist)
# Last updated: 2026-05-11 (Commit 22)

---

## Q1 — Anatomy of a RAG prompt

**Difficulty:** beginner

**Question:**
Describe the four standard elements of a well-structured RAG prompt template. For each
element, explain what it contains and why it must be present.

**Correct answer criteria:**
1. System instruction — tells the LLM its role and rules: answer from the provided
   context only, cite passages, and what to do when the answer is not in the context.
   Must be present so the LLM does not blend context with world knowledge.
2. Context block — contains the retrieved text chunks, clearly delimited (e.g., with
   XML tags, triple-backticks, or "Context:"). Must be present and clearly marked so
   the LLM knows which text is source material vs. user input.
3. User question — the original query from the user. Must be present and clearly
   separated from the context block to prevent confusion.
4. Output format directive — tells the LLM how to structure its response (e.g., "Answer
   in 2–3 sentences," "Use bullet points," "Include the source passage"). Must be present
   if consistency across responses is required.

**Partial credit criteria:**
- Names and describes three of four elements correctly
- Names all four elements but cannot explain why each is required (only describes
  what it contains)

**Incorrect / no-credit criteria:**
- Cannot name more than two elements
- Describes context injection as "putting documents in the chat history" rather than
  in a structured prompt template
- Does not distinguish system instruction from the user question

---

## Q2 — The "answer only from context" instruction

**Difficulty:** beginner

**Question:**
Why does a RAG prompt typically include an instruction like "Answer only from the
provided context. If the answer is not in the context, say 'I don't know.'"?
What happens if this instruction is omitted?

**Correct answer criteria:**
- Without this instruction, the LLM will freely blend the retrieved context with its
  parametric knowledge (information baked into its weights during training)
- This blending can produce answers that sound correct but are not grounded in the
  retrieved documents — responses that are factually right by luck but cannot be traced
  to a source, or responses that mix stale parametric knowledge with current document
  content
- The "I don't know" fallback is equally important: it gives the LLM a graceful exit
  when the retrieved context does not contain the answer, preventing it from hallucinating
  a plausible-sounding answer instead
- For applications requiring auditability or citation, the "only from context" rule
  is not just quality-improving — it is a functional requirement

**Partial credit criteria:**
- Correctly explains the blending risk when the instruction is omitted but does not
  address why the "I don't know" fallback matters
- Explains the importance of the fallback but does not explain the blending risk

**Incorrect / no-credit criteria:**
- Believes the instruction is stylistic preference with no quality impact
- Claims LLMs always use context when it is present, regardless of instruction
- Confuses "answer from context" with "do not use the internet"

---

## Q3 — Context window management under pressure

**Difficulty:** intermediate

**Question:**
You retrieve top-10 chunks for a complex query, but the total tokens in the chunks plus
the prompt template exceeds your LLM's context window. Describe two strategies for
handling this, and identify the risk each introduces.

**Correct answer criteria:**
- Strategy 1: reduce top-K — retrieve fewer chunks (e.g., top-5 instead of top-10).
  Risk: the most relevant chunk may have ranked 6th–10th and is now excluded from the
  prompt, directly harming answer quality.
- Strategy 2: truncate chunks — shorten each chunk to fit (e.g., keep only the first
  200 tokens of each chunk). Risk: the relevant content within a chunk may appear in
  the truncated portion, cutting off a complete answer.
- Acceptable alternatives:
  - Reduce chunk size at indexing time (addressed before query time, not at inference)
  - Use a larger-context LLM (addressed at model selection time)
  - Chunk-level summarization: use an LLM to compress each chunk while preserving key
    information before injection. Risk: introduces an additional LLM call (latency and
    cost) and may lose specific details needed for precise answers.

**Partial credit criteria:**
- Describes two strategies but only identifies the risk for one
- Identifies the risks correctly but describes only one strategy

**Incorrect / no-credit criteria:**
- Suggests increasing the context window (hardware/model-level — not a prompt strategy)
- Cannot identify any risk associated with either strategy
- Recommends discarding the query and asking the user to rephrase

---

## Q4 — "Lost in the middle" phenomenon

**Difficulty:** intermediate

**Question:**
Research on long-context LLMs has identified the "lost in the middle" phenomenon.
Describe what this means, and explain how you would design your prompt and retrieval
strategy to mitigate it.

**Correct answer criteria:**
- Lost in the middle: LLMs exhibit non-uniform attention across long context windows —
  they attend most strongly to content at the beginning and end of the context and attend
  least to content in the middle. When the most relevant chunk is placed in the middle
  of a 10-chunk context block, the LLM may effectively ignore it.
- Mitigation at the prompt level: place the most relevant chunk first (or last) in the
  context block, not in the middle. If you have a relevance-ranked list, consider
  alternating high-relevance chunks at the start and end.
- Mitigation at the retrieval level: use a reranker to ensure the top-1 most relevant
  chunk is correctly identified and placed first; reduce the number of chunks injected
  (quality over quantity) to keep the context shorter and reduce the middle region.
- Mitigation at generation level: use an explicit "The most important passage is
  delimited with [IMPORTANT]..." instruction to draw attention to specific content.

**Partial credit criteria:**
- Correctly describes the phenomenon but only provides one mitigation strategy
- Provides two mitigation strategies but does not explain the attention mechanism
  that causes the effect

**Incorrect / no-credit criteria:**
- Describes "lost in the middle" as a chunking problem (it is an LLM attention problem)
- Claims larger context windows solve the problem (they do not — the effect scales with
  window size)
- Cannot identify any mitigation strategy

---

## Q5 — Hallucination mitigation through prompt design

**Difficulty:** intermediate

**Question:**
List three specific prompt design patterns that reduce LLM hallucination in a RAG
system. For each, explain the mechanism by which it reduces hallucination.

**Correct answer criteria:**
Any three of the following (each with a mechanism explanation):

1. "Answer only from context" instruction — prevents the model from introducing
   parametric knowledge not present in the retrieved chunks
2. Explicit uncertainty signaling — "If you are not certain, say so" — trains the model
   to express low confidence rather than hallucinate a confident-sounding answer
3. Citation requirement — "For each claim, cite the specific passage it comes from" —
   forces the model to anchor every statement to a retrieved text, making
   ungrounded claims structurally impossible in the output format
4. Negative instruction — "Do not include information that is not in the provided context,
   even if you believe it to be true" — closes the gap left by an implicit "answer from
   context" instruction
5. Response length constraint — "Answer in 2–3 sentences" — shorter responses leave
   less room for hallucinated elaboration and force the model toward the most direct,
   context-supported answer

**Partial credit criteria:**
- Names three patterns but provides mechanism explanation for only one or two
- Provides mechanisms correctly but names fewer than three distinct patterns

**Incorrect / no-credit criteria:**
- Lists patterns that are not prompt-level interventions (e.g., "use a better LLM,"
  "improve retrieval quality")
- Cannot explain the mechanism for any of the named patterns
- Lists only one pattern with one mechanism

---

## Q6 — Prompt template consistency for evaluation

**Difficulty:** intermediate

**Question:**
A team is A/B testing two retrieval strategies (dense vs. hybrid) to determine which
produces better answers. They use slightly different prompt templates for each strategy
(different system instructions and context formatting). Explain why this experimental
design is flawed and how to fix it.

**Correct answer criteria:**
- The flaw: prompt template variation is a confounding variable. If strategy A uses
  "Answer from context:" and strategy B uses "You are a helpful assistant. Context:",
  any quality difference in the output could be caused by the prompt template difference
  rather than the retrieval strategy difference. The experiment cannot determine which
  factor (retrieval or prompt) drove the observed quality difference.
- Fix: hold the prompt template constant across both conditions — use exactly the same
  template for both retrieval strategies. Only vary the input that differs by design
  (the retrieved chunks).
- More broadly: in any RAG evaluation, each pipeline stage (chunking, embedding, retrieval,
  prompt, generation model) should be varied independently in experiments, holding
  all other stages constant. This is controlled experimentation applied to ML systems.

**Partial credit criteria:**
- Identifies the confounding variable problem but cannot explain how it specifically
  affects the A/B comparison
- Describes the fix correctly (constant template) but cannot explain why the original
  design is flawed

**Incorrect / no-credit criteria:**
- Believes different templates are fine because "they say the same thing"
- Cannot identify any problem with varying multiple components in one experiment
- Recommends running more experiments rather than controlling the variables

---

## Q7 — Handling multi-document synthesis

**Difficulty:** advanced

**Question:**
A user asks: "Summarize the key differences between the 2022 and 2023 versions of our
product roadmap." The answer requires synthesizing information from two different
documents. What prompt design considerations apply specifically to multi-document
synthesis, and what failure modes are most likely?

**Correct answer criteria:**
- Prompt design considerations:
  1. Document attribution: label each context chunk with its source document clearly
     (e.g., "--- 2022 Roadmap ---" and "--- 2023 Roadmap ---") so the LLM knows which
     document each passage comes from when synthesizing a comparison
  2. Explicit synthesis instruction: add "Compare the information from [Document A]
     and [Document B] directly" — without this, the LLM may summarize each document
     separately rather than producing a comparative synthesis
  3. Ordering: place the two documents in a consistent, predictable order to take
     advantage of the LLM's positional attention (not interleaved)
- Failure modes:
  1. Attribution confusion: the LLM assigns a feature to the wrong year
  2. "Lost in the middle" with interleaved chunks from both documents
  3. Failure to synthesize — the LLM separately summarizes each document without
     comparing them, despite being asked to compare
  4. Partial synthesis — the LLM only uses one document and ignores the other

**Partial credit criteria:**
- Identifies two of three prompt design considerations without covering failure modes
- Correctly identifies failure modes without connecting them to prompt design choices
  that prevent them

**Incorrect / no-credit criteria:**
- Recommends using separate queries for each document and concatenating the answers
  (does not address synthesis as a single prompt operation)
- Cannot identify attribution confusion as a failure mode
- Describes no prompt-level mitigations

---

## Q8 — System prompt vs. user prompt placement of context

**Difficulty:** advanced

**Question:**
A developer is debating whether to inject retrieved context in the system prompt or in
the user message turn. Describe two considerations that favor each placement, and
identify when the choice may affect model behavior in a measurable way.

**Correct answer criteria:**
- System prompt placement advantages:
  1. Persistent across a multi-turn conversation — context injected in the system prompt
     is visible for all turns, useful for session-level context that doesn't change
  2. Signals to the model that the context is a fixed instruction/background, not
     user-provided input — some models attend differently to system vs. user content
- User message placement advantages:
  1. Reflects the dynamic nature of per-query retrieval — each query retrieves
     different chunks; placing them in the user turn makes them clearly query-specific
  2. Avoids polluting the system prompt with large, variable content that may not
     benefit from being treated as persistent instruction
- When the choice matters measurably:
  1. Multi-turn conversations where context changes per query — system prompt context
     is static across turns, which may cause stale context issues if documents change
  2. Models with different attention patterns for system vs. user content — some models
     are fine-tuned to treat system prompt as high-authority instructions, which may
     produce stronger "answer only from context" adherence when context is in the system prompt

**Partial credit criteria:**
- Identifies two considerations for one placement but only one for the other
- Correctly identifies the multi-turn concern but cannot identify any other consideration

**Incorrect / no-credit criteria:**
- Claims system prompt and user turn placement are always equivalent
- Recommends system prompt for all cases without identifying the stale context risk in
  multi-turn scenarios
- Cannot explain what a "system prompt" is distinct from the user message

---

## Q9 — Constraining synthesis without over-constraining fluency

**Difficulty:** advanced

**Question:**
You are designing a system prompt for a RAG system that must not synthesize beyond the
retrieved context — every claim in the answer must be traceable to a retrieved chunk.
Describe a constraint formulation that works, what over-constraining looks like and why
it is also a failure mode, and how you would test whether your constraint is effective.

**Correct answer criteria:**
- Effective constraint formulation: the instruction must be specific about what constitutes
  a grounded claim and what the fallback behavior is when the context is insufficient.
  A working formulation: "Answer only using information explicitly stated in the provided
  context. For each claim you make, identify which context passage supports it. If the
  context does not contain sufficient information to answer the question, respond: 'The
  provided context does not contain enough information to answer this question.'" The key
  elements are: explicit attribution requirement (forces the model to anchor claims),
  explicit fallback phrasing (prevents the model from soft-hallucinating with hedged
  language), and a positive definition of what "grounding" means (not just "don't
  hallucinate")
- Over-constraining failure mode: if the instruction demands verbatim quotation or
  prohibits paraphrasing, the model produces mechanical, unreadable responses — it
  copy-pastes chunks rather than synthesizing them into a coherent answer. Users abandon
  the system because responses are unhelpful even when technically grounded. Over-
  constraining also causes the model to refuse valid inference (e.g., if context says
  "the process runs every 6 hours" and the user asks "does it run daily?", a maximally
  constrained model says "I cannot confirm this" instead of answering "yes, it runs 4
  times daily based on the retrieved context")
- Testing effectiveness: evaluate faithfulness (RAGAS) to confirm grounded claims are
  high; simultaneously test answer_relevancy to confirm the answers are still useful.
  A successful constraint formulation produces high faithfulness without degrading
  answer_relevancy. Also sample 20–30 responses and manually check for: refused valid
  inferences (over-constraint), ungrounded claims (under-constraint), and awkward
  verbatim copy-paste (over-constraint signal)

**Partial credit criteria:**
- Correctly describes an effective constraint formulation but does not identify over-
  constraining as a distinct failure mode with its own quality cost
- Identifies over-constraining as a problem but cannot describe a testing procedure that
  distinguishes it from under-constraining

**Incorrect / no-credit criteria:**
- Proposes only "answer from context" as the complete constraint without including an
  explicit fallback or attribution mechanism
- Claims over-constraining is not possible — that any level of constraint is better than
  no constraint
- Cannot describe any method for testing whether the constraint is working

---

## Q10 — Diagnosing lost-in-the-middle in production

**Difficulty:** advanced

**Question:**
You suspect that the "lost in the middle" phenomenon is actively degrading your production
RAG system. Your pipeline injects 8 retrieved chunks, ordered by relevance score (most
relevant first). Describe the metric pattern that would confirm lost-in-the-middle is
occurring, how you would distinguish it from a retrieval quality problem, and what
mitigation you would apply.

**Correct answer criteria:**
- Metric pattern that confirms lost-in-the-middle: run a controlled experiment on a fixed
  test set. For each query, record the position of the ground truth chunk among the 8
  injected chunks. Compute faithfulness separately for queries where the ground truth chunk
  is in positions 1–2 vs. positions 4–6 vs. positions 7–8. If faithfulness is significantly
  higher when the ground truth is at the beginning or end of the context block (and
  significantly lower in the middle), lost-in-the-middle is occurring. A faithfulness drop
  of 0.15 or more between "beginning/end" vs. "middle" positions is a strong signal
- How to distinguish from retrieval quality problem: a retrieval problem would manifest as
  low context_recall (the ground truth chunk is simply not retrieved) or low context_
  precision (too many irrelevant chunks). Lost-in-the-middle is a generation attention
  problem that occurs after retrieval — the correct chunk IS in the context, but the LLM
  fails to use it. The distinguishing check: confirm the ground truth chunk is present
  in the retrieved set (retrieval is working) while faithfulness is still low for middle-
  position queries
- Mitigation: reorder chunks so the most relevant chunk is always at position 1 (or
  position 8 if you use recency bias as a secondary position). Do not use pure relevance-
  descending order with a large chunk count — the second and third most relevant chunks
  should be placed at the end, not in the middle. Reduce the number of injected chunks
  (from 8 to 4–5) to shrink the "middle zone" that LLM attention avoids

**Partial credit criteria:**
- Correctly describes the position-based faithfulness experiment but does not describe how
  to distinguish it from a retrieval problem
- Correctly identifies the mitigation (reorder, reduce chunk count) but cannot describe
  the metric experiment that confirms the phenomenon is occurring

**Incorrect / no-credit criteria:**
- Diagnoses lost-in-the-middle based only on low faithfulness without the position
  correlation analysis (low faithfulness has many causes; the position correlation is
  what distinguishes this specific failure mode)
- Recommends fixing the retrieval stage (improving recall or precision) for what is a
  generation attention problem
- Claims increasing context window size eliminates lost-in-the-middle (the effect scales
  with window size — a larger window does not fix positional attention bias)

---

## Q11 — LLM attention across mixed-format multi-document prompts

**Difficulty:** advanced

**Question:**
Your RAG system retrieves chunks from three documents with different formatting conventions:
Document A is a markdown table (rows and columns), Document B is a narrative prose paragraph,
and Document C is a numbered list. All three are injected into the same prompt context block.
How does an LLM's attention behave differently across these three formats, and what concrete
mitigation exists for the attention inconsistency?

**Correct answer criteria:**
- Attention behavior differences:
  1. Markdown tables: LLMs are trained on tables in markdown format but attend to table
     content less uniformly than prose — they tend to read tables row-by-row and may miss
     values in interior rows or columns, especially when the table is wide or the relevant
     value is at a non-salient position. Numeric values in tables are particularly prone
     to misreading or omission
  2. Narrative prose: LLMs attend most reliably to prose because the majority of their
     training data is prose. Sentence-structured claims in prose are more likely to be
     incorporated into the generation than equivalent information expressed as a table cell
  3. Numbered lists: list items are attended to more reliably than table cells because
     each list item is a discrete, linearly presented statement. However, LLMs may attend
     to the first 3–5 items more strongly than later items in a long list (positional bias
     applies within a list structure)
- Concrete mitigations:
  1. Normalize format before injection: convert tables and lists to prose sentences before
     inserting them into the context block. "The retention period for EU users is 90 days"
     is more reliably attended to than a table row. This is the most effective mitigation
     but adds a pre-processing step
  2. Explicit format flagging in the system prompt: instruct the LLM "The context includes
     tables, lists, and prose. Treat all formats equally. Pay particular attention to values
     in tables." This partially mitigates but does not eliminate the attention asymmetry
  3. Place table-containing chunks at the beginning of the context block (most attended
     position) to compensate for the lower baseline attention to table content

**Partial credit criteria:**
- Correctly describes the attention difference for two of three formats but cannot describe
  any mitigation
- Describes the normalization mitigation correctly but attributes all attention differences
  to chunk size or position rather than format

**Incorrect / no-credit criteria:**
- Claims LLMs attend equally to all formatting styles because they process tokens uniformly
- Cannot identify any difference in how LLMs handle table content vs. prose content
- Recommends increasing model size as the primary mitigation for format-based attention
  inconsistency
