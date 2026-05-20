/* ============================================================
   App.jsx — prototype shell. Routes between landing → auth → chat.
   ============================================================ */

const App = () => {
  const [screen, setScreen] = React.useState("chat"); // "landing" | "login" | "register" | "chat"
  const [email, setEmail] = React.useState("ada@team.dev");

  // Sync screen with hash for share / refresh
  React.useEffect(() => {
    const fromHash = () => {
      const h = (window.location.hash || "").replace("#", "");
      if (["landing", "login", "register", "chat"].includes(h)) setScreen(h);
    };
    fromHash();
    window.addEventListener("hashchange", fromHash);
    return () => window.removeEventListener("hashchange", fromHash);
  }, []);

  const go = (s) => { setScreen(s); window.location.hash = s; };

  return (
    <div className="kit-bg">
      <nav className="kit-nav-strip" aria-label="Prototype screens">
        <button className={screen === "landing"  ? "active" : ""} onClick={() => go("landing")}>Landing</button>
        <button className={screen === "login"    ? "active" : ""} onClick={() => go("login")}>Login</button>
        <button className={screen === "register" ? "active" : ""} onClick={() => go("register")}>Register</button>
        <button className={screen === "chat"     ? "active" : ""} onClick={() => go("chat")}>Chat</button>
      </nav>

      {screen === "landing" && (
        <Landing onSignIn={() => go("login")} onStart={() => go("register")} />
      )}
      {screen === "login" && (
        <LoginCard
          onSubmit={(e) => { setEmail(e); go("chat"); }}
          onSwap={() => go("register")}
        />
      )}
      {screen === "register" && (
        <RegisterCard
          onSubmit={(e) => { setEmail(e); go("chat"); }}
          onSwap={() => go("login")}
        />
      )}
      {screen === "chat" && (
        <ChatShell email={email} onSignOut={() => go("landing")} />
      )}
    </div>
  );
};

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
