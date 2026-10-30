import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import { Badge, C, Card, CcySelect, Err, Field, Meter, fmt, levelColor, useAction } from "../ui.jsx";

export default function AI() {
  const [f, setF] = useState({ amount: 8000, from_ccy: "USD", to_ccy: "INR", urgency: 1 });
  const [r, setR] = useState(null);
  const [hist, setHist] = useState([]);
  const [models, setModels] = useState(null);
  const { busy, err, run } = useAction();
  const loadHist = () => api.get("/ai/history/").then(setHist).catch(() => {});
  useEffect(() => { loadHist(); api.get("/ai/models/").then(setModels).catch(() => {}); }, []);
  const set = (k) => (v) => setF({ ...f, [k]: v?.target ? v.target.value : v });
  const go = () => run(async () => { setR(await api.post("/ai/recommend/", { ...f, amount: Number(f.amount), urgency: Number(f.urgency) })); loadHist(); });
  const fx = r?.fx_prediction;
  return (<>
    <h1>AI Recommendation Engine</h1>
    <p className="sub">Machine-learning models (scikit-learn) recommend the payment method, the best timing, the expected exchange-rate movement and the overall transaction risk.</p>
    <Card>
      <div className="row">
        <Field label="Amount"><input type="number" value={f.amount} onChange={set("amount")} /></Field>
        <Field label="From"><CcySelect value={f.from_ccy} onChange={set("from_ccy")} /></Field>
        <Field label="To"><CcySelect value={f.to_ccy} onChange={set("to_ccy")} /></Field>
        <Field label="Urgency"><select value={f.urgency} onChange={set("urgency")}><option value={0}>Low</option><option value={1}>Normal</option><option value={2}>High</option></select></Field>
      </div>
      <Err e={err} /><button className="btn" disabled={busy} onClick={go}>{busy ? "Analysing…" : "Get recommendation"}</button>
      {busy && <span className="note">First run trains the models (a few seconds).</span>}
    </Card>
    {r && <>
      <div className="grid g3">
        <Card title="Best payment method"><div className="big" style={{ fontSize: "1.8rem" }}>{r.method.label}</div><p>{r.method.justification}</p>
          <p className="note">Cheapest: {r.method.cheapest} · Fastest: {r.method.fastest} · Model agrees with rule engine: {r.method.model_agrees ? "yes" : "no"} · accuracy {r.method.model_accuracy}</p></Card>
        <Card title="Optimal timing"><div className="big" style={{ fontSize: "1.8rem" }}>{r.timing.action}</div><p>{r.timing.reason}</p></Card>
        <Card title="Transaction risk"><Badge v={r.risk.level}>{r.risk.level.toUpperCase()}</Badge>
          {Object.entries(r.risk.probabilities).map(([l, p]) => <div key={l} style={{ margin: "8px 0" }}><span className="note">{l} {Math.round(p * 100)}%</span><Meter value={p * 100} color={levelColor(l)} /></div>)}
          <p className="note">Main drivers: {r.risk.drivers.map((x) => `${x.feature} (${Math.round(x.importance * 100)}%)`).join(", ")} · model accuracy {r.risk.model_accuracy}</p></Card>
      </div>
      <Card title={`${fx.pair} rate prediction - 7-day direction: ${fx.direction_7d} (P(up) = ${fx.prob_up_7d})`}>
        <div className="grid g2">
          <ResponsiveContainer width="100%" height={220}><LineChart data={fx.history.map((v, i) => ({ day: i - 59, rate: v }))}><CartesianGrid strokeDasharray="3 3" stroke="#d9d3c4" /><XAxis dataKey="day" /><YAxis domain={["auto", "auto"]} /><Tooltip /><Line dataKey="rate" stroke={C.forest} dot={false} strokeWidth={2} /></LineChart></ResponsiveContainer>
          <table><thead><tr><th>Horizon</th><th className="n">Expected change</th><th className="n">±1σ noise</th><th className="n">Expected rate</th></tr></thead>
            <tbody>{fx.horizons.map((h) => <tr key={h.days}><td>{h.days} day(s)</td><td className="n" style={{ color: h.expected_change_pct >= 0 ? "#2f7d4f" : C.red }}>{h.expected_change_pct}%</td><td className="n">{h.sigma_pct}%</td><td className="n">{h.expected_rate}</td></tr>)}</tbody></table>
        </div>
        <p className="note">Direction model accuracy on held-out data: {fx.model_accuracy} (naive majority-class baseline {fx.naive_baseline}). History is simulated.</p>
      </Card>
    </>}
    <div className="grid g2">
      {models && <Card title="Models in use"><table><thead><tr><th>Model</th><th>Algorithm</th><th className="n">Accuracy</th></tr></thead>
        <tbody>{models.models.map((m) => <tr key={m.name}><td>{m.name}</td><td>{m.algorithm}</td><td className="n">{m.accuracy ?? "-"}</td></tr>)}</tbody></table><p className="note">{models.note}</p></Card>}
      <Card title="Recent recommendations"><table><tbody>{hist.map((h) => <tr key={h.id}><td>{fmt(h.request.amount, 0)} {h.request.from_ccy}→{h.request.to_ccy}</td><td>{h.method}</td><td>{h.timing}</td><td><Badge v={h.risk_level} /></td></tr>)}</tbody></table>
        {!hist.length && <p className="note">No recommendations yet.</p>}</Card>
    </div>
  </>);
}
