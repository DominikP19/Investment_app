import app.db as db
import csv
from flask import Blueprint


bp = Blueprint('test', __name__, url_prefix='/import')

@bp.route('/assets_csv', methotds=['POST'])
def import_assets():
    pass

@bp.route('/transactions_csv', methods=['POST'])
def import_transactions():
    pass

@bp.route('/assets_manual', methods=['POST'])
def import_assets_manual():
    pass

@bp.route('/transactions_manual', methods=['POST'])
def import_transactions_manual():
    pass