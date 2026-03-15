import asyncio

from core.app import bot, dp, logger, YandexMusicMiddleware
from core.config import YAM_TOKEN
from handlers.inline import router as inline_router
from utils.db import init_db
from utils.ya_music import YandexMusicClient


async def main():
    yam_client = YandexMusicClient(YAM_TOKEN)
    await yam_client.init()

    dp.update.middleware(YandexMusicMiddleware(yam_client))
    dp.include_router(inline_router)

    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Bot started")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
