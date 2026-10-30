"""Module 2: FX risk calculators. Rates are quote-per-base (e.g. EUR/USD = USD per EUR)."""
import math
import numpy as np
from . import market

Z95 = 1.645


def pnl(amount, booked_rate, new_rate, direction="RECEIVABLE"):
    """P/L in quote (home) currency from a rate move on a foreign-currency amount."""
    if booked_rate <= 0 or new_rate <= 0:
        raise ValueError("Rates must be positive")
    diff = new_rate - booked_rate
    profit = amount * diff if direction == "RECEIVABLE" else -amount * diff
    return dict(pnl=round(profit, 2), pct=round(profit / (amount * booked_rate) * 100, 3),
                booked_value=round(amount * booked_rate, 2), new_value=round(amount * new_rate, 2),
                outcome="gain" if profit > 0 else "loss" if profit < 0 else "flat")


def rate_scenarios(base, quote, days=90, shock_pct=None, n=500):
    """Exchange-rate fluctuation simulator: Monte-Carlo percentile fan + deterministic shocks."""
    spot, vol = market.rate(base, quote), max(market.pair_vol(base, quote), 0.002)
    paths = market.simulate_paths(spot, vol, days, n=n, seed=42)
    pct = np.percentile(paths, [5, 25, 50, 75, 95], axis=0)
    step = max(days // 30, 1)
    fan = [dict(day=int(d), p5=round(float(pct[0][d]), 5), p25=round(float(pct[1][d]), 5),
                p50=round(float(pct[2][d]), 5), p75=round(float(pct[3][d]), 5),
                p95=round(float(pct[4][d]), 5)) for d in range(0, days + 1, step)]
    shocks = [dict(shock_pct=s, rate=round(spot * (1 + s / 100), 5)) for s in (shock_pct or [-10, -5, -2, 2, 5, 10])]
    return dict(base=base, quote=quote, spot=round(spot, 5), annual_vol_pct=round(vol * 100, 2),
                horizon_days=days, fan=fan, shocks=shocks,
                terminal=dict(mean=round(float(paths[:, -1].mean()), 5),
                              worst_5pct=round(float(pct[0][-1]), 5), best_95pct=round(float(pct[4][-1]), 5)))


def level(score):
    return "Low" if score < 33 else "Medium" if score < 66 else "High"


def exposure_summary(positions, home="USD", horizon_days=30):
    """positions: [{currency, amount, direction, due_days}] -> net exposure, VaR, risk score."""
    net, gross = {}, 0.0
    for p in positions:
        usd = market.to_usd(float(p["amount"]), p["currency"])
        signed = usd if p["direction"] == "RECEIVABLE" else -usd
        d = net.setdefault(p["currency"], dict(receivable=0.0, payable=0.0, net=0.0))
        d["receivable" if signed > 0 else "payable"] += abs(usd)
        d["net"] += signed
        if p["currency"] != home:
            gross += abs(usd)
    rows, sig = [], []
    for c, d in net.items():
        vol = market.ANNUAL_VOL[c]
        s = abs(d["net"]) * vol * math.sqrt(horizon_days / 365) if c != home else 0.0
        rows.append(dict(currency=c, receivable_usd=round(d["receivable"], 2), payable_usd=round(d["payable"], 2),
                         net_usd=round(d["net"], 2), annual_vol_pct=round(vol * 100, 2),
                         var95_usd=round(s * Z95, 2), country_risk=market.COUNTRY[c][1]))
        if c != home:
            sig.append(s)
    sig = np.array(sig)
    if len(sig):  # portfolio VaR, constant pairwise correlation 0.3
        corr = np.full((len(sig), len(sig)), 0.3) + np.eye(len(sig)) * 0.7
        pvar = Z95 * float(np.sqrt(sig @ corr @ sig))
    else:
        pvar = 0.0
    score = min(100.0, (pvar / gross) / 0.10 * 100) if gross else 0.0
    return dict(home=home, horizon_days=horizon_days, gross_exposure_usd=round(gross, 2),
                net_exposure_usd=round(sum(r["net_usd"] for r in rows if r["currency"] != home), 2),
                portfolio_var95_usd=round(pvar, 2), fx_risk_score=round(score, 1), level=level(score),
                by_currency=rows)


def forward_rate(base, quote, days):
    """Covered interest parity: F = S * (1 + r_quote t) / (1 + r_base t)."""
    t = days / 365
    s = market.rate(base, quote)
    return s, s * (1 + market.INTEREST[quote] * t) / (1 + market.INTEREST[base] * t)


def forward_simulation(base, quote, amount, days, direction="BUY", n=2000):
    """Locking a forward vs staying unhedged. BUY = must buy `amount` of base (payable);
    SELL = will sell `amount` of base (receivable). Values in quote currency."""
    s, f = forward_rate(base, quote, days)
    vol = max(market.pair_vol(base, quote), 0.002)
    st = market.simulate_paths(s, vol, days, n=n, seed=7)[:, -1]
    sign = 1 if direction == "SELL" else -1
    locked = amount * f
    fwd_better = (amount * st > locked) if direction == "BUY" else (amount * st < locked)
    scen = [dict(percentile=q, spot_at_maturity=round(float(np.percentile(st, q)), 5),
                 unhedged_value=round(amount * float(np.percentile(st, q)), 2), locked_value=round(locked, 2),
                 hedge_benefit=round(sign * (locked - amount * float(np.percentile(st, q))), 2))
            for q in (5, 25, 50, 75, 95)]
    return dict(base=base, quote=quote, direction=direction, amount=amount, tenor_days=days,
                spot=round(s, 5), forward_rate=round(f, 5), forward_points=round(f - s, 5),
                locked_value=round(locked, 2),
                prob_forward_better_pct=round(float(fwd_better.mean() * 100), 1),
                unhedged_std=round(float((amount * st).std()), 2), scenarios=scen)


def hedge_recommendation(currency, net_usd, due_days, certainty=0.8, tolerance="medium", home="USD"):
    market.check_ccy(currency)
    if currency == home:
        raise ValueError("No FX exposure for the home currency")
    vol = market.ANNUAL_VOL[currency]
    ratio = {"low": 0.9, "medium": 0.6, "high": 0.3}.get(tolerance, 0.6) * (0.5 + 0.5 * certainty)
    if vol < 0.01:
        return dict(currency=currency, hedge_ratio_pct=0, primary="No hedge needed",
                    strategies=[dict(name="Monitor only", fit="High",
                                     why=f"{currency} is closely managed/pegged (vol {vol*100:.1f}%).")],
                    summary="Currency is effectively pegged; hedging cost outweighs benefit.")
    side = "receivable" if net_usd > 0 else "payable"
    st = []
    if certainty >= 0.6:
        if due_days <= 180:
            st.append(dict(name="Forward contract", fit="High",
                           why="Cash flow is certain and near-term; a forward locks the rate at zero upfront cost."))
        else:
            st.append(dict(name="Layered forwards (rolling hedge)", fit="High",
                           why="Long tenor: hedge in tranches to average rates and manage credit lines."))
    else:
        st.append(dict(name="FX option (" + ("put" if side == "receivable" else "call") + ")", fit="High",
                       why="Cash flow is uncertain; an option caps downside without obligation."))
    if certainty >= 0.6 and vol >= 0.08:
        st.append(dict(name="FX option collar", fit="Medium",
                       why="High volatility; a collar reduces premium while bounding the worst case."))
    st.append(dict(name="Natural hedge / netting", fit="Medium",
                   why=f"Match {currency} receivables and payables, or invoice/borrow in {currency}."))
    st.append(dict(name="Multi-currency account", fit="Low" if due_days > 60 else "Medium",
                   why="Hold the currency to avoid repeated conversions."))
    return dict(currency=currency, side=side, exposure_usd=round(abs(net_usd), 2), annual_vol_pct=round(vol * 100, 2),
                hedge_ratio_pct=round(ratio * 100), primary=st[0]["name"], strategies=st,
                summary=f"Hedge about {round(ratio*100)}% of the {side} exposure using {st[0]['name']}.")
