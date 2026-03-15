import os
from pathlib import Path

from sqlalchemy import create_engine, Column, String
from sqlalchemy.orm import declarative_base, sessionmaker

DB_PATH = "./data/bot.db"

# Создаём директорию для БД, если не существует
db_dir = Path(DB_PATH).parent
db_dir.mkdir(parents=True, exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()


class CachedAudio(Base):
    __tablename__ = "cached_audios"

    id = Column(String, primary_key=True)
    yam_id = Column(String, unique=True, index=True, nullable=False)
    tg_file_id = Column(String, unique=True, nullable=False)


Base.metadata.create_all(engine)


def get(yam_id: str) -> CachedAudio | None:
    session = Session()
    try:
        return session.query(CachedAudio).filter(CachedAudio.yam_id == yam_id).first()
    finally:
        session.close()


def save(yam_id: str, tg_file_id: str):
    session = Session()
    try:
        cached = CachedAudio(id=yam_id, yam_id=yam_id, tg_file_id=tg_file_id)
        session.add(cached)
        session.commit()
    finally:
        session.close()
