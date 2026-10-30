"""Module 1 & 3: payment channel simulation and provider cost model."""
from . import market

# fees are in USD (converted to source currency); tiers = [(min_usd_amount, value)]
PROVIDERS = {
    "swift": dict(label="SWIFT Transfer", kind="channel", fixed=40.0, pct=[(0, .001)],
                  markup=[(0, .018), (25000, .008), (100000, .003)], days=(1, 3), limit=10_000_000,
                  desc="Interbank messaging network; correspondent banks may deduct intermediary fees.",
                  steps=[("Payment order created", 0), ("Sender bank screening (AML/KYC)", 2),
                         ("SWIFT MT103 message sent", 4), ("Correspondent bank routing", 18),
                         ("Beneficiary bank credits account", 36)]),
    "wire": dict(label="Traditional Wire Transfer", kind="channel", fixed=35.0, pct=[(0, .0005)],
                 markup=[(0, .022), (25000, .012), (100000, .006)], days=(2, 5), limit=10_000_000,
                 desc="Bank-to-bank wire with manual operations and cut-off times.",
                 steps=[("Wire request submitted at branch/online", 0), ("Compliance review", 6),
                        ("Cut-off time & batch processing", 24), ("Funds released to receiving bank", 60),
                        ("Beneficiary credited", 84)]),
    "card": dict(label="International Card Payment", kind="channel", fixed=0.30, pct=[(0, .029)],
                 markup=[(0, .03)], days=(0, 1), limit=5000,
                 desc="Card network authorisation with dynamic currency conversion.",
                 steps=[("Card details tokenised", 0), ("Authorisation request to issuer", 0.01),
                        ("3-D Secure / fraud check", 0.02), ("Network clearing", 12), ("Merchant settlement", 24)]),
    "wallet": dict(label="Digital Wallet", kind="channel", fixed=0.0, pct=[(0, .005)],
                   markup=[(0, .012)], days=(0, 1), limit=50000,
                   desc="Wallet-to-wallet transfer on a closed-loop network.",
                   steps=[("Wallet balance verified", 0), ("Currency conversion", 0.01),
                          ("Ledger transfer between wallets", 0.02), ("Recipient wallet credited", 0.05),
                          ("Optional cash-out to bank", 12)]),
    "wise": dict(label="Wise", kind="provider", fixed=1.0, pct=[(0, .0065), (10000, .005), (100000, .004)],
                 markup=[(0, 0.0)], days=(0, 2), limit=250000, desc="Mid-market rate with transparent fee.",
                 steps=[("Quote locked", 0), ("Funds received", 2), ("Local payout", 12)]),
    "paypal": dict(label="PayPal", kind="provider", fixed=0.49, pct=[(0, .029)], markup=[(0, .04)],
                   days=(0, 1), limit=60000, desc="High FX margin on conversion.",
                   steps=[("Payment authorised", 0), ("Conversion at PayPal rate", 0.1), ("Recipient credited", 6)]),
    "western_union": dict(label="Western Union", kind="provider", fixed=5.0, pct=[(0, .005)],
                          markup=[(0, .035), (5000, .025)], days=(0, 1), limit=50000,
                          desc="Agent network, fast but wide FX spread.",
                          steps=[("Order placed", 0), ("Funds collected", 1), ("Available for pickup/deposit", 12)]),
    "bank_transfer": dict(label="Bank Transfer", kind="provider", fixed=20.0, pct=[(0, .002)],
                          markup=[(0, .025), (25000, .014), (100000, .007)], days=(2, 4), limit=10_000_000,
                          desc="Standard international bank transfer.",
                          steps=[("Transfer initiated", 0), ("Bank processing", 24), ("Credited", 72)]),
}
CHANNELS = ["swift", "wire", "card", "wallet"]
OPTIMIZER = ["swift", "wise", "paypal", "western_union", "bank_transfer"]
URGENCY_WEIGHT = {0: 0.05, 1: 0.30, 2: 1.0}  # % cost-equivalent per day of delay


def _tier(tiers, usd):
    v = tiers[0][1]
    for thr, val in tiers:
        if usd >= thr:
            v = val
    return v


def quote(key, amount, frm, to):
    p = PROVIDERS[key]
    usd = market.to_usd(amount, frm)
    mid = market.rate(frm, to)
    fixed = p["fixed"] * market.USD_RATES[frm]
    pct_fee = amount * _tier(p["pct"], usd)
    markup = _tier(p["markup"], usd)
    fx_cost = amount * markup
    fee_total = fixed + pct_fee
    total = fee_total + fx_cost
    applied = mid * (1 - markup)
    received = max(amount - fee_total, 0) * applied
    lo, hi = p["days"]
    mid_days = (lo + hi) / 2
    delay = market.COUNTRY[to][2]
    exp_days = mid_days + (delay if mid_days >= 1 else delay * 0.2)
    eligible = usd <= p["limit"]
    return dict(
        provider=key, label=p["label"], kind=p["kind"], description=p["desc"],
        fixed_fee=round(fixed, 2), percentage_fee=round(pct_fee, 2), fee_total=round(fee_total, 2),
        fx_markup_pct=round(markup * 100, 2), fx_markup_cost=round(fx_cost, 2),
        total_cost=round(total, 2), cost_pct=round(total / amount * 100, 3),
        mid_rate=round(mid, 6), applied_rate=round(applied, 6), recipient_gets=round(received, 2),
        days_min=lo, days_max=hi, expected_days=round(exp_days, 2), eligible=eligible,
        reason=None if eligible else f"Amount exceeds provider limit of USD {p['limit']:,}",
    )


def _validate(amount, frm, to):
    market.check_ccy(frm), market.check_ccy(to)
    if frm == to:
        raise ValueError("Source and destination currency must differ")
    if amount <= 0:
        raise ValueError("Amount must be positive")


def simulate(key, amount, frm, to):
    """Simulate one payment through a channel with a timeline of workflow steps."""
    _validate(amount, frm, to)
    if key not in PROVIDERS:
        raise ValueError("Unknown payment channel")
    q = quote(key, amount, frm, to)
    p = PROVIDERS[key]
    extra_h = market.COUNTRY[to][2] * 24 if q["expected_days"] >= 1 else 0
    steps, n = [], len(p["steps"])
    for i, (name, hours) in enumerate(p["steps"]):
        h = hours + (extra_h * i / max(n - 1, 1))
        steps.append(dict(step=i + 1, name=name, eta_hours=round(h, 2)))
    warnings = []
    if not q["eligible"]:
        warnings.append(q["reason"])
    if q["cost_pct"] > 3:
        warnings.append("Total cost exceeds 3% of the transfer amount - consider an alternative.")
    if market.COUNTRY[to][1] >= 40:
        warnings.append(f"Destination country risk is elevated ({market.COUNTRY[to][0]}); expect compliance checks.")
    return dict(quote=q, steps=steps, warnings=warnings)


def compare(amount, frm, to, urgency=1, keys=None):
    _validate(amount, frm, to)
    quotes = [quote(k, amount, frm, to) for k in (keys or OPTIMIZER)]
    ok = [q for q in quotes if q["eligible"]] or quotes
    w = URGENCY_WEIGHT.get(urgency, 0.3)
    for q in quotes:
        q["utility"] = round(q["cost_pct"] + w * q["expected_days"], 3)
    cheapest = min(ok, key=lambda q: q["total_cost"])
    fastest = min(ok, key=lambda q: (q["expected_days"], q["total_cost"]))
    best = min(ok, key=lambda q: q["utility"])
    savings = max(q["total_cost"] for q in ok) - cheapest["total_cost"]
    return dict(quotes=sorted(quotes, key=lambda q: (not q["eligible"], q["total_cost"])),
                cheapest=cheapest["provider"], fastest=fastest["provider"], best_value=best["provider"],
                max_savings=round(savings, 2),
                summary=f"{cheapest['label']} is cheapest at {cheapest['cost_pct']}% "
                        f"({frm} {cheapest['total_cost']:,}); choosing it saves up to {frm} {savings:,.2f} "
                        f"versus the most expensive option.")
