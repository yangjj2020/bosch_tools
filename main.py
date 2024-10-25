from flask import Flask

from app.router import temperature_bp, report_bp, index_bp

main = Flask(__name__, template_folder='templates', static_folder='static')
main.register_blueprint(index_bp)
main.register_blueprint(report_bp)
main.register_blueprint(temperature_bp)

if __name__ == '__main__':
    main.run(debug=True, threaded=True)
