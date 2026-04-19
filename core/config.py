import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str | None = os.getenv("BOT_TOKEN")
YAM_TOKEN: str | None = os.getenv("YAM_TOKEN")
CHAT_ID: str | None = os.getenv("CHAT_ID")
