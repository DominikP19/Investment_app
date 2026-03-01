import app.db as db
from app.forms import AssetForm
import csv
from flask import Blueprint, g, render_template, request, redirect, url_for, flash

bp = Blueprint('data_import', __name__, url_prefix='/import')

def get_asset_types():
    con = db.get_db()
    error = None
    try:
        result = con.execute('SELECT id, code FROM asset_types;').fetchall()
    except Exception as e:
        #todo: add logging
        error = f'Failed to fetch asset types: {str(e)}'

    flash(error)
    return result

@bp.route('/import_csv', methods=['GET', 'POST'])
def import_csv():
    return render_template('import_csv.html')

@bp.route('/asset_manual', methods=['GET', 'POST'])
def import_asset_manual():
    error = None
    form = AssetForm()
    form.asset_type.choices = get_asset_types()
    if form.validate_on_submit():
        con = db.get_db()
        name = form.name.data
        isin = form.isin.data
        ticker = form.ticker.data
        asset_type = form.asset_type.data
        try:
            con.execute(
            "INSERT INTO ASSETS (name, isin, ticker, asset_type_id) VALUES (%s, %s, %s, %s)",
            (name, isin, ticker, asset_type)
            )
            con.commit()
        except Exception as e:
            error = f"ASSETS insert failed: {str(e)}"

        return redirect(url_for('data_import.asset_list'))

    flash(error)
    flash(form.asset_type.data)

    return render_template('add_asset.html', form=form)

@bp.route('/asset_list', methods=['GET'])
def asset_list():
    con = db.get_db()
    error = None
    try:
        assets = con.execute('SELECT a.name, a.isin, a.ticker, at.name as asset_type FROM assets a \
                            INNER JOIN asset_types at ON at.id = a.asset_type_id;').fetchall()
    except Exception as e:
        error = f'Failed to fetch assets: {str(e)}'
    flash(error)
    flash(assets)
    return render_template('asset_list.html', assets=assets)

@bp.route('/transaction_manual', methods=['GET', 'POST'])
def import_transaction_manual():
    return render_template('add_transaction.html')

@bp.route('/transaction_list', methods=['GET'])
def transaction_list():
    return render_template('transaction_list.html')