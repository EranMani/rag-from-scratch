# MCQ Bank — langgraph_fundamentals
# Topic: langgraph_fundamentals
# Phase: 3 (Advanced Topics)
# Questions: 20 (5 novice, 5 intermediate, 5 advanced, 5 expert)
# Last updated: 2026-05-23 (Commit 50)

---

## MCQ-1 — Node definition in a computation graph

**Difficulty:** novice
**Topic:** langgraph_fundamentals

**Question:**
In a directed computation graph, what is a node?

**Options:**
A. A database record that stores intermediate results between pipeline runs
B. A discrete operation or processing unit that receives state, performs work, and returns an updated state
C. A connection between two processing units that carries data in both directions
D. A configuration file that specifies which functions are available to the graph

**Correct answer:** B

**Explanation:**
In a computation graph, a node is the unit of work. It receives the current shared state, performs an operation (call an LLM, run a retrieval step, apply a transformation), and returns an updated version of that state. Nodes are not storage records (A), not connections between units (C — that is an edge), and not configuration files (D). Each node has a defined input (state) and a defined output (updated state), which is what allows the graph to sequence and branch execution.

**Why A is wrong:** A node is not a persistence construct. Nodes are operational units, not storage records. A developer familiar with database design patterns may conflate "node" as a data storage concept (as in a graph database node) with the computation graph meaning, where a node is a processing function.

**Why C is wrong:** Connections that carry data between nodes are edges, not nodes. Confusing nodes and edges is the most common entry-level misconception about graph architecture — it reflects reading a graph diagram without understanding the distinction between processing units and data flow connectors.

**Why D is wrong:** Nodes are not configuration files. They are executable operations. A developer who thinks of a graph as a declarative configuration rather than an execution structure may reach for this answer, but nodes are the "what runs" component — not the "what is available" component.

---

## MCQ-2 — Edge definition in a computation graph

**Difficulty:** novice
**Topic:** langgraph_fundamentals

**Question:**
What does a directed edge represent in a computation graph?

**Options:**
A. A shared memory buffer that both connected nodes can read and write simultaneously
B. The data transformation logic that converts one node's output format to the next node's input format
C. A directed connection that defines the allowed sequence of execution — from which node to which node control flows after a step completes
D. A checkpoint that saves the graph's current state to persistent storage

**Correct answer:** C

**Explanation:**
A directed edge defines execution flow: when node A completes, control passes to node B. Edges are structural — they encode the valid transitions in the graph. They do not perform transformations (B — that is the node's job), they do not provide shared memory access (A — shared state is a separate concept), and they do not trigger persistence (D — that is checkpointing). The direction of an edge is what makes the graph "directed" — execution moves in a defined direction, not bidirectionally.

**Why A is wrong:** Shared memory is a property of the graph's state object, not of an individual edge. Edges define which nodes connect; state defines what data flows. A developer who has worked with message-passing concurrency may associate connections with shared buffers, but in computation graphs edges are purely structural routing constructs.

**Why B is wrong:** Data format transformation is not an edge's responsibility. In a well-designed graph, all nodes read from and write to a shared state schema. If transformation is needed, it happens inside a node. Attributing transformation to edges reflects a misconception about where computation lives in a graph architecture.

**Why D is wrong:** Checkpointing is a separate graph capability that can be enabled or disabled independently of edge structure. An edge does not trigger a save operation — it triggers the execution of the next node. Conflating routing with persistence is a common error when first encountering graphs with memory.

---

## MCQ-3 — Acyclic vs. cyclic graphs

**Difficulty:** novice
**Topic:** langgraph_fundamentals

**Question:**
What distinguishes a cyclic graph from an acyclic graph in the context of agentic computation?

**Options:**
A. A cyclic graph stores state in a database; an acyclic graph stores state in memory only
B. A cyclic graph can contain loops — nodes can be visited more than once within a single execution; an acyclic graph executes each node at most once
C. A cyclic graph allows multiple entry points; an acyclic graph has exactly one entry point
D. A cyclic graph requires human input at each node; an acyclic graph executes fully automatically

**Correct answer:** B

**Explanation:**
The defining difference is whether execution can loop back. An acyclic graph (DAG) has no cycles — once a node completes, execution never returns to it. A cyclic graph can route execution back to a previously visited node, enabling self-correction loops, retry behaviors, and iterative refinement. For agentic systems, cycles are what enable an agent to check its own output and decide to redo a step rather than always proceeding linearly. State storage and entry points are not what distinguish cyclic from acyclic graphs.

**Why A is wrong:** State storage location (database vs. memory) is a checkpointing configuration decision, not a property of graph topology. Both cyclic and acyclic graphs can persist state to a database if checkpointing is enabled. Topology and storage are independent concerns.

**Why C is wrong:** Multiple entry points vs. single entry point is an independent graph design choice that does not correlate with cyclic vs. acyclic topology. A cyclic graph can have one entry point, and an acyclic graph can theoretically have multiple starting nodes. The cycle/acycle distinction is purely about whether execution can revisit nodes.

**Why D is wrong:** Human-in-the-loop involvement is an optional design pattern that can be applied to either cyclic or acyclic graphs. Requiring human approval at a node is a conditional routing decision, not a property of the graph type. Associating cycles with human input reflects a surface reading of "loop = waiting for something."

---

## MCQ-4 — What graph compilation validates

**Difficulty:** novice
**Topic:** langgraph_fundamentals

**Question:**
Before a graph can be executed, it must be compiled. Which of the following best describes what compilation validates?

**Options:**
A. Compilation runs a test query through the graph to verify that the LLM nodes return coherent responses
B. Compilation checks that all nodes are connected into a valid execution structure — that entry and exit points are defined, that every node is reachable, and that there are no structural contradictions
C. Compilation converts the graph definition into a database schema for storing execution results
D. Compilation locks the graph so that no additional nodes or edges can be added after execution begins

**Correct answer:** B

**Explanation:**
Graph compilation is a structural validation step. It confirms that the graph as defined is executable: entry points exist, terminal conditions are reachable, all defined nodes have edges connecting them, and the execution structure is internally consistent. Compilation does not run a test query with a real LLM (A) — it validates structure, not behavior. It does not produce a database schema (C) — it produces an executable artifact. And while the compiled graph is a fixed artifact, the purpose of compilation is validation and artifact creation, not just locking (D).

**Why A is wrong:** Compilation is a structural check, not a behavioral test. Running a test query would require an LLM call, which is expensive and non-deterministic. Structural validation is cheap and deterministic. A developer who expects compilation to behave like integration testing will be confused when compilation passes but runtime behavior is unexpected — because compilation never tested runtime behavior.

**Why C is wrong:** Compilation does not produce a storage schema. It produces an executable graph artifact. The outputs of graph execution (state at each step) may be persisted, but that persistence is handled by checkpointing configuration, not by the compilation step. Conflating the graph definition with a data model is a category error.

**Why D is wrong:** Preventing mutation is a consequence of compiling (you work with the compiled artifact, not the builder), but it is not the purpose of compilation. The purpose is structural validation — confirming the graph is executable before any invocation attempt. Framing it as a locking mechanism misses the validation function entirely.

---

## MCQ-5 — Graph vs. sequential chain

**Difficulty:** novice
**Topic:** langgraph_fundamentals

**Question:**
Which capability does a graph architecture provide that a sequential chain cannot?

**Options:**
A. Calling an external API from within a processing step
B. Routing execution to different nodes based on the current state — including looping back to a previous node
C. Accepting a user query as input and producing a text response as output
D. Logging each step's input and output for observability

**Correct answer:** B

**Explanation:**
A sequential chain executes a fixed sequence of steps in order: step 1, step 2, step 3, done. It cannot branch and cannot loop. A graph architecture adds conditional routing (the next node depends on the current state) and cycles (execution can return to a node it has already visited). This enables behaviors that sequential chains cannot produce: self-correction, retrieval-on-demand, retry loops, and parallel branches that merge downstream. API calls (A), accepting input/output (C), and logging (D) are all available in sequential chains as well.

**Why A is wrong:** External API calls are a node-level capability — any processing step can call an API regardless of whether the step is in a chain or a graph. The graph architecture does not uniquely enable API access. A developer who equates "graph" with "can do more complex things" may reach for this, but API calls are not what distinguishes the two architectures.

**Why C is wrong:** Accepting a query and returning a response is the basic interface of both sequential chains and graphs. Input-output handling is not unique to graph architecture. A developer who reads question C literally may think it is trivially obviously not the answer — but it is included because some developers do conflate "agentic" with "conversational."

**Why D is wrong:** Logging and observability tooling can be applied to sequential chains as well as graphs. Adding trace logging to a chain step is a framework feature, not a graph architecture feature. The distinguishing capability of graphs is execution topology, not observability.

---

## MCQ-6 — State flow between nodes

**Difficulty:** intermediate
**Topic:** langgraph_fundamentals

**Question:**
In a graph execution, how does data move from one node to the next?

**Options:**
A. Each node's return value is passed directly as a positional argument to the next node's function signature
B. Nodes read from and write to a shared state object; each node updates fields in that state, and the updated state is what subsequent nodes receive as input
C. Nodes communicate by writing to a message queue; the next node consumes its message and acknowledges receipt
D. The graph serializes each node's output to JSON, transmits it over a local socket to the next node, and deserializes it on the other side

**Correct answer:** B

**Explanation:**
In a graph execution model, all nodes share a single state object. A node receives the current state, performs its work, and returns an update (the fields it changed). The graph merges that update into the state and passes the updated state to the next node. This shared-state architecture means nodes are loosely coupled — a retrieval node does not need to know the LLM node's function signature; both just read and write the fields they care about in shared state. Direct argument passing (A), message queues (C), and socket serialization (D) are not the model.

**Why A is wrong:** Direct positional argument passing would create tight coupling between adjacent nodes — changing one node's return type would break all downstream nodes that consume it. The shared state model avoids this. A developer who thinks of nodes as ordinary function call chains will expect argument passing, but graph nodes are designed for loose coupling via shared state, not tight coupling via function signatures.

**Why C is wrong:** Message queues are a distributed systems pattern for decoupling producers and consumers across process boundaries. Graph node execution within a single compiled graph is in-process and synchronous — nodes do not communicate via queues. A developer with distributed systems background may recognize the "pass data between processing units" pattern and reach for message queuing as the mechanism.

**Why D is wrong:** JSON serialization over a socket describes a microservices or IPC pattern. Graph node execution happens within a single process. There is no serialization/deserialization overhead between nodes — state is passed in memory. Attributing socket-level communication to within-graph execution reflects a misunderstanding of graph execution boundaries.

---

## MCQ-7 — Conditional routing mechanism

**Difficulty:** intermediate
**Topic:** langgraph_fundamentals

**Question:**
In a graph with conditional routing, what determines which node executes next after a given node completes?

**Options:**
A. The node's return value's data type — the graph infers the next node based on whether the return was a string, integer, or dict
B. A routing function that examines the current state and returns the name of the next node to execute
C. The alphabetical order of node names — the graph executes nodes in alphabetical sequence unless interrupted by an error
D. The LLM's free-text output — the graph parses the LLM response for a destination node name

**Correct answer:** B

**Explanation:**
Conditional routing in a graph is implemented via a routing function (sometimes called a conditional edge function). After a node completes, the graph calls this function with the current state; the function inspects state values and returns the identifier of the next node to execute. This is what enables branching: the routing function can return "node_A" or "node_B" or "END" depending on what the state contains. Return type inference (A) is not a mechanism; alphabetical ordering (C) does not exist; and raw LLM output parsing (D) would be fragile and is not the graph's routing mechanism.

**Why A is wrong:** A graph does not infer routing from return value types. This misconception may arise from familiarity with dynamically typed languages where function return types carry meaning, but graph routing is an explicit structural decision made at graph definition time — not inferred at runtime from type signatures.

**Why C is wrong:** There is no alphabetical node ordering in graph execution. Nodes execute in the order determined by edges and routing functions. A developer who has not encountered computation graphs may assume some default ordering (alphabetical, registration order), but graphs are explicitly wired — there is no default sequence.

**Why D is wrong:** Having the LLM embed the next node name in its free-text output and parsing it is a fragile anti-pattern, not the graph's routing mechanism. The graph's routing is structural and deterministic based on state values — it does not depend on parsing natural language. Some agentic patterns do ask an LLM to "decide" the next step, but this decision is captured in a structured state field before routing occurs, not extracted directly from raw LLM output by the routing infrastructure.

---

## MCQ-8 — Why conditional routing differs from in-node if-statements

**Difficulty:** intermediate
**Topic:** langgraph_fundamentals

**Question:**
A developer says: "I can get the same branching behavior by putting an if-statement inside a node's logic — why would I define a separate conditional edge in the graph structure?" What is the strongest argument for conditional edges at the graph level?

**Options:**
A. Conditional edges execute faster than if-statements because they run at compile time rather than at runtime
B. Conditional edges at the graph level make the branching structure explicit and inspectable as topology — the routing logic is part of the graph's definition, not hidden inside node implementations
C. Conditional edges are required by the LLM provider's API contract; if-statements inside nodes are not permitted
D. Conditional edges prevent the graph from entering infinite loops; if-statements inside nodes cannot enforce cycle termination

**Correct answer:** B

**Explanation:**
The key difference is where the branching decision lives. An if-statement inside a node embeds routing logic in node implementation — it is invisible to the graph structure and cannot be reasoned about, visualized, or modified without reading inside the node. A conditional edge defined at the graph level makes the branching visible as graph topology: you can inspect the graph and see which conditions lead to which nodes without opening any node implementation. This matters for debugging (trace which branch was taken), for visualization, and for maintaining the separation between computation (nodes) and control flow (edges). The other options describe fabricated constraints.

**Why A is wrong:** Conditional edges do not run at compile time — they are routing functions that execute at runtime after each node completes. Compilation validates structure; it does not pre-evaluate routing decisions. A developer who conflates "compiled" with "static/pre-computed" will reach for this, but graph compilation is structural validation, not pre-execution.

**Why C is wrong:** LLM provider APIs have no opinion on whether branching logic is in nodes or edges. This is a graph architecture decision entirely under the developer's control. No external API contract governs internal graph routing structure.

**Why D is wrong:** Conditional edges do not inherently prevent infinite loops, and if-statements inside nodes can implement termination logic. Cycle termination requires an explicit termination condition — whether it is expressed as a conditional edge or as logic inside a node is a design choice, not a capability difference. Both mechanisms require the developer to define when to stop looping.

---

## MCQ-9 — What a compiled graph produces

**Difficulty:** intermediate
**Topic:** langgraph_fundamentals

**Question:**
After a graph definition is compiled, what does the compilation produce, and how is it used?

**Options:**
A. A static report listing all nodes, their connections, and their expected latencies at runtime
B. An executable artifact that accepts an initial state as input and orchestrates node execution according to the defined topology — invocable like a function
C. A SQL migration script that creates database tables for storing each node's intermediate results
D. A Docker image containing the graph definition and all its dependencies, ready for container deployment

**Correct answer:** B

**Explanation:**
Compilation takes a graph definition (nodes, edges, routing functions) and produces an executable artifact — a callable object that runs the graph when invoked with an initial state. The compiled graph is what you invoke to run the agent. It handles the execution loop: calling the next node, routing based on state, managing state updates, triggering checkpoints if configured. It is not a report (A), not a database migration (C), and not a container image (D). The compilation step is analogous to compiling source code to a binary: the definition becomes an executable.

**Why A is wrong:** Compilation is not a reporting step. It does not estimate latencies or produce documentation. A developer who has used static analysis tools may think of "compilation" as generating a report about the code, but graph compilation is a transformation from definition to executable, not an analysis step.

**Why C is wrong:** Graph compilation has no relationship to database migrations. State persistence in graphs is handled by checkpointing configuration, which is separate from the compilation process. A developer who thinks "graph compiles → storage is set up" has conflated two independent concerns.

**Why D is wrong:** Container images are deployment artifacts. Graph compilation produces an in-process executable object, not a deployable container. Packaging a graph for deployment (containerization, scaling) is an infrastructure concern separate from compilation, which is purely about creating an executable from the graph definition.

---

## MCQ-10 — Checkpointing and multi-turn memory

**Difficulty:** intermediate
**Topic:** langgraph_fundamentals

**Question:**
A graph agent needs to remember the context of a conversation across multiple turns — not just within one invocation, but across separate invocations separated by minutes or hours. Which graph mechanism enables this?

**Options:**
A. The LLM's context window automatically retains conversation history between invocations if the same model instance is used
B. Checkpointing — the graph persists the full state at the end of each invocation, and a subsequent invocation resumes from the last saved state for the same conversation thread
C. A global in-memory dictionary that all graph instances share to store conversation state between invocations
D. Increasing the top-k retrieval parameter so that more historical context is included in each new invocation

**Correct answer:** B

**Explanation:**
Checkpointing is the mechanism that enables multi-turn conversational memory. At the end of each graph invocation (or at configurable intermediate points), the full state is persisted to a durable store. When the next message in a conversation arrives, the graph retrieves the checkpoint for that conversation's thread identifier and resumes execution from the saved state. The LLM's context window is stateless between invocations (A). A global in-memory dictionary (C) does not survive process restarts and does not scale across multiple processes. Increasing top-k (D) is a retrieval parameter, not a state persistence mechanism.

**Why A is wrong:** LLMs are stateless. They do not retain information between API calls. Each invocation receives exactly what is in the prompt and nothing more. A developer who thinks the LLM "remembers" previous conversations without explicit state management is holding a fundamental misconception about how language model inference works — state must be managed externally.

**Why C is wrong:** A global in-memory dictionary is a fragile single-process solution that cannot survive restarts, cannot scale across workers, and cannot resume after a service interruption. Real checkpointing uses durable storage (a database, a file system, a key-value store). Treating shared process memory as equivalent to durable checkpointing is a reliability anti-pattern.

**Why D is wrong:** Top-k is the number of chunks retrieved from the vector store per query. It controls the breadth of retrieval context for a single invocation, not the persistence of conversation history across invocations. Increasing top-k does not make the graph remember anything — it just retrieves more chunks for the current turn.

---

## MCQ-11 — State not persisting between turns

**Difficulty:** advanced
**Topic:** langgraph_fundamentals

**Question:**
A multi-turn conversational graph agent is deployed. Users report that the agent "forgets" everything from previous turns on each new message — each response treats the conversation as if it just started. The graph definition and node logic are correct. What is the most likely structural cause?

**Options:**
A. The LLM node's prompt template is not including the conversation history field from state — it is only using the current user message
B. Checkpointing is not configured, so the graph executes with a fresh initial state on every invocation rather than resuming from a persisted state
C. The routing function is directing every invocation to the graph's entry node, bypassing the state accumulation logic
D. The state schema does not include a conversation history field, so even if checkpointing were enabled, conversation history could not be stored

**Correct answer:** B

**Explanation:**
The symptom is complete amnesia on every turn — the agent behaves as if each invocation is the first. This is the characteristic failure mode when checkpointing is absent. Without a checkpointer, the graph has no mechanism to retrieve the previous state for a conversation thread. Each invocation starts from the initial state provided at call time. The graph is structurally correct — the problem is that no state is being persisted between invocations. A describes a prompt template issue that would cause partial forgetting (the state exists but is not used in the prompt), not total amnesia. C and D describe other structural gaps that would produce different symptom patterns.

**Why A is wrong:** If checkpointing is working but the prompt template omits the history field, the agent would have access to the history in state but would not include it in the LLM's context. The symptom would be that the LLM behaves as if it forgot — but the state would still accumulate correctly. More importantly, with no checkpointing at all, even a correct prompt template cannot fix the problem because there is no state to read history from.

**Why C is wrong:** The routing function directing to the entry node every time would cause the graph to always start at the beginning of its logic — but if checkpointing were configured, it would still resume from the persisted state at that entry node. The combination of "always start at entry" with "resume from checkpoint" can work correctly; the combination of "no checkpointing" with "starts at entry" is the actual problem.

**Why D is wrong:** If the state schema lacks a conversation history field, the developer would have noticed during initial testing that history was not accumulating — the symptom would be obvious from the start, not discovered in deployment. More importantly, this diagnosis is secondary: if checkpointing is not configured, the state schema is irrelevant because no state survives between invocations regardless of its schema.

---

## MCQ-12 — Infinite cycle in a graph

**Difficulty:** advanced
**Topic:** langgraph_fundamentals

**Question:**
A graph agent is designed to iteratively refine a draft until a quality check node marks the draft as acceptable. In production, some conversations cause the agent to loop indefinitely. The quality check node always returns "needs_revision." What is the most likely structural root cause?

**Options:**
A. The quality check node is not connected to the terminal node — there is no edge from "acceptable" to END, so even an acceptable draft keeps looping
B. The state field that tracks the draft is not being updated by the revision node — the revision node returns a new draft but does not write it to the shared state, so the quality check always sees the original unrevised draft
C. The LLM temperature is set too high, causing the revision node to produce drafts that consistently fail quality criteria
D. The graph's maximum iteration count is not configured, so the graph framework does not automatically terminate cycles

**Correct answer:** B

**Explanation:**
If the revision node does not correctly write the revised draft back to the shared state, the quality check node reads the same unrevised draft on every iteration. The cycle never terminates because the draft never changes. This is the most common structural cause of infinite cycles in graph agents: a node produces an updated value but fails to commit it to the state correctly (wrong field name, returning a non-update value, state merge logic not applied). The quality check node is working correctly — it sees a draft that genuinely needs revision. The error is upstream at the state write.

**Why A is wrong:** If there were no edge from "acceptable" to END, the graph would fail at compile time (structural validation would catch an unreachable terminal condition). A graph that compiles successfully has a valid path to termination defined at the structural level. Runtime infinite looping points to a runtime state problem, not a compile-time structural absence.

**Why C is wrong:** LLM temperature affects the diversity and creativity of generated text, not the systematic quality of revisions. High temperature might produce varied drafts, but it would not cause every single revision to fail quality checks — some would pass. Systematic infinite looping requires a consistent failure condition, which points to a state management problem rather than probabilistic LLM behavior.

**Why D is wrong:** A maximum iteration count is a useful safeguard, but its absence does not cause the underlying bug. If the iteration count were configured, it would terminate the loop without fixing the state write problem — the agent would still produce wrong answers up to the maximum count. The root cause is the revision node not writing to state, and the fix must be at that level.

---

## MCQ-13 — Routing always taking one branch

**Difficulty:** advanced
**Topic:** langgraph_fundamentals

**Question:**
A graph has a conditional routing function that should route to "retrieve" when the answer cannot be found in context, and "respond" when the answer is sufficient. In production, the routing function always routes to "respond," even when the answer quality is clearly insufficient. The routing function code is logically correct when read in isolation. What is the most likely structural cause?

**Options:**
A. The routing function is not registered as a conditional edge — it was added as a regular node, so it executes and writes its output to state but does not control routing
B. The state field that the routing function reads to make its decision is not being written by the preceding node — the field is always its initial/default value, which maps to the "respond" branch
C. The "retrieve" node is not compiled into the graph, so the routing function cannot route to a node that does not exist and falls back to "respond"
D. The conditional routing function is being called once at compile time and its result is hardcoded into the edge definition for all subsequent invocations

**Correct answer:** B

**Explanation:**
If the routing function reads a state field that the preceding node never writes, that field retains its initial value throughout execution. If the default value maps to the "respond" branch (e.g., an empty string or None that evaluates to "sufficient"), the routing function will always choose "respond" regardless of actual answer quality. The routing function logic is correct — its input is wrong. This is a state write gap: a node is responsible for populating a field that downstream routing depends on, and it is not fulfilling that responsibility. The routing function cannot compensate for a state it never receives.

**Why A is wrong:** If the routing function were added as a regular node rather than a conditional edge, it would execute and write its output to state, but it would not control routing — execution would continue on a fixed path. This would not produce "always responds" — it would produce a routing failure that manifests as a structural error or a consistently wrong execution path. This is a valid concern but not the most common cause of always-one-branch routing in a compiled, structurally valid graph.

**Why C is wrong:** An uncompiled node would be caught at compilation time. If "retrieve" were not registered in the graph, the compile step would fail when the routing function referenced a node name that does not exist in the graph. A graph that has compiled successfully has all referenced nodes present.

**Why D is wrong:** Routing functions execute at runtime after each node, not once at compile time. Compilation validates that the routing function is syntactically correct and references valid node names — it does not pre-evaluate the function or hardcode its output. A developer who conflates graph compilation with static analysis may think routing is resolved at compile time, but routing is inherently dynamic.

---

## MCQ-14 — Graph topology vs. chain topology

**Difficulty:** advanced
**Topic:** langgraph_fundamentals

**Question:**
A team is building a research assistant that should: (1) attempt to answer from cached knowledge, (2) retrieve from a vector store only if cached knowledge is insufficient, and (3) verify the answer quality after retrieval and loop back to retrieval if quality is low. Which architecture correctly handles this behavior, and why?

**Options:**
A. A sequential chain — the chain's conditional step feature handles branching without requiring graph topology
B. A graph — because the behavior requires conditional branching (cache vs. retrieve) and a cycle (loop back to retrieval if quality is low), neither of which a sequential chain can express
C. A graph — because vector store retrieval can only be performed inside a graph node, not inside a sequential chain step
D. A sequential chain — because the three behaviors can be written as three consecutive function calls with if-statements at each step

**Correct answer:** B

**Explanation:**
This behavior requires two capabilities that sequential chains cannot express: conditional branching (attempt cached answer, then either proceed directly to response or branch to retrieval based on cache sufficiency) and a cycle (retrieval → quality check → loop back to retrieval if needed). Sequential chains execute fixed sequences. You can embed if-statements in chain steps (D), but that hides routing in implementation and cannot express a loop back to a previous step — once a chain step completes, execution can only move forward. A graph topology makes both the conditional branch and the cycle explicit and executable. C is incorrect because retrieval is not topology-constrained.

**Why A is wrong:** Sequential chains do not have a "conditional step feature" that enables real branching at the chain structure level. A chain's steps execute in a fixed sequence. Conditional logic inside a step can choose between outputs, but it cannot redirect execution back to a previous step. This answer invents a capability that chains do not have.

**Why C is wrong:** Vector store retrieval is a capability that any processing step can perform — whether in a chain or a graph. The choice of graph topology is not driven by what retrieval requires; it is driven by the control flow the application requires. A developer who associates "retrieval = graph" is confusing a capability (retrieval) with an architectural requirement (cycling and branching).

**Why D is wrong:** Three consecutive function calls with if-statements describes a sequential chain with inline branching logic. This can handle the first conditional (cache vs. retrieve) if the logic always moves forward, but it cannot express the loop (return to retrieval if quality is low) without implementing an explicit while loop outside the chain framework — which is effectively implementing a graph manually without the graph infrastructure.

---

## MCQ-15 — The LLM as a node within the graph

**Difficulty:** advanced
**Topic:** langgraph_fundamentals

**Question:**
In a graph-based agent, which statement correctly describes the relationship between the LLM and the graph?

**Options:**
A. The LLM is the graph — it decides which nodes to call and in what order based on its reasoning about the user's request
B. The LLM is one node within the graph; the graph's topology governs what the LLM can do, what inputs it receives, and what happens with its output
C. The LLM and the graph are parallel systems — the LLM generates the response and the graph handles storage and routing of that response
D. The graph is a prompt template that the LLM fills in; the LLM's output is the "graph execution result"

**Correct answer:** B

**Explanation:**
The graph architecture defines the structure: which nodes exist, in what order they can execute, and what routing decisions are possible. The LLM is just one node in that structure. The graph controls what context the LLM receives (through what has been accumulated in state before the LLM node executes), what the LLM can do (its output is written to a state field, not freely executed), and what happens next (the routing function uses the LLM's output to determine the next node). The LLM does not control the graph — the graph constrains and channels what the LLM can do.

**Why A is wrong:** This describes a fully autonomous LLM agent that reasons about its own execution. In a graph architecture, execution topology is defined at definition time, not generated by the LLM at runtime. The LLM may produce content that a routing function uses to choose a branch, but the set of available branches and what each branch does is determined by the graph, not by the LLM.

**Why C is wrong:** The LLM and the graph are not parallel systems. They are nested: the LLM is embedded within the graph as one of its nodes. The LLM does not run independently alongside the graph — it runs when the graph routes execution to the LLM node, and its output is captured in the graph's state like any other node's output.

**Why D is wrong:** The graph is not a prompt template. A prompt template is a text artifact that structures what is sent to an LLM. A graph is an execution architecture — a structure of nodes and edges. The LLM's output is not the "graph execution result" — the graph may continue executing after the LLM node completes, routing to additional nodes before producing a final response.

---

## MCQ-16 — Resuming from a checkpoint

**Difficulty:** expert
**Topic:** langgraph_fundamentals

**Question:**
A graph agent with checkpointing enabled handles a multi-step workflow. After the third node completes, the process crashes. When the system restarts and the same conversation thread is resumed, which behavior is correct?

**Options:**
A. The graph re-executes all nodes from the beginning, but it compares each node's output to the checkpoint and skips nodes whose output matches what was previously saved
B. The graph resumes execution from the checkpoint saved after the third node completed — it begins at the fourth node with the state as it existed at the time of the crash
C. The graph discards the checkpoint and re-executes from the beginning because partial checkpoints are not valid resumption points
D. The graph replays all three nodes in read-only mode to reconstruct state, then executes the fourth node for the first time

**Correct answer:** B

**Explanation:**
Checkpointing saves the full state at each step. If the graph checkpointed after the third node completed, the crash left a valid, complete state snapshot at that point. When the conversation thread resumes, the graph loads the checkpoint for that thread and begins at the next step — the fourth node — with the state exactly as it was when the checkpoint was saved. No re-execution of completed steps is needed. The graph does not compare outputs (A), does not discard partial checkpoints (C), and does not replay in read-only mode (D). Resumption from a checkpoint is the exact purpose of checkpointing.

**Why A is wrong:** Re-executing all nodes and comparing outputs is a replay-and-verify strategy that adds unnecessary computation. Checkpoint-based resumption does not re-run completed steps — it treats the saved state as authoritative and starts from the next uncompleted step. A developer who thinks of checkpointing as "memoization" may expect this behavior, but checkpointing is state persistence for resumption, not result caching for deduplication.

**Why C is wrong:** A checkpoint saved after a successfully completed node is a complete and valid resumption point. The graph framework saves state at defined checkpoint intervals, and those saves are complete state snapshots. A developer who thinks "partial checkpoint" means an incomplete save is conflating checkpoint frequency with checkpoint completeness — each checkpoint is a complete state capture, even if checkpoints do not occur at every possible moment.

**Why D is wrong:** Read-only replay is unnecessary overhead. If the state was correctly saved to the checkpoint store, the graph can read that state directly without replaying the nodes that produced it. Replaying nodes to reconstruct state would require those nodes to be deterministic — which is not guaranteed for LLM nodes. Checkpointing exists precisely to avoid replaying non-deterministic computations.

---

## MCQ-17 — What graph topology cannot change at runtime

**Difficulty:** expert
**Topic:** langgraph_fundamentals

**Question:**
A production graph agent is observed taking an unexpected execution path through nodes that are not part of the expected workflow. The state at the time of deviation shows that the LLM produced a response suggesting an alternative action. What is the correct interpretation of this situation?

**Options:**
A. The LLM modified the graph's edge structure at runtime, adding a new execution path based on its reasoning
B. The routing function used the LLM's output as input and returned a node name that was already defined in the graph's compiled topology — the LLM influenced the routing decision but did not change the topology
C. The graph's compilation was incomplete, leaving some edges undefined and defaulting to an automatic fallback path
D. The unexpected path was introduced by a checkpointing error that loaded the state from a different conversation thread

**Correct answer:** B

**Explanation:**
Graph topology is fixed at compile time. The set of nodes and the set of possible execution paths are determined when the graph is compiled — they cannot be modified at runtime. What a routing function can do is select among the predefined paths based on state (including state fields populated by an LLM node). If the LLM produced a response that led the routing function to choose an infrequently used but valid branch, the path is "unexpected" from an operational monitoring perspective but is structurally correct. The LLM influenced the decision, but the path it led to was already compiled into the graph. The graph executed correctly — the operational surprise is a monitoring gap, not a graph fault.

**Why A is wrong:** A running graph cannot modify its own edge structure. The compiled graph is a fixed artifact. No node — including an LLM node — can add, remove, or redirect edges at runtime. A developer who anthropomorphizes the LLM as "deciding to do something different" may reach for this, but LLM output is data that flows through state and influences routing functions — it does not modify execution infrastructure.

**Why C is wrong:** An incomplete compilation would produce a compile-time error, not a silent runtime fallback. If any edge were undefined or a node were referenced without being registered, the compile step would fail. A graph that compiled successfully has all edges and nodes fully defined. The unexpected path is a defined path — it was not a fallback for a missing edge.

**Why D is wrong:** A checkpointing error that loaded the wrong thread's state would produce a very different symptom: the agent would respond to the wrong conversation history, likely producing incoherent responses given the mismatch. An unexpected but coherent execution path within the correct conversation context is not consistent with a state-loading error.

---

## MCQ-18 — Parallel branches in a graph

**Difficulty:** expert
**Topic:** langgraph_fundamentals

**Question:**
A graph is designed to query two different knowledge bases in parallel and then synthesize the results. After both retrieval nodes complete, a synthesis node combines their outputs. Which statement correctly describes how the graph manages this parallel execution pattern?

**Options:**
A. The graph framework automatically detects that two nodes have no dependency between them and executes them in separate threads; no explicit graph structure is needed to express parallelism
B. The graph topology must explicitly define parallel branches — both retrieval nodes are connected from a common predecessor, and a merge node is connected from both — the framework then executes branches in parallel when the structure indicates it
C. Parallel execution requires running two separate compiled graph instances simultaneously, with a coordinator process collecting their outputs
D. Parallel branches are not possible in a single compiled graph; the developer must implement the two retrievals sequentially inside a single node

**Correct answer:** B

**Explanation:**
Parallel execution in a graph architecture requires explicit topology: both retrieval nodes must be connected as successors to a common predecessor node (the "fan-out" point), and a synthesis node must be connected as a successor to both retrieval nodes (the "fan-in" point). With this structure defined, the graph framework can execute the parallel branches concurrently. The parallelism is not auto-detected from dependency analysis (A) — it must be structurally encoded. It does not require separate graph instances (C) — parallel branches are a single-graph feature. And sequential fallback within a single node (D) sacrifices the latency benefits of parallelism while adding implementation complexity.

**Why A is wrong:** Automatic dependency analysis and implicit parallelism is not how graph frameworks work. The topology must be explicit. A developer who has worked with dataflow frameworks (like Apache Spark) where parallelism is inferred from data dependencies may expect automatic parallelism detection, but computation graph frameworks require the developer to wire the parallel structure explicitly.

**Why C is wrong:** Two separate compiled graph instances with a coordinator is a distributed computing pattern — it is a solution to a different problem (scale-out across processes or machines). For parallel branches within a single execution, this pattern adds unnecessary complexity and coordination overhead. Parallel branches in a single compiled graph are the appropriate mechanism.

**Why D is wrong:** Implementing two retrievals sequentially inside a single node is a valid approach for simplicity but sacrifices latency. If both retrievals take 500ms, sequential execution takes 1000ms while parallel execution takes 500ms. More importantly, D claims parallel branches are impossible — this is incorrect. Graph frameworks explicitly support fan-out/fan-in topologies for parallel execution.

---

## MCQ-19 — Cycle termination guarantee

**Difficulty:** expert
**Topic:** langgraph_fundamentals

**Question:**
A graph agent is designed to iteratively improve a response until it meets a quality threshold. The quality check is performed by an LLM judge node. In production, the agent occasionally loops indefinitely even though the judge was expected to eventually approve the response. Which analysis correctly identifies the structural gap?

**Options:**
A. The graph framework should automatically terminate any cycle that runs more than 10 iterations; if the cycle is running indefinitely, the framework has a bug
B. Cycle termination depends entirely on the LLM judge's output — since the LLM is non-deterministic, a cycle that the judge never terminates is a known limitation of LLM-based routing
C. The graph has no hard termination condition defined — there is no iteration counter in state, no maximum cycle count configured, and no fallback exit condition. The cycle terminates only if the LLM judge produces a specific output, which may never occur for some inputs
D. The graph should be refactored to a sequential chain for any workflow involving cycles, because chains handle iteration limits automatically

**Correct answer:** C

**Explanation:**
An LLM judge is a non-deterministic component. For some inputs, the judge may consistently find the response insufficient — perhaps because the task is genuinely too hard, because the revision node produces degraded outputs, or because the quality criteria are miscalibrated. A graph that relies solely on the LLM judge's output to terminate a cycle has no safety net. The structural gap is the absence of a hard termination condition: an iteration counter that increments with each cycle, a maximum cycle count that triggers a graceful exit edge, or a fallback condition that exits the cycle after N attempts regardless of quality. The graph framework does not auto-terminate (A), but this is a design responsibility, not a bug. B incorrectly treats the problem as a known limitation rather than a fixable design gap. D is incorrect — sequential chains cannot express cycles.

**Why A is wrong:** Graph frameworks do not automatically impose iteration limits. The developer is responsible for defining when cycles terminate. Expecting the framework to auto-terminate cycles reflects a misunderstanding of what the framework guarantees — it guarantees structural validity and state management, not behavioral termination. Some frameworks do provide a configurable maximum step count as a safety setting, but this is optional configuration, not default behavior.

**Why B is wrong:** Treating infinite looping as an inherent limitation of LLM-based routing is incorrect and operationally dangerous. The fix is to add a hard termination condition — an iteration counter that exits the cycle after N attempts regardless of the judge's output. Non-determinism in an LLM node does not make cycle termination impossible; it makes hard termination conditions mandatory.

**Why D is wrong:** Sequential chains cannot express cycles — this is one of the reasons graphs exist. Refactoring a cyclic workflow to a chain would eliminate the cycle, producing a workflow that makes exactly one improvement attempt regardless of quality. This does not solve the problem — it removes the iterative refinement capability that motivated the graph design.

---

## MCQ-20 — State schema as a contract

**Difficulty:** expert
**Topic:** langgraph_fundamentals

**Question:**
Two developers each own different nodes in a shared graph. Developer A's node populates a state field named `retrieved_context`. Developer B's LLM node reads that field to construct a prompt. After a refactor, Developer A renames the field to `retrieval_results`. Developer B's node was not updated. What failure mode occurs, and at what point is it surfaced?

**Options:**
A. The failure is caught at compile time — the graph compiler validates that all state field reads have a corresponding write with the same field name
B. The failure is silent at runtime — Developer B's node reads `retrieved_context` from state, which is now always absent (None or empty), and the LLM generates a response without retrieval context, producing hallucinated answers with no error
C. The failure surfaces as a type error at the first invocation — the graph framework validates state field types at runtime and raises an exception when a field is absent
D. The failure is caught when the routing function executes — routing functions inspect state for consistency before passing control to the next node

**Correct answer:** B

**Explanation:**
State fields in a graph are typically accessed by name from a dictionary or schema object. If Developer B's node reads `retrieved_context` and that field is no longer written (it is now `retrieval_results`), the read returns None, an empty string, or the default value for that field. No exception is raised — the node receives empty context, constructs a prompt with empty context, and the LLM generates a response as if no retrieval occurred. The failure is a silent quality regression: answers become hallucinated or unsupported, but the pipeline completes without errors. Graph compilation does not validate that every read field is written by some node — it validates structural connectivity (node reachability, edge definitions), not data flow contracts. This is a category of failure that requires explicit data flow testing or schema validation tooling.

**Why A is wrong:** Graph compilation validates structural topology — nodes, edges, routing function signatures. It does not validate that every field read by any node will be written by a preceding node. Data flow validation at compile time would require static analysis of all node implementations, which is not a standard graph compilation feature. A developer who expects the compiler to catch this will be surprised when the graph compiles cleanly and the failure surfaces as silent quality degradation in production.

**Why C is wrong:** Graph frameworks do not perform runtime type validation on individual state field accesses at the framework level. State is passed as a structured object, and reading an absent field returns a default value, not a type error. The LLM node does not raise an exception for receiving an empty context field — it processes whatever it receives. Type errors would require the developer to add explicit validation within the node.

**Why D is wrong:** Routing functions examine specific state fields to make routing decisions. They do not perform a general consistency check of all state fields. A routing function that routes based on answer quality would not notice that `retrieved_context` is absent unless it specifically checked that field. Routing functions are not a general-purpose state validation layer.

---
