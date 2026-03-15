import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
YAM_TOKEN = os.getenv("YAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or BOT_TOKEN == "NO_TOKEN":
    raise ValueError("BOT_TOKEN not found")
if not YAM_TOKEN:
    raise ValueError("YAM_TOKEN not found")
if not CHAT_ID:
    raise ValueError("DUMP_CHAT_ID not found")
