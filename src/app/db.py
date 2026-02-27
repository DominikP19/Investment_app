import psycopg

from flask import current_app, g

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

def init_app(app):
    app.teardown_appcontext(close_db)