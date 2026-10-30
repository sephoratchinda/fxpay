# FXPay - Smart Cross-Border Payment & FX Risk Management System

Full-stack web platform that simulates international payments, quantifies foreign-exchange risk, optimises payment cost and uses machine learning to recommend payment method, timing and risk class.

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + Recharts |
| Backend | Django 5 + Django REST Framework |
| Auth | JWT (djangorestframework-simplejwt), access 60 min / refresh 7 days |
| Database | PostgreSQL (SQLite fallback for quick local runs) |
| AI/ML | Python, scikit-learn (RandomForest, GradientBoosting, Ridge) |
| Deployment | Docker, docker-compose, Render blueprint (`render.yaml`) |

## Modules
1. **International Payments** - SWIFT, wire, card, wallet simulation with workflow timeline, fees, FX margin, settlement time.
2. **FX Risk Calculator** - Monte-Carlo rate simulator, P/L calculator, exposure + VaR, forward-contract simulation (covered interest parity), hedging recommendation engine.
3. **Payment Cost Optimizer** - SWIFT vs Wise vs PayPal vs Western Union vs bank transfer; cheapest / fastest / best-value.
4. **Risk Analytics Dashboard** - exposure, FX risk score, country risk, expected delays, transaction analytics.
5. **AI Recommendation Engine** - best method, optimal timing, 1/3/7/14-day rate prediction, Low/Medium/High risk classification.

## Run in VS Code (no Docker) - recommended first

Prerequisites: Python 3.10+, Node 18+.

**Terminal 1 - backend**
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations core
python manage.py migrate
python manage.py runserver 8000        # API on http://localhost:8000/api/
```
(Uses SQLite automatically when `DATABASE_URL` is not set.)

**Terminal 2 - frontend**
```bash
cd frontend
npm install
npm run dev                            # http://localhost:5173  (proxies /api to :8000)
```
Open http://localhost:5173, **Register**, then on the Risk Dashboard click **Load sample data**.

## Run with Docker (PostgreSQL)
```bash
docker compose up --build
```
App: http://localhost:3000 - API: http://localhost:8000/api/health/

## Tests
```bash
cd backend
python -m unittest core.tests.test_services   # business-logic + ML tests (no DB needed)
python manage.py test                          # full suite incl. API integration tests
```

## Repository layout
```
backend/   Django project (config/), app core/ (models, views, urls, services/, tests/)
  core/services/  market.py payments.py fx.py ml.py   <- all business logic & ML
frontend/  React app (src/pages/*)
docs/      API.md  UML.md  DATABASE.md + schema.sql  TEST_REPORT.md  USER_MANUAL.md  DEPLOYMENT.md
docker-compose.yml  render.yaml
```

## Important notes
* Market data (rates, volatility, interest rates, country risk, provider fees) is **simulated** so the system works offline. It is isolated in `core/services/market.py` and `payments.py`; replace with a live feed for production.
* FX history is synthetic; ML direction accuracy near the naive baseline is expected and is reported honestly in the UI.
* Change `SECRET_KEY` and set `DEBUG=0` for any real deployment.


(.venv) PS C:\MY PROJECTS\fxpay\frontend> npm run dev

backend/db.sqlite3        # in the explorer to see database

.venv\Scripts\Activate.ps1
python manage.py runserver 8000          #
