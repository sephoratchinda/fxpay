-- PostgreSQL schema (equivalent to Django migrations; Django creates it automatically)
CREATE TABLE auth_user (id BIGSERIAL PRIMARY KEY, username VARCHAR(150) UNIQUE NOT NULL, email VARCHAR(254), password VARCHAR(128) NOT NULL,
  is_staff BOOLEAN DEFAULT FALSE, date_joined TIMESTAMPTZ DEFAULT now());

CREATE TABLE core_transaction (
  id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
  channel VARCHAR(30) NOT NULL, from_ccy CHAR(3) NOT NULL, to_ccy CHAR(3) NOT NULL,
  amount NUMERIC(18,2) NOT NULL CHECK (amount > 0), exchange_rate NUMERIC(18,6) NOT NULL,
  fee_total NUMERIC(18,2) NOT NULL, fx_cost NUMERIC(18,2) NOT NULL, received_amount NUMERIC(18,2) NOT NULL,
  expected_days DOUBLE PRECISION DEFAULT 1, status VARCHAR(12) DEFAULT 'PROCESSING', risk_level VARCHAR(6) DEFAULT 'Low',
  recipient_name VARCHAR(120), steps JSONB DEFAULT '[]', created_at TIMESTAMPTZ DEFAULT now());
CREATE INDEX ON core_transaction (user_id, created_at DESC);

CREATE TABLE core_exposureposition (
  id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
  currency CHAR(3) NOT NULL, amount NUMERIC(18,2) NOT NULL, direction VARCHAR(10) NOT NULL CHECK (direction IN ('RECEIVABLE','PAYABLE')),
  due_days INT DEFAULT 30, description VARCHAR(200), created_at TIMESTAMPTZ DEFAULT now());

CREATE TABLE core_forwardcontract (
  id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
  base_ccy CHAR(3) NOT NULL, quote_ccy CHAR(3) NOT NULL, amount NUMERIC(18,2) NOT NULL, direction VARCHAR(4) NOT NULL,
  spot_rate NUMERIC(18,6) NOT NULL, forward_rate NUMERIC(18,6) NOT NULL, tenor_days INT NOT NULL, created_at TIMESTAMPTZ DEFAULT now());

CREATE TABLE core_airecommendation (
  id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
  request JSONB NOT NULL, response JSONB NOT NULL, risk_level VARCHAR(6) NOT NULL, created_at TIMESTAMPTZ DEFAULT now());
