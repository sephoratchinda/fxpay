# UML Diagrams (Mermaid - renders on GitHub and in VS Code with a Mermaid preview extension)

## Architecture
```mermaid
flowchart LR
  U[User browser] -->|HTTPS + JWT| FE[React SPA / nginx]
  FE -->|REST /api| API[Django REST API]
  API --> SVC[Services: market, payments, fx]
  API --> ML[ML service: scikit-learn]
  API --> DB[(PostgreSQL)]
  ML --> SVC
```

## Use case
```mermaid
flowchart LR
  A((Customer / Treasurer)) --- UC1[Register / Login]
  A --- UC2[Simulate & send payment]
  A --- UC3[Compare provider costs]
  A --- UC4[Simulate FX movements & P/L]
  A --- UC5[Manage currency exposure]
  A --- UC6[Simulate forward contract]
  A --- UC7[Get hedging recommendation]
  A --- UC8[View risk dashboard]
  A --- UC9[Get AI recommendation]
  AD((Admin)) --- UC10[Manage data via Django admin]
  UC9 -. includes .-> UC3
  UC9 -. includes .-> UC11[Predict FX movement]
  UC2 -. includes .-> UC12[Classify risk]
```

## Class diagram
```mermaid
classDiagram
  class User { +id +username +email +password }
  class Transaction { +channel +from_ccy +to_ccy +amount +exchange_rate +fee_total +fx_cost +received_amount +expected_days +status +risk_level +steps }
  class ExposurePosition { +currency +amount +direction +due_days }
  class ForwardContract { +base_ccy +quote_ccy +amount +direction +spot_rate +forward_rate +tenor_days }
  class AIRecommendation { +request +response +risk_level }
  User "1" --> "*" Transaction
  User "1" --> "*" ExposurePosition
  User "1" --> "*" ForwardContract
  User "1" --> "*" AIRecommendation
  class PaymentService { +quote() +simulate() +compare() }
  class FxService { +pnl() +rate_scenarios() +exposure_summary() +forward_simulation() +hedge_recommendation() }
  class MlService { +recommend() +classify_risk() +predict_fx() +best_timing() }
  class MarketData { +rate() +history() +simulate_paths() }
  PaymentService --> MarketData
  FxService --> MarketData
  MlService --> PaymentService
  MlService --> MarketData
```

## Sequence - send a payment
```mermaid
sequenceDiagram
  actor U as User
  participant FE as React
  participant API as Django API
  participant P as PaymentService
  participant M as MlService
  participant DB as PostgreSQL
  U->>FE: fill form, click Send
  FE->>API: POST /api/payments/ (JWT)
  API->>API: validate input
  API->>P: simulate(channel, amount, from, to)
  P-->>API: quote + workflow steps
  API->>M: classify_risk(...)
  M-->>API: Low/Medium/High
  API->>DB: INSERT transaction
  API-->>FE: 201 transaction + warnings
  FE-->>U: confirmation + timeline
```

## Sequence - AI recommendation
```mermaid
sequenceDiagram
  actor U as User
  participant API as Django API
  participant M as MlService
  U->>API: POST /api/ai/recommend/
  API->>M: recommend(amount, from, to, urgency)
  M->>M: compare providers (cost model)
  M->>M: method model predict
  M->>M: FX direction + horizon regressors
  M->>M: risk classifier predict_proba
  M-->>API: method, timing, fx_prediction, risk
  API->>API: store AIRecommendation
  API-->>U: 200 JSON
```

## Activity - payment decision
```mermaid
flowchart TD
  S([Start]) --> I[Enter amount, currencies, urgency]
  I --> V{Valid?}
  V -- no --> E[Show error] --> I
  V -- yes --> C[Compare providers]
  C --> L{Within channel limit?}
  L -- no --> X[Exclude provider]
  L -- yes --> R[Rank by cost / speed]
  X --> R
  R --> A[AI: timing + risk class]
  A --> H{High risk?}
  H -- yes --> W[Warn & suggest hedge] --> D
  H -- no --> D[Send payment]
  D --> T([Track status to COMPLETED])
```
