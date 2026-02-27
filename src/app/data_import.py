import app.db as db
import csv
from flask import Blueprint


bp = Blueprint('data_import', __name__, url_prefix='/import')

@bp.route('/assets_csv', methods=['POST'])
def import_assets_csv():
    pass

@bp.route('/transactions_csv', methods=['POST'])
def import_transactions_csv():
    pass

@bp.route('/assets_manual', methods=['POST'])
def import_assets_manual():
    pass

@bp.route('/transactions_manual', methods=['POST'])
def import_transactions_manual():
    pass