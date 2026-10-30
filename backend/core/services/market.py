"""Simulated market data: spot rates, volatility, interest rates, country risk.
All figures are illustrative so the system works offline. Swap `USD_RATES`
with a live API (e.g. exchangerate.host) in production."""
import zlib
import numpy as np

USD_RATES = {  # units of currency per 1 USD
    "USD": 1.0, "EUR": 0.92, "GBP": 0.79, "INR": 83.3, "JPY": 149.5,
    "AUD": 1.53, "CAD": 1.36, "SGD": 1.34, "AED": 3.6725, "CNY": 7.24,
}
ANNUAL_VOL = {"USD": 0.0, "EUR": 0.075, "GBP": 0.085, "INR": 0.045, "JPY": 0.105,
              "AUD": 0.115, "CAD": 0.07, "SGD": 0.05, "AED": 0.005, "CNY": 0.04}
INTEREST = {"USD": 0.045, "EUR": 0.025, "GBP": 0.04, "INR": 0.065, "JPY": 0.005,
            "AUD": 0.04, "CAD": 0.03, "SGD": 0.03, "AED": 0.045, "CNY": 0.02}
# currency -> (country, risk score 0-100, extra expected settlement delay in days)
COUNTRY = {
    "USD": ("United States", 10, 0.0), "EUR": ("Eurozone", 15, 0.1),
    "GBP": ("United Kingdom", 15, 0.1), "INR": ("India", 40, 0.8),
    "JPY": ("Japan", 15, 0.2), "AUD": ("Australia", 12, 0.2),
    "CAD": ("Canada", 12, 0.1), "SGD": ("Singapore", 8, 0.1),
    "AED": ("UAE", 30, 0.4), "CNY": ("China", 45, 1.0),
}
CURRENCIES = sorted(USD_RATES)


def check_ccy(c):
    if c not in USD_RATES:
        raise ValueError(f"Unsupported currency: {c}")
    return c


def rate(frm, to):
    """Mid-market rate: units of `to` per 1 `frm`."""
    return USD_RATES[check_ccy(to)] / USD_RATES[check_ccy(frm)]


def to_usd(amount, ccy):
    return amount / USD_RATES[ccy]


def pair_vol(frm, to):
    a, b = ANNUAL_VOL[frm], ANNUAL_VOL[to]
    return float(np.sqrt(max(a * a + b * b - 2 * 0.3 * a * b, 0)))


def _seed(key):
    return zlib.crc32(key.encode()) & 0xFFFFFFFF


def history(frm, to, days=600):
    """Deterministic synthetic daily history (ends at today's spot) with mild
    momentum and mean reversion so ML models have learnable structure."""
    rng = np.random.default_rng(_seed(f"{frm}{to}"))
    sigma = max(pair_vol(frm, to), 0.003) / np.sqrt(252)
    r = np.zeros(days)
    logp = np.zeros(days)
    for t in range(1, days):
        ma = logp[max(0, t - 20):t].mean()
        r[t] = 0.30 * r[t - 1] - 0.05 * (logp[t - 1] - ma) + rng.normal(0, sigma)
        logp[t] = logp[t - 1] + r[t]
    p = np.exp(logp)
    return p * (rate(frm, to) / p[-1])


def simulate_paths(spot, vol, days, n=500, drift=0.0, seed=None):
    """Geometric Brownian Motion Monte-Carlo. Returns paths[n, days+1]."""
    rng = np.random.default_rng(seed)
    dt = 1 / 365
    z = rng.standard_normal((n, days))
    inc = (drift - 0.5 * vol ** 2) * dt + vol * np.sqrt(dt) * z
    logp = np.concatenate([np.zeros((n, 1)), np.cumsum(inc, axis=1)], axis=1)
    return spot * np.exp(logp)
