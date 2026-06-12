import datetime
import io
from decimal import Decimal

import app.db

ASSET_CSV = (
    "name,isin,ticker,asset_type_code,date,price,currency\n"
    "Acme Corp,US0000000001,ACME,STOCK,2026-01-15,123.45,USD\n"
)


def fake_lookups(query, *args, **kwargs):
    """Serve the dropdown-choice lookup queries used by the forms."""
    q = query.lower()
    if 'from asset_type' in q:
        return [(1, 'STOCK')]
    if 'from transaction_type' in q:
        return [(1, 'BUY')]
    if 'from portfolio' in q:
        return [(1, 'General')]
    if 'from asset' in q:
        return [(1, 'Acme Corp')]
    raise AssertionError(f'unexpected query: {query}')


class TestAssetRoutes:
    def test_add_asset_get(self, client, monkeypatch):
        monkeypatch.setattr(app.db, 'select_query', fake_lookups)

        resp = client.get('/import/asset_manual')

        assert resp.status_code == 200
        assert b'Add Asset' in resp.data

    def test_add_asset_post(self, client, monkeypatch, fake_con):
        monkeypatch.setattr(app.db, 'select_query', fake_lookups)

        resp = client.post('/import/asset_manual', data={
            'name': 'Acme Corp',
            'isin': 'US0000000001',
            'ticker': 'ACME',
            'asset_type': '1',
            'currency': 'USD',
            'submit': 'Add',
        })

        assert resp.status_code == 302
        assert resp.headers['Location'].endswith('/import/asset_list')
        query, params = fake_con.executed[0]
        assert 'INSERT INTO ASSET' in query
        assert params == ('Acme Corp', 'US0000000001', 'ACME', 1, 'USD')
        assert fake_con.committed

    def test_asset_list(self, client, monkeypatch):
        assets = [{'id': 1, 'name': 'Acme Corp', 'isin': 'US0000000001',
                   'ticker': 'ACME', 'asset_type': 'Stock', 'currency': 'USD'}]
        monkeypatch.setattr(app.db, 'select_query', lambda *a, **k: assets)

        resp = client.get('/import/asset_list')

        assert resp.status_code == 200
        assert b'Acme Corp' in resp.data

    def test_edit_asset_get_prefills_form(self, client, monkeypatch):
        def fake_select(query, *args, **kwargs):
            if 'WHERE id' in query:
                return {'id': 1, 'name': 'Acme Corp', 'isin': 'US0000000001',
                        'ticker': 'ACME', 'asset_type_id': 1, 'currency': 'USD'}
            return fake_lookups(query, *args, **kwargs)
        monkeypatch.setattr(app.db, 'select_query', fake_select)

        resp = client.get('/import/asset_edit/1')

        assert resp.status_code == 200
        assert b'Acme Corp' in resp.data

    def test_delete_asset(self, client, fake_con):
        resp = client.post('/import/asset_delete/1')

        assert resp.status_code == 302
        query, params = fake_con.executed[0]
        assert 'DELETE FROM ASSET' in query
        assert params == (1,)
        assert fake_con.committed


class TestTransactionRoutes:
    def test_add_transaction_get(self, client, monkeypatch):
        monkeypatch.setattr(app.db, 'select_query', fake_lookups)

        resp = client.get('/import/transaction_manual')

        assert resp.status_code == 200
        assert b'Add Transaction' in resp.data

    def test_edit_transaction_get_prefills_form(self, client, monkeypatch):
        def fake_select(query, *args, **kwargs):
            if 'WHERE id' in query:
                return {'id': 1, 'date': datetime.date(2026, 1, 15),
                        'description': 'test buy', 'transaction_type_id': 1,
                        'asset_id': 1, 'quantity': 10, 'price': Decimal('100.50'),
                        'total_amount': None, 'currency': 'PLN',
                        'fee': Decimal('2.50'), 'tax_amount': None, 'portfolio_id': 1}
            return fake_lookups(query, *args, **kwargs)
        monkeypatch.setattr(app.db, 'select_query', fake_select)

        resp = client.get('/import/transaction_edit/1')

        assert resp.status_code == 200
        assert b'test buy' in resp.data

    def test_add_transaction_post(self, client, monkeypatch, fake_con):
        monkeypatch.setattr(app.db, 'select_query', fake_lookups)

        resp = client.post('/import/transaction_manual', data={
            'date': '2026-01-15',
            'description': 'test buy',
            'transaction_type': '1',
            'asset': '1',
            'quantity': '10',
            'price': '100.50',
            'currency': 'PLN',
            'fee': '2.50',
            'portfolio': '1',
            'submit': 'Add',
        })

        assert resp.status_code == 302
        assert resp.headers['Location'].endswith('/import/transaction_list')
        query, params = fake_con.executed[0]
        assert 'INSERT INTO TRANSACTION' in query
        assert params[0] == datetime.date(2026, 1, 15)
        assert params[5] == Decimal('100.50')
        assert fake_con.committed

    def test_transaction_list(self, client, monkeypatch):
        transactions = [{
            'id': 1, 'date': datetime.date(2026, 1, 15), 'description': 'test buy',
            'transaction_type': 'BUY', 'asset': 'Acme Corp', 'quantity': 10,
            'currency': 'PLN', 'price': Decimal('100.50'),
            'total_amount': Decimal('1007.50'), 'fee': Decimal('2.50'),
            'tax_amount': Decimal('0'), 'portfolio': 'General',
        }]
        monkeypatch.setattr(app.db, 'select_query', lambda *a, **k: transactions)

        resp = client.get('/import/transaction_list')

        assert resp.status_code == 200
        assert b'Acme Corp' in resp.data

    def test_delete_transaction(self, client, fake_con):
        resp = client.post('/import/transaction_delete/1')

        assert resp.status_code == 302
        query, params = fake_con.executed[0]
        assert 'DELETE FROM TRANSACTION' in query
        assert params == (1,)
        assert fake_con.committed


class TestFileImports:
    def test_import_pages_render(self, client):
        assert client.get('/import/asset_import').status_code == 200
        assert client.get('/import/transaction_import').status_code == 200

    def test_asset_import_post(self, client, monkeypatch):
        captured = {}

        def fake_import(rows):
            captured['rows'] = rows
            return len(rows), 0

        monkeypatch.setattr(app.db, 'import_assets', fake_import)
        monkeypatch.setattr(app.db, 'select_query', lambda *a, **k: [])

        resp = client.post(
            '/import/asset_import',
            data={'file': (io.BytesIO(ASSET_CSV.encode()), 'assets.csv'), 'submit': 'Upload'},
            content_type='multipart/form-data',
            follow_redirects=True,
        )

        assert resp.status_code == 200
        assert captured['rows'][0]['name'] == 'Acme Corp'
        assert '1 inserted, 0 skipped' in resp.data.decode()

    def test_asset_import_rejects_non_csv(self, client, monkeypatch):
        called = []
        monkeypatch.setattr(app.db, 'import_assets', lambda rows: called.append(rows))

        resp = client.post(
            '/import/asset_import',
            data={'file': (io.BytesIO(b'not a csv'), 'assets.txt'), 'submit': 'Upload'},
            content_type='multipart/form-data',
        )

        # form validation fails, page re-renders without importing
        assert resp.status_code == 200
        assert called == []

    def test_invalid_csv_flashes_error(self, client, monkeypatch):
        monkeypatch.setattr(app.db, 'select_query', lambda *a, **k: [])

        bad_csv = b"name,isin\nAcme,US1\n"
        resp = client.post(
            '/import/asset_import',
            data={'file': (io.BytesIO(bad_csv), 'assets.csv'), 'submit': 'Upload'},
            content_type='multipart/form-data',
            follow_redirects=True,
        )

        assert resp.status_code == 200
        assert 'Asset file processing failed' in resp.data.decode()
