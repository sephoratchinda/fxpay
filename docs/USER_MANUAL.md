# User Manual

## 1. Getting started
Open the app -> **Register** (username, optional email, password >= 8 chars) -> you are signed in automatically. Use **Sign out** (bottom of sidebar) to leave. Sessions use JWT and renew automatically for 7 days.
First time? Go to **Risk Dashboard -> Load sample data** to populate everything.

## 2. International Payments
1. Choose a channel (SWIFT, Wire, Card, Wallet) - the description explains how it works.
2. Enter amount, source and destination currency, recipient.
3. **Simulate** shows mid-market vs applied rate, fees, hidden FX margin, total cost %, amount received, expected days and the step-by-step processing timeline (hours from start). Warnings flag high cost, limits, or risky destinations.
4. **Send payment** saves it. In *My transactions* click **Advance** to move it Processing -> Completed.

## 3. FX Risk Calculator (5 tabs)
* **Rate simulator** - choose a pair and horizon; the chart shows the median path and the 5-95% band; table shows instant +/-2/5/10% shocks.
* **Profit / loss** - enter foreign amount, booked and new rate (home per foreign unit) and whether it is a receivable or payable.
* **Exposure** - add receivables/payables per currency. See gross/net exposure in USD, 95% 30-day VaR and a 0-100 risk score (Low <33, Medium <66, High).
* **Forward contract** - lock a forward at the interest-parity rate and compare with unhedged outcomes at 5th-95th percentile; "forward better in X%" shows how often the hedge would have won. Save to keep the contract.
* **Hedging** - set cash-flow certainty, risk tolerance and due date. The engine proposes a hedge ratio and ranked strategies (forward, layered forwards, options, collar, netting, multi-currency account).

## 4. Cost Optimizer
Enter amount, currencies and urgency (cost-first vs speed-first). The bar chart and table compare five providers; the highlighted row is cheapest; tags show fastest. Over-limit providers are greyed out.

## 5. Risk Dashboard
KPIs, FX risk score, transaction-risk mix, pending payments with expected delay, exposure and VaR per currency, weekly volume, channel cost table, country-risk meters and slowest corridors.

## 6. AI Recommendations
Enter a transfer and urgency. Output: best method with justification, send-now vs wait timing, rate forecast for 1/3/7/14 days with uncertainty, and a Low/Medium/High risk class with probabilities and key drivers. The first request trains the models (a few seconds). The *Models in use* table shows algorithms and accuracy.

## 7. Troubleshooting
| Symptom | Fix |
|---|---|
| Blank page / network error | Is the backend on :8000? Check http://localhost:8000/api/health/ |
| 401 after a long time | Sign out and in again |
| `no such table` | Run `python manage.py makemigrations core && python manage.py migrate` |
| Docker db not ready | `docker compose down -v && docker compose up --build` |
