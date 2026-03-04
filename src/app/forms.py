from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DecimalField, FileField, SubmitField
from wtforms.validators import DataRequired, InputRequired

class AssetForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    isin = StringField('ISIN')
    ticker = StringField('Ticker')
    asset_type = SelectField('Asset Type', coerce=int, validators=[InputRequired()])

class AssetFormAdd(AssetForm):
    submit = SubmitField('Add')

class AssetFormEdit(AssetForm):
    submit = SubmitField('Update')
    #delete = SubmitField('Delete')


class TransactionForm(FlaskForm):
    date = StringField('Date', validators=[DataRequired()])
    description = StringField('Description')
    transaction_type = SelectField('Transaction Type', coerce=int, validators=[InputRequired()])
    asset = SelectField('Asset', coerce=int, validators=[InputRequired()])
    quantity = DecimalField('Quantity', validators=[DataRequired()])
    price = DecimalField('Price', validators=[DataRequired()])
    total_amount = DecimalField('Total Amount', validators=[DataRequired()])
    currency = StringField('Currency', validators=[DataRequired()])
    fee = DecimalField('Fee', default=0)
    tax_amount = DecimalField('Tax Amount', default=0)
    portfolio = SelectField('Portfolio', coerce=int, validators=[InputRequired()])

class TransactionFormAdd(TransactionForm):
    submit = SubmitField('Add')

class TransactionFormEdit(TransactionForm):
    submit = SubmitField('Update')
    #delete = SubmitField('Delete')
