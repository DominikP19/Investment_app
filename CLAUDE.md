# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Personal investment tracking app: Flask + psycopg frontend over a PostgreSQL database that contains most of the business logic (PL/pgSQL triggers and views). Runs entirely via Docker Compose. The README mentions FastAPI as the original plan, but the actual stack is Flask.

## Commands

Everything runs through Docker Compose (requires a `.env` file in the repo root with `POSTGRES_USER`, `POSTGRES_PW`, `POSTGRES_DB`, `DB_HOST`, `PGADMIN_MAIL`, `PGADMIN_PW`):

```sh
docker compose up --build        # build and run everything
docker compose up --build app    # rebuild just the Flask app
docker compose down -v           # tear down INCLUDING the db volume (destroys data)
```

- App: http://localhost:8000 (Flask dev server with `--debug`)
- pgAdmin: http://localhost:5050
- Postgres: localhost:5432

App code is `COPY`'d into the image (no bind mount), so Python/template changes require rebuilding the `app` container despite debug mode.

The database schema is seeded only on first creation of the `db_data` volume (`db/*.sql` are copied to `/docker-entrypoint-initdb.d/`). **Any change to `db/01_table_seed.sql` or `db/02_trigger_seed.sql` requires recreating the volume** (`docker compose down -v`) or applying the SQL manually via pgAdmin/psql.

Tests run locally with pytest (no Docker/Postgres needed — DB access is monkeypatched, see `tests/conftest.py`):

```sh
pip install -r requirements-dev.txt   # app deps + pytest
python -m pytest                      # run all tests
python -m pytest tests/test_parser.py::TestAssetParseCsv::test_valid_file  # single test
```

`pytest.ini` sets `pythonpath = src` so the `app` package imports without installation, and `testpaths = tests` (note: `src/app/test.py` is a debug blueprint at `/test/read`, not a test file). There is no linter configured.

## Architecture

### Business logic lives in PostgreSQL, not Python

The Flask layer (`src/app/`) is thin CRUD: it renders templates, validates forms, and runs INSERT/SELECT statements. The financial logic is implemented in `db/02_trigger_seed.sql`:

- **`trg_calc_transaction`** (BEFORE INSERT/UPDATE on `TRANSACTION`): computes `total_amount`, dividend/interest tax, and for sells: validates the position is large enough (raises an exception otherwise), computes realized gain (`transaction_result`) and capital-gains tax using FIFO cost basis from `TRANSACTION_LOT`.
- **`trg_calc_transaction_lot`** (AFTER INSERT/UPDATE on `TRANSACTION`): maintains `TRANSACTION_LOT` (FIFO tax lots) — buys create lots, sells consume/split them.
- **CSV import flow**: Python parses CSVs (`parser.py`) and inserts into staging tables `STG_ASSET_DATA` / `STG_TRANSACTION_DATA`; staging triggers validate (raising exceptions for unknown assets/types/portfolios) and then create the real `ASSET`/`ASSET_VALUATION`/`TRANSACTION` rows — which in turn fire the transaction triggers above.
- **Views**: `POSITION` aggregates transactions + lots + latest `ASSET_VALUATION` + latest `EXCHANGE_RATE` (converted to PLN) into per-asset-per-portfolio positions with gains/taxes; `PORTFOLIO_SUMMARY` filters it to `quantity > 0` and is what the main page displays.

Consequence: when changing how amounts/taxes/lots are computed, the change belongs in the SQL triggers/views, and existing rows are NOT retroactively recalculated.

### Flask app structure (`src/app/`)

- `__init__.py` — app factory (`create_app`), registers blueprints, defines the `money` Jinja filter.
- `db.py` — psycopg connection per request (`g.db`, torn down on app context teardown), `select_query()` helper (positional `dict`/`fetchall` flags), staging-table import helpers. Errors surface to the UI via `flash()` rather than raising.
- `portfolio.py` — blueprint at `/`: portfolio summary index, `/dashboard`, `/historical_valuation` (Plotly line chart + button that snapshots current `PORTFOLIO_SUMMARY` into `PORTFOLIO_VALUATION`; unique on portfolio+date, so once per day).
- `data_import.py` — blueprint at `/import`: manual add/edit/delete and CSV import for assets and transactions.
- `forms.py` — Flask-WTF forms; SelectField choices are populated from DB lookup tables at request time.
- `parser.py` — CSV parsing/validation; defines the exact expected column sets and `%Y-%m-%d` date format.
- `log.py` — placeholder, not implemented (DB `LOG` table exists but is unused).
- Plotly charts are serialized with `plotly.io.to_json` and rendered client-side in templates.

### Data conventions

- Money uses the `FINANCIAL` domain (`NUMERIC(20,4)`); use `decimal.Decimal` on the Python side.
- Base currency is PLN; foreign-currency positions are converted via the latest `EXCHANGE_RATE` row to PLN.
- Transaction types are 3-letter codes: `BUY`, `SEL`, `DIV`, `INT`, `FEE`, `TAX`, `TRT`, `TRF`. DIV/INT transactions carry their amount in `price` with `quantity = 0`.
- Imported transaction CSVs must be sorted oldest-to-newest (FIFO lot tracking depends on insert order).
- Portfolios model Polish account types (IKE/IKZE are tax-free, tax rate via `TAX_RATE`).
- `data/` is gitignored and holds real personal CSV extracts — don't commit it.
