import app.db as db
from flask import (Blueprint, render_template)


bp = Blueprint('portfolio', __name__)

@bp.route('/', methods=['GET'])
def index():
    query = "SELECT a.name as asset_name, po.name as portfolio_name, p.quantity, p.currency, " \
    "p.avg_buy_price, p.total_cost, p.total_fee, p.total_tax, p.current_price, " \
    "p.current_holding_value, p.current_unrealized_gain, p.realized_gain, " \
    "p.total_dividend, p.dividend_tax, p.total_interest, p.interest_tax, " \
    "p.total_gain, p.all_tax, p.total_gained_value " \
    "FROM portfolio_summary p " \
    "INNER JOIN asset a " \
    "ON p.asset_id = a.id " \
    "INNER JOIN portfolio po " \
    "ON p.portfolio_id = po.id " \
    "ORDER BY po.name, a.name;"

    positions = db.select_query(query, dict=True, fetchall=True)
    return render_template('index.html', positions=positions)

@bp.route('/dashboard', methods=['GET'])
def dashboard():
    return render_template('dashboard.html')

@bp.route('/historical_valuation', methods=['GET'])
def historical_valuation():
    return render_template('portfolio_valuation.html')