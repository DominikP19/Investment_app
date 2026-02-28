import app.db as db
import csv
from flask import (Blueprint, render_template)


bp = Blueprint('data_import', __name__, url_prefix='/import')

@bp.route('/import_csv', methods=['GET', 'POST'])
def import_csv():
    return render_template('import_csv.html')

@bp.route('/asset_manual', methods=['GET', 'POST'])
def import_asset_manual():
    return render_template('add_asset.html')

@bp.route('/transaction_manual', methods=['GET', 'POST'])
def import_transaction_manual():
    return render_template('add_transaction.html')