import psycopg

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

def import_transaction(rows: list[dict]) -> tuple[int,int]:
    return 0,0

def init_app(app):
    app.teardown_appcontext(close_db)