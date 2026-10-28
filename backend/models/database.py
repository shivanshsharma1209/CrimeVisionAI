import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from config import Config

engine = create_engine(
    Config.SQLALCHEMY_DATABASE_URI,
    connect_args={"check_same_thread": False} if "sqlite" in Config.SQLALCHEMY_DATABASE_URI else {},
)

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.query = SessionLocal.query_property()


class DBProxy:
    """Compatibility proxy for db.session and scoped session operations."""
    @property
    def session(self):
        return SessionLocal


db = DBProxy()


def get_db():
    """FastAPI dependency for database sessions."""
    db_session = SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()
