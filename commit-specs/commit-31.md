# Commit 31 Spec — `ui-auth-pages`
> **Project:** rag-from-scratch · **Assignee:** Aria · **Load only for the active commit.**

---

### Commit 31 — `ui-auth-pages`

**Commit message:** `feat: refine login and register pages to match Auth.jsx spec (EranMani)`

**Body:**
Updates copy, layout, and CSS in `login_page()` and `register_page()` to match the
`Auth.jsx` UI kit design. All Python handlers are preserved exactly.

**Requested by EranMani.**

---

### Reference files (read all before writing any code)

- `UI_Design/ui_kits/app/Auth.jsx` — LoginCard and RegisterCard layout
- `UI_Design/colors_and_type.css` — all design tokens
- `UI_Design/reference/design-spec.md` §3.2 and §3.3 — exact copy changes
- `UI_Design/screenshots/02-screen.png` — visual target

---

### Login page (`login_page()`) — changes only

**Copy changes:**
- Sub-label: `"Sign in to continue your learning path"` ← was `"Sign in to your account"`
- Email field label: `"Email address"` ← was `"Username or Email"`
- Button: `"Continue →"` ← was `"Login"`
- Register link text: `"Don't have an account? Create one →"` ← was `"Create a new account"`

**Layout / CSS changes:**
- Card: add `auth-brand` section matching Auth.jsx — BrandMark SVG (48px) + "RAG Tutor" wordmark + tagline `"Your AI-powered RAG learning assistant"` vertically centered below logo
- Input fields: add field label as a visible `<span>` above the input (matching Auth.jsx `Field` component pattern); currently labels are placeholder-only
- Button: orange-top-bar card accent `border-top: 3px solid #f97316` — keep existing
- Add `auth-tag` class tagline: small, `--c-muted`, centered

**What must NOT change:**
- `do_login()` async function — not a single line
- `app.storage.user` writes
- `ui.navigate.to("/")` after successful login
- `verify_stored_bearer()` guard at top of function

---

### Register page (`register_page()`) — changes only

**Copy changes:**
- Sub-label: `"Create your account to start learning"` ← was `"Create your account"`
- Button: `"Create account →"` (add arrow) ← was `"Create account"`
- Login link: `"Already learning? Sign in →"` ← was `"Already have an account? Sign in"`
- Success heading: `"You're all set."` ← was `"You're signed in"`
- Success body: `"Your profile is ready. Start with your first question →"` ← was `"Your account is ready. Continue to the chat when you like."`

**Layout / CSS changes:**
- Card: violet-top-bar accent `border-top: 3px solid #8b5cf6` — keep existing
- Match field label visibility pattern from login page (above-input labels)
- Success state button: `"Go to chat →"` (add arrow) ← was `"Go to chat"`

**Field order in register form (match Auth.jsx RegisterCard):**
1. Display name
2. Email address
3. Password

Currently the order is email / password / display_name — swap to match spec.

**What must NOT change:**
- `do_register()` async function — not a single line
- `show_success()` function structure (clear + rebuild wrapper)
- `app.storage.user` writes
- `fetch_profile_email()` call
- `verify_stored_bearer()` guard at top of function

---

### CSS rules

- Extend existing `.rag-login-input` styles — do not replace them
- Add `.auth-brand`, `.auth-tag`, `.auth-sub`, `.auth-submit`, `.auth-swap` classes
  matching Auth.jsx CSS patterns
- Orange focus ring for login (`rgba(249,115,22,*)`), violet for register (`rgba(139,92,246,*)`)
  — this distinction already exists in the codebase; keep it

---

### Files touched

- `src/app/ui.py` — `login_page()` and `register_page()` functions only

---

### Testing — done when

- [ ] Login page renders with `"Sign in to continue your learning path"` sub-label
- [ ] Email field shows label `"Email address"` above the input
- [ ] Login button reads `"Continue →"`
- [ ] Register link reads `"Don't have an account? Create one →"`
- [ ] Register page renders with `"Create your account to start learning"` sub-label
- [ ] Field order is: Display name → Email → Password
- [ ] Register button reads `"Create account →"`
- [ ] Login link reads `"Already learning? Sign in →"`
- [ ] Success state shows `"You're all set."` heading
- [ ] Successful login navigates to `/` (logic unchanged)
- [ ] Successful register shows success state then navigates to `/` (logic unchanged)
- [ ] Both pages retain their respective colored top border (orange login, violet register)
