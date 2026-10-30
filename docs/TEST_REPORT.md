# Test Report

## 1. Automated tests
| Suite | Command | Tests | Result |
|---|---|---|---|
| Business logic + ML (`core/tests/test_services.py`) | `python -m unittest core.tests.test_services` | 21 | **21 passed** (executed during development) |
| API integration (`core/tests/test_api.py`) | `python manage.py test` | 10 | Run on your machine and paste output/screenshot here for submission |

## 2. Test cases
| ID | Module | Scenario | Expected | Automated |
|---|---|---|---|---|
| T01 | Market | EUR/USD x USD/EUR = 1; cross-rate consistency | equality | yes |
| T02 | Market | Unsupported currency | ValueError / HTTP 400 | yes |
| T03 | Market | History deterministic, ends at spot | identical runs | yes |
| T04 | Payments | SWIFT simulation yields >=4 workflow steps and positive cost | pass | yes |
| T05 | Payments | Same currency / negative amount rejected | 400 | yes |
| T06 | Payments | Card limit (USD 5,000) enforced | not eligible / 400 | yes |
| T07 | Optimizer | Cheapest = true minimum of eligible quotes | pass | yes |
| T08 | Optimizer | USD 5k -> Wise cheapest; USD 500k -> SWIFT (Wise limit) | pass | yes |
| T09 | FX | Receivable gain when foreign currency appreciates | +2,000 on 100k @1.08->1.10 | yes |
| T10 | FX | Payable loses when foreign currency appreciates | negative P/L | yes |
| T11 | FX | Forward = S(1+r_q t)/(1+r_b t) | exact | yes |
| T12 | FX | Offsetting receivable/payable nets to zero risk | score 0 | yes |
| T13 | FX | AUD portfolio scores riskier than AED (peg) | pass | yes |
| T14 | Hedge | Pegged currency -> no hedge; uncertain flow -> option | pass | yes |
| T15 | AI | Risk class monotonic (small SGD < large AUD->CNY) | pass | yes |
| T16 | AI | High urgency -> "Send now"; probabilities sum to 1 | pass | yes |
| T17 | AI | Model held-out accuracy: risk > 0.75, method > 0.85 | measured 0.85 / 0.99 | yes |
| T18 | Auth | Register + login returns JWT; bad password 401 | pass | API suite |
| T19 | Auth | Protected endpoint without token | 401 | API suite |
| T20 | Payments | Send -> advance -> COMPLETED; list returns 1 | pass | API suite |
| T21 | Security | User B cannot see User A's exposures | empty list | API suite |
| T22 | Dashboard | After seeding: 25 transactions, risk score > 0 | pass | API suite |
| T23 | UI (manual) | Register -> seed -> each page renders without console errors | pass | manual |

## 3. Measured ML performance (development run)
* Risk classifier (RandomForest): 0.85 hold-out accuracy.
* Method recommender: 0.99 (it learns the platform's own cost model - distillation).
* FX 7-day direction: 0.46-0.70 depending on pair vs. majority baseline 0.51-0.61. With simulated history this is expected to be close to chance; with real data results will differ.
