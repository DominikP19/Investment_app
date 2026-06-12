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
     'current_holding_value': Decimal('3000'), 'current_unrealized_gain': Decimal('500'),
     'realized_gain': Decimal('100')},
    {'asset_name': 'Treasury Bond', 'portfolio_name': 'IKE', 'asset_type_code': 'BOND',
     'current_holding_value': Decimal('2000'), 'current_unrealized_gain': Decimal('-50'),
     'realized_gain': None},
    {'asset_name': 'Acme Corp', 'portfolio_name': 'IKE', 'asset_type_code': 'STOCK',
     'current_holding_value': Decimal('1000'), 'current_unrealized_gain': None,
     'realized_gain': None},
    # gain == 0: shows in the allocation donut but is dropped from the gain bar
    {'asset_name': 'Cash', 'portfolio_name': 'General', 'asset_type_code': 'CASH',
     'current_holding_value': Decimal('700'), 'current_unrealized_gain': None,
     'realized_gain': None},
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


def test_dashboard_donuts(client, monkeypatch):
    monkeypatch.setattr(app.db, 'select_query', fake_dashboard_queries)

    resp = client.get('/dashboard')
    html = resp.data.decode()

    # two separate figures, one per card
    all_fig = extract_chart_json(html, 'donut-all-data')
    stock_fig = extract_chart_json(html, 'donut-stocks-data')

    all_donut = all_fig['data'][0]
    # aggregated per asset across portfolios, sorted descending by value
    assert all_donut['labels'] == ['Acme Corp', 'Treasury Bond', 'Cash']
    assert all_donut['values'] == [4000, 2000, 700]
    assert all_donut['hole'] == 0.62
    assert all_donut['sort'] is False
    assert all_donut['textinfo'] == 'percent'
    assert all_fig['layout']['showlegend'] is True
    assert all_fig['layout']['uniformtext'] == {'minsize': 11, 'mode': 'hide'}
    assert all_fig['layout']['annotations'][0]['text'] == '<b>6,700</b><br>PLN'

    stock_donut = stock_fig['data'][0]
    assert stock_donut['labels'] == ['Acme Corp']
    assert stock_donut['values'] == [4000]
    assert stock_fig['layout']['annotations'][0]['text'] == '<b>4,000</b><br>PLN'


def test_dashboard_donut_groups_top_6_plus_other(client, monkeypatch):
    positions = [
        {'asset_name': f'Asset {i}', 'portfolio_name': 'General',
         'asset_type_code': 'STOCK',
         'current_holding_value': Decimal(100 * i),
         'current_unrealized_gain': None, 'realized_gain': None}
        for i in range(1, 9)  # values 100 .. 800
    ]

    def fake_select(query, *args, **kwargs):
        if 'sum(total_dividend)' in query.lower():
            return DASHBOARD_TOTALS
        return positions
    monkeypatch.setattr(app.db, 'select_query', fake_select)

    resp = client.get('/dashboard')

    donut = extract_chart_json(resp.data.decode(), 'donut-all-data')['data'][0]
    assert len(donut['labels']) == 7  # top 6 + Other
    assert donut['labels'][:2] == ['Asset 8', 'Asset 7']
    assert donut['labels'][-1] == 'Other (2)'
    assert donut['values'][-1] == 300  # 100 + 200
    assert donut['marker']['colors'][-1] == '#c7c9ce'


def test_dashboard_bar_chart(client, monkeypatch):
    monkeypatch.setattr(app.db, 'select_query', fake_dashboard_queries)

    resp = client.get('/dashboard')

    fig = extract_chart_json(resp.data.decode(), 'bar-data')
    bar = fig['data'][0]
    # bar encodes realized + unrealized gain, ascending so biggest gain is on
    # top; the zero-gain Cash row is filtered out entirely
    assert bar['y'] == ['Treasury Bond', 'Acme Corp']
    assert bar['x'] == [-50, 600]
    assert 'autorange' not in fig['layout']['yaxis']
    assert bar['text'] == ['−50', '+600']
    colors = bar['marker']['color']
    assert colors == ['#d3403c', '#0a8754']
    # visible zeroline and dynamic height
    assert fig['layout']['xaxis']['zerolinecolor'] == '#d4d4d8'
    assert fig['layout']['height'] == 220  # max(220, 2 * 28 + 60)


def test_historical_valuation_get_renders_chart(client, monkeypatch):
    rows = [
        {'date': datetime.date(2026, 1, 1), 'total_value': Decimal('100'), 'total_cost': Decimal('90')},
        {'date': datetime.date(2026, 2, 1), 'total_value': Decimal('120'), 'total_cost': Decimal('95')},
    ]
    monkeypatch.setattr(app.db, 'select_query', lambda *a, **k: rows)

    resp = client.get('/historical_valuation')

    assert resp.status_code == 200
    assert b'Value vs. cost over time' in resp.data
    fig = extract_chart_json(resp.data.decode(), 'chart-data')
    assert [t['name'] for t in fig['data']] == ['Total Cost', 'Total Value']
    assert fig['data'][1]['fill'] == 'tonexty'


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
