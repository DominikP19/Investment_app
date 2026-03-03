import app.db as db
from app.forms import AssetFormAdd, AssetFormEdit
import csv
from flask import Blueprint, g, render_template, request, redirect, url_for, flash

bp = Blueprint('data_import', __name__, url_prefix='/import')

def get_asset_types():
    con = db.get_db()
    error = None
    result = None
    try:
        result = con.execute('SELECT id, code FROM asset_type;').fetchall()
    except Exception as e:
        #todo: add logging
        error = f'Failed to fetch asset types: {str(e)}'

    flash(error)
    return result

def get_asset(id):
    con = db.get_db()
    error = None
    result = None
    try:
        result = con.execute('SELECT id, name, isin, ticker, asset_type_id FROM asset WHERE id = %s;', (id,)).fetchone()
    except Exception as e:
        #todo: add logging
        error = f'Failed to fetch asset: {str(e)}'

    flash(error)
    return result

@bp.route('/import_csv', methods=['GET', 'POST'])
def import_csv():
    return render_template('import_csv.html')

@bp.route('/asset_manual', methods=['GET', 'POST'])
def import_asset_manual():
    error = None
    form = AssetFormAdd()
    form.asset_type.choices = get_asset_types()
    if form.validate_on_submit():
        con = db.get_db()
        name = form.name.data
        isin = form.isin.data
        ticker = form.ticker.data
        asset_type = form.asset_type.data
        try:
            con.execute(
            "INSERT INTO ASSET (name, isin, ticker, asset_type_id) VALUES (%s, %s, %s, %s)",
            (name, isin, ticker, asset_type)
            )
            con.commit()
        except Exception as e:
            error = f"ASSET insert failed: {str(e)}"

        return redirect(url_for('data_import.asset_list'))

    flash(error)

    return render_template('asset_add.html', form=form)

@bp.route('/asset_list', methods=['GET'])
def asset_list():
    con = db.get_db()
    error = None
    try:
        #change to row_facotry to have dict and better template definition
        assets = con.execute('SELECT a.id, a.name, a.isin, a.ticker, at.name as asset_type FROM asset a \
                            INNER JOIN asset_type at ON at.id = a.asset_type_id;').fetchall()
    except Exception as e:
        error = f'Failed to fetch assets: {str(e)}'

    flash(error)

    return render_template('asset_list.html', assets=assets)

@bp.route('/asset_edit/<int:id>', methods=['GET', 'POST'])
def asset_edit(id):
    error = None
    asset = get_asset(id)
    form = AssetFormEdit()
    if request.method == 'GET':
        form.name.data = asset[1]
        form.isin.data = asset[2]
        form.ticker.data = asset[3]

    form.asset_type.choices = get_asset_types()

    if form.validate_on_submit():
        con = db.get_db()
        name = form.name.data
        isin = form.isin.data
        ticker = form.ticker.data
        asset_type = form.asset_type.data
        try:
            con.execute(
            "UPDATE ASSET SET name=%s, isin=%s, ticker=%s, asset_type_id=%s WHERE id=%s",
            (name, isin, ticker, asset_type, id)
            )
            con.commit()
        except Exception as e:
            error = f"ASSET update failed: {str(e)}"

        return redirect(url_for('data_import.asset_list'))
    
    flash(error)
    flash(id)
    
    return render_template('asset_edit.html', form=form, id=id)

@bp.route('/asset_delete/<int:id>', methods=['POST'])
def asset_delete(id):
    con = db.get_db()
    error = None
    try:
        con.execute("DELETE FROM ASSET WHERE id=%s", (id,))
        con.commit()
    except Exception as e:
        error = f"ASSET delete failed: {str(e)}"

    flash(error)

    return redirect(url_for('data_import.asset_list'))

@bp.route('/transaction_manual', methods=['GET', 'POST'])
def import_transaction_manual():
    return render_template('transaction_add.html')

@bp.route('/transaction_list', methods=['GET'])
def transaction_list():
    return render_template('transaction_list.html')

@bp.route('/transaction_edit/<int:id>', methods=['GET', 'POST'])
def transaction_edit(id):
    return render_template('edit_transaction.html', id=id)

@bp.route('/transaction_delete/<int:id>', methods=['POST'])
def transaction_delete(id):
    con = db.get_db()
    error = None
    try:
        con.execute("DELETE FROM TRANSACTION WHERE id=%s", (id,))
        con.commit()
    except Exception as e:
        error = f"TRANSACTION delete failed: {str(e)}"

    flash(error)

    return redirect(url_for('data_import.transaction_list'))