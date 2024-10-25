__coding__ = "utf-8"

from flask import render_template

from app.router import index_bp


@index_bp.route('/', methods=['GET'])
def temperature_idx():
    return render_template('main.html')


@index_bp.route('/welcome', methods=['GET'])
def welcome():
    return render_template('welcome.html')
