from flask import Flask
from flask_jwt_extended import JWTManager

from config import Config
from database import init_db


app = Flask(__name__)

# auth(authentication) route
from routes.auth import auth_bp
app.register_blueprint(auth_bp)

# properties route
from routes.properties import properties_bp
app.register_blueprint(properties_bp)

# profile route (edit user's profile)
from routes.profile import profile_bp
app.register_blueprint(profile_bp)

# availability route
from routes.availability import availability_bp
app.register_blueprint(availability_bp)

app.config.from_object(Config)
jwt = JWTManager(app)


with app.app_context():
    init_db()


@app.route('/')
def home():
    return 'DreamStay API is running!'


if __name__ == '__main__':
    app.run()