import { useEffect, useState } from "react";
import { api } from "../api.js";
import { Badge, Card, CcySelect, Err, Field, fmt, useAction } from "../ui.jsx";

export default function Payments() {
  const [meta, setMeta] = useState(null);
  const [f, setF] = useState({ channel: "swift", amount: 5000, from_ccy: "USD", to_ccy: "EUR", recipient_name: "" });
  const [sim, setSim] = useState(null);
  const [txs, setTxs] = useState([]);
  const { busy, err, run } = useAction();
  const load = () => api.get("/payments/").then(setTxs).catch(() => {});
  useEffect(() => { api.get("/meta/").then(setMeta); load(); }, []);
  const body = () => ({ ...f, amount: Number(f.amount) });
  const set = (k) => (v) => setF({ ...f, [k]: v?.target ? v.target.value : v });
  const desc = meta?.channels.find((c) => c.key === f.channel)?.description;
  const q = sim?.quote;
  return (<>
    <h1>International Payments</h1>
    <p className="sub">Simulate SWIFT, wire, card and wallet transfers. See the processing workflow, fees, FX margin and expected settlement time before you send.</p>
    <div className="grid g2">
      <Card title="New payment">
        <Field label="Payment channel"><select value={f.channel} onChange={set("channel")}>{meta?.channels.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}</select></Field>
        <p className="note">{desc}</p>
        <div className="row">
          <Field label="Amount"><input type="number" min="0" value={f.amount} onChange={set("amount")} /></Field>
          <Field label="From"><CcySelect value={f.from_ccy} onChange={set("from_ccy")} /></Field>
          <Field label="To"><CcySelect value={f.to_ccy} onChange={set("to_ccy")} /></Field>
        </div>
        <Field label="Recipient name"><input value={f.recipient_name} onChange={set("recipient_name")} /></Field>
        <Err e={err} />
        <button className="btn alt" disabled={busy} onClick={() => run(async () => setSim(await api.post("/payments/simulate/", body())))}>Simulate</button>
        <button className="btn" disabled={busy} onClick={() => run(async () => { const t = await api.post("/payments/", body()); setSim(await api.post("/payments/simulate/", body())); load(); })}>Send payment</button>
      </Card>
      {q && <Card title="Quote &amp; workflow">
        <table><tbody>
          <tr><td>Mid-market rate</td><td className="n">{q.mid_rate}</td></tr>
          <tr><td>Rate applied (after {q.fx_markup_pct}% margin)</td><td className="n">{q.applied_rate}</td></tr>
          <tr><td>Transfer fees</td><td className="n">{f.from_ccy} {fmt(q.fee_total)}</td></tr>
          <tr><td>Hidden FX margin cost</td><td className="n">{f.from_ccy} {fmt(q.fx_markup_cost)}</td></tr>
          <tr><td><b>Total cost</b> ({q.cost_pct}%)</td><td className="n"><b>{f.from_ccy} {fmt(q.total_cost)}</b></td></tr>
          <tr><td><b>Recipient receives</b></td><td className="n"><b>{f.to_ccy} {fmt(q.recipient_gets)}</b></td></tr>
          <tr><td>Expected settlement</td><td className="n">{q.expected_days} days ({q.days_min}-{q.days_max})</td></tr>
        </tbody></table>
        {sim.warnings.map((w) => <div className="warn" key={w}>{w}</div>)}
        <h3 style={{ marginTop: 16 }}>Processing steps</h3>
        <ol className="timeline">{sim.steps.map((s) => <li key={s.step}>{s.name} <small>+{s.eta_hours}h</small></li>)}</ol>
      </Card>}
    </div>
    <Card title="My transactions">
      <table>
        <thead><tr><th>#</th><th>Channel</th><th>Corridor</th><th className="n">Amount</th><th className="n">Cost</th><th className="n">Received</th><th>Risk</th><th>Status</th><th /></tr></thead>
        <tbody>{txs.map((t) => (
          <tr key={t.id}><td>{t.id}</td><td>{t.channel}</td><td>{t.from_ccy}→{t.to_ccy}</td><td className="n">{fmt(t.amount)}</td>
            <td className="n">{fmt(Number(t.fee_total) + Number(t.fx_cost))}</td><td className="n">{fmt(t.received_amount)}</td>
            <td><Badge v={t.risk_level} /></td><td><Badge v={t.status} /></td>
            <td>{t.status !== "COMPLETED" && <button className="btn sm" onClick={() => api.post(`/payments/${t.id}/advance/`).then(load)}>Advance</button>}</td></tr>
        ))}</tbody>
      </table>
      {!txs.length && <p className="note">No transactions yet. Send one above, or load sample data from the Risk Dashboard.</p>}
    </Card>
  </>);
}
