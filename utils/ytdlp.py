import asyncio
import json
import logging
import re
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import yt_dlp
from yt_dlp.utils import DownloadError

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


class ProtectedTrackError(RuntimeError):
    pass


class _YtDlpLogger:
    def debug(self, message: str) -> None:
        logger.debug(message)

    def warning(self, message: str) -> None:
        logger.warning(message)

    def error(self, message: str) -> None:
        logger.debug(message)


TELEGRAM_AUDIO_EXTENSIONS = {"mp3", "m4a"}
STREAMING_PROTOCOL_MARKERS = ("m3u8", "f4m", "dash")
SOUNDCLOUD_RESOLVE_URL = "https://api-v2.soundcloud.com/resolve"
SOUNDCLOUD_HEADERS = {"User-Agent": "Mozilla/5.0"}


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


def _is_supported_direct_audio(format_info: dict) -> bool:
    return (
        _is_direct_file(format_info)
        and format_info.get("ext") in TELEGRAM_AUDIO_EXTENSIONS
    )


def _select_telegram_audio_format(info: dict) -> dict:
    formats = [
        fmt for fmt in info.get("formats", [])
        if _is_supported_direct_audio(fmt)
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


def _is_soundcloud_url(url: str) -> bool:
    return bool(re.match(DIRECT_EXTRACT_PATTERNS[0], url))


def _has_protected_soundcloud_streams(info: dict) -> bool:
    transcodings = (info.get("media") or {}).get("transcodings") or []
    for transcoding in transcodings:
        protocol = ((transcoding.get("format") or {}).get("protocol") or "").lower()
        if protocol.startswith(("cbc-", "ctr-")) or "encrypted" in protocol:
            return True
    return False


def _resolve_soundcloud_info(ydl: yt_dlp.YoutubeDL, url: str) -> dict | None:
    try:
        extractor = ydl.get_info_extractor("Soundcloud")
        extractor.initialize()
        client_id = getattr(extractor, "_CLIENT_ID", None)
    except Exception:
        return None

    if not client_id:
        return None

    query = urlencode({"url": url, "client_id": client_id})
    request = Request(f"{SOUNDCLOUD_RESOLVE_URL}?{query}", headers=SOUNDCLOUD_HEADERS)
    try:
        with urlopen(request, timeout=10) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None


def _is_protected_download_error(
    url: str,
    error: DownloadError,
    ydl: yt_dlp.YoutubeDL,
) -> bool:
    message = str(error).lower()
    if "drm" in message:
        return True
    if _is_soundcloud_url(url) and "http error 404" in message:
        info = _resolve_soundcloud_info(ydl, url)
        return bool(info and _has_protected_soundcloud_streams(info))
    return False


async def extract_track_info(url: str) -> ExternalTrack:
    def _extract():
        ydl_opts = {
            'format': 'bestaudio[ext=mp3]/bestaudio[ext=m4a]/bestaudio/best',
            'quiet': True,
            'logger': _YtDlpLogger(),
            'no_warnings': True,
            'noplaylist': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except DownloadError as e:
                if _is_protected_download_error(url, e, ydl):
                    raise ProtectedTrackError("Track is protected from download") from e
                raise
            selected_format = _select_telegram_audio_format(info)
            if not _is_supported_direct_audio(selected_format):
                raise ProtectedTrackError("Track has no direct downloadable audio")
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
