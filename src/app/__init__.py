import os

from flask import Flask

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    
    app.config.from_mapping(
        POSTGRES_USER=os.getenv('POSTGRES_USER'),
        POSTGRES_PASSWORD=os.getenv('POSTGRES_PASSWORD'),
        POSTGRES_DB=os.getenv('POSTGRES_DB')
    )
    # need to add permissions in Dockerfile for this to work
    #os.makedirs(app.instance_path, exist_ok=True)

    @app.route('/hello')
    def hello():
        return "Hello from the Investment App!"

    return app