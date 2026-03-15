import asyncio
import logging
from dataclasses import dataclass
from typing import List, Callable, Any, TypeVar

from yandex_music import ClientAsync, Track as YMTrack
from yandex_music.exceptions import NetworkError

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_async(retries: int = 3, delay: float = 1.0):
    def decorator(func: Callable[..., Any]):
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except NetworkError as e:
                    last_exception = e
                    if attempt < retries - 1:
                        wait_time = delay * (2 ** attempt)
                        logger.warning(
                            f"NetworkError (attempt {attempt + 1}/{retries}): {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
            raise last_exception

        return wrapper

    return decorator


class YandexMusicClient:
    def __init__(self, token: str) -> None:
        self._token = token
        self._client: ClientAsync | None = None

    async def init(self) -> None:
        if self._client is None:
            self._client = await ClientAsync(self._token).init()
            logger.info("Yandex Music client initialized")

    @property
    def client(self) -> ClientAsync:
        if self._client is None:
            raise RuntimeError("Yandex Music client not initialized")
        return self._client

    @retry_async(retries=3, delay=1.0)
    async def search(self, query: str) -> List["YandexTrack"]:
        result = await self.client.search(query, type_="track")
        if not result or not result.tracks or not result.tracks.results:
            logger.warning(f"No results found for query: '{query}'")
            return []
        return [YandexTrack(track) for track in result.tracks.results[:20]]

    @retry_async(retries=3, delay=1.0)
    async def get_track_data(self, track_id: str | int) -> "YandexTrack":
        tracks = await self.client.tracks([track_id])
        if not tracks or not tracks[0]:
            logger.error(f"Track {track_id} not found")
            raise ValueError(f"Track {track_id} not found")
        return YandexTrack(tracks[0])

    @retry_async(retries=3, delay=1.0)
    async def get_track_with_download(self, track_id: str | int) -> tuple["YandexTrack", str]:
        tracks = await self.client.tracks([track_id])
        if not tracks or not tracks[0]:
            logger.error(f"Track {track_id} not found")
            raise ValueError(f"Track {track_id} not found")
        track = YandexTrack(tracks[0])
        link = await track.get_download_link(tracks[0])
        return track, link


@dataclass
class YandexTrack:
    yandex_track_id: str
    title: str
    artists: str
    link: str
    cover_url: str | None
    duration: int

    def __init__(self, track: YMTrack) -> None:
        object.__setattr__(self, "yandex_track_id", str(track.id))
        object.__setattr__(self, "title", track.title)
        object.__setattr__(self, "artists", ", ".join([a.name for a in track.artists]))
        object.__setattr__(self, "link", f"https://music.yandex.ru/track/{track.id}")
        object.__setattr__(
            self,
            "cover_url",
            "https://" + track.cover_uri.replace("%%", "400x400") if track.cover_uri else None,
        )
        object.__setattr__(
            self,
            "duration",
            int(track.duration_ms / 1000) if track.duration_ms else 0,
        )

    @retry_async(retries=3, delay=1.0)
    async def get_download_link(self, track: YMTrack) -> str:
        info = await track.get_specific_download_info_async(codec="mp3", bitrate_in_kbps=320)
        if info:
            return await info.get_direct_link_async()
        download_infos = await track.get_download_info_async()
        if download_infos:
            return await download_infos[0].get_direct_link_async()
        logger.error(f"No download link available for track {self.yandex_track_id}")
        raise ValueError("No download info available")
