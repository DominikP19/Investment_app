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
    totals = {
        'total_cost': sum(filter(None, (p['total_cost'] for p in positions))),
        'total_fee': sum(filter(None, (p['total_fee'] for p in positions))),
        'total_tax': sum(filter(None, (p['total_tax'] for p in positions))),
        'current_holding_value': sum(filter(None, (p['current_holding_value'] for p in positions))),
        'current_unrealized_gain': sum(filter(None, (p['current_unrealized_gain'] for p in positions))),
        'realized_gain': sum(filter(None, (p['realized_gain'] for p in positions))),
        'total_dividend': sum(filter(None, (p['total_dividend'] for p in positions))),
        'dividend_tax': sum(filter(None, (p['dividend_tax'] for p in positions))),
        'total_interest': sum(filter(None, (p['total_interest'] for p in positions))),
        'interest_tax': sum(filter(None, (p['interest_tax'] for p in positions))),
        'total_gain': sum(filter(None, (p['total_gain'] for p in positions))),
        'all_tax': sum(filter(None, (p['all_tax'] for p in positions))),
        'total_gained_value': sum(filter(None, (p['total_gained_value'] for p in positions)))
    }
    return render_template('index.html', positions=positions, totals=totals)

@bp.route('/dashboard', methods=['GET'])
def dashboard():
    return render_template('dashboard.html')

@bp.route('/historical_valuation', methods=['GET'])
def historical_valuation():
    return render_template('portfolio_valuation.html')