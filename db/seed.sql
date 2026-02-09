\c APP_DB

CREATE TABLE IF NOT EXISTS ACCOUNTS (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    account_type VARCHAR(50) NOT NULL,
    currency VARCHAR(3) NOT NULL
);

CREATE TABLE IF NOT EXISTS ASSET_TYPES (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    code VARCHAR(20) NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS LOG (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    type VARCHAR(10) NOT NULL,
    message TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS PORTFOLIOS (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    taxable BOOLEAN NOT NULL DEFAULT TRUE
);

INSERT INTO PORTFOLIOS (name, taxable) VALUES
('General', TRUE),
('IKE', FALSE),
('IKZE', FALSE),
('Brokerage', TRUE);

CREATE TABLE IF NOT EXISTS STG_ASSET_DATA (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    isin VARCHAR(20) NOT NULL,
    ticker varchar(20) NOT NULL,
    asset_type_code VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    value NUMERIC(20, 4) NOT NULL,
    currency VARCHAR(3) NOT NULL
);

CREATE TABLE IF NOT EXISTS STG_TRANSACTION_DATA (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 --   asset_isin VARCHAR(20),
 --   asset_name VARCHAR(100) NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    transaction_type_code VARCHAR(3) NOT NULL,
    units NUMERIC(20, 4) NOT NULL,
    unit_price NUMERIC(20, 4) NOT NULL,
    total_amount NUMERIC(20, 4) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    fee NUMERIC(20, 4) NOT NULL DEFAULT 0,
    total_with_fee NUMERIC(20, 4) NOT NULL,
    tax_amount NUMERIC(20, 4) NOT NULL DEFAULT 0,
    portfolio_name VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS TRANSACTION_TYPES (
    code VARCHAR(3) PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS ASSETS (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    isin VARCHAR(20) NOT NULL UNIQUE,
    ticker varchar(20) NOT NULL UNIQUE,
    asset_type INTEGER NOT NULL,
    constraint fk_asset_type FOREIGN KEY (asset_type) REFERENCES ASSET_TYPES(id)
);

CREATE TABLE IF NOT EXISTS ASSET_VALUATIONS (
    id SERIAL PRIMARY KEY,
    asset_id INTEGER NOT NULL,
    date DATE NOT NULL,
    value NUMERIC(20, 4) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    constraint fk_asset FOREIGN KEY (asset_id) REFERENCES ASSETS(id)
);

CREATE TABLE IF NOT EXISTS TRANSACTIONS (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    description TEXT NOT NULL,
    transaction_type VARCHAR(3) NOT NULL,
    asset_id INTEGER NOT NULL,
    units NUMERIC(20, 4) NOT NULL,
    amount NUMERIC(20, 4) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    portfolio_id INTEGER NOT NULL,
    fee NUMERIC(20, 4) NOT NULL DEFAULT 0,
    tax_amount NUMERIC(20, 4) NOT NULL DEFAULT 0,
    constraint fk_portfolio FOREIGN KEY (portfolio_id) REFERENCES PORTFOLIOS(id),
    constraint fk_asset FOREIGN KEY (asset_id) REFERENCES ASSETS(id),
    constraint fk_transaction_type FOREIGN KEY (transaction_type) REFERENCES TRANSACTION_TYPES(code)
);

CREATE TABLE IF NOT EXISTS BOOKINGS (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    transaction_id INTEGER NOT NULL,
    debit_account_id INTEGER NOT NULL,
    credit_account_id INTEGER NOT NULL,
    amount NUMERIC(20, 4) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    constraint fk_transaction FOREIGN KEY (transaction_id) REFERENCES TRANSACTIONS(id),
    constraint fk_debit_account FOREIGN KEY (debit_account_id) REFERENCES ACCOUNTS(id),
    constraint fk_credit_account FOREIGN KEY (credit_account_id) REFERENCES ACCOUNTS(id)
);

CREATE TABLE IF NOT EXISTS PORTFOLIO_VALUATIONS (
    id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL,
    date DATE NOT NULL,
    total_value NUMERIC(20, 4) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    constraint fk_portfolio FOREIGN KEY (portfolio_id) REFERENCES PORTFOLIOS(id)
);