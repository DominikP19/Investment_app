import app.db as db
import plotly
import plotly.graph_objects as go
from decimal import Decimal
from plotly.subplots import make_subplots
from flask import Blueprint, flash, redirect, render_template, url_for
from app.forms import ValuationForm


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

def aggregate_by_asset(positions: list[dict]) -> dict:
    aggregated = {}
    for pos in positions:
        entry = aggregated.setdefault(pos['asset_name'],
                                      {'value': Decimal(0), 'gain': Decimal(0)})
        entry['value'] += pos['current_holding_value']
        if pos['current_unrealized_gain'] is not None:
            entry['gain'] += pos['current_unrealized_gain']
    return aggregated

@bp.route('/dashboard', methods=['GET'])
def dashboard():
    # POSITION instead of PORTFOLIO_SUMMARY so closed positions still
    # contribute their realized gains, dividends and fees
    totals_query = "SELECT sum(total_dividend) as total_dividend, " \
    "sum(total_interest) as total_interest, sum(total_fee) as total_fee, " \
    "sum(realized_gain) as realized_gain, " \
    "sum(current_unrealized_gain) as unrealized_gain " \
    "FROM position;"

    totals = db.select_query(totals_query, dict=True, fetchall=False)

    positions_query = "SELECT a.name as asset_name, po.name as portfolio_name, " \
    "at.code as asset_type_code, p.current_holding_value, " \
    "p.current_unrealized_gain " \
    "FROM portfolio_summary p " \
    "INNER JOIN asset a ON p.asset_id = a.id " \
    "INNER JOIN asset_type at ON a.asset_type_id = at.id " \
    "INNER JOIN portfolio po ON p.portfolio_id = po.id " \
    "ORDER BY p.current_holding_value DESC NULLS LAST;"

    positions = db.select_query(positions_query, dict=True, fetchall=True)
    valued = [p for p in positions if p['current_holding_value'] is not None]

    all_breakdown = aggregate_by_asset(valued)
    stock_breakdown = aggregate_by_asset(
        [p for p in valued if p['asset_type_code'] == 'STOCK'])

    pie_fig = make_subplots(
        rows=1, cols=2,
        specs=[[{'type': 'domain'}, {'type': 'domain'}]],
        subplot_titles=('All Positions', 'Stocks Only'))
    pie_fig.add_trace(go.Pie(
        labels=list(all_breakdown.keys()),
        values=[entry['value'] for entry in all_breakdown.values()],
        name='All Positions'), row=1, col=1)
    pie_fig.add_trace(go.Pie(
        labels=list(stock_breakdown.keys()),
        values=[entry['value'] for entry in stock_breakdown.values()],
        name='Stocks Only'), row=1, col=2)
    pie_fig.update_layout(
        title='Portfolio Breakdown',
        template='plotly_white',
        height=450
    )

    assets = sorted(all_breakdown.items(),
                    key=lambda item: item[1]['value'], reverse=True)
    bar_fig = go.Figure(go.Bar(
        x=[entry['value'] for _, entry in assets],
        y=[name for name, _ in assets],
        orientation='h',
        marker_color=['#2e7d32' if entry['gain'] >= 0 else '#c62828'
                      for _, entry in assets],
        text=[f"{entry['gain']:+,.2f}" for _, entry in assets],
        textposition='auto'
    ))
    bar_fig.update_layout(
        title='Asset Value with Unrealized Gain/Loss',
        xaxis_title='Current Holding Value (PLN)',
        template='plotly_white',
        height=max(450, 40 * len(assets) + 150),
        # most valuable asset on top
        yaxis=dict(autorange='reversed')
    )

    return render_template('dashboard.html', totals=totals,
                           pie_plot=plotly.io.to_json(pie_fig),
                           bar_plot=plotly.io.to_json(bar_fig))

@bp.route('/historical_valuation', methods=['GET', 'POST'])
def historical_valuation():
    form = ValuationForm()

    query = "SELECT date,  sum(total_value) as total_value, sum(total_cost) as total_cost " \
    "FROM PORTFOLIO_VALUATION GROUP BY date ORDER BY date ASC;"

    rows = db.select_query(query, dict=True, fetchall=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[row['date'] for row in rows], 
        y=[row['total_value'] for row in rows], 
        mode='lines+markers', 
        name='Total Value'))
    
    fig.add_trace(go.Scatter(
        x=[row['date'] for row in rows], 
        y=[row['total_cost'] for row in rows], 
        mode='lines+markers', 
        name='Total Cost'))
    
    fig.update_layout(
        title='Historical Portfolio Valuation',
        xaxis_title='Date',
        yaxis_title='Amount (PLN)',
        legend_title='Legend',
        template='plotly_white'
    )

    if form.validate_on_submit():
        con = db.get_db()
        try:
            con.execute(
                "INSERT INTO PORTFOLIO_VALUATION (portfolio_id, date, currency, " \
                "total_value, total_cost) " \
                "SELECT portfolio_id, current_date, 'PLN', " \
                "sum(current_holding_value) as total_value, " \
                "sum(total_cost) as total_cost " \
                "FROM portfolio_summary GROUP BY portfolio_id;"
            )
            con.commit()
            flash("Current valuation added successfully!", )
        except Exception as e:
            con.rollback()
            flash(f"Error during valuation insert: {e}",)

        return redirect(url_for('portfolio.historical_valuation'))

    # last 10 valuations, newest first
    valuations = rows[-10:][::-1]

    return render_template('portfolio_valuation.html', form=form,
                           plot=plotly.io.to_json(fig), valuations=valuations)