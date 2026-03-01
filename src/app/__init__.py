import os
from flask import Flask

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    
    app.config.from_mapping(
        POSTGRES_USER=os.getenv('POSTGRES_USER'),
        POSTGRES_PASSWORD=os.getenv('POSTGRES_PASSWORD'),
        POSTGRES_DB=os.getenv('POSTGRES_DB'),
        DB_HOST=os.getenv('DB_HOST'),
        SECRET_KEY='dev'
    )

    @app.route('/hello')
    def hello():
        return "Hello from the Investment App!"
    
    # Adding context teardown to close the database connection after each request
    import app.db as db
    db.init_app(app)

    import app.test as test
    app.register_blueprint(test.bp)   

    import app.data_import as data_import
    app.register_blueprint(data_import.bp)

    import app.portfolio as portfolio
    app.register_blueprint(portfolio.bp)
    app.add_url_rule('/', endpoint='index')

        
    return app
