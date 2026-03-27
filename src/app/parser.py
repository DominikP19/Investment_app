import csv
import io
import datetime
from decimal import Decimal

ASSET_EXPECTED_COLUMNS = {'name', 'isin', 'ticker', 'asset_type_code','date', 'price', 'currency'}
TRANSACTION_EXPECTED_COLUMNS = {'date','asset_name', 'ticker', 'transaction_type_code', 
                                'quantity', 'currency', 'price', 'total_amount', 'fee',
                                'total_with_fee', 'tax_amount', 'portfolio_name'}
DATE_FORMAT = '%Y-%m-%d'

def asset_parse_csv(file_bytes: bytes) -> list[dict]:
    text = file_bytes.decode('utf-8')
    reader = csv.DictReader(io.StringIO(text))

    reader.fieldnames = [f.strip().lower() for f in reader.fieldnames]
    missing = ASSET_EXPECTED_COLUMNS - set(reader.fieldnames)

    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")

    rows = []
    for i, row in enumerate(reader, start=2):
        try:
            rows.append({
                'name':             row['name'].strip(),
                'isin':             row['isin'].strip(),
                'ticker':           row['ticker'].strip(),
                'asset_type_code':  row['asset_type_code'].strip(),
                'date':             datetime.datetime.strptime(row['date'].strip(), DATE_FORMAT),
                'price':            Decimal(row['price']),
                'currency':         row['currency'].strip()
                })
        except (ValueError, KeyError) as e:
            raise ValueError(f"Invalid data on row {i}: {e}")

    return rows

def transaction_parse_csv(file_bytes: bytes) -> list[dict]:
    text = file_bytes.decode('utf-8')
    reader = csv.DictReader(io.StringIO(text))

    reader.fieldnames = [f.strip().lower() for f in reader.fieldnames]
    missing = TRANSACTION_EXPECTED_COLUMNS - set(reader.fieldnames)

    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")
    
    rows = []
    for i, row in enumerate(reader, start =2):
        try:
            rows.append({
                'date':                     datetime.datetime.strptime(row['date'].strip(), DATE_FORMAT),
                'asset_name':               row['asset_name'].strip(),
                'ticker':                   row['ticker'].strip(),
                'transaction_type_code':    row['transaction_type_code'].strip(),
                'quantity':                 int(row['quantity']),
                'currency':                 row['currency'].strip(),
                'price':                    Decimal(row['price']),
                'total_amount':             Decimal(row['total_amount']),
                'fee':                      Decimal(row['fee']),
                'total_with_fee':           Decimal(row['total_with_fee']),
                'tax_amount':               (Decimal(row['tax_amount']) if row['tax_amount'] else None),
                'portfolio_name':           row['portfolio_name'].strip()
            })
        except (ValueError, KeyError) as e:
            raise ValueError(f"Invalid data on row {i}: {e}")
    
    return rows