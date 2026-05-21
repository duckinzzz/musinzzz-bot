import asyncio
import logging
import re
from dataclasses import dataclass

import yt_dlp

logger = logging.getLogger(__name__)

DIRECT_EXTRACT_PATTERNS = [
    r"https://soundcloud\.com/[^/]+/[^/]+",
    r"https://(www\.)?youtube\.com/watch\?v=",
    r"https://youtu\.be/[^/]+",
]


@dataclass
class ExternalTrack:
    url: str
    title: str
    artist: str
    duration: int
    thumbnail: str | None
    direct_url: str
    http_headers: dict[str, str]
    filename: str


TELEGRAM_AUDIO_EXTENSIONS = {"mp3", "m4a"}
STREAMING_PROTOCOL_MARKERS = ("m3u8", "f4m", "dash")


def is_direct_extract_url(url: str) -> bool:
    return any(re.match(pattern, url) for pattern in DIRECT_EXTRACT_PATTERNS)


def _safe_filename(title: str, ext: str | None) -> str:
    safe_title = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", title).strip(" .")
    safe_ext = ext or "mp3"
    return f"{safe_title or 'audio'}.{safe_ext}"


def _number(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _is_direct_file(format_info: dict) -> bool:
    protocol = (format_info.get("protocol") or "").lower()
    return bool(format_info.get("url")) and not any(
        marker in protocol for marker in STREAMING_PROTOCOL_MARKERS
    )


def _select_telegram_audio_format(info: dict) -> dict:
    formats = [
        fmt for fmt in info.get("formats", [])
        if _is_direct_file(fmt) and fmt.get("ext") in TELEGRAM_AUDIO_EXTENSIONS
    ]
    if not formats:
        return info

    return max(
        formats,
        key=lambda fmt: (
            fmt.get("ext") == "mp3",
            _number(fmt.get("abr") or fmt.get("tbr")),
        ),
    )


async def extract_track_info(url: str) -> ExternalTrack:
    def _extract():
        ydl_opts = {
            'format': 'bestaudio[ext=mp3]/bestaudio[ext=m4a]/bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            selected_format = _select_telegram_audio_format(info)
            title = info.get('title', 'Unknown')
            ext = selected_format.get('ext') or info.get('ext')
            return ExternalTrack(
                url=url,
                title=title,
                artist=info.get('uploader', 'Unknown'),
                duration=int(info.get('duration', 0)) if info.get('duration') else 0,
                thumbnail=info.get('thumbnail'),
                direct_url=selected_format.get('url') or info.get('url'),
                http_headers=selected_format.get('http_headers') or info.get('http_headers') or {},
                filename=_safe_filename(title, ext),
            )

    return await asyncio.to_thread(_extract)
