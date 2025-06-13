from flask import Flask
from flask_jwt_extended import JWTManager

from config import Config
from database import init_db


app = Flask(__name__)


app.config.from_object(Config)
jwt = JWTManager(app)


with app.app_context():
    init_db()


@app.route('/')
def home():
    return 'DreamStay API is running!'

if __name__ == '__main__':
    app.run()