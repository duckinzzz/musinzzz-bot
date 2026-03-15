import logging
from dataclasses import dataclass
from typing import List

from yandex_music import Client, Track as YMTrack

from core.config import YAM_TOKEN

logger = logging.getLogger(__name__)

client = Client(YAM_TOKEN).init()


@dataclass
class YandexTrack:
    title: str
    artists: str
    link: str
    cover_url: str | None
    duration: int
    yandex_track_id: str

    def __init__(self, track: YMTrack):
        self.yandex_track_id = str(track.id)
        self.title = track.title
        self.artists = ", ".join([artist.name for artist in track.artists])
        self.link = f"https://music.yandex.ru/track/{self.yandex_track_id}"
        self.cover_url = "https://" + track.cover_uri.replace("%%", "400x400") if track.cover_uri else None
        self.duration = int(track.duration_ms / 1000) if track.duration_ms else 0

    def get_download_link(self) -> str:
        track = client.tracks([self.yandex_track_id])[0]
        info = track.get_specific_download_info(codec="mp3", bitrate_in_kbps=320)
        if info:
            link = info.get_direct_link()
            return link
        download_infos = track.get_download_info()
        if download_infos:
            link = download_infos[0].get_direct_link()
            return link
        logger.error(f"No download link available for track {self.yandex_track_id}")
        raise ValueError("No download info available")


def search(query: str) -> List[YandexTrack]:
    result = client.search(query, type_="track")
    if not result.tracks or not result.tracks.results:
        logger.warning(f"No results found for query: '{query}'")
        return []
    tracks = [YandexTrack(track) for track in result.tracks.results[:20]]
    return tracks


def get_track_data(track_id: str | int) -> YandexTrack:
    tracks = client.tracks([track_id])
    if not tracks or not tracks[0]:
        logger.error(f"Track {track_id} not found")
        raise ValueError(f"Track {track_id} not found")
    track = YandexTrack(tracks[0])
    return track
