import app.db as db
from flask import (Blueprint, jsonify)

bp = Blueprint('test', __name__, url_prefix='/test')

@bp.route('/read', methods=['GET'])
def read():
    query = f'select * from account_types;'
    database = db.get_db()
    try:
        result = database.execute(query).fetchall()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    