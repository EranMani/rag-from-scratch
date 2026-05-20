/* ============================================================
   Landing.jsx — hero, problem, features, modules, CTA footer.
   ============================================================ */

const MODULES = [
  { num: "01", title: "RAG Fundamentals",     desc: "The architecture, the intuition, the why.",                 pct: 92 },
  { num: "02", title: "Vector Databases",     desc: "FAISS, Pinecone, Weaviate — and when to use each.",         pct: 71 },
  { num: "03", title: "Retrieval Methods",    desc: "Semantic, keyword, hybrid, re-ranking.",                    pct: 48 },
  { num: "04", title: "Chunking Strategies",  desc: "The decision that breaks more pipelines than any other.",   pct: 32 },
  { num: "05", title: "LangChain",            desc: "Chains, agents, and retrieval pipelines in code.",          pct: 12 },
  { num: "06", title: "Production Patterns",  desc: "Caching, eval, observability, latency tuning.",             pct: 4  },
];

const HeroMock = () => (
  <div className="hero-mock">
    <div className="hero-mock-title">Live · RAG Tutor</div>
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div className="msg-row user" style={{ justifyContent: 'flex-end' }}>
        <div className="bubble user" style={{ fontSize: 12.5, padding: '10px 12px' }}>
          Why does cosine similarity outperform dot product for normalized embeddings?
        </div>
      </div>
      <div className="msg-row">
        <div className="avatar assistant" style={{ width: 26, height: 26, fontSize: 9.5 }}>RT</div>
        <div className="bubble assistant" style={{ fontSize: 12.5, padding: '10px 12px' }}>
          For unit-normalized vectors they're mathematically equivalent — same ranking, different scale.
          Where it matters is when norms <em style={{ color: '#e879f9', fontStyle: 'normal' }}>aren't</em> equal:
          dot product amplifies high-norm chunks. With <code style={{ fontSize: 11 }}>bge-large</code> embeddings
          you'll see a measurable shift on rare-token queries.
        </div>
      </div>
      <div className="kc-card" style={{ padding: '12px 14px', marginTop: 4 }}>
        <div className="kc-label" style={{ fontSize: 10 }}><span className="kc-star">✦</span>Knowledge Check</div>
        <div className="kc-q" style={{ fontSize: 12.5, margin: '8px 0 8px' }}>
          Which embedding model normalizes outputs by default?
        </div>
      </div>
    </div>
  </div>
);

const Marquee = () => {
  const items = ['RAG Fundamentals', 'Vector Databases', 'Retrieval Methods', 'Chunking Strategies', 'LangChain', 'Production Patterns'];
  const row = (
    <span>
      {items.map((t, i) => (
        <React.Fragment key={i}>
          {t}
          <span className="marquee-dot" />
        </React.Fragment>
      ))}
    </span>
  );
  return (
    <div className="marquee">
      <div className="marquee-track">{row}{row}</div>
    </div>
  );
};

const Feature = ({ icon, title, copy }) => (
  <div className="feature">
    <span className="feature-icon">{icon}</span>
    <h3>{title}</h3>
    <p>{copy}</p>
  </div>
);

const Landing = ({ onSignIn, onStart }) => (
  <div className="landing">
    <nav className="landing-nav">
      <BrandLockup />
      <div className="landing-nav-links">
        <a>Features</a>
        <a>How It Works</a>
        <a>Docs</a>
      </div>
      <button className="btn btn-primary" onClick={onStart}>
        Start Learning Free <Icon name="arrow" size={14} />
      </button>
    </nav>

    <section className="hero">
      <div style={{ position: 'absolute', inset: '-40px -32px 0', zIndex: 0 }}>
        <ParticleNetwork density={28} />
      </div>
      <div className="hero-content">
        <div>
          <div className="hero-eyebrow">AI-NATIVE LEARNING SYSTEM</div>
          <h1>Master RAG.<br/>Ship with confidence.</h1>
          <p className="sub">
            RAG Tutor adapts to your level in real time — tracking your gaps,
            building on your strengths, and guiding you from fundamentals to production‑grade systems.
          </p>
          <div className="hero-cta-row">
            <button className="btn btn-primary large" onClick={onStart}>Start for Free <Icon name="arrow" size={15}/></button>
            <button className="btn btn-secondary">See how it works <Icon name="down" size={14}/></button>
          </div>
          <div className="hero-social">No credit card required · Personalizes to your level instantly</div>
        </div>
        <HeroMock />
      </div>
    </section>

    <Marquee />

    <section className="section">
      <div className="problem-grid">
        <div>
          <div className="section-eyebrow">THE PROBLEM</div>
          <h2 className="gradient">RAG is everywhere.<br/>Understanding it deeply is rare.</h2>
          <p>
            Most teams bolt together a LangChain tutorial and call it a RAG pipeline.
            Then they wonder why retrieval quality degrades, why hallucinations creep
            in at the edges, why their re‑ranker makes things worse.
          </p>
          <p>
            The real issues — chunking strategy, embedding model choice, index
            configuration, retrieval scoring, hybrid search, production caching — live
            in the space between the tutorial and the production system.
          </p>
        </div>
        <div className="before-after">
          <div className="ba-card bad">
            <span className="ba-tag">Without</span>
            <ul className="ba-list">
              <li>Hardcoded k=4. No re-rank.</li>
              <li>Fixed-size chunks. Lost context.</li>
              <li>Cosine, no hybrid. Rare tokens miss.</li>
              <li>No eval. Vibes-based shipping.</li>
              <li>Latency unknown. Caches absent.</li>
            </ul>
          </div>
          <div className="ba-card good">
            <span className="ba-tag">With RAG Tutor</span>
            <ul className="ba-list">
              <li>Adaptive k, learned per query class.</li>
              <li>Recursive chunking by doc structure.</li>
              <li>Hybrid BM25 + dense, with reranker.</li>
              <li>Recall@10 in CI. Regression alarms.</li>
              <li>Cache layers tuned to p50 latency.</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section className="section" style={{ paddingTop: 20 }}>
      <div className="section-eyebrow" style={{ textAlign: 'center' }}>HOW IT WORKS</div>
      <h2 style={{ textAlign: 'center', marginBottom: 48 }}>Built different.</h2>
      <div className="features">
        <Feature
          icon={<Icon name="brain" size={22} color="#f97316" strokeWidth={1.6} />}
          title="Knows what you know"
          copy="Every question you ask updates your knowledge profile. RAG Tutor adapts every response to your current mastery level — not a generic difficulty setting."
        />
        <Feature
          icon={<Icon name="layers" size={22} color="#ec4899" strokeWidth={1.6} />}
          title="From zero to production"
          copy="Six modules cover every layer of the RAG stack — fundamentals, vector databases, retrieval methods, chunking, LangChain, and production patterns. In that order, for a reason."
        />
        <Feature
          icon={<Icon name="check-circuit" size={22} color="#a78bfa" strokeWidth={1.6} />}
          title="Learns from your answers"
          copy="After each response, RAG Tutor surfaces a knowledge check. Your answers train its model of you — so the next response is sharper, more targeted, more useful."
        />
      </div>
    </section>

    <section className="section">
      <div className="section-eyebrow">CURRICULUM</div>
      <h2>Six modules. One coherent path.</h2>
      <p style={{ color: 'var(--c-muted)', maxWidth: 520, fontSize: '1rem', marginBottom: 36, lineHeight: 1.6 }}>
        Designed to build on each other — not to be consumed in isolation.
      </p>
      <div className="modules">
        {MODULES.map(m => (
          <div className="module" key={m.num}>
            <div className="module-num">{m.num}</div>
            <div className="module-title">{m.title}</div>
            <div className="module-desc">{m.desc}</div>
            <div className="module-bar"><div className="module-fill" style={{ width: `${m.pct}%` }} /></div>
          </div>
        ))}
      </div>
    </section>

    <section className="cta-footer">
      <div className="section-eyebrow">GET STARTED</div>
      <h2 className="gradient" style={{ fontSize: 'clamp(2.2rem, 4vw, 3.2rem)' }}>Start learning today.</h2>
      <p>Your first session is free. No setup. No configuration. Just ask your first question and watch the system adapt.</p>
      <button className="btn btn-primary large" onClick={onStart}>Get Started <Icon name="arrow" size={15} /></button>
      <div style={{ marginTop: 18, fontFamily: 'var(--f-sans)', fontSize: 13, color: 'var(--c-muted)' }}>
        Already have an account?{' '}
        <a onClick={onSignIn} style={{ color: 'var(--c-fg)', borderBottom: '1px solid rgba(236,72,153,0.4)', paddingBottom: 1, cursor: 'pointer' }}>Sign in →</a>
      </div>
    </section>

    <footer className="site-footer">
      <BrandLockup size={24} />
      <div>© 2026 RAG Tutor · retrieve · augment · generate · master</div>
    </footer>
  </div>
);

window.Landing = Landing;
