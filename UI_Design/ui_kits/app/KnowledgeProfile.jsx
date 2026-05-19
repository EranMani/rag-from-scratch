/* ============================================================
   KnowledgeProfile.jsx — sidebar contents.
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

const ModuleRow = ({ num, name, score }) => (
  <div className="mod-row">
    <div className="mod-head">
      <span className="mod-name">{num} · {name}</span>
      <span className="mod-score">{score.toFixed(2)}</span>
    </div>
    <div className="mod-track">
      <div className="mod-fill" style={{ width: `${Math.round(score * 100)}%` }} />
    </div>
  </div>
);

const KnowledgeProfile = ({ level = "advanced", scores, queries = 47, lastActive = "today" }) => (
  <aside className="sidebar">
    <div className="sb-section">
      <h4>Your Profile</h4>
      <div className="sb-mastery">
        <MasteryChip level={level} />
        <div className="sb-tagline">{MASTERY_COPY[level]}</div>
      </div>
    </div>

    <div className="sb-section">
      <h4>Module Progress</h4>
      <div>
        {scores.map(s => (
          <ModuleRow key={s.num} num={s.num} name={s.name} score={s.score} />
        ))}
      </div>
    </div>

    <div className="sb-stats">
      <div className="sb-stat"><span>questions asked</span><b>{queries}</b></div>
      <div className="sb-stat"><span>last session</span><b>{lastActive}</b></div>
      <div className="sb-stat"><span>build</span><b>v0.4.2</b></div>
    </div>
  </aside>
);

Object.assign(window, { KnowledgeProfile, MasteryChip, ModuleRow });
