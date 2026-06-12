import datetime
import json
import re
from decimal import Decimal

import app.db


def extract_chart_json(html, element_id):
    """Pull an embedded plotly figure out of its <script type="application/json"> tag."""
    match = re.search(rf'id="{element_id}">\s*(.*?)\s*</script>', html, re.S)
    assert match, f'no chart data found for #{element_id}'
    return json.loads(match.group(1))


def make_position(**overrides):
    pos = {
        'asset_name': 'Acme Corp',
        'portfolio_name': 'General',
        'quantity': 10,
        'currency': 'PLN',
        'avg_buy_price': Decimal('100.0000'),
        'total_cost': Decimal('1000.00'),
        'total_fee': Decimal('5.00'),
        'total_tax': Decimal('0'),
        'current_price': Decimal('110'),
        'current_holding_value': Decimal('1100.00'),
        'current_unrealized_gain': Decimal('100.00'),
        'realized_gain': None,
        'total_dividend': None,
        'dividend_tax': None,
        'total_interest': None,
        'interest_tax': None,
        'total_gain': Decimal('0'),
        'all_tax': Decimal('0'),
        'total_gained_value': Decimal('100.00'),
    }
    pos.update(overrides)
    return pos


def test_index_lists_positions_and_totals(client, monkeypatch):
    positions = [
        make_position(),
        make_position(asset_name='Treasury Bond',
                      total_cost=Decimal('2000.50'),
                      current_holding_value=Decimal('2100.00')),
    ]
    monkeypatch.setattr(app.db, 'select_query', lambda *a, **k: positions)

    resp = client.get('/')

    assert resp.status_code == 200
    html = resp.data.decode()
    assert 'Acme Corp' in html
    assert 'Treasury Bond' in html
    # totals row: summed total_cost and current_holding_value
    assert '3,000.50' in html
    assert '3,200.00' in html


def test_index_with_no_positions(client, monkeypatch):
    monkeypatch.setattr(app.db, 'select_query', lambda *a, **k: [])

    resp = client.get('/')

    assert resp.status_code == 200
    assert b'Total' in resp.data


DASHBOARD_TOTALS = {
    'total_dividend': Decimal('120.50'),
    'total_interest': Decimal('30.00'),
    'total_fee': Decimal('15.25'),
    'realized_gain': Decimal('200.00'),
    'unrealized_gain': Decimal('450.00'),
}

DASHBOARD_POSITIONS = [
    {'asset_name': 'Acme Corp', 'portfolio_name': 'General', 'asset_type_code': 'STOCK',
     'current_holding_value': Decimal('3000'), 'current_unrealized_gain': Decimal('500')},
    {'asset_name': 'Treasury Bond', 'portfolio_name': 'IKE', 'asset_type_code': 'BOND',
     'current_holding_value': Decimal('2000'), 'current_unrealized_gain': Decimal('-50')},
    {'asset_name': 'Acme Corp', 'portfolio_name': 'IKE', 'asset_type_code': 'STOCK',
     'current_holding_value': Decimal('1000'), 'current_unrealized_gain': None},
]


def fake_dashboard_queries(query, *args, **kwargs):
    if 'sum(total_dividend)' in query.lower():
        return DASHBOARD_TOTALS
    return DASHBOARD_POSITIONS


def test_dashboard_totals_table(client, monkeypatch):
    monkeypatch.setattr(app.db, 'select_query', fake_dashboard_queries)

    resp = client.get('/dashboard')

    assert resp.status_code == 200
    html = resp.data.decode()
    for value in ('120.50', '30.00', '15.25', '200.00', '450.00'):
        assert value in html


def test_dashboard_pie_charts(client, monkeypatch):
    monkeypatch.setattr(app.db, 'select_query', fake_dashboard_queries)

    resp = client.get('/dashboard')

    fig = extract_chart_json(resp.data.decode(), 'pie-data')
    all_pie, stock_pie = fig['data']
    # all positions, aggregated per asset across portfolios
    assert all_pie['labels'] == ['Acme Corp', 'Treasury Bond']
    assert all_pie['values'] == [4000, 2000]
    # stocks only
    assert stock_pie['labels'] == ['Acme Corp']
    assert stock_pie['values'] == [4000]
    titles = [a['text'] for a in fig['layout']['annotations']]
    assert titles == ['All Positions', 'Stocks Only']


def test_dashboard_bar_chart(client, monkeypatch):
    monkeypatch.setattr(app.db, 'select_query', fake_dashboard_queries)

    resp = client.get('/dashboard')

    fig = extract_chart_json(resp.data.decode(), 'bar-data')
    bar = fig['data'][0]
    # aggregated per asset across portfolios, most valuable first
    assert bar['y'] == ['Acme Corp', 'Treasury Bond']
    assert bar['x'] == [4000, 2000]
    # most valuable asset rendered at the top
    assert fig['layout']['yaxis']['autorange'] == 'reversed'
    # summed gain/loss labels on each bar, losses coloured differently
    assert bar['text'] == ['+500.00', '-50.00']
    colors = bar['marker']['color']
    assert colors[0] != colors[1]


def test_historical_valuation_get_renders_chart(client, monkeypatch):
    rows = [
        {'date': datetime.date(2026, 1, 1), 'total_value': Decimal('100'), 'total_cost': Decimal('90')},
        {'date': datetime.date(2026, 2, 1), 'total_value': Decimal('120'), 'total_cost': Decimal('95')},
    ]
    monkeypatch.setattr(app.db, 'select_query', lambda *a, **k: rows)

    resp = client.get('/historical_valuation')

    assert resp.status_code == 200
    assert b'Historical Portfolio Valuation' in resp.data


def test_historical_valuation_table_shows_last_10_newest_first(client, monkeypatch):
    rows = [{'date': datetime.date(2026, month, 1),
             'total_value': Decimal(100 + month),
             'total_cost': Decimal(90)}
            for month in range(1, 13)]
    monkeypatch.setattr(app.db, 'select_query', lambda *a, **k: rows)

    resp = client.get('/historical_valuation')

    # the chart JSON above the table contains all dates, so only inspect the table
    table = resp.data.decode().split('Last 10 Valuations')[1]
    assert '2026-12-01' in table
    assert '2026-03-01' in table
    assert '2026-02-01' not in table
    assert '2026-01-01' not in table
    assert table.index('2026-12-01') < table.index('2026-03-01')  # newest first
    assert '22.00' in table  # gain column: 112 - 90


def test_historical_valuation_post_inserts_snapshot(client, monkeypatch, fake_con):
    monkeypatch.setattr(app.db, 'select_query', lambda *a, **k: [])

    resp = client.post('/historical_valuation', data={'submit': 'Perform Valuation'})

    assert resp.status_code == 302
    assert resp.headers['Location'].endswith('/historical_valuation')
    assert any('INSERT INTO PORTFOLIO_VALUATION' in query for query, _ in fake_con.executed)
    assert fake_con.committed
