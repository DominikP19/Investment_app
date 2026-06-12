from decimal import Decimal

import pytest


def test_hello(client):
    resp = client.get('/hello')

    assert resp.status_code == 200
    assert b"Hello from the Investment App!" in resp.data


@pytest.mark.parametrize(('value', 'expected'), [
    (None, '0'),
    (0, '0.00'),
    (Decimal('1234.5'), '1,234.50'),
    (Decimal('-12.3'), '-12.30'),
    (Decimal('1234567.891'), '1,234,567.89'),
])
def test_money_filter(app, value, expected):
    money = app.jinja_env.filters['money']
    assert money(value) == expected
