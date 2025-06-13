from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


from models import Base
from config import Config


engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, echo=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db():
    """
    We can create a new session to work with the database through this function.
    Yields an object generator.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()