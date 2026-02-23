import psycopg

from flask import current_app, g

def get_db():
    if 'db' not in g:
        g.db = psycopg.connect(
            user=current_app.config['POSTGRES_USER'],
            password=current_app.config['POSTGRES_PASSWORD'],
            dbname=current_app.config['POSTGRES_DB']
        )
    return g.db

def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()

def read_db(query, params=None):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(query, params)
        result = cur.fetchall()
        cur.close()
        db.close()
        return result