from unittest import result

from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DecimalField, FileField, SubmitField
from wtforms.validators import DataRequired, InputRequired

class AssetForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    isin = StringField('ISIN')
    ticker = StringField('Ticker')
    asset_type = SelectField('Asset Type', coerce=int, validators=[InputRequired()])
    submit = SubmitField('Add')
