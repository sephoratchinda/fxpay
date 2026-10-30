# Database Schema
Full DDL: [`schema.sql`](schema.sql). Django generates the same tables via migrations.

```mermaid
erDiagram
  AUTH_USER ||--o{ CORE_TRANSACTION : makes
  AUTH_USER ||--o{ CORE_EXPOSUREPOSITION : holds
  AUTH_USER ||--o{ CORE_FORWARDCONTRACT : books
  AUTH_USER ||--o{ CORE_AIRECOMMENDATION : requests
  CORE_TRANSACTION { bigint id PK  string channel  string from_ccy  string to_ccy  numeric amount  numeric exchange_rate  numeric fee_total  numeric fx_cost  numeric received_amount  float expected_days  string status  string risk_level  jsonb steps }
  CORE_EXPOSUREPOSITION { bigint id PK  string currency  numeric amount  string direction  int due_days }
  CORE_FORWARDCONTRACT { bigint id PK  string base_ccy  string quote_ccy  numeric amount  string direction  numeric spot_rate  numeric forward_rate  int tenor_days }
  CORE_AIRECOMMENDATION { bigint id PK  jsonb request  jsonb response  string risk_level }
```
Reference data (currencies, volatility, country risk, provider fee tables) lives in code (`services/market.py`, `services/payments.py`) so it is version-controlled and unit-tested.
