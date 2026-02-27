import app.db as db
import csv
from flask import Blueprint


bp = Blueprint('portfolio', __name__)

@bp.route('/')
def index():
    pass

@bp.route('/dashboard', methods=['GET'])
def dashboard():
    pass

@bp.route('/transactions', methods=['GET'])
def transactions():
    pass

@bp.route('/historical_valuation', methods=['GET'])
def historical_valuation():
    pass