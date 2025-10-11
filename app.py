from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_cors import CORS
import os
from config import Config
from database import init_db


app = Flask(__name__)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.config.from_object(Config)

app.config['MAX_CONTENT_LENGTH'] = Config.IMAGE_MAX_COUNT * Config.IMAGE_MAX_MB * 1024 * 1024
print("R2 ACTIVE:", Config.USE_R2, "ENDPOINT:", Config.R2_ENDPOINT, "PUBLIC:", Config.R2_PUBLIC_BASE_URL,
          flush=True)
if Config.USE_R2 and (not Config.R2_PUBLIC_BASE_URL or not Config.R2_BUCKET_NAME):
    raise RuntimeError("R2 misconfigured: set R2_PUBLIC_BASE_URL and R2_BUCKET_NAME")

app.config['JSON_SORT_KEYS'] = False

CORS(app, resources={r"/*": {"origins": allowed_origins}},
  supports_credentials=False,
  methods=["GET", "HEAD", "OPTIONS","POST"],
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

from routes.property_images import images_bp
app.register_blueprint(images_bp)

# gallery route
from routes.booking import booking_bp
app.register_blueprint(booking_bp)


jwt = JWTManager(app)

with app.app_context():
    init_db()


@app.route('/')
def home():
    return jsonify({"status": "DreamStay is running"}), 200


if __name__ == '__main__':
    app.run()