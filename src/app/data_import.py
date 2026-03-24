import app.db as db
import app.parser as parser
from psycopg.rows import dict_row
from app.forms import AssetFormAdd, AssetFormEdit, TransactionFormAdd, TransactionFormEdit, AssetFileImport, TransactionFileImport
import decimal
from flask import Blueprint, g, render_template, request, redirect, url_for, flash

bp = Blueprint('data_import', __name__, url_prefix='/import')

def select_query(query, dict=False, fetchall=False, *params):
    conn = db.get_db()
    error = None
    result = None
    result_dict = None
    if dict:
        cur = conn.cursor(row_factory=dict_row)
        try:
            result_dict = cur.execute(query, params).fetchall() if fetchall else cur.execute(query, params).fetchone()
        except Exception as e:
            error = f'Failed to execute query: {str(e)}'
    else:       
        try:
            result = conn.execute(query, params).fetchall() if fetchall else conn.execute(query, params).fetchone()
        except Exception as e:
            error = f'Failed to execute query: {str(e)}'

    if error:   
        flash(error)

    return result_dict if dict else result

@bp.route('/asset_manual', methods=['GET', 'POST'])
def import_asset_manual():
    error = None
    query = "SELECT id, code FROM asset_type;"
    form = AssetFormAdd()
    form.asset_type.choices = select_query(query, dict=False, fetchall=True)
    if form.validate_on_submit():
        con = db.get_db()
        name = form.name.data
        isin = form.isin.data
        ticker = form.ticker.data
        asset_type = form.asset_type.data
        currency = form.currency.data
        try:
            con.execute(
            "INSERT INTO ASSET (name, isin, ticker, asset_type_id, currency) VALUES (%s, %s, %s, %s, %s)",
            (name, isin, ticker, asset_type, currency)
            )
            con.commit()
        except Exception as e:
            error = f"ASSET insert failed: {str(e)}"

        return redirect(url_for('data_import.asset_list'))

    flash(error)

    return render_template('asset_add.html', form=form)

@bp.route('/asset_list', methods=['GET'])
def asset_list():
    query = "SELECT a.id, a.name, a.isin, a.ticker, at.name as asset_type, a.currency FROM asset a " \
                            "INNER JOIN asset_type at ON at.id = a.asset_type_id;"
    
    assets = select_query(query, dict=True, fetchall=True)

    return render_template('asset_list.html', assets=assets)

@bp.route('/asset_edit/<int:id>', methods=['GET', 'POST'])
def asset_edit(id):
    error = None
    query_asset = "SELECT id, name, isin, ticker, asset_type_id, currency " \
        "FROM asset WHERE id = %s;"
    asset = select_query(query_asset, True, False, id)
    form = AssetFormEdit()
    if request.method == 'GET':
        form.name.data = asset['name']
        form.isin.data = asset['isin']
        form.ticker.data = asset['ticker']
        form.currency.data = asset['currency']

    query_asset_type = "SELECT id, code FROM asset_type;"
    form.asset_type.choices = select_query(query_asset_type, dict=False, fetchall=True)

    if form.validate_on_submit():
        con = db.get_db()
        name = form.name.data
        isin = form.isin.data
        ticker = form.ticker.data
        asset_type = form.asset_type.data
        currency = form.currency.data
        try:
            con.execute(
            "UPDATE ASSET SET name=%s, isin=%s, ticker=%s, asset_type_id=%s," \
            " currency=%s WHERE id=%s",
            (name, isin, ticker, asset_type, currency, id)
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
    error = None
    query_asset = "SELECT id, name FROM asset;"
    query_portfolio = "SELECT id, name FROM portfolio;"
    query_transaction_type = "SELECT id, code FROM transaction_type;"
    form = TransactionFormAdd()
    form.asset.choices = select_query(query_asset, dict=False, fetchall=True)
    form.portfolio.choices = select_query(query_portfolio, dict=False, fetchall=True)
    form.transaction_type.choices = select_query(query_transaction_type, dict=False, fetchall=True)

    if form.validate_on_submit():
        con = db.get_db()
        date = form.date.data
        description = form.description.data
        transaction_type = form.transaction_type.data
        asset = form.asset.data
        quantity = form.quantity.data
        price = decimal.Decimal(form.price.data)
        currency = form.currency.data
        fee = decimal.Decimal(form.fee.data)
        portfolio = form.portfolio.data

        try:
            con.execute(
                "INSERT INTO TRANSACTION (date, description, transaction_type_id, " \
                "asset_id, quantity, price, currency, fee, portfolio_id) " \
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (date, description, transaction_type, asset, quantity, 
                 price, currency, fee, portfolio)
            )
            con.commit()
        except Exception as e:
            error = f"TRANSACTION insert failed: {str(e)}"

        return redirect(url_for('data_import.transaction_list'))

    flash(error)

    return render_template('transaction_add.html', form=form)

@bp.route('/transaction_list', methods=['GET'])
def transaction_list():
    query = "SELECT t.id, t.date, t.description, tt.code as transaction_type, " \
    "a.name as asset, t.quantity, t.currency, t.price, t.total_amount, t.fee, " \
    "t.tax_amount, p.name as portfolio " \
    "FROM TRANSACTION t " \
    "JOIN transaction_type tt " \
    "ON t.transaction_type_id = tt.id " \
    "JOIN asset a " \
    "ON t.asset_id = a.id " \
    "JOIN portfolio p " \
    "ON t.portfolio_id = p.id;"

    transactions = select_query(query, dict=True, fetchall=True)

    return render_template('transaction_list.html', transactions=transactions)

@bp.route('/transaction_edit/<int:id>', methods=['GET', 'POST'])
def transaction_edit(id):
    error = None
    query_transaction = "SELECT id, date, description, transaction_type_id, " \
    "asset_id, quantity, price, total_amount, currency, fee, tax_amount, " \
    "portfolio_id " \
    "FROM TRANSACTION WHERE id=%s"
    transaction = select_query(query_transaction, True, False, id)
    form = TransactionFormEdit()
    if request.method == 'GET':
        form.date.data = transaction['date']
        form.description.data = transaction['description']
        form.transaction_type.data = transaction['transaction_type_id']
        form.asset.data = transaction['asset_id']
        form.quantity.data = transaction['quantity']
        form.currency.data = transaction['currency']
        form.price.data = transaction['price']
        form.fee.data = transaction['fee']
        form.portfolio.data = transaction['portfolio_id']

    query_asset = "SELECT id, name FROM asset;"
    query_portfolio = "SELECT id, name FROM portfolio;"
    query_transaction_type = "SELECT id, code FROM transaction_type;"
    form.asset.choices = select_query(query_asset, dict=False, fetchall=True)
    form.portfolio.choices = select_query(query_portfolio, dict=False, fetchall=True)
    form.transaction_type.choices = select_query(query_transaction_type, dict=False, fetchall=True)

    if form.validate_on_submit():
        con = db.get_db()
        date = form.date.data
        description = form.description.data
        transaction_type = form.transaction_type.data
        asset = form.asset.data
        quantity = form.quantity.data
        price = decimal.Decimal(form.price.data)
        currency = form.currency.data
        fee = decimal.Decimal(form.fee.data)
        portfolio = form.portfolio.data

        try:
            con.execute(
                "UPDATE TRANSACTION SET date=%s, description=%s, transaction_type_id=%s, " \
                "asset_id=%s, quantity=%s, price=%s, currency=%s, fee=%s, " \
                "portfolio_id=%s WHERE id=%s",
                (date, description, transaction_type, asset, quantity,
                 price, currency, fee, portfolio, id)
            )
            con.commit()
        except Exception as e:
            error = f"TRANSACTION update failed: {str(e)}"

        return redirect(url_for('data_import.transaction_list'))

    flash(error)

    return render_template('transaction_edit.html', form=form, id=id)

@bp.route('/transaction_delete/<int:id>', methods=['POST'])
def transaction_delete(id):
    con = db.get_db()
    try:
        con.execute("DELETE FROM TRANSACTION WHERE id=%s", (id,))
        con.commit()
    except Exception as e:
        flash(f"TRANSACTION delete failed: {str(e)}")

    return redirect(url_for('data_import.transaction_list'))

@bp.route('/asset_import', methods=['GET', 'POST'])
def asset_import():
    form = AssetFileImport()

    if form.validate_on_submit():
        file = form.file.data

        try:
            data = parser.asset_parse_csv(file.read)
            inserted, skipped = db.insert_assets(data)
            flash(f"Asset file processed - {inserted} inserted, {skipped} skipped")
        except Exception as e:
            flash(f"Asset file processing failed: {str(e)}")
        
        return redirect(url_for('data_import.asset_list'))
    
    return render_template('asset_import.html', form=form)
    
@bp.route('/transaction_import', methods=['GET', 'POST'])
def transaction_import():
    form = TransactionFileImport()

    if form.validate_on_submit():
        file = form.file.data

        try:
            data = parser.transaction_parse_csv(file.read)
            inserted, skipped = db.insert_transactions(data)
            flash(f"Transaction file processed - {inserted} inserted, {skipped} skipped")
        except Exception as e:
            flash(f"Transaction file processing failed: {str(e)}")
               
        return redirect(url_for('data_import.transaction_list'))
    
    return render_template('transaction_import.html', form=form)
  