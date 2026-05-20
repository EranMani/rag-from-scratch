/* ============================================================
   KnowledgeProfile.jsx — sidebar contents.
   Tabbed: "Current" (active module + topics) and "Overview" (all modules).
   ============================================================ */

const MASTERY_COPY = {
  novice:       "Just getting started — great time to build foundations.",
  intermediate: "You've got the core. Time to go deeper.",
  advanced:     "Strong foundations. Let's tackle production complexity.",
  expert:       "You're in the top tier. Ask me anything.",
};

const MasteryChip = ({ level }) => (
  <span className={`mastery-chip mc-${level}`}>
    <span className="dot" />
    {level.charAt(0).toUpperCase() + level.slice(1)}
  </span>
);

/* -- Tab bar (underline indicator, sunset gradient) -- */
const SidebarTabs = ({ value, onChange, tabs }) => (
  <div className="sb-tabs" role="tablist">
    {tabs.map(t => (
      <button
        key={t}
        role="tab"
        aria-selected={value === t}
        className={"sb-tab" + (value === t ? " active" : "")}
        onClick={() => onChange(t)}
      >
        {t}
      </button>
    ))}
  </div>
);

/* -- Inline check / pending dot SVG icons -- */
const CheckIcon = () => (
  <svg className="topic-icon done" viewBox="0 0 16 16" aria-hidden>
    <circle cx="8" cy="8" r="7" fill="url(#tg)" />
    <defs>
      <linearGradient id="tg" x1="0" x2="1" y1="0" y2="1">
        <stop offset="0" stopColor="#f97316" />
        <stop offset="0.5" stopColor="#ec4899" />
        <stop offset="1" stopColor="#8b5cf6" />
      </linearGradient>
    </defs>
    <path d="M4.5 8.2 L7 10.6 L11.5 5.8" fill="none" stroke="#fff" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
const PendingIcon = () => (
  <svg className="topic-icon pending" viewBox="0 0 16 16" aria-hidden>
    <circle cx="8" cy="8" r="6.5" fill="none" stroke="currentColor" strokeWidth="1.2" />
    <circle cx="8" cy="8" r="2" fill="currentColor" />
  </svg>
);

/* -- Topic row inside Current tab -- */
const TopicRow = ({ name, done }) => (
  <li className={"topic-row" + (done ? " done" : "")}>
    {done ? <CheckIcon /> : <PendingIcon />}
    <span className="topic-name">{name}</span>
  </li>
);

/* -- Compact module row inside Overview tab -- */
const OverviewRow = ({ num, name, done, total, locked }) => {
  const pct = total === 0 ? 0 : (done / total) * 100;
  return (
    <div className={"ov-row" + (locked ? " locked" : "")}>
      <div className="ov-row-head">
        <span className="ov-num">{num}</span>
        <span className="ov-name">{name}</span>
        <span className="ov-frac">{locked ? "—" : `${done}/${total}`}</span>
      </div>
      {!locked && (
        <div className="ov-track">
          <div className="ov-fill" style={{ width: `${pct}%` }} />
        </div>
      )}
    </div>
  );
};

/* -- Tab views -- */

const CurrentView = ({ module }) => {
  const done = module.topics.filter(t => t.done).length;
  const total = module.topics.length;
  const pct = (done / total) * 100;
  return (
    <div className="sb-section">
      <div className="cur-head">
        <span className="cur-eyebrow">Active module · {module.num}</span>
        <h3 className="cur-title">{module.name}</h3>
      </div>

      <div className="cur-progress">
        <div className="cur-track">
          <div className="cur-fill" style={{ width: `${pct}%` }} />
        </div>
        <span className="cur-frac">{done} / {total}</span>
      </div>

      <ul className="topic-list">
        {module.topics.map((t, i) => (
          <TopicRow key={i} name={t.name} done={t.done} />
        ))}
      </ul>
    </div>
  );
};

const OverviewView = ({ modules }) => {
  const completed = modules.filter(m => !m.locked && m.topics.every(t => t.done)).length;
  const total = modules.length;
  const pct = (completed / total) * 100;
  return (
    <div className="sb-section">
      <div className="ov-summary">
        <div className="ov-summary-head">
          <span className="ov-summary-label">Overall progress</span>
          <span className="ov-summary-frac">{completed} / {total} modules</span>
        </div>
        <div className="ov-summary-track">
          <div className="ov-summary-fill" style={{ width: `${pct}%` }} />
        </div>
      </div>

      <div className="ov-list">
        {modules.map(m => {
          const d = m.topics.filter(t => t.done).length;
          return (
            <OverviewRow
              key={m.num}
              num={m.num}
              name={m.name}
              done={d}
              total={m.topics.length}
              locked={m.locked}
            />
          );
        })}
      </div>
    </div>
  );
};

/* -- Sidebar -- */

const KnowledgeProfile = ({
  level = "advanced",
  modules,
  activeModuleNum,
  queries = 47,
  lastActive = "today",
}) => {
  const [tab, setTab] = React.useState("Current");
  const active =
    modules.find(m => m.num === activeModuleNum) ||
    modules.find(m => !m.topics.every(t => t.done) && !m.locked) ||
    modules[0];

  return (
    <aside className="sidebar">
      {/* Mastery badge — top */}
      <div className="sb-section sb-mastery-section">
        <MasteryChip level={level} />
        <div className="sb-tagline">{MASTERY_COPY[level]}</div>
      </div>

      {/* Tab bar */}
      <SidebarTabs value={tab} onChange={setTab} tabs={["Current", "Overview"]} />

      {/* Tab content */}
      <div className="sb-tab-panel">
        {tab === "Current"  && <CurrentView module={active} />}
        {tab === "Overview" && <OverviewView modules={modules} />}
      </div>

      {/* Footer */}
      <div className="sb-stats">
        <div className="sb-stat"><span>questions asked</span><b>{queries}</b></div>
        <div className="sb-stat"><span>last session</span><b>{lastActive}</b></div>
      </div>
    </aside>
  );
};

Object.assign(window, {
  KnowledgeProfile, MasteryChip,
  SidebarTabs, CurrentView, OverviewView,
  TopicRow, OverviewRow,
});
