import os

from dotenv import load_dotenv


load_dotenv()


class Config:
    """ This class contains the database and Flask configuration structure. """
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
    SECRET_KEY = os.getenv('SECRET_KEY')
    DEBUG = os.getenv('DEBUG', 'False') == 'True'