import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import { Badge, C, Card, CcySelect, Err, Field, fmt, useAction } from "../ui.jsx";

export default function Optimizer() {
  const [f, setF] = useState({ amount: 10000, from_ccy: "USD", to_ccy: "INR", urgency: 1 });
  const [res, setRes] = useState(null);
  const { busy, err, run } = useAction();
  const set = (k) => (v) => setF({ ...f, [k]: v?.target ? v.target.value : v });
  const go = () => run(async () => setRes(await api.post("/optimizer/compare/", { ...f, amount: Number(f.amount), urgency: Number(f.urgency) })));
  return (<>
    <h1>Payment Cost Optimizer</h1>
    <p className="sub">Compares SWIFT, Wise, PayPal, Western Union and bank transfer on fees, FX margin and speed, then picks the most economical option.</p>
    <Card>
      <div className="row">
        <Field label="Amount"><input type="number" value={f.amount} onChange={set("amount")} /></Field>
        <Field label="From"><CcySelect value={f.from_ccy} onChange={set("from_ccy")} /></Field>
        <Field label="To"><CcySelect value={f.to_ccy} onChange={set("to_ccy")} /></Field>
        <Field label="Urgency"><select value={f.urgency} onChange={set("urgency")}><option value={0}>Low - cost first</option><option value={1}>Normal</option><option value={2}>High - speed first</option></select></Field>
      </div>
      <Err e={err} /><button className="btn" disabled={busy} onClick={go}>Compare providers</button>
    </Card>
    {res && <>
      <Card title="Recommendation"><p style={{ margin: 0 }}>{res.summary}</p>
        <p className="note">Fastest: <b>{res.quotes.find((q) => q.provider === res.fastest).label}</b> · Best value for your urgency: <b>{res.quotes.find((q) => q.provider === res.best_value).label}</b></p></Card>
      <div className="grid g2">
        <Card title={`Total cost (${f.from_ccy})`}>
          <ResponsiveContainer width="100%" height={260}><BarChart data={res.quotes.filter((q) => q.eligible)}>
            <CartesianGrid strokeDasharray="3 3" stroke="#d9d3c4" /><XAxis dataKey="label" tick={{ fontSize: 11 }} /><YAxis /><Tooltip />
            <Bar dataKey="total_cost" name="Total cost">{res.quotes.filter((q) => q.eligible).map((q) => <Cell key={q.provider} fill={q.provider === res.cheapest ? C.forest : C.sand} />)}</Bar>
          </BarChart></ResponsiveContainer>
        </Card>
        <Card title="Breakdown">
          <table><thead><tr><th>Provider</th><th className="n">Fees</th><th className="n">FX margin</th><th className="n">Total %</th><th className="n">Days</th><th className="n">Recipient gets</th></tr></thead>
            <tbody>{res.quotes.map((q) => (
              <tr key={q.provider} className={q.provider === res.cheapest ? "best" : q.eligible ? "" : "dim"}>
                <td>{q.label} {q.provider === res.cheapest && <Badge v="tag">cheapest</Badge>}{q.provider === res.fastest && <Badge v="tag">fastest</Badge>}</td>
                <td className="n">{fmt(q.fee_total)}</td><td className="n">{fmt(q.fx_markup_cost)}</td><td className="n">{q.cost_pct}</td>
                <td className="n">{q.expected_days}</td><td className="n">{q.eligible ? fmt(q.recipient_gets) : "over limit"}</td></tr>
            ))}</tbody></table>
        </Card>
      </div>
    </>}
  </>);
}
