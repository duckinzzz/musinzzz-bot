import asyncio
import logging
import sys
from typing import Any, Awaitable, Callable, Dict

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import TelegramObject, Update

from core.config import BOTSTATS_API_TOKEN, BOT_TOKEN
from utils.ya_music import YandexMusicClient

BOTSTATS_URL = "https://botstats.duckinzzz.ru/api/"

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


class BotStatsMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: dict[str, Any],
    ) -> Any:
        if event.chosen_inline_result:
            json = {
                "token": BOTSTATS_API_TOKEN,
                "bot_name": 'musinzzz_bot',
                "payload": {
                    "username": event.chosen_inline_result.from_user.username,
                    "first_name": event.chosen_inline_result.from_user.first_name,
                    "last_name": event.chosen_inline_result.from_user.last_name,
                    "message": event.chosen_inline_result.query,
                    "result_id": event.chosen_inline_result.result_id,
                },
            }
            asyncio.create_task(send_stats(json=json))
        return await handler(event, data)


async def send_stats(json: dict[str, Any]) -> None:
    if not BOTSTATS_API_TOKEN:
        return
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(
                BOTSTATS_URL,
                json=json,
                timeout=aiohttp.ClientTimeout(total=5),
            )
    except Exception:
        logger.debug("BotStats request failed", exc_info=True)
