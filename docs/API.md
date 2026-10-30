# REST API Documentation

Base URL: `/api` - JSON. All endpoints except `health`, `auth/register`, `auth/login`, `auth/refresh` require `Authorization: Bearer <access_token>`. Validation failures return `400 {"error": "..."}`.

## Auth
| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/auth/register/` | `{username, email, password(min 8)}` | 201 user |
| POST | `/auth/login/` | `{username, password}` | `{access, refresh}` |
| POST | `/auth/refresh/` | `{refresh}` | `{access}` |
| GET | `/auth/me/` | - | `{id, username, email}` |
| GET | `/health/` | - | `{status:"ok"}` |
| GET | `/meta/` | - | currencies, channels, providers |
| POST | `/demo/seed/` | - | creates 25 sample transactions + 6 exposures |

## Module 1 - Payments
| Method | Path | Body | Notes |
|---|---|---|---|
| POST | `/payments/simulate/` | `{channel: swift\|wire\|card\|wallet, amount, from_ccy, to_ccy}` | returns `quote`, `steps[]`, `warnings[]` (not saved) |
| POST | `/payments/` | same + `recipient_name, urgency` | saves transaction, classifies risk; 400 if over channel limit |
| GET | `/payments/` | - | user's transactions |
| POST | `/payments/{id}/advance/` | - | INITIATED -> PROCESSING -> COMPLETED |

## Module 2 - FX risk
| Method | Path | Body |
|---|---|---|
| POST | `/fx/scenarios/` | `{base, quote, days, shocks?[]}` -> percentile fan chart data + shocks |
| POST | `/fx/pnl/` | `{amount, booked_rate, new_rate, direction: RECEIVABLE\|PAYABLE}` -> `{pnl, pct, outcome}` |
| GET/POST | `/fx/exposures/` | `{currency, amount, direction, due_days, description}` |
| DELETE | `/fx/exposures/{id}/` | - |
| GET | `/fx/exposure-summary/?horizon=30` | gross/net exposure, 95% VaR, `fx_risk_score`, per-currency rows |
| POST | `/fx/forward/` | `{base, quote, amount, tenor_days, direction: BUY\|SELL, save?}` |
| GET | `/fx/forwards/` | saved forward contracts |
| POST | `/fx/hedge/` | `{certainty 0-1, tolerance low\|medium\|high, due_days, currency?, net_usd?}` (auto-picks largest exposure if currency omitted) |

## Module 3 - Optimizer
`POST /optimizer/compare/` `{amount, from_ccy, to_ccy, urgency 0-2}` -> `quotes[]` (fees, FX margin, total cost, %, applied rate, recipient amount, expected days, eligibility), `cheapest`, `fastest`, `best_value`, `max_savings`, `summary`.

## Module 4 - Dashboard
`GET /dashboard/` -> `kpis`, `exposure`, `by_channel`, `weekly_volume`, `risk_distribution`, `country_risk`, `corridor_delays`, `pending_payments`.

## Module 5 - AI
| Method | Path | Notes |
|---|---|---|
| POST | `/ai/recommend/` `{amount, from_ccy, to_ccy, urgency}` | returns `method`, `timing`, `fx_prediction`, `risk` (level, probabilities, feature drivers, accuracy); stored in history |
| GET | `/ai/history/` | last 20 recommendations |
| GET | `/ai/models/` | algorithms, features, held-out accuracy |

### Example
```bash
TOKEN=$(curl -s -X POST localhost:8000/api/auth/login/ -H 'Content-Type: application/json' -d '{"username":"alice","password":"password123"}' | python -c "import sys,json;print(json.load(sys.stdin)['access'])")
curl -X POST localhost:8000/api/optimizer/compare/ -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"amount":10000,"from_ccy":"USD","to_ccy":"INR","urgency":1}'
```
