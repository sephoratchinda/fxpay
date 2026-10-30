import { useState } from "react";

export const CCYS = ["USD", "EUR", "GBP", "INR", "JPY", "AUD", "CAD", "SGD", "AED", "CNY"];
export const C = { forest: "#1f4d3f", green: "#2f6e5a", red: "#c8442b", amber: "#c98a1b", sand: "#b9ad8e", ink: "#14201c" };
export const fmt = (n, d = 2) => (n === null || n === undefined ? "-" : Number(n).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d }));
export const usd = (n) => "$" + fmt(n, 0);

export const Card = ({ title, children, sub }) => (
  <section className="card">{title && <h2>{title}</h2>}{sub && <p className="note">{sub}</p>}{children}</section>
);
export const Field = ({ label, children }) => <label>{label}{children}</label>;
export const Badge = ({ v, children }) => <span className={`badge b-${v}`}>{children ?? v}</span>;
export const Stat = ({ label, value, children }) => <div className="stat"><span>{label}</span><b>{value}</b>{children}</div>;
export const Err = ({ e }) => (e ? <div className="err">{e}</div> : null);
export const Meter = ({ value, color }) => <div className="meter"><i style={{ width: `${Math.min(value, 100)}%`, background: color }} /></div>;
export const levelColor = (l) => (l === "Low" ? "#2f7d4f" : l === "Medium" ? C.amber : C.red);

export const CcySelect = ({ value, onChange }) => (
  <select value={value} onChange={(e) => onChange(e.target.value)}>{CCYS.map((c) => <option key={c}>{c}</option>)}</select>
);

export function Tabs({ tabs, children }) {
  const [on, setOn] = useState(tabs[0]);
  return (<>
    <div className="tabs">{tabs.map((t) => <button key={t} className={t === on ? "on" : ""} onClick={() => setOn(t)}>{t}</button>)}</div>
    {children(on)}
  </>);
}

/** run an async action with loading + error state */
export function useAction() {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const run = async (fn) => {
    setBusy(true); setErr("");
    try { return await fn(); } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };
  return { busy, err, run };
}
