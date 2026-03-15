import logging
import sys
from typing import Any, Awaitable, Callable, Dict

from aiogram import Bot, Dispatcher
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import Update

from core.config import BOT_TOKEN
from utils.ya_music import YandexMusicClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("bot_core")
logger.info(f"Bot starting | token ends with ...{BOT_TOKEN[-6:]}")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


class YandexMusicMiddleware(BaseMiddleware):
    def __init__(self, client: YandexMusicClient) -> None:
        self.client = client

    async def __call__(
            self,
            handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
            event: Update,
            data: Dict[str, Any],
    ) -> Any:
        data["yam_client"] = self.client
        return await handler(event, data)
