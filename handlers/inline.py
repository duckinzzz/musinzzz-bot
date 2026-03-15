import hashlib
import re

from aiogram import Router
from aiogram.types import (
    InlineQuery,
    ChosenInlineResult,
    InlineQueryResultAudio,
    URLInputFile,
    InputMediaAudio,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from core.app import bot
from core.config import CHAT_ID
from utils import db
from utils.ya_music import YandexMusicClient, YandexTrack, logger

router = Router()
result_ids: dict[str, str] = {}


def get_loading_markup(track_id: str | int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⏳", callback_data=str(track_id))]]
    )


def track_as_inline_result(track: YandexTrack) -> InlineQueryResultAudio:
    result_id = hashlib.md5(str(track.yandex_track_id).encode()).hexdigest()
    result_ids[result_id] = track.yandex_track_id
    return InlineQueryResultAudio(
        id=result_id,
        audio_url="https://cdn.jsdelivr.net/gh/duckinzzz/musinzzz-bot/baoba.mp3",
        title=track.title,
        performer=track.artists,
        audio_duration=track.duration,
        reply_markup=get_loading_markup(track.yandex_track_id),
    )


@router.inline_query()
async def inline_search(inline_query: InlineQuery, yam_client: YandexMusicClient):
    query = inline_query.query
    items = []

    if query.startswith("https://"):
        match = re.match(
            r"https://music.yandex.(ru|by|kz|com)/album/(\d+)/track/(\d+)", query
        )
        if match:
            album_id, track_id = match.group(2), match.group(3)
            full_id = f"{track_id}:{album_id}"
            track = await yam_client.get_track_data(full_id)
            items.append(track_as_inline_result(track))
    elif query:
        tracks = await yam_client.search(query)
        items = [track_as_inline_result(track) for track in tracks]

    await bot.answer_inline_query(inline_query.id, results=items, cache_time=5)


@router.chosen_inline_result()
async def process_chosen_track(
        chosen_result: ChosenInlineResult,
        yam_client: YandexMusicClient,
):
    result_id = chosen_result.result_id
    inline_message_id = chosen_result.inline_message_id

    if not inline_message_id or result_id not in result_ids:
        return

    full_yam_id = result_ids[result_id]
    db_yam_id = full_yam_id.split(":", 1)[0] if ":" in full_yam_id else full_yam_id

    cached = await db.get(db_yam_id)
    tg_file_id = cached.tg_file_id if cached else None

    if not tg_file_id:
        track_data, download_link = await yam_client.get_track_with_download(full_yam_id)
        try:
            file = await bot.send_audio(
                chat_id=CHAT_ID,
                audio=URLInputFile(download_link),
                title=track_data.title,
                performer=track_data.artists,
                thumbnail=URLInputFile(track_data.cover_url) if track_data.cover_url else None,
                duration=track_data.duration,
            )
            tg_file_id = file.audio.file_id
            await db.save(db_yam_id, tg_file_id)
        except Exception as e:
            await bot.edit_message_text(
                inline_message_id=inline_message_id,
                text="❌Не удалось отправить трек\nПопробуйте снова",
            )
            logger.error(e)
            return
    else:
        track_data = await yam_client.get_track_data(full_yam_id)

    await bot.edit_message_media(
        media=InputMediaAudio(
            media=tg_file_id,
            title=track_data.title,
            performer=track_data.artists,
            thumbnail=URLInputFile(track_data.cover_url) if track_data.cover_url else None,
            duration=track_data.duration,
        ),
        inline_message_id=inline_message_id,
    )

    await bot.edit_message_caption(
        inline_message_id=inline_message_id,
        caption=f"<a href='{track_data.link}'>Я.Музыка</a>",
        parse_mode="HTML",
    )
