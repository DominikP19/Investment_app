import datetime
from decimal import Decimal

import pytest

import app.parser as parser

ASSET_CSV = (
    "name,isin,ticker,asset_type_code,date,price,currency\n"
    "Acme Corp,US0000000001,ACME,STOCK,2026-01-15,123.45,USD\n"
    "Treasury Bond,,,BOND,2026-01-15,100,PLN\n"
)

TRANSACTION_CSV = (
    "date,asset_name,ticker,transaction_type_code,quantity,currency,price,"
    "total_amount,fee,total_with_fee,tax_amount,portfolio_name\n"
    "2026-01-15,Acme Corp,ACME,BUY,10,USD,123.45,1234.50,5,1239.50,0,General\n"
    "2026-02-01,Acme Corp,ACME,DIV,0,USD,50,,,,9.50,General\n"
)


class TestAssetParseCsv:
    def test_valid_file(self):
        rows = parser.asset_parse_csv(ASSET_CSV.encode())

        assert len(rows) == 2
        assert rows[0] == {
            'name': 'Acme Corp',
            'isin': 'US0000000001',
            'ticker': 'ACME',
            'asset_type_code': 'STOCK',
            'date': datetime.datetime(2026, 1, 15),
            'price': Decimal('123.45'),
            'currency': 'USD',
        }

    def test_empty_optional_fields_become_none(self):
        rows = parser.asset_parse_csv(ASSET_CSV.encode())

        assert rows[1]['isin'] is None
        assert rows[1]['ticker'] is None

    def test_header_is_normalized(self):
        csv_text = (
            " Name ,ISIN,Ticker,Asset_Type_Code,DATE,Price,Currency\n"
            "Acme Corp,,,STOCK,2026-01-15,1,PLN\n"
        )
        rows = parser.asset_parse_csv(csv_text.encode())
        assert rows[0]['name'] == 'Acme Corp'

    def test_header_only_returns_no_rows(self):
        header = "name,isin,ticker,asset_type_code,date,price,currency\n"
        assert parser.asset_parse_csv(header.encode()) == []

    def test_missing_column_raises(self):
        csv_text = "name,isin,ticker,asset_type_code,date,price\nAcme,,,STOCK,2026-01-15,1\n"
        with pytest.raises(ValueError, match='currency'):
            parser.asset_parse_csv(csv_text.encode())

    def test_invalid_price_reports_row_number(self):
        csv_text = (
            "name,isin,ticker,asset_type_code,date,price,currency\n"
            "Acme,,,STOCK,2026-01-15,not-a-price,PLN\n"
        )
        with pytest.raises(ValueError, match='row 2'):
            parser.asset_parse_csv(csv_text.encode())

    def test_invalid_date_format_raises(self):
        csv_text = (
            "name,isin,ticker,asset_type_code,date,price,currency\n"
            "Acme,,,STOCK,15-01-2026,1,PLN\n"
        )
        with pytest.raises(ValueError, match='row 2'):
            parser.asset_parse_csv(csv_text.encode())


class TestTransactionParseCsv:
    def test_valid_file(self):
        rows = parser.transaction_parse_csv(TRANSACTION_CSV.encode())

        assert len(rows) == 2
        assert rows[0] == {
            'date': datetime.datetime(2026, 1, 15),
            'asset_name': 'Acme Corp',
            'ticker': 'ACME',
            'transaction_type_code': 'BUY',
            'quantity': 10,
            'currency': 'USD',
            'price': Decimal('123.45'),
            'total_amount': Decimal('1234.50'),
            'fee': Decimal('5'),
            'total_with_fee': Decimal('1239.50'),
            'tax_amount': Decimal('0'),
            'portfolio_name': 'General',
        }

    def test_dividend_row_with_zero_quantity(self):
        rows = parser.transaction_parse_csv(TRANSACTION_CSV.encode())

        div = rows[1]
        assert div['transaction_type_code'] == 'DIV'
        assert div['quantity'] == 0
        assert div['total_amount'] is None
        assert div['fee'] is None
        assert div['tax_amount'] == Decimal('9.50')

    def test_missing_columns_raise(self):
        csv_text = "date,asset_name\n2026-01-15,Acme\n"
        with pytest.raises(ValueError, match='missing required columns'):
            parser.transaction_parse_csv(csv_text.encode())

    def test_invalid_quantity_reports_row_number(self):
        bad = TRANSACTION_CSV.replace(',10,USD', ',ten,USD')
        with pytest.raises(ValueError, match='row 2'):
            parser.transaction_parse_csv(bad.encode())
