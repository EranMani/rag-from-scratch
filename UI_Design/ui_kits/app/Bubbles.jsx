/* ============================================================
   Bubbles.jsx — UserBubble, AssistantBubble, ThinkingBubble, Welcome
   ============================================================ */

const UserBubble = ({ children, initials = "YO" }) => (
  <div className="msg-row user">
    <div className="bubble user">
      <span className="bubble-name" style={{ textAlign: 'right' }}>you</span>
      {children}
    </div>
    <div className="avatar user">{initials}</div>
  </div>
);

const AssistantBubble = ({ children }) => (
  <div className="msg-row">
    <div className="avatar assistant">RT</div>
    <div className="bubble assistant">
      <span className="bubble-name">RAG Tutor</span>
      {children}
    </div>
  </div>
);

const ThinkingBubble = () => (
  <div className="msg-row">
    <div className="avatar assistant">RT</div>
    <div className="thinking-bubble">
      <span className="d d1" />
      <span className="d d2" />
      <span className="d d3" />
      <span className="lbl">Retrieving…</span>
    </div>
  </div>
);

const WelcomeCard = ({ sessions }) => (
  <div className="welcome-card">
    <h3>Welcome back.</h3>
    <p>Your profile has <strong style={{ color: 'var(--c-fg)' }}>{sessions}</strong> sessions so far. What would you like to explore today?</p>
  </div>
);

Object.assign(window, { UserBubble, AssistantBubble, ThinkingBubble, WelcomeCard });
