import { useEffect, useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import { Badge, C, Card, Meter, Stat, fmt, levelColor, usd, useAction } from "../ui.jsx";

export default function Dashboard() {
  const [d, setD] = useState(null);
  const { busy, err, run } = useAction();
  const load = () => api.get("/dashboard/").then(setD);
  useEffect(() => { load(); }, []);
  if (!d) return <p>Loading…</p>;
  const k = d.kpis;
  const empty = k.transactions === 0 && d.exposure.by_currency.length === 0;
  return (<>
    <h1>Risk Analytics Dashboard</h1>
    <p className="sub">Currency exposure, FX risk, country risk, settlement delays and payment performance in one view.</p>
    {empty && <Card title="No data yet"><p>Load realistic sample transactions and exposures to explore the dashboard.</p>
      <button className="btn" disabled={busy} onClick={() => run(async () => { await api.post("/demo/seed/"); await load(); })}>Load sample data</button>{err && <div className="err">{err}</div>}</Card>}
    <div className="grid g4" style={{ marginBottom: 18 }}>
      <Stat label="Transactions" value={k.transactions}><span> · {k.pending} pending</span></Stat>
      <Stat label="Volume (USD)" value={usd(k.volume_usd)} />
      <Stat label="Total cost" value={usd(k.total_cost_usd)}><span> · {k.avg_cost_pct}% average</span></Stat>
      <Stat label="95% VaR (30d)" value={usd(k.var95_usd)} />
    </div>
    <div className="grid g3">
      <Card title="FX risk score"><div className="big" style={{ color: levelColor(k.fx_risk_level) }}>{k.fx_risk_score}</div>
        <p><Badge v={k.fx_risk_level} /> out of 100</p><Meter value={k.fx_risk_score} color={levelColor(k.fx_risk_level)} /></Card>
      <Card title="Transaction risk mix">
        <ResponsiveContainer width="100%" height={160}><PieChart><Pie data={d.risk_distribution} dataKey="count" nameKey="level" innerRadius={38} outerRadius={65}>
          {d.risk_distribution.map((r) => <Cell key={r.level} fill={levelColor(r.level)} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer>
        <p className="note">{d.risk_distribution.map((r) => `${r.level}: ${r.count}`).join(" · ")}</p>
      </Card>
      <Card title="Pending payments &amp; expected delay">
        <table><tbody>{d.pending_payments.map((p) => <tr key={p.id}><td>#{p.id} {p.corridor}</td><td className="n">{fmt(p.amount, 0)}</td><td className="n">{p.expected_days}d</td></tr>)}</tbody></table>
        {!d.pending_payments.length && <p className="note">Nothing pending.</p>}
      </Card>
    </div>
    <div className="grid g2">
      <Card title="Currency exposure (USD)">
        <ResponsiveContainer width="100%" height={250}><BarChart data={d.exposure.by_currency}><CartesianGrid strokeDasharray="3 3" stroke="#d9d3c4" /><XAxis dataKey="currency" /><YAxis /><Tooltip />
          <Bar dataKey="net_usd" name="Net exposure">{d.exposure.by_currency.map((e) => <Cell key={e.currency} fill={e.net_usd >= 0 ? C.green : C.red} />)}</Bar>
          <Bar dataKey="var95_usd" name="95% VaR" fill={C.amber} /></BarChart></ResponsiveContainer>
      </Card>
      <Card title="Weekly payment volume (USD)">
        <ResponsiveContainer width="100%" height={250}><AreaChart data={d.weekly_volume}><CartesianGrid strokeDasharray="3 3" stroke="#d9d3c4" /><XAxis dataKey="week" tick={{ fontSize: 10 }} /><YAxis /><Tooltip />
          <Area dataKey="volume_usd" name="Volume" stroke={C.forest} fill={C.sand} /></AreaChart></ResponsiveContainer>
      </Card>
      <Card title="Cost by payment channel">
        <table><thead><tr><th>Channel</th><th className="n">Txns</th><th className="n">Volume</th><th className="n">Avg cost %</th><th className="n">Avg days</th></tr></thead>
          <tbody>{d.by_channel.map((c) => <tr key={c.channel}><td>{c.channel}</td><td className="n">{c.count}</td><td className="n">{usd(c.volume_usd)}</td><td className="n">{c.avg_cost_pct}</td><td className="n">{c.avg_days}</td></tr>)}</tbody></table>
      </Card>
      <Card title="Country risk assessment">
        <table><thead><tr><th>Country</th><th>Risk (0-100)</th><th className="n">Typical delay</th><th className="n">Txns</th></tr></thead>
          <tbody>{d.country_risk.map((c) => <tr key={c.currency}><td>{c.country} ({c.currency})</td>
            <td style={{ width: "40%" }}><Meter value={c.risk_score} color={c.risk_score >= 40 ? C.red : c.risk_score >= 25 ? C.amber : C.green} /></td>
            <td className="n">+{c.avg_delay_days}d</td><td className="n">{c.transactions}</td></tr>)}</tbody></table>
      </Card>
    </div>
    {d.corridor_delays.length > 0 && <Card title="Slowest corridors (avg expected settlement)">
      <ResponsiveContainer width="100%" height={200}><BarChart data={d.corridor_delays} layout="vertical"><CartesianGrid strokeDasharray="3 3" stroke="#d9d3c4" /><XAxis type="number" /><YAxis type="category" dataKey="corridor" width={90} /><Tooltip />
        <Bar dataKey="avg_days" name="Days" fill={C.forest} /></BarChart></ResponsiveContainer></Card>}
  </>);
}
