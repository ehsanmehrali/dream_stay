import os
from dotenv import load_dotenv


load_dotenv()


class Config:
    """ This class contains the database and Flask configuration structure. """
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
    SECRET_KEY = os.getenv('SECRET_KEY')
    DEBUG = os.getenv('DEBUG', 'False') == 'True'

    # Images
    IMAGE_UPLOAD_DIR = os.getenv('IMAGE_UPLOAD_DIR', os.path.abspath('uploads'))
    IMAGE_BASE_URL = os.getenv('IMAGE_BASE_URL', '/uploads')
    IMAGE_MAX_MB = float(os.getenv('IMAGE_MAX_MB', '10'))
    IMAGE_MAX_COUNT = int(os.getenv('IMAGE_MAX_COUNT', '20'))
    IMAGE_ALLOWED_FORMATS = set((os.getenv('IMAGE_ALLOWED_FORMATS', 'jpg,jpeg,png,webp,heic')).lower().split(','))