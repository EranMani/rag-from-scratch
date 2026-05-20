/* ============================================================
   ChatShell.jsx — header + sidebar + chat column + composer.
   ============================================================ */

const DEFAULT_MODULES = [
  {
    num: "01", name: "RAG Fundamentals",
    topics: [
      { name: "What RAG is and isn't", done: true },
      { name: "Retrieval vs. fine-tuning", done: true },
      { name: "End-to-end pipeline shape", done: true },
      { name: "When RAG fails", done: true },
    ],
  },
  {
    num: "02", name: "Vector Databases",
    topics: [
      { name: "Embedding spaces", done: true },
      { name: "ANN indexes (HNSW, IVF)", done: true },
      { name: "Quantization tradeoffs", done: false },
      { name: "Hybrid search filters", done: false },
      { name: "Picking a vector store", done: false },
    ],
  },
  {
    num: "03", name: "Retrieval Methods",
    topics: [
      { name: "Dense retrieval", done: false },
      { name: "Sparse retrieval (BM25)", done: false },
      { name: "Reranking with cross-encoders", done: false },
      { name: "Query expansion", done: false },
    ],
  },
  {
    num: "04", name: "Chunking Strategies",
    locked: true,
    topics: [
      { name: "Fixed vs. semantic chunks", done: false },
      { name: "Overlap and context windows", done: false },
      { name: "Structured document parsing", done: false },
    ],
  },
  {
    num: "05", name: "LangChain",
    locked: true,
    topics: [
      { name: "Runnable interface", done: false },
      { name: "Retrievers and chains", done: false },
      { name: "Streaming and tracing", done: false },
    ],
  },
  {
    num: "06", name: "Production Patterns",
    locked: true,
    topics: [
      { name: "Eval harnesses", done: false },
      { name: "Latency budgets", done: false },
      { name: "Caching and cost control", done: false },
      { name: "Monitoring drift", done: false },
    ],
  },
];

const SAMPLE_REPLIES = [
  {
    body: (
      <>
        Short queries lack the lexical surface area that cross‑encoder rerankers
        rely on. Two practical adjustments:
        <ol style={{ paddingLeft: 18, margin: '10px 0' }}>
          <li>Skip rerank when <code>len(tokens) &lt; 6</code> — fall back to the dense scorer.</li>
          <li>Lower retrieval <code>k</code> from <code>20</code> to <code>8</code> for terse queries; rerank precision degrades faster than recall.</li>
        </ol>
        On <code>ms‑marco</code>‑tuned rerankers you'll see ~12% recall@10 recovery on single‑token queries.
      </>
    ),
    check: {
      question: "Which retrieval setting is most sensitive to short queries?",
      choices: ["Embedding dimension", "Top‑k cutoff", "Index quantization level", "Distance metric"],
    },
  },
];

const ChatShell = ({ email, onSignOut }) => {
  const [tab, setTab] = React.useState("Learn");
  const [messages, setMessages] = React.useState([
    { kind: "welcome", sessions: 12 },
  ]);
  const [thinking, setThinking] = React.useState(false);
  const scrollRef = React.useRef(null);

  React.useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, thinking]);

  const send = (text) => {
    setMessages(m => [...m, { kind: "user", text }]);
    setThinking(true);
    setTimeout(() => {
      setThinking(false);
      const reply = SAMPLE_REPLIES[0];
      setMessages(m => [...m,
        { kind: "assistant", body: reply.body },
        { kind: "check", q: reply.check.question, choices: reply.check.choices },
      ]);
    }, 1400);
  };

  const initials = (email || "you").split("@")[0].slice(0, 2).toUpperCase();

  return (
    <div className="chat-stage">
      <header className="chat-header">
        <div className="chat-header-left">
          <BrandLockup size={28} />
          <div className="chat-tabs">
            {["Learn", "System"].map(t => (
              <button key={t} className={"chat-tab" + (tab === t ? " active" : "")} onClick={() => setTab(t)}>
                {t}
              </button>
            ))}
          </div>
        </div>
        <div className="chat-header-right">
          <span className="user-pill">
            <span className="user-pill-av">{initials}</span>
            {email || "ada@team.dev"}
          </span>
          <button className="btn btn-ghost" onClick={onSignOut}>Sign out</button>
        </div>
      </header>

      <div className="chat-body">
        <KnowledgeProfile
          level="advanced"
          modules={DEFAULT_MODULES}
          activeModuleNum="02"
          queries={47}
          lastActive="2h ago"
        />

        <div className="chat-column">
          <div className="chat-scroll" ref={scrollRef}>
            <div className="chat-inner">
              {messages.map((m, i) => {
                if (m.kind === "welcome")   return <WelcomeCard key={i} sessions={m.sessions} />;
                if (m.kind === "user")      return <UserBubble  key={i} initials={initials}>{m.text}</UserBubble>;
                if (m.kind === "assistant") return <AssistantBubble key={i}>{m.body}</AssistantBubble>;
                if (m.kind === "check")     return <KnowledgeCheck key={i} question={m.q} choices={m.choices} />;
                return null;
              })}
              {thinking && <ThinkingBubble />}
            </div>
          </div>
          <Composer onSend={send} disabled={thinking} />
        </div>
      </div>
    </div>
  );
};

window.ChatShell = ChatShell;
