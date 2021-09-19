from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO


app = Flask(__name__)
# TODO: tighten security
CORS(app)
socketio = SocketIO(app, cors_allowed_origins='*')

from routes import routes
app.register_blueprint(routes)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0')
