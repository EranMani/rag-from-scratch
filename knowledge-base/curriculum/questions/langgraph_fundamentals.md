# Question Bank: `langgraph_fundamentals`
# Phase: 3 — Advanced Topics
# Maintained by: RAG Specialist
# Last updated: 2026-05-23 (Commit 50)
# Questions: 19 (5 novice, 5 intermediate, 5 advanced, 4 expert)

---

## Q1 — Nodes, edges, and state

**Difficulty:** novice

**Question:**
Describe the three fundamental building blocks of a directed computation graph: nodes, edges, and state. What does each one represent, and what role does each play during graph execution?

**Correct answer criteria:**
- Node: a discrete unit of work — receives the current state, performs an operation, and returns an updated state
- Edge: a directed connection between nodes that defines which node executes next — the structural path that execution follows
- State: a shared data structure passed to each node as input and updated by each node as output; the mechanism by which data flows through the graph without nodes needing direct references to each other
- The three are complementary: nodes define what runs, edges define what runs next, and state defines what data moves through the graph

**Partial credit criteria:**
- Correctly describes two of the three components but conflates the third (e.g., treats edges and state as the same thing, or treats nodes as passive data containers)
- Describes all three but cannot articulate how they interact during execution

**Incorrect / no-credit criteria:**
- Defines edges as bidirectional or as data containers
- Defines state as a configuration file rather than a runtime data structure
- Cannot distinguish nodes (operations) from edges (connections)

---

## Q2 — Why graphs enable agentic behavior

**Difficulty:** novice

**Question:**
A developer says: "A sequential chain is just simpler — I don't need a graph." Explain two specific behaviors that a graph architecture enables that a sequential chain cannot support.

**Correct answer criteria:**
- Behavior 1: conditional branching at the graph topology level — after a node completes, the next node executed depends on the current state; execution can follow different paths through the graph depending on what the nodes discover
- Behavior 2: cycles — execution can loop back to a node that has already run, enabling iterative refinement, self-correction, and retry loops without writing explicit while loops outside the framework
- The key insight: these capabilities are structural — they are properties of the graph definition, not of any individual node's logic

**Partial credit criteria:**
- Correctly identifies one behavior with a clear explanation
- Identifies both behaviors but describes them as properties of individual nodes rather than of the graph topology

**Incorrect / no-credit criteria:**
- Claims that sequential chains can express cycles or conditional routing at the chain level
- Describes capabilities (API calls, LLM use, retrieval) that are equally available in sequential chains
- Cannot articulate the difference between conditional logic inside a node and conditional routing at the graph level

---

## Q3 — What compilation is for

**Difficulty:** novice

**Question:**
A developer builds a graph definition — they add nodes, define edges, and register routing functions. Before the graph can be executed, they must compile it. What does the compilation step accomplish, and what would happen if execution were attempted directly from the uncompiled definition?

**Correct answer criteria:**
- Compilation validates the graph's structural integrity: entry points are defined, terminal conditions are reachable, all referenced nodes are registered, all edges connect valid node names
- Compilation produces an executable artifact from the definition — a callable object that can be invoked with an initial state
- Without compilation, the definition is a specification, not an executable; invocation attempts would either fail immediately or produce undefined behavior
- Compilation is a one-time cost at setup time, not a per-invocation cost

**Partial credit criteria:**
- Correctly describes what compilation produces (an executable artifact) but cannot explain what structural validations it performs
- Correctly explains what happens without compilation but cannot describe the validation step

**Incorrect / no-credit criteria:**
- Claims compilation runs the graph with a test input to verify behavior
- Claims compilation is optional or interchangeable with "initializing" the graph
- Cannot distinguish the uncompiled definition from the compiled executable

---

## Q4 — State as shared data flow

**Difficulty:** novice

**Question:**
In a graph with three nodes — a retrieval node, an LLM node, and a formatting node — explain how data produced by the retrieval node reaches the formatting node. Why does the graph use a shared state object rather than direct function calls between nodes?

**Correct answer criteria:**
- The retrieval node writes its output (e.g., retrieved chunks) to a field in the shared state object and returns the updated state
- The graph updates the shared state with the retrieval node's output and passes the updated state to the LLM node, which reads the retrieved chunks from state, processes them, and writes its output to another state field
- The formatting node then receives the state containing both the retrieved chunks and the LLM output and reads what it needs
- The shared state model provides loose coupling: no node needs to know the function signature or return type of any other node; all nodes communicate through agreed-upon state fields

**Partial credit criteria:**
- Correctly describes the mechanism of state passing but cannot explain why shared state is preferable to direct argument passing
- Correctly explains the loose coupling benefit but gives an inaccurate description of how state is passed

**Incorrect / no-credit criteria:**
- Describes nodes passing arguments directly to each other's function signatures
- Claims nodes communicate by writing to external storage (a database or a file) rather than to the in-memory state object
- Cannot explain what "shared" means in shared state

---

## Q5 — Distinguishing a graph from a chain

**Difficulty:** novice

**Question:**
A junior developer is designing a RAG system. For the first version, the user sends a query, the system retrieves relevant documents, and an LLM generates an answer. For the second version, the system should check its own answer and, if confidence is low, retrieve additional documents and generate a revised answer. For which version is a graph required, and why?

**Correct answer criteria:**
- Version 1 can be implemented as a sequential chain: query → retrieve → generate is a fixed, linear sequence with no branching or looping
- Version 2 requires a graph: it needs conditional routing (check confidence → branch to "done" or "retrieve again") and a cycle (the ability to loop back to the retrieval step from the answer-checking step)
- The key requirement that forces graph architecture: the cycle — the system must be able to return to a previously completed step based on the outcome of a later step
- Sequential chains execute each step exactly once in order; a return to a previous step cannot be expressed in chain topology

**Partial credit criteria:**
- Correctly identifies that Version 2 needs a graph but cites the wrong reason (e.g., "because it uses an LLM" rather than "because it requires a cycle")
- Correctly identifies the cycle as the distinguishing requirement but claims Version 1 also requires a graph

**Incorrect / no-credit criteria:**
- Claims both versions require graphs or that both can be implemented as chains
- Identifies the need for a graph but cannot explain what specific capability requires it
- Attributes the graph requirement to a language or library constraint rather than a structural requirement

---

## Q6 — How conditional routing works operationally

**Difficulty:** intermediate

**Question:**
Describe the operational mechanism of conditional routing in a graph. When a node completes, what happens next? What determines which of several possible next nodes executes? How is this different from embedding an if-statement inside a node's implementation?

**Correct answer criteria:**
- When a node completes, the graph checks the edge definition for that node — if the edge is conditional, it calls the registered routing function with the current state
- The routing function inspects one or more state fields and returns the identifier of the next node to execute (or the terminal signal)
- Which next node executes is determined by the routing function's return value — this is a runtime decision based on current state, not a compile-time fixed path
- The difference from an in-node if-statement: conditional routing is part of the graph's structural definition and is visible as topology; it separates the concerns of "what to compute" (node logic) from "what to do next" (edge logic). An if-statement inside a node hides routing in implementation and cannot be inspected or modified without reading node code

**Partial credit criteria:**
- Correctly describes the routing function mechanism but cannot articulate the difference from in-node branching
- Correctly explains why conditional edges are preferable but gives an inaccurate description of how the routing function is invoked

**Incorrect / no-credit criteria:**
- States that conditional routing is determined by the graph at compile time (routing is a runtime decision based on state)
- States that the LLM directly controls which edge is followed by naming the next node in its output
- Cannot distinguish a routing function from a node

---

## Q7 — State schema as an interface contract

**Difficulty:** intermediate

**Question:**
In a multi-developer project, four developers each own different nodes in a shared graph. Explain why the state schema is the most critical shared contract in this project. What happens when a node writes to a field name that another node expects to read under a different name, and at what point is this failure detected?

**Correct answer criteria:**
- The state schema is the interface between all nodes: it defines what fields exist, what each field contains, and implicitly, which nodes write each field and which nodes read each field
- In multi-developer scenarios, the state schema is the only way nodes communicate — a node cannot inspect what another node does internally, only what it writes to state
- When a writing node uses a different field name than the reading node expects: the reading node receives None or the field's default value; it processes an empty input without raising an exception; downstream output is wrong (e.g., the LLM generates a response with no retrieved context, producing hallucinated answers)
- The failure is detected at runtime as a quality degradation, not as an error — the pipeline completes without exceptions, making the failure invisible to error monitoring

**Partial credit criteria:**
- Correctly identifies the state schema as the shared contract but cannot describe the failure mode when field names diverge
- Correctly describes the failure mode (silent quality degradation) but cannot explain why no exception is raised

**Incorrect / no-credit criteria:**
- Claims the graph compiler validates that all field reads have a corresponding write
- Claims the failure causes an immediate runtime exception
- Cannot explain why the state schema matters beyond "all nodes use it"

---

## Q8 — Checkpointing design decisions

**Difficulty:** intermediate

**Question:**
A graph agent needs to support multi-turn conversations across an indefinite number of sessions. The team is designing the checkpointing strategy. Explain what checkpointing must persist, how checkpoint retrieval works when a new message arrives in an ongoing conversation, and what the operational consequences of missing a checkpoint between two consecutive nodes are.

**Correct answer criteria:**
- What must be persisted: the complete state object at each checkpoint interval — all accumulated fields including conversation history, retrieved context, decisions made, and any intermediate values that subsequent nodes depend on
- How retrieval works: each conversation thread has a unique identifier; when a new message arrives, the graph retrieves the checkpoint associated with that thread identifier and initializes execution from that saved state rather than from the empty initial state
- Consequence of a missing checkpoint between two nodes: if a crash or restart occurs in that gap, the graph has no saved state from which to resume at the correct point — it must either re-execute from the last available checkpoint (potentially re-running already-completed nodes) or start from scratch, losing work and risking inconsistency
- The frequency and granularity of checkpointing is a tradeoff: more frequent checkpointing reduces work lost on failure but increases storage I/O per execution step

**Partial credit criteria:**
- Correctly describes what is persisted and how thread-based retrieval works but cannot explain the operational consequence of a checkpoint gap
- Correctly identifies the consequence of checkpoint gaps but describes checkpoint retrieval incorrectly (e.g., the graph always starts from scratch and replays)

**Incorrect / no-credit criteria:**
- States that checkpointing is the LLM's responsibility (LLMs are stateless between invocations)
- States that the graph automatically re-executes all nodes from the beginning and discards the checkpoint after any failure
- Cannot explain what a "thread identifier" is or why separate threads require separate checkpoint namespaces

---

## Q9 — Graph topology and what the LLM can do

**Difficulty:** intermediate

**Question:**
Explain how the graph topology constrains and shapes the LLM's behavior within a graph-based agent. Give a concrete example of a behavior the LLM cannot produce on its own in a graph, regardless of what it generates, because the graph's structure prevents it.

**Correct answer criteria:**
- The graph topology defines the set of possible execution paths. The LLM operates within one node; its output can influence routing decisions but cannot add new nodes, remove edges, or create execution paths that were not defined at compile time
- The LLM's output is data written to state; what the graph does with that data is determined by the routing functions and edge structure, not by the LLM
- Concrete example: if the graph has no edge connecting the LLM node to a "call external service" node, the LLM cannot cause an external service call regardless of what it generates. The graph simply does not have that path. The LLM might write "I need to call the external service" to state, but without the edge, execution cannot route there
- This is why graph topology is the correct place to enforce capability boundaries: you constrain what an agent can do structurally, not just by prompting

**Partial credit criteria:**
- Correctly explains that the LLM cannot exceed the topology's defined paths but cannot provide a concrete example
- Provides a concrete example but frames it as a prompt engineering constraint rather than a structural constraint

**Incorrect / no-credit criteria:**
- Claims the LLM can modify the graph's edge structure at runtime based on its reasoning
- Cannot distinguish between what the LLM produces as output and what the graph does with that output
- Frames the topology as a suggestion that the LLM follows voluntarily rather than a structural enforcement

---

## Q10 — Fan-out and fan-in for parallel retrieval

**Difficulty:** intermediate

**Question:**
A research agent should query two different knowledge bases simultaneously to minimize latency, then combine the results before generating a response. Describe how the graph topology must be structured to enable this parallel retrieval pattern. What is the "fan-out" node and the "fan-in" node, and what role does state play in the merge?

**Correct answer criteria:**
- Fan-out: a node (or edge structure) that routes execution to both retrieval nodes from a common predecessor — both retrieval nodes are successors of the same predecessor, enabling the framework to execute them concurrently
- Fan-in: a synthesis or merge node that is defined as a successor to both retrieval nodes — it waits for both branches to complete before executing
- State plays the merge role: each retrieval node writes its results to a different state field (e.g., `results_from_source_a` and `results_from_source_b`); when the synthesis node executes, it reads both fields from the state, which contains the accumulated writes from both parallel branches
- The graph topology (not application code) expresses the parallelism — the developer does not write explicit threading logic; the framework infers parallel execution from the fan-out structure

**Partial credit criteria:**
- Correctly describes the fan-out and fan-in structure but cannot explain how state accumulates results from parallel branches
- Correctly explains the state accumulation mechanism but describes the topology as requiring explicit threading code

**Incorrect / no-credit criteria:**
- States that parallel retrieval requires two separate compiled graphs with a coordinator process
- Claims parallel branches cannot share the same state object
- Cannot explain what "fan-out" and "fan-in" mean in a graph execution context

---

## Q11 — Diagnosing a broken routing function

**Difficulty:** advanced

**Question:**
A graph agent is designed to route to one of three nodes based on the classification of a user query: "factual," "opinion," or "procedural." In production, all queries route to the "factual" handler, even when users ask for opinions or step-by-step instructions. The routing function logic reads a `query_class` field from state and returns the corresponding node name. The routing function's logic is correct when tested in isolation. Trace the failure to its most likely root cause and describe the diagnostic steps to confirm it.

**Correct answer criteria:**
- Most likely root cause: the classification node that is supposed to write `query_class` to state is either (a) not writing the field at all, (b) writing to a different field name than the routing function reads, or (c) always classifying queries as "factual" due to a prompt or model configuration issue
- The routing function is correct in isolation but receives a default or wrong value for `query_class` — if the default value maps to "factual," the function always returns "factual"
- Diagnostic step 1: add instrumentation to inspect the state at the point the routing function executes — print or log the value of `query_class`. If it is always None, empty, or "factual," the problem is in the writing node
- Diagnostic step 2: verify the field name the classification node writes matches the field name the routing function reads — a common cause is a variable name typo introduced during refactoring
- Diagnostic step 3: test the classification node independently with a known "opinion" and "procedural" query to confirm it produces the correct classifications when run outside the graph
- The routing function should not be modified until the write-side failure is confirmed and fixed

**Partial credit criteria:**
- Correctly identifies the state write gap as the likely cause but cannot describe systematic diagnostic steps
- Correctly describes all three diagnostic steps but misidentifies the root cause as a routing function bug

**Incorrect / no-credit criteria:**
- Proposes rewriting the routing function to handle the default value without investigating the classification node
- Attributes the failure to the graph compiler without checking whether the graph compiled successfully
- Cannot distinguish between a routing function bug and a state population bug

---

## Q12 — Cycle termination design

**Difficulty:** advanced

**Question:**
A graph agent iteratively refines a generated answer using an LLM evaluator node. The evaluator reads the current answer and decides whether to accept it or request another revision. Describe two specific failure modes that arise from relying solely on the LLM evaluator to terminate the cycle, and design a termination strategy that prevents both.

**Correct answer criteria:**
- Failure mode 1 (evaluator never approves): for some queries, the revision process does not converge — each revised answer still fails the evaluator's criteria, causing infinite looping. This can occur if the evaluator's criteria are too strict, if the revision node degrades quality rather than improving it, or if the task is genuinely outside the model's capability
- Failure mode 2 (state not updated between iterations): if the revision node fails to write the revised answer back to the correct state field, the evaluator always sees the original answer and always requests revision — the cycle runs indefinitely with no actual improvement occurring
- Termination strategy: (1) maintain an iteration counter in state, incremented by the revision node on each pass; (2) add a hard exit condition in the routing function: if the counter exceeds a maximum (e.g., 5 iterations), route to a graceful exit node regardless of the evaluator's decision; (3) add a state write verification check — the revision node should write a hash or fingerprint of the revised answer so the routing function can detect if the answer has not changed between iterations, which would trigger an early exit
- The hard iteration cap must be defined at graph design time and must be a structural guarantee — it cannot depend on the LLM to count iterations correctly

**Partial credit criteria:**
- Correctly identifies both failure modes but designs a termination strategy that only addresses one of them
- Designs a complete termination strategy but correctly identifies only one failure mode

**Incorrect / no-credit criteria:**
- Proposes solving the problem by improving the LLM evaluator's prompt (this addresses neither structural failure mode)
- Cannot identify that state write failures can cause infinite looping
- Designs a termination strategy that relies on the LLM to recognize it has been running too long and self-terminate

---

## Q13 — Tracing an execution path through a graph

**Difficulty:** advanced

**Question:**
A graph has four nodes: `classify`, `retrieve`, `generate`, and `escalate`. The routing after `classify` sends the query to `retrieve` if it is answerable, or to `escalate` if it requires human intervention. The routing after `generate` sends the response to the user if confidence is high, or loops back to `retrieve` if confidence is low (up to three times). A user submits a query that the classifier marks as answerable, the first generation attempt has low confidence, the second retrieval improves it to medium confidence, and the second generation attempt has high confidence. Write out the complete sequence of nodes executed and the state changes that trigger each routing decision.

**Correct answer criteria:**
- Execution sequence: `classify` → `retrieve` (first) → `generate` (first) → `retrieve` (second) → `generate` (second) → END
- After `classify`: the routing function reads a `query_class` field written by classify; value is "answerable," routes to `retrieve`
- After first `generate`: the routing function reads a `confidence` field written by generate; value is "low," iteration counter is 1 (below maximum of 3), routes back to `retrieve`
- After second `retrieve`: routes to `generate` (unconditional edge — retrieve always proceeds to generate)
- After second `generate`: the routing function reads `confidence`; value is "high," routes to END
- State changes that trigger routing: `query_class` = "answerable" after classify; `confidence` = "low" and `retry_count` = 1 after first generate; `confidence` = "high" and `retry_count` = 2 after second generate

**Partial credit criteria:**
- Correctly traces the node sequence but cannot identify which specific state field values trigger each routing decision
- Correctly identifies all routing decisions and their triggers but makes an error in the execution sequence

**Incorrect / no-credit criteria:**
- Produces a sequence that includes `escalate` (the classifier marked the query as answerable, so escalate should not be visited)
- Cannot identify the role of the iteration counter in the routing decision
- Traces the sequence in a direction that violates the defined edge structure

---

## Q14 — Checkpoint resume after failure

**Difficulty:** advanced

**Question:**
A graph agent processes a multi-step document analysis workflow with checkpoints configured after each node. The workflow has five nodes. After the third node completes and its checkpoint is saved, a process restart occurs. When the workflow resumes, describe exactly what happens: where does execution start, what state does it begin with, and what are the operational implications if the third node has a side effect (for example, it sent a notification to an external system)?

**Correct answer criteria:**
- Execution resumes at the fourth node — the graph loads the checkpoint saved after the third node and begins there
- The initial state for the resumed execution is exactly the state captured in the checkpoint — all fields written by nodes one through three are present; the state is identical to what it was immediately after the third node completed
- No re-execution of nodes one through three occurs — the checkpoint is the authoritative record of their output
- Side effect implication: if the third node sent an external notification, that notification was already sent before the crash. On resume, the notification is not re-sent (the third node does not re-execute). This is correct behavior if the notification should be sent exactly once. However, if the crash occurred after the notification was sent but before the checkpoint was saved, the graph might re-execute the third node on resume (since no checkpoint exists for it), and the notification would be sent again — a "at least once" delivery problem. Correct design requires that the checkpoint be saved immediately after the side effect completes, and that external side effects be idempotent where possible.

**Partial credit criteria:**
- Correctly describes where execution resumes and the initial state but does not address the side effect implication
- Correctly identifies the side effect risk but describes the resumption point incorrectly

**Incorrect / no-credit criteria:**
- States that execution re-starts from node one on any failure
- States that all five nodes re-execute and checkpoints are used only for logging
- Cannot explain what an "idempotent" side effect is or why it matters for checkpoint-based resumption

---

## Q15 — Self-correction loop design

**Difficulty:** advanced

**Question:**
Design the graph topology for a RAG agent that should self-correct retrieval. The agent should first generate an answer from an initial retrieval, then evaluate whether the retrieved context was actually used in the answer (a faithfulness check), and if faithfulness is below a threshold, retrieve again with a refined query before generating a final answer. The cycle should terminate after at most two refinement attempts. Describe the nodes, the edges (including which are conditional), and the state fields that carry information between nodes.

**Correct answer criteria:**
- Nodes: `initial_retrieve`, `generate`, `faithfulness_check`, `refine_query`, `re_retrieve`, `final_generate` (or a unified approach with a single `retrieve` node and a cycle counter)
- Acceptable simplified topology: `retrieve` → `generate` → `faithfulness_check` → (conditional) → `END` if faithful or `refine_query` if unfaithful → `retrieve` (cycle back) → `generate` → `faithfulness_check` → (conditional) → `END` regardless (iteration cap reached)
- Required state fields: `retrieved_context` (written by retrieve, read by generate and faithfulness_check), `answer` (written by generate, read by faithfulness_check), `faithfulness_score` (written by faithfulness_check, read by routing function), `refinement_count` (incremented by refine_query or the routing function, read by routing function to enforce the two-attempt cap), `refined_query` (written by refine_query, read by re-retrieve)
- Conditional edges: after `faithfulness_check`, routing function reads `faithfulness_score` and `refinement_count`; if score is above threshold, route to END; if score is below threshold and count is less than 2, route to `refine_query`; if score is below threshold and count equals 2, route to END (cap reached)
- The iteration cap must be enforced in the routing function by reading state, not by relying on the LLM faithfulness checker to stop on its own

**Partial credit criteria:**
- Describes a valid topology and all required state fields but does not explicitly enforce the two-attempt cap in the routing function
- Enforces the cap correctly but omits one or more required state fields from the design

**Incorrect / no-credit criteria:**
- Proposes a sequential chain (which cannot express the cycle)
- Describes a topology where the cycle can run more than two times without a structural cap
- Cannot identify which state fields the routing function must read to make its decision

---

## Q16 — Why graph topology is the right place for capability boundaries

**Difficulty:** expert

**Question:**
A security-conscious team is building a graph agent that should be able to search internal documentation, summarize documents, and answer questions. The agent must never be allowed to send emails or post to external systems, even if a user's query could be interpreted as requesting that action. Explain why enforcing this boundary in the graph topology is more reliable than enforcing it through prompt instructions to the LLM, and describe what the topology-based enforcement looks like in practice.

**Correct answer criteria:**
- Prompt-based enforcement relies on the LLM choosing to comply with instructions every time — it is probabilistic. A sufficiently crafted user query, a model update, or a prompt injection could cause the LLM to generate a response that bypasses or ignores the instruction. Prompt instructions are not a structural guarantee.
- Topology-based enforcement: if there is no node in the graph that sends email or posts to external systems, and no edge that connects any existing node to such a capability, then the agent structurally cannot perform those actions. No output the LLM generates can trigger email sending because the graph has no execution path to an email-sending node.
- In practice: the graph contains only `search_documentation`, `summarize`, and `answer` nodes. The LLM node's output is written to state fields that the routing function reads — the routing function can only route to defined successors. Since "send_email" is not a defined node, the routing function cannot return it; the state field the LLM might write with "send email" is simply not connected to any execution path.
- The topology-based approach converts a policy (the agent should not send email) into a structural constraint (the agent cannot send email) — the difference between a rule the system chooses to follow and a rule the system physically cannot violate.

**Partial credit criteria:**
- Correctly identifies that prompt instructions are probabilistic and topology is structural but cannot describe what the topology looks like in practice
- Correctly describes the topology in practice but frames prompt instructions as equally reliable

**Incorrect / no-credit criteria:**
- Claims that prompt instructions and topology enforcement are equivalent in reliability
- Describes topology enforcement as adding a filter node that the LLM's output passes through (this is still probabilistic — the filter node would need to correctly identify all possible email-sending requests)
- Cannot explain what "structural constraint" means in the context of graph execution

---

## Q17 — Diagnosing state schema drift in a live graph

**Difficulty:** expert

**Question:**
A graph agent has been in production for three months. A developer adds a new node to the graph and introduces a new state field `user_intent` that the new node writes and a downstream routing function reads. After deployment, the routing function always routes to the default branch even for queries where `user_intent` should trigger the alternative path. No exceptions are logged. Describe the systematic diagnostic process for this failure, identifying at least three possible root causes and the observation that would confirm or rule out each one.

**Correct answer criteria:**
- Root cause 1 (new node not executing): the new node may not be connected correctly in the graph — either no edge routes to it or the edge condition is never satisfied. Confirm by adding execution logging to the new node; if no log lines appear, the node is not being executed. Rule out by confirming the node appears in the execution trace.
- Root cause 2 (field name mismatch): the new node writes to `user_intent` but the routing function reads `userIntent` or `intent` — a naming inconsistency. Confirm by logging the full state dictionary at the point the routing function executes and checking whether `user_intent` is present and populated. Rule out by confirming the field exists in state with the expected value.
- Root cause 3 (state merge conflict): if the graph merges state updates using a reducer that overwrites with the previous state on conflict, a node that runs after the new node may be overwriting `user_intent` with a default or empty value. Confirm by logging state immediately after the new node and again immediately before the routing function; if the field is present after the node but absent before routing, a later node is clearing it. Rule out if state is consistent between the two checkpoints.
- Root cause 4 (routing function reads stale compiled version): in environments with hot-reloading or cached compiled graphs, the deployed execution may still use an older compiled graph that does not include the new node. Confirm by verifying the process is running the most recently compiled graph version. Rule out by restarting the service with a fresh compilation.
- Correct debugging order: log state at the routing function first (cheapest, most direct) → trace whether the new node executed → check for field name mismatch → investigate merge conflicts.

**Partial credit criteria:**
- Identifies three root causes correctly but cannot describe the specific observation that confirms or rules out each one
- Correctly performs the diagnostic in the right order but identifies fewer than three root causes

**Incorrect / no-credit criteria:**
- Proposes rewriting the routing function to handle None or empty `user_intent` without investigating the write-side failure
- Cannot identify state merge conflicts as a possible cause
- Attributes the failure to the graph framework without any evidence of a framework bug

---

## Q18 — Multi-agent graph coordination

**Difficulty:** expert

**Question:**
A team wants to build a system where a "planner" graph agent breaks a complex task into subtasks, and multiple "executor" graph agents each handle one subtask in parallel. The planner and executors are separate compiled graphs. Describe the coordination architecture: how does the planner pass subtasks to executors, how do executor results return to the planner, and what failure mode arises if an executor crashes mid-execution and how does checkpointing address it?

**Correct answer criteria:**
- Coordination architecture: the planner graph's state contains a list of subtasks; a fan-out node (or a dispatch mechanism) invokes each executor graph with one subtask as input state; each executor is a separate compiled graph invocation with its own thread identifier and checkpoint namespace
- Result return: each executor's final state (containing the subtask result) is passed back to the planner — this can be done by the dispatch node collecting executor return values or by a shared coordination store that executors write to and the planner reads from; the planner's fan-in node waits for all executor results before proceeding
- Failure mode on executor crash: if an executor crashes mid-execution and checkpointing is configured for the executor graph, the executor can resume from its last checkpoint when restarted — it does not re-execute the subtask from the beginning. If checkpointing is not configured, the executor must restart the full subtask.
- The planner must handle partial results: if one executor fails and cannot be recovered, the planner's fan-in node must decide whether to proceed with incomplete results, retry the failed executor, or escalate to the user. This requires the planner's state to track which executors have completed and which have failed, so the fan-in routing function can make an informed decision.

**Partial credit criteria:**
- Correctly describes the dispatch and result return mechanism but does not address the executor crash failure mode
- Correctly addresses the crash and checkpointing scenario but describes the coordination architecture with a single shared graph rather than separate compiled graphs per executor

**Incorrect / no-credit criteria:**
- Describes a sequential rather than parallel executor pattern
- States that the planner graph's state automatically includes all executor states (separate compiled graphs have separate state namespaces)
- Cannot explain why the planner needs to track executor completion status in its own state

---

## Q19 — Graph versioning and live migrations

**Difficulty:** expert

**Question:**
A production graph agent with thousands of active conversation threads needs to be upgraded to a new graph version that adds a node and changes the state schema (a new required field is added). Active threads have checkpoints saved under the old schema. Describe the migration challenge, the failure mode that occurs if old checkpoints are loaded into the new graph without modification, and a strategy to migrate safely without interrupting active conversations.

**Correct answer criteria:**
- Migration challenge: the new graph expects a state object with a new required field; checkpoints saved under the old schema do not contain this field; when the new graph loads an old checkpoint, the new field is absent from the initial state
- Failure mode: the new node (which reads the new field) receives None or an empty default; depending on what the node does with that value, it may produce incorrect output, route unexpectedly, or raise an exception — the behavior is undefined with respect to the application's intent
- Safe migration strategy option 1 (additive with default): design the new field with a sensible default value (e.g., an empty string, a "not_set" sentinel) that the new node handles gracefully. Old checkpoints load without error; the new node detects the default and takes a safe fallback path. This allows gradual migration as threads naturally complete and new ones start under the new schema.
- Safe migration strategy option 2 (checkpoint migration): before deploying the new graph, run a migration job that reads every active checkpoint, adds the new field with its computed or default value, and saves the updated checkpoint back to the store. New graph is deployed only after all checkpoints are migrated.
- Option 1 is preferred for large-scale systems because it avoids a migration window and allows zero-downtime deployment; Option 2 guarantees all threads start with correct state but requires a migration window and fails if any checkpoint cannot be migrated.
- The new field must not be required in a way that causes hard failures for old checkpoints — schema evolution must be backward-compatible or gated behind a migration step.

**Partial credit criteria:**
- Correctly identifies the failure mode and describes one migration strategy with its tradeoffs
- Describes both migration strategies but cannot explain why backward compatibility requires either a default value or a migration step

**Incorrect / no-credit criteria:**
- Proposes terminating all active conversation threads before deploying the new graph (operationally unacceptable for most systems)
- Claims the new graph automatically handles missing fields by re-running the nodes that would have populated them
- Cannot explain what "schema evolution" means in the context of checkpointed graph state

---
