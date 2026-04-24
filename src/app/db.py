import psycopg
from psycopg.rows import dict_row

from flask import current_app, g, flash

def get_db():
    if 'db' not in g:
        g.db = psycopg.connect(
            dbname=current_app.config['POSTGRES_DB'],
            user=current_app.config['POSTGRES_USER'],
            password=current_app.config['POSTGRES_PASSWORD'],
            host=current_app.config['DB_HOST'],
            port="5432"
        )
    return g.db

def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()

def import_assets(rows: list[dict]) -> tuple[int,int]:
    inserted, skipped = 0, 0
    with get_db() as con:
        with con.cursor() as cur:
            for row in rows:
                try:
                    con.execute('INSERT INTO STG_ASSET_DATA \
                            (name, isin, ticker, asset_type_code, \
                            date, price, currency) \
                            VALUES (%(name)s, %(isin)s, %(ticker)s, \
                            %(asset_type_code)s, %(date)s, \
                            %(price)s, %(currency)s ) ON CONFLICT \
                            (name, isin, date, price, currency) \
                            DO NOTHING', row)
                    if cur.rowcount:
                        inserted += 1
                    else:
                        skipped += 1
                except Exception as e:
                    flash(f"Error during insert {str(e)}")
    return inserted,skipped

def import_transactions(rows: list[dict]) -> tuple[int,int]:
    inserted, skipped = 0, 0
    with get_db() as con:
        with con.cursor() as cur:
            for row in rows:
                try:
                    con.execute('INSERT INTO STG_TRANSACTION_DATA \
                                (date, asset_name, ticker, \
                                 transaction_type_code, quantity,  \
                                 currency, price, total_amount, fee,  \
                                 total_with_fee, tax_amount, \
                                 portfolio_name) \
                                 VALUES (%(date)s, %(asset_name)s,  \
                                 %(ticker)s, %(transaction_type_code)s,  \
                                 %(quantity)s, %(currency)s, %(price)s,  \
                                 %(total_amount)s, %(fee)s,  \
                                 %(total_with_fee)s, %(tax_amount)s, \
                                 %(portfolio_name)s )', row
                                )
                    if cur.rowcount:
                        inserted += 1
                    else:
                        skipped += 1
                except Exception as e:
                    flash(f"Error during insert {str(e)}")
    return inserted,skipped


def select_query(query: str, dict: bool = False, fetchall:bool = False, *params: int | str) -> dict | list:
    conn = get_db()
    result = None
    result_dict = None
    if dict:
        cur = conn.cursor(row_factory=dict_row)
        try:
            result_dict = cur.execute(query, params).fetchall() if fetchall else cur.execute(query, params).fetchone()
        except Exception as e:
            error = f'Failed to execute query: {str(e)}'
    else:       
        try:
            result = conn.execute(query, params).fetchall() if fetchall else conn.execute(query, params).fetchone()
        except Exception as e:
            flash(f'Failed to execute query: {str(e)}')

    return result_dict if dict else result

def init_app(app):
    app.teardown_appcontext(close_db)