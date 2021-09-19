from flask import Flask, request
from flask_cors import CORS
from flask_socketio import SocketIO


app = Flask(__name__)
# TODO: tighten security
CORS(app)
socketio = SocketIO(app, cors_allowed_origins='*')


@app.before_request
def log_request_info():
    app.logger.debug('Headers: %s', request.headers)
    app.logger.debug('Body: %s', request.get_data())


from routes import routes
app.register_blueprint(routes)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0')
