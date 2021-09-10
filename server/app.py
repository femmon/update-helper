from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)

from routes import routes
app.register_blueprint(routes)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0')
