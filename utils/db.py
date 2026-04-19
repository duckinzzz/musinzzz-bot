from pathlib import Path

from sqlalchemy import Column, String
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

DB_PATH = "./data/bot.db"

db_dir = Path(DB_PATH).parent
db_dir.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(f"sqlite+aiosqlite:///{DB_PATH}", echo=False)
session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


class CachedAudio(Base):
    __tablename__ = "cached_audios"
    id = Column(String, primary_key=True)
    yam_id = Column(String, unique=True, index=True, nullable=False)
    tg_file_id = Column(String, unique=True, nullable=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get(yam_id: str) -> CachedAudio | None:
    async with session_factory() as session:
        return await session.get(CachedAudio, yam_id)


async def save(yam_id: str, tg_file_id: str):
    async with session_factory() as session:
        session.add(CachedAudio(id=yam_id, yam_id=yam_id, tg_file_id=tg_file_id))
        await session.commit()
