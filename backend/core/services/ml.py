"""Module 5: AI recommendation engine (scikit-learn).

Four models, all trained on first use (a few seconds) and cached in memory:
  1. RiskClassifier      RandomForest -> Low / Medium / High transaction risk
  2. MethodRecommender   RandomForest -> best payment provider for the situation
  3. FX direction model  GradientBoosting -> will the pair rise over next 7 days
  4. FX move regressors  Ridge (per horizon) -> expected % change, used for timing
Training data for 1 and 2 is generated from the platform's own cost/risk model
(knowledge distillation), FX models use the pair's (simulated) price history.
Replace `market.history` with real data to use live history."""
from functools import lru_cache
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import Ridge
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

from . import market, payments

RISK_LABELS = ["Low", "Medium", "High"]
RISK_FEATURES = ["log10 amount (USD)", "pair volatility", "destination country risk", "expected delay (days)",
                 "urgency"]
METHOD_FEATURES = ["log10 amount (USD)", "urgency", "destination delay", "destination country risk"]
METHOD_KEYS = list(payments.PROVIDERS)
HORIZONS = [1, 3, 7, 14]


def risk_score(log_amt, vol, crisk, days, urgency):
    """Ground-truth rule used to synthesise labelled training data."""
    return (0.30 * np.clip((log_amt - 2) / 4, 0, 1) + 0.30 * np.clip(vol / 0.12, 0, 1) +
            0.25 * np.clip(crisk / 60, 0, 1) + 0.10 * np.clip(days / 6, 0, 1) + 0.05 * urgency / 2)


def _risk_features(amount_usd, frm, to, days, urgency):
    return [np.log10(max(amount_usd, 1)), market.pair_vol(frm, to), market.COUNTRY[to][1], days, urgency]


@lru_cache(maxsize=1)
def risk_model():
    rng = np.random.default_rng(1)
    n = 4000
    X = np.column_stack([rng.uniform(2, 6.5, n), rng.uniform(0, 0.13, n), rng.uniform(5, 60, n),
                         rng.uniform(0, 6, n), rng.integers(0, 3, n)])
    s = risk_score(*X.T) + rng.normal(0, 0.04, n)
    y = np.digitize(s, [0.33, 0.55])
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=1, stratify=y)
    m = RandomForestClassifier(n_estimators=80, max_depth=8, random_state=1).fit(Xtr, ytr)
    return m, round(float(accuracy_score(yte, m.predict(Xte))), 3)


@lru_cache(maxsize=1)
def method_model():
    rng = np.random.default_rng(2)
    ccys = [c for c in market.CURRENCIES]
    X, y = [], []
    for _ in range(3000):
        usd = 10 ** rng.uniform(1.5, 6.3)
        urg = int(rng.integers(0, 3))
        to = ccys[rng.integers(len(ccys))]
        frm = "USD" if to != "USD" else "EUR"
        res = payments.compare(usd * market.USD_RATES[frm], frm, to, urgency=urg, keys=METHOD_KEYS)
        X.append([np.log10(usd), urg, market.COUNTRY[to][2], market.COUNTRY[to][1]])
        y.append(METHOD_KEYS.index(res["best_value"]))
    X, y = np.array(X), np.array(y)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=2)
    m = RandomForestClassifier(n_estimators=60, max_depth=10, random_state=2).fit(Xtr, ytr)
    return m, round(float(accuracy_score(yte, m.predict(Xte))), 3)


def _fx_features(p, t):
    lr = np.diff(np.log(p))
    r = lr[t - 5:t]  # 5 most recent log-returns up to t
    ma5, ma20 = p[t - 4:t + 1].mean(), p[t - 19:t + 1].mean()
    return np.concatenate([r, [ma5 / ma20 - 1, p[t] / ma20 - 1, lr[t - 10:t].std()]])


@lru_cache(maxsize=64)
def fx_models(frm, to):
    p = market.history(frm, to)
    ts = range(25, len(p) - max(HORIZONS) - 1)
    X = np.array([_fx_features(p, t) for t in ts])
    out = {}
    cut = int(len(X) * 0.8)
    for h in HORIZONS:
        yv = np.array([np.log(p[t + h] / p[t]) for t in ts])
        out[h] = Ridge(alpha=1e-3).fit(X[:cut], yv[:cut])
    y7 = np.array([int(p[t + 7] > p[t]) for t in ts])
    clf = GradientBoostingClassifier(n_estimators=60, max_depth=2, random_state=3).fit(X[:cut], y7[:cut])
    acc = float(accuracy_score(y7[cut:], clf.predict(X[cut:])))
    base = max(y7[cut:].mean(), 1 - y7[cut:].mean())
    return dict(clf=clf, reg=out, acc=round(acc, 3), baseline=round(float(base), 3), p=p, X_last=_fx_features(p, len(p) - 1))


def predict_fx(frm, to):
    m = fx_models(frm, to)
    x = m["X_last"].reshape(1, -1)
    prob_up = float(m["clf"].predict_proba(x)[0][list(m["clf"].classes_).index(1)])
    vol_d = max(market.pair_vol(frm, to), 0.002) / np.sqrt(252)
    horizons = []
    for h in HORIZONS:
        e = float(m["reg"][h].predict(x)[0])
        horizons.append(dict(days=h, expected_change_pct=round(e * 100, 3), sigma_pct=round(vol_d * np.sqrt(h) * 100, 3),
                             expected_rate=round(float(m["p"][-1] * np.exp(e)), 5)))
    direction = "Up" if prob_up > 0.55 else "Down" if prob_up < 0.45 else "Sideways"
    hist = [round(float(v), 5) for v in m["p"][-60:]]
    return dict(pair=f"{frm}/{to}", spot=round(float(m["p"][-1]), 5), direction_7d=direction,
                prob_up_7d=round(prob_up, 3), horizons=horizons, history=hist,
                model_accuracy=m["acc"], naive_baseline=m["baseline"])


def best_timing(fx, urgency):
    """Rate = units of `to` per `frm`; a higher future rate means the recipient gets more, so waiting helps."""
    if urgency == 2:
        return dict(action="Send now", wait_days=0, reason="High urgency selected - settlement speed outweighs rate timing.")
    best = max(fx["horizons"], key=lambda h: h["expected_change_pct"] / h["sigma_pct"])
    edge = best["expected_change_pct"] / best["sigma_pct"]
    if best["expected_change_pct"] > 0 and edge > 0.15:
        return dict(action=f"Wait ~{best['days']} day(s)", wait_days=best["days"],
                    reason=f"Model expects the rate to improve {best['expected_change_pct']}% "
                           f"(vs ±{best['sigma_pct']}% noise) in {best['days']} day(s).")
    return dict(action="Send now", wait_days=0,
                reason="No horizon shows a favourable expected move large relative to its volatility; waiting only adds risk.")


def recommend(amount, frm, to, urgency=1):
    payments._validate(amount, frm, to)
    usd = market.to_usd(amount, frm)
    cmp = payments.compare(amount, frm, to, urgency=urgency, keys=METHOD_KEYS)
    fx = predict_fx(frm, to)
    # method
    mm, macc = method_model()
    mx = np.array([[np.log10(max(usd, 1)), urgency, market.COUNTRY[to][2], market.COUNTRY[to][1]]])
    proba = mm.predict_proba(mx)[0]
    order = [METHOD_KEYS[mm.classes_[i]] for i in np.argsort(proba)[::-1]]
    ml_pick = next((k for k in order if next(q for q in cmp["quotes"] if q["provider"] == k)["eligible"]), cmp["best_value"])
    best_q = next(q for q in cmp["quotes"] if q["provider"] == ml_pick)
    # risk
    rm, racc = risk_model()
    best_days = best_q["expected_days"]
    rx = np.array([_risk_features(usd, frm, to, best_days, urgency)])
    rp = rm.predict_proba(rx)[0]
    level = RISK_LABELS[int(rm.classes_[int(np.argmax(rp))])]
    imp = sorted(zip(RISK_FEATURES, rm.feature_importances_), key=lambda t: -t[1])
    timing = best_timing(fx, urgency)
    why = (f"{best_q['label']} gives the best cost/speed trade-off for urgency level {urgency}: "
           f"{best_q['cost_pct']}% total cost, ~{best_days} day(s), recipient receives "
           f"{to} {best_q['recipient_gets']:,}.")
    return dict(
        method=dict(provider=ml_pick, label=best_q["label"], justification=why, quote=best_q,
                    rule_based_best=cmp["best_value"], model_agrees=ml_pick == cmp["best_value"],
                    cheapest=cmp["cheapest"], fastest=cmp["fastest"], model_accuracy=macc),
        timing=timing, fx_prediction=fx,
        risk=dict(level=level, probabilities={RISK_LABELS[int(c)]: round(float(p), 3) for c, p in zip(rm.classes_, rp)},
                  drivers=[dict(feature=f, importance=round(float(i), 3)) for f, i in imp[:3]], model_accuracy=racc),
    )


def model_info():
    _, racc = risk_model()
    _, macc = method_model()
    fx = fx_models("USD", "INR")
    return dict(models=[
        dict(name="Transaction risk classifier", algorithm="RandomForestClassifier", accuracy=racc, features=RISK_FEATURES),
        dict(name="Payment method recommender", algorithm="RandomForestClassifier", accuracy=macc, features=METHOD_FEATURES),
        dict(name="FX direction (7d), sample USD/INR", algorithm="GradientBoostingClassifier", accuracy=fx["acc"],
             naive_baseline=fx["baseline"], features=["5 lagged returns", "MA5/MA20", "price vs MA20", "10d volatility"]),
        dict(name="FX expected move (1/3/7/14d)", algorithm="Ridge regression", accuracy=None, features=["same as above"]),
    ], note="FX history is simulated; direction accuracy near the naive baseline is expected for efficient markets.")


def classify_risk(amount_usd, frm, to, days, urgency=1):
    rm, _ = risk_model()
    x = np.array([_risk_features(amount_usd, frm, to, days, urgency)])
    return RISK_LABELS[int(rm.classes_[int(np.argmax(rm.predict_proba(x)[0]))])]
