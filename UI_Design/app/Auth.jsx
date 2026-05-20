/* ============================================================
   Auth.jsx — LoginCard (orange top bar) + RegisterCard (violet)
   ============================================================ */

const Field = ({ label, type = "text", placeholder, value, onChange, autoFocus }) => (
  <label className="field">
    <span>{label}</span>
    <input
      type={type} placeholder={placeholder}
      value={value} onChange={onChange} autoFocus={autoFocus}
    />
  </label>
);

const LoginCard = ({ onSubmit, onSwap }) => {
  const [email, setEmail] = React.useState("ada@team.dev");
  const [pwd, setPwd] = React.useState("••••••••");
  return (
    <div className="auth-stage">
      <div className="auth-card login">
        <div className="auth-brand">
          <BrandMark size={48} />
          <div className="word">RAG Tutor</div>
          <div className="auth-tag">Your AI‑powered RAG learning assistant</div>
        </div>
        <div className="auth-sub">Sign in to continue your learning path</div>

        <Field label="Email address" type="email" placeholder="you@team.dev" value={email} onChange={(e) => setEmail(e.target.value)} autoFocus />
        <Field label="Password" type="password" placeholder="••••••••" value={pwd} onChange={(e) => setPwd(e.target.value)} />

        <button className="auth-submit" onClick={(e) => { e.preventDefault(); onSubmit && onSubmit(email); }}>
          Continue →
        </button>

        <div className="auth-swap">
          Don't have an account? <a onClick={onSwap}>Create one →</a>
        </div>
      </div>
    </div>
  );
};

const RegisterCard = ({ onSubmit, onSwap }) => {
  const [email, setEmail] = React.useState("");
  const [pwd, setPwd] = React.useState("");
  const [name, setName] = React.useState("");
  return (
    <div className="auth-stage">
      <div className="auth-card register">
        <div className="auth-brand">
          <BrandMark size={48} />
          <div className="word">RAG Tutor</div>
          <div className="auth-tag">Your AI‑powered RAG learning assistant</div>
        </div>
        <div className="auth-sub">Create your account to start learning</div>

        <Field label="Display name" placeholder="Ada Lovelace" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
        <Field label="Email address" type="email" placeholder="you@team.dev" value={email} onChange={(e) => setEmail(e.target.value)} />
        <Field label="Password" type="password" placeholder="At least 8 characters" value={pwd} onChange={(e) => setPwd(e.target.value)} />

        <button className="auth-submit" onClick={(e) => { e.preventDefault(); onSubmit && onSubmit(email || "you@team.dev"); }}>
          Create account →
        </button>

        <div className="auth-swap">
          Already learning? <a onClick={onSwap}>Sign in →</a>
        </div>
      </div>
    </div>
  );
};

Object.assign(window, { LoginCard, RegisterCard, Field });
