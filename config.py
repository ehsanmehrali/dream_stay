import os
from dotenv import load_dotenv


load_dotenv()

class Config:
    """ This class contains the database and Flask configuration structure. """
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
    SECRET_KEY = os.getenv('SECRET_KEY')
    DEBUG = os.getenv('DEBUG', 'False') == 'True'

    # Images
    USE_R2 = os.getenv('USE_R2', 'false').lower() == 'true'
    R2_ACCOUNT_ID = os.getenv('R2_ACCOUNT_ID')
    R2_ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID')
    R2_SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
    R2_BUCKET_NAME = os.getenv('R2_BUCKET_NAME')
    R2_JURISDICTION = os.getenv('R2_JURISDICTION', 'DEFAULT').upper()

    # Endpoint for upload/delete (S3 API)
    R2_ENDPOINT = os.getenv('R2_ENDPOINT') or (
        f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    )

    # Public domain to display (now r2.dev which the dashboard gave me)
    R2_PUBLIC_BASE_URL = os.getenv('R2_PUBLIC_BASE_URL', '').rstrip('/')

    IMAGE_MAX_COUNT = int(os.getenv("IMAGE_MAX_COUNT", "30"))
    IMAGE_MAX_MB = int(os.getenv("IMAGE_MAX_MB", "15"))

