import app.db as db
import csv
from flask import (Blueprint, render_template)


bp = Blueprint('portfolio', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/dashboard', methods=['GET'])
def dashboard():
    pass

@bp.route('/transactions', methods=['GET'])
def transactions():
    pass

@bp.route('/historical_valuation', methods=['GET'])
def historical_valuation():
    pass