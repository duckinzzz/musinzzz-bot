import asyncio

from core.app import bot, dp, logger
from handlers.inline import router as inline_router


async def announce_start():
    logger.info("Bot started")


async def main():
    dp.include_router(inline_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await announce_start()

    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
