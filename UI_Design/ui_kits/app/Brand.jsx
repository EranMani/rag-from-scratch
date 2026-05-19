/* ============================================================
   Brand.jsx — logomark, wordmark, sparkle, icon set.
   ============================================================ */

const BrandMark = ({ size = 32 }) => (
  <span className="brand-mark" style={{ width: size, height: size, fontSize: size * 0.5 }}>R</span>
);

const Wordmark = ({ size = "1.35rem" }) => (
  <span style={{
    fontFamily: 'var(--f-sans)', fontWeight: 700, fontSize: size,
    letterSpacing: '-0.02em',
    backgroundImage: 'var(--g-sunset)',
    WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent',
  }}>
    RAG Tutor
  </span>
);

const BrandLockup = ({ size = 32 }) => (
  <div className="brand-row">
    <BrandMark size={size} />
    <Wordmark />
  </div>
);

const Sparkle = ({ size = 14, color = "#a78bfa" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={color} aria-hidden>
    <path d="M12 2 L13.5 10.5 L22 12 L13.5 13.5 L12 22 L10.5 13.5 L2 12 L10.5 10.5 Z" />
  </svg>
);

const Icon = ({ name, size = 18, color = "currentColor", strokeWidth = 1.6 }) => {
  const paths = {
    send: <><path d="M22 2 L11 13" /><path d="M22 2 l-7 20 -4 -9 -9 -4 z" /></>,
    search: <><circle cx="11" cy="11" r="7" /><path d="M21 21 l-4.3 -4.3" /></>,
    arrow: <><path d="M5 12 h14" /><path d="M13 6 l6 6 -6 6" /></>,
    down: <><path d="M12 5 v14" /><path d="M6 13 l6 6 6 -6" /></>,
    chat: <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />,
    layers: <><path d="M12 2 L2 7 l10 5 10 -5 z" /><path d="M2 17 l10 5 10 -5" /><path d="M2 12 l10 5 10 -5" /></>,
    target: <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="3" /></>,
    check: <path d="M20 6 L9 17 L4 12" />,
    code: <><polyline points="16 18 22 12 16 6" /><polyline points="8 6 2 12 8 18" /></>,
    user: <><circle cx="12" cy="8" r="4" /><path d="M4 21 c0 -4.4 3.6 -8 8 -8 s8 3.6 8 8" /></>,
    settings: <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" /></>,
    plus: <><path d="M12 5 v14" /><path d="M5 12 h14" /></>,
    sparkle: <path d="M12 2 L13.5 10.5 L22 12 L13.5 13.5 L12 22 L10.5 13.5 L2 12 L10.5 10.5 Z" />,
    brain: <><path d="M9 3 a3 3 0 0 0 -3 3 a3 3 0 0 0 -3 3 v3 a3 3 0 0 0 3 3 v3 a3 3 0 0 0 3 3 h0 a3 3 0 0 0 3 -3 V3 a0 0 0 0 0 0 0 z" /><path d="M15 3 a3 3 0 0 1 3 3 a3 3 0 0 1 3 3 v3 a3 3 0 0 1 -3 3 v3 a3 3 0 0 1 -3 3 h0 a3 3 0 0 1 -3 -3 V3 a0 0 0 0 1 0 0 z" /></>,
    stack: <><rect x="3" y="3" width="18" height="6" rx="1.5" /><rect x="3" y="14" width="18" height="6" rx="1.5" /></>,
    "check-circuit": <><path d="M3 12 h4 l2 -2 l2 2 h2" /><path d="M14 14 l2 2 l5 -7" /></>,
  };
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
         stroke={color} strokeWidth={strokeWidth}
         strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      {paths[name] || null}
    </svg>
  );
};

Object.assign(window, { BrandMark, Wordmark, BrandLockup, Sparkle, Icon });
