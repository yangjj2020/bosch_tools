__coding__ = "utf-8"

from flask import Blueprint

index_bp = Blueprint('index', __name__, url_prefix='/')
report_bp = Blueprint('report', __name__, url_prefix='/report')
temperature_bp = Blueprint('temperature', __name__, url_prefix='/temperature')

from app.router import Index
from app.router import ReportAuto, Index
from app.router import Temperature
