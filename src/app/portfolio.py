import app.db as db
import plotly
import plotly.graph_objects as go
from decimal import Decimal
from flask import Blueprint, flash, redirect, render_template, url_for
from app.forms import ValuationForm


bp = Blueprint('portfolio', __name__)

PLOT_PALETTE = ['#2563eb', '#7c3aed', '#0a8754', '#d97706',
                '#dc2626', '#0891b2', '#64748b']
DONUT_PALETTE = ['#2563eb', '#7c3aed', '#0a8754', '#d97706',
                 '#dc2626', '#0891b2', '#db2777', '#65a30d']
OTHER_COLOR = '#c7c9ce'

def plot_base_layout() -> dict:
    # shared minimal Plotly layout matching the GUI design (mockup/gui_mockup.html)
    return dict(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='-apple-system, "Segoe UI", system-ui, sans-serif',
                  size=12, color='#71717a'),
        margin=dict(l=55, r=15, t=10, b=35),
        colorway=PLOT_PALETTE,
        hoverlabel=dict(bgcolor='#1b1b1f', font=dict(color='#fff', size=12),
                        bordercolor='rgba(0,0,0,0)'),
        xaxis=dict(gridcolor='rgba(0,0,0,0)', zeroline=False, linecolor='#e7e7e9'),
        yaxis=dict(gridcolor='#f1f1f3', zeroline=False, tickformat=',.0f'),
    )

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
        if pos['realized_gain'] is not None:
            entry['gain'] += pos['realized_gain']
    return aggregated

def top_n_plus_other(breakdown: dict, n: int = 6) -> list[tuple]:
    """(name, value) pairs sorted descending, with everything beyond the
    n largest grouped into an 'Other (count)' slice."""
    items = sorted(((name, entry['value']) for name, entry in breakdown.items()),
                   key=lambda item: item[1], reverse=True)
    top, rest = items[:n], items[n:]
    if rest:
        top.append((f"Other ({len(rest)})", sum(value for _, value in rest)))
    return top

def build_donut(breakdown: dict) -> go.Figure:
    slices = top_n_plus_other(breakdown)
    total = sum(entry['value'] for entry in breakdown.values())
    colors = [OTHER_COLOR if name.startswith('Other (')
              else DONUT_PALETTE[i % len(DONUT_PALETTE)]
              for i, (name, _) in enumerate(slices)]
    fig = go.Figure(go.Pie(
        labels=[name for name, _ in slices],
        values=[value for _, value in slices],
        hole=0.62,
        sort=False,  # pre-sorted descending so Other stays last
        direction='clockwise',
        textinfo='percent',
        textposition='inside',
        insidetextorientation='horizontal',
        marker=dict(colors=colors, line=dict(color='#fff', width=2)),
        hovertemplate='%{label}: %{value:,.0f} PLN (%{percent})<extra></extra>'))
    layout = plot_base_layout()
    del layout['xaxis'], layout['yaxis']  # no cartesian axes on donuts
    layout.update(
        margin=dict(l=10, r=10, t=10, b=10),
        height=300,
        showlegend=True,
        legend=dict(orientation='v', x=1.02, y=0.5, yanchor='middle',
                    font=dict(size=12)),
        # hide percentages that would not fit inside their slice
        uniformtext=dict(minsize=11, mode='hide'),
        annotations=[dict(text=f"<b>{total:,.0f}</b><br>PLN", showarrow=False,
                          font=dict(size=15, color='#1b1b1f'))])
    fig.update_layout(**layout)
    return fig

def build_gain_bar(breakdown: dict) -> go.Figure:
    # assets with no gain/loss (cash, cars, unvalued real estate) are noise
    gains = sorted(((name, entry['gain']) for name, entry in breakdown.items()
                    if entry['gain'] != 0),
                   key=lambda item: item[1])  # ascending: biggest gain on top
    fig = go.Figure(go.Bar(
        x=[gain for _, gain in gains],
        y=[name for name, _ in gains],
        orientation='h',
        marker=dict(color=['#0a8754' if gain >= 0 else '#d3403c'
                           for _, gain in gains],
                    opacity=0.85),
        text=[f"{'+' if gain >= 0 else '−'}{abs(gain):,.0f}"
              for _, gain in gains],
        textposition='outside',
        cliponaxis=False,
        hovertemplate='%{y}: %{x:,.0f} PLN<extra></extra>'))
    layout = plot_base_layout()
    layout.update(
        margin=dict(l=95, r=70, t=10, b=35),
        bargap=0.25,
        height=max(220, len(gains) * 28 + 60))
    layout['xaxis'] = dict(gridcolor='#f1f1f3', zeroline=True,
                           zerolinecolor='#d4d4d8', tickformat=',.0f',
                           linecolor='rgba(0,0,0,0)')
    layout['yaxis'] = dict(gridcolor='rgba(0,0,0,0)', zeroline=False)
    fig.update_layout(**layout)
    return fig

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
    "p.current_unrealized_gain, p.realized_gain " \
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

    return render_template(
        'dashboard.html', totals=totals,
        donut_all_plot=plotly.io.to_json(build_donut(all_breakdown)),
        donut_stocks_plot=plotly.io.to_json(build_donut(stock_breakdown)),
        bar_plot=plotly.io.to_json(build_gain_bar(all_breakdown)))

@bp.route('/historical_valuation', methods=['GET', 'POST'])
def historical_valuation():
    form = ValuationForm()

    query = "SELECT date,  sum(total_value) as total_value, sum(total_cost) as total_cost " \
    "FROM PORTFOLIO_VALUATION GROUP BY date ORDER BY date ASC;"

    rows = db.select_query(query, dict=True, fetchall=True)

    # cost first so the value trace can fill down to it (tonexty)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[row['date'] for row in rows],
        y=[row['total_cost'] for row in rows],
        mode='lines',
        name='Total Cost',
        line=dict(color='#a1a1aa', width=1.5, dash='dot'),
        hovertemplate='Cost: %{y:,.0f} PLN<extra></extra>'))

    fig.add_trace(go.Scatter(
        x=[row['date'] for row in rows],
        y=[row['total_value'] for row in rows],
        mode='lines',
        name='Total Value',
        line=dict(color='#2563eb', width=2.2),
        fill='tonexty',
        fillcolor='rgba(37,99,235,.07)',
        hovertemplate='Value: %{y:,.0f} PLN<extra></extra>'))

    line_layout = plot_base_layout()
    line_layout.update(
        hovermode='x unified',
        hoverlabel=dict(bgcolor='#fff', font=dict(color='#1b1b1f', size=12),
                        bordercolor='#e7e7e9'),
        legend=dict(orientation='h', x=0, y=1.08),
        height=340)
    line_layout['xaxis'].update(showspikes=True, spikecolor='#d4d4d8',
                                spikethickness=1, spikedash='solid')
    fig.update_layout(**line_layout)

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