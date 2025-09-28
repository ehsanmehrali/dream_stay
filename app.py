from os.path import exists

from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
import os

from config import Config
from database import init_db


app = Flask(__name__)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.config.from_object(Config)
app.config['JSON_SORT_KEYS'] = False

    # os.mkdir(Config.IMAGE_UPLOAD_DIR, exist_ok=True)

CORS(app, resources={r"/*": {"origins": allowed_origins}},
  supports_credentials=False,
  methods=["GET", "HEAD", "OPTIONS"],
  allow_headers=["Content-Type", "Accept", "Authorization"])

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

from routes.search import search_bp
app.register_blueprint(search_bp)

from routes.booking import booking_bp
app.register_blueprint(booking_bp)

app.config.from_object(Config)
jwt = JWTManager(app)


with app.app_context():
    init_db()


@app.route('/')
def home():
    return 'DreamStay API is running!'


if __name__ == '__main__':
    app.run()