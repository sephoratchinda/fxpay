import { useEffect, useState } from "react";
import { api, login, register, tokens } from "./api.js";
import { Err, Field, useAction } from "./ui.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Payments from "./pages/Payments.jsx";
import FxRisk from "./pages/FxRisk.jsx";
import Optimizer from "./pages/Optimizer.jsx";
import AI from "./pages/AI.jsx";

const PAGES = [
  ["Risk Dashboard", Dashboard], ["International Payments", Payments], ["FX Risk Calculator", FxRisk],
  ["Cost Optimizer", Optimizer], ["AI Recommendations", AI],
];

function Login({ onDone }) {
  const [mode, setMode] = useState("login");
  const [f, setF] = useState({ username: "", email: "", password: "" });
  const [show, setShow] = useState(false);
  const { busy, err, run } = useAction();
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const submit = (e) => {
    e.preventDefault();
    run(async () => { mode === "login" ? await login(f.username, f.password) : await register(f.username, f.email, f.password); onDone(); });
  };
  return (
    <div className="login">
      <h1>FXPay</h1>
      <p className="sub">
        Smart cross-border payments &amp; foreign exchange risk management.
      </p>
      <form className="card" onSubmit={submit}>
        <h2>{mode === "login" ? "Sign in" : "Create account"}</h2>
        <Field label="Username">
          <input value={f.username} onChange={set("username")} required />
        </Field>
        {mode === "register" && (
          <Field label="Email">
            <input type="email" value={f.email} onChange={set("email")} />
          </Field>
        )}
        <Field label="Password (min 8 characters)">
          <div className="pw">
            <input
              type={show ? "text" : "password"}
              value={f.password}
              onChange={set("password")}
              required
            />
            <button
              type="button"
              className="eye"
              onClick={() => setShow(!show)}
              aria-label={show ? "Hide password" : "Show password"}
            >
              {show ? (
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                  <line x1="1" y1="1" x2="23" y2="23" />
                </svg>
              ) : (
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              )}
            </button>
          </div>
        </Field>
        <Err e={err} />
        <button className="btn" disabled={busy}>
          {mode === "login" ? "Sign in" : "Register"}
        </button>
        <button
          type="button"
          className="btn alt"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
        >
          {mode === "login" ? "New here? Register" : "Have an account? Sign in"}
        </button>
      </form>
    </div>
  );
}

export default function App() {
  const [authed, setAuthed] = useState(!!tokens.get());
  const [page, setPage] = useState(0);
  const [user, setUser] = useState(null);
  useEffect(() => { if (authed) api.get("/auth/me/").then(setUser).catch(() => {}); }, [authed]);
  if (!authed) return <Login onDone={() => setAuthed(true)} />;
  const Page = PAGES[page][1];
  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">FXPay<small>Cross-border payments &amp; FX risk</small></div>
        {PAGES.map(([name], i) => <button key={name} className={`nav ${i === page ? "on" : ""}`} onClick={() => setPage(i)}>{name}</button>)}
        <div className="who">{user?.username}<br /><a href="#" style={{ color: "inherit" }} onClick={() => { tokens.clear(); setAuthed(false); }}>Sign out</a></div>
      </aside>
      <main><Page /></main>
    </div>
  );
}
