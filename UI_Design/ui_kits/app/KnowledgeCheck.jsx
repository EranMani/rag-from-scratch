/* ============================================================
   KnowledgeCheck.jsx — violet ambient quiz card.
   ============================================================ */

const KnowledgeCheck = ({ question, choices, onAnswer }) => {
  const [picked, setPicked] = React.useState(null);
  return (
    <div className="kc-card">
      <div className="kc-label"><span className="kc-star">✦</span>Knowledge Check</div>
      <div className="kc-q">{question}</div>
      <div className="kc-choices">
        {choices.map((c, i) => {
          const key = String.fromCharCode(65 + i);
          const isPicked = picked === i;
          return (
            <button
              key={i} className="kc-choice"
              style={isPicked ? {
                borderColor: 'rgba(236,72,153,0.6)',
                background: 'rgba(236,72,153,0.10)',
                boxShadow: '0 0 0 3px rgba(236,72,153,0.16)',
              } : null}
              onClick={() => { setPicked(i); onAnswer && onAnswer(i); }}
            >
              <span className="kc-key">{key}</span>{c}
            </button>
          );
        })}
      </div>
    </div>
  );
};

window.KnowledgeCheck = KnowledgeCheck;
