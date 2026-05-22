"""SQLite + SQLAlchemy session for user accounts."""
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "legal_advisor.db"


def sqlite_url(db_path: Path | None = None) -> str:
    path = (db_path or DEFAULT_DB_PATH).resolve()
    return f"sqlite:///{path.as_posix()}"


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str):
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(database_url, connect_args=connect_args)


def make_session_factory(database_url: str) -> sessionmaker[Session]:
    return sessionmaker(autocommit=False, autoflush=False, bind=make_engine(database_url))


def init_db(database_url: str) -> None:
    from backend.models import User  # noqa: F401

    engine = make_engine(database_url)
    Base.metadata.create_all(bind=engine)
