import { useEffect, useState } from "react";
import { Area, Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import { Badge, C, Card, CcySelect, Err, Field, Meter, Stat, Tabs, fmt, levelColor, usd, useAction } from "../ui.jsx";

const useForm = (init) => { const [f, setF] = useState(init); return [f, (k) => (v) => setF({ ...f, [k]: v?.target ? v.target.value : v })]; };

function Scenarios() {
  const [f, set] = useForm({ base: "EUR", quote: "USD", days: 90 });
  const [r, setR] = useState(null);
  const { busy, err, run } = useAction();
  return (<>
    <Card title="Exchange-rate fluctuation simulator" sub="Monte-Carlo (geometric Brownian motion, 500 paths). Shaded band = 5th-95th percentile.">
      <div className="row">
        <Field label="Base"><CcySelect value={f.base} onChange={set("base")} /></Field>
        <Field label="Quote"><CcySelect value={f.quote} onChange={set("quote")} /></Field>
        <Field label="Horizon (days)"><input type="number" value={f.days} onChange={set("days")} /></Field>
      </div>
      <Err e={err} /><button className="btn" disabled={busy} onClick={() => run(async () => setR(await api.post("/fx/scenarios/", { ...f, days: Number(f.days) })))}>Simulate</button>
    </Card>
    {r && <div className="grid g2">
      <Card title={`${r.base}/${r.quote} projected range`}>
        <p className="note">Spot {r.spot} · annual volatility {r.annual_vol_pct}% · 5% worst case {r.terminal.worst_5pct} · 95% best case {r.terminal.best_95pct}</p>
        <ResponsiveContainer width="100%" height={280}><ComposedChart data={r.fan.map((d) => ({ ...d, band: [d.p5, d.p95] }))}>
          <CartesianGrid strokeDasharray="3 3" stroke="#d9d3c4" /><XAxis dataKey="day" /><YAxis domain={["auto", "auto"]} /><Tooltip />
          <Area dataKey="band" name="5-95%" fill={C.sand} stroke="none" fillOpacity={0.5} /><Line dataKey="p50" name="Median" stroke={C.forest} dot={false} strokeWidth={2} />
        </ComposedChart></ResponsiveContainer>
      </Card>
      <Card title="Instant shocks"><table><thead><tr><th>Shock</th><th className="n">Resulting rate</th></tr></thead>
        <tbody>{r.shocks.map((s) => <tr key={s.shock_pct}><td>{s.shock_pct > 0 ? "+" : ""}{s.shock_pct}%</td><td className="n">{s.rate}</td></tr>)}</tbody></table></Card>
    </div>}
  </>);
}

function Pnl() {
  const [f, set] = useForm({ amount: 100000, booked_rate: 1.08, new_rate: 1.12, direction: "RECEIVABLE" });
  const [r, setR] = useState(null);
  const { busy, err, run } = useAction();
  return (<div className="grid g2">
    <Card title="Currency movement profit / loss" sub="Rates are home-currency per 1 unit of foreign currency (e.g. USD per EUR).">
      <div className="row">
        <Field label="Foreign amount"><input type="number" value={f.amount} onChange={set("amount")} /></Field>
        <Field label="Booked rate"><input type="number" step="0.0001" value={f.booked_rate} onChange={set("booked_rate")} /></Field>
        <Field label="New rate"><input type="number" step="0.0001" value={f.new_rate} onChange={set("new_rate")} /></Field>
        <Field label="Position"><select value={f.direction} onChange={set("direction")}><option value="RECEIVABLE">Receivable (you receive FX)</option><option value="PAYABLE">Payable (you pay FX)</option></select></Field>
      </div>
      <Err e={err} /><button className="btn" disabled={busy} onClick={() => run(async () => setR(await api.post("/fx/pnl/", { ...f, amount: Number(f.amount), booked_rate: Number(f.booked_rate), new_rate: Number(f.new_rate) })))}>Calculate</button>
    </Card>
    {r && <Card title="Result"><div className="big" style={{ color: r.pnl >= 0 ? "#2f7d4f" : C.red }}>{r.pnl >= 0 ? "+" : ""}{fmt(r.pnl)}</div>
      <p><Badge v={r.outcome} /> {r.pct}% of booked value</p><p className="note">Booked value {fmt(r.booked_value)} → now {fmt(r.new_value)}</p></Card>}
  </div>);
}

function Exposure() {
  const [list, setList] = useState([]);
  const [sum, setSum] = useState(null);
  const [f, set] = useForm({ currency: "EUR", amount: 100000, direction: "RECEIVABLE", due_days: 60, description: "" });
  const { err, run } = useAction();
  const load = () => { api.get("/fx/exposures/").then(setList); api.get("/fx/exposure-summary/").then(setSum); };
  useEffect(load, []);
  return (<>
    <Card title="Currency exposure calculator" sub="Add receivables and payables; exposure is netted per currency and converted to USD. VaR = 95% / 30-day.">
      <div className="row">
        <Field label="Currency"><CcySelect value={f.currency} onChange={set("currency")} /></Field>
        <Field label="Amount"><input type="number" value={f.amount} onChange={set("amount")} /></Field>
        <Field label="Type"><select value={f.direction} onChange={set("direction")}><option value="RECEIVABLE">Receivable</option><option value="PAYABLE">Payable</option></select></Field>
        <Field label="Due in (days)"><input type="number" value={f.due_days} onChange={set("due_days")} /></Field>
      </div>
      <Err e={err} /><button className="btn" onClick={() => run(async () => { await api.post("/fx/exposures/", { ...f, amount: Number(f.amount), due_days: Number(f.due_days) }); load(); })}>Add position</button>
    </Card>
    {sum && <div className="grid g2">
      <Card title="Net exposure by currency (USD)">
        <ResponsiveContainer width="100%" height={240}><BarChart data={sum.by_currency}><CartesianGrid strokeDasharray="3 3" stroke="#d9d3c4" /><XAxis dataKey="currency" /><YAxis /><Tooltip /><Legend />
          <Bar dataKey="receivable_usd" name="Receivable" fill={C.green} /><Bar dataKey="payable_usd" name="Payable" fill={C.red} /></BarChart></ResponsiveContainer>
      </Card>
      <Card title="Portfolio risk">
        <div className="row"><Stat label="Gross exposure" value={usd(sum.gross_exposure_usd)} /><Stat label="Net exposure" value={usd(sum.net_exposure_usd)} /><Stat label="95% VaR (30d)" value={usd(sum.portfolio_var95_usd)} /></div>
        <p style={{ marginTop: 14 }}>FX risk score <b>{sum.fx_risk_score}</b> / 100 <Badge v={sum.level} /></p><Meter value={sum.fx_risk_score} color={levelColor(sum.level)} />
      </Card>
    </div>}
    <Card title="Positions"><table><thead><tr><th>Currency</th><th>Type</th><th className="n">Amount</th><th className="n">Due (d)</th><th /></tr></thead>
      <tbody>{list.map((p) => <tr key={p.id}><td>{p.currency}</td><td>{p.direction}</td><td className="n">{fmt(p.amount)}</td><td className="n">{p.due_days}</td>
        <td><button className="btn sm alt" onClick={() => api.del(`/fx/exposures/${p.id}/`).then(load)}>Remove</button></td></tr>)}</tbody></table></Card>
  </>);
}

function Forward() {
  const [f, set] = useForm({ base: "EUR", quote: "USD", amount: 100000, tenor_days: 90, direction: "BUY" });
  const [r, setR] = useState(null);
  const { busy, err, run } = useAction();
  const go = (save) => run(async () => setR(await api.post("/fx/forward/", { ...f, amount: Number(f.amount), tenor_days: Number(f.tenor_days), save })));
  return (<>
    <Card title="Forward contract simulation" sub="Forward rate from covered interest-rate parity. Compare locking today's forward vs. waiting for the spot rate.">
      <div className="row">
        <Field label="Base"><CcySelect value={f.base} onChange={set("base")} /></Field>
        <Field label="Quote"><CcySelect value={f.quote} onChange={set("quote")} /></Field>
        <Field label="Amount of base"><input type="number" value={f.amount} onChange={set("amount")} /></Field>
        <Field label="Tenor (days)"><input type="number" value={f.tenor_days} onChange={set("tenor_days")} /></Field>
        <Field label="You will"><select value={f.direction} onChange={set("direction")}><option value="BUY">Buy base (payable)</option><option value="SELL">Sell base (receivable)</option></select></Field>
      </div>
      <Err e={err} /><button className="btn" disabled={busy} onClick={() => go(false)}>Simulate</button><button className="btn alt" disabled={busy} onClick={() => go(true)}>Simulate &amp; save contract</button>
    </Card>
    {r && <Card title={`Locked rate ${r.forward_rate} (spot ${r.spot}, points ${r.forward_points})`}>
      <p>Locked value <b>{r.quote} {fmt(r.locked_value)}</b> · forward beats unhedged in <b>{r.prob_forward_better_pct}%</b> of simulations · unhedged std. dev. {fmt(r.unhedged_std)}</p>
      <table><thead><tr><th>Spot at maturity (percentile)</th><th className="n">Spot</th><th className="n">Unhedged value</th><th className="n">Forward value</th><th className="n">Hedge benefit</th></tr></thead>
        <tbody>{r.scenarios.map((s) => <tr key={s.percentile}><td>{s.percentile}th</td><td className="n">{s.spot_at_maturity}</td><td className="n">{fmt(s.unhedged_value)}</td><td className="n">{fmt(s.locked_value)}</td>
          <td className="n" style={{ color: s.hedge_benefit >= 0 ? "#2f7d4f" : C.red }}>{fmt(s.hedge_benefit)}</td></tr>)}</tbody></table>
    </Card>}
  </>);
}

function Hedge() {
  const [f, set] = useForm({ certainty: 0.8, tolerance: "medium", due_days: 60, currency: "", net_usd: 100000 });
  const [r, setR] = useState(null);
  const { busy, err, run } = useAction();
  const go = () => run(async () => { const b = { certainty: Number(f.certainty), tolerance: f.tolerance, due_days: Number(f.due_days) };
    if (f.currency) { b.currency = f.currency; b.net_usd = Number(f.net_usd); } setR(await api.post("/fx/hedge/", b)); });
  return (<>
    <Card title="Hedging recommendation engine" sub="Leave currency empty to analyse your largest net position from the Exposure tab.">
      <div className="row">
        <Field label="Currency (optional)"><select value={f.currency} onChange={set("currency")}><option value="">Auto (largest exposure)</option>{["EUR", "GBP", "INR", "JPY", "AUD", "CAD", "SGD", "AED", "CNY"].map((c) => <option key={c}>{c}</option>)}</select></Field>
        {f.currency && <Field label="Net exposure (USD, + receivable / - payable)"><input type="number" value={f.net_usd} onChange={set("net_usd")} /></Field>}
        <Field label="Due in (days)"><input type="number" value={f.due_days} onChange={set("due_days")} /></Field>
        <Field label={`Cash-flow certainty: ${Math.round(f.certainty * 100)}%`}><input type="range" min="0" max="1" step="0.05" value={f.certainty} onChange={set("certainty")} /></Field>
        <Field label="Risk tolerance"><select value={f.tolerance} onChange={set("tolerance")}><option value="low">Low (hedge more)</option><option value="medium">Medium</option><option value="high">High (hedge less)</option></select></Field>
      </div>
      <Err e={err} /><button className="btn" disabled={busy} onClick={go}>Recommend</button>
    </Card>
    {r && <Card title={`${r.currency}: ${r.primary}`}><p>{r.summary}</p>
      <table><thead><tr><th>Strategy</th><th>Fit</th><th>Why</th></tr></thead><tbody>{r.strategies.map((s) => <tr key={s.name}><td><b>{s.name}</b></td><td>{s.fit}</td><td>{s.why}</td></tr>)}</tbody></table></Card>}
  </>);
}

export default function FxRisk() {
  return (<>
    <h1>Foreign Exchange Risk Calculator</h1>
    <p className="sub">Quantify how currency moves affect your transactions, then test hedging strategies.</p>
    <Tabs tabs={["Rate simulator", "Profit / loss", "Exposure", "Forward contract", "Hedging"]}>
      {(t) => t === "Rate simulator" ? <Scenarios /> : t === "Profit / loss" ? <Pnl /> : t === "Exposure" ? <Exposure /> : t === "Forward contract" ? <Forward /> : <Hedge />}
    </Tabs>
  </>);
}
