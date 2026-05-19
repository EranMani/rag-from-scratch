/* ============================================================
   Composer.jsx — input bar with high-glow send button.
   ============================================================ */

const Composer = ({ onSend, disabled }) => {
  const [value, setValue] = React.useState("");
  const [focused, setFocused] = React.useState(false);
  const taRef = React.useRef(null);

  const submit = () => {
    const v = value.trim();
    if (!v || disabled) return;
    onSend && onSend(v);
    setValue("");
    if (taRef.current) taRef.current.style.height = 'auto';
  };

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
  };

  const autosize = (e) => {
    setValue(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 140) + 'px';
  };

  return (
    <div className="composer">
      <div className={"composer-inner" + (focused ? " focused" : "")}>
        <textarea
          ref={taRef}
          className="composer-input" rows="1"
          placeholder="Ask anything about RAG, embeddings, retrieval, LangChain…"
          value={value}
          onChange={autosize}
          onKeyDown={onKey}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
        />
        <button className="composer-send" onClick={submit} disabled={!value.trim() || disabled} title="Send (Enter)" aria-label="Send">
          <Icon name="send" size={16} color="#fff" strokeWidth={2} />
        </button>
      </div>
      <div className="composer-hint">Enter to send · Shift+Enter for newline</div>
    </div>
  );
};

window.Composer = Composer;
