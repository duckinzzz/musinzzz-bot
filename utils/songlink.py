from urllib.parse import quote

import aiohttp


async def fetch_songlink_data(url):
    api_url = (
        f"https://api.song.link/v1-alpha.1/links"
        f"?url={quote(url, safe='')}"
        f"&userCountry=US"
        f"&songIfSingle=true"
    )

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as response:
            response.raise_for_status()
            data = await response.json()

            links = data.get('linksByPlatform', {})
            yandex_track_id = links.get('yandex')['url'].split('/')[-1]
            songlink_url = data.get('pageUrl', {})

            if songlink_url:
                return yandex_track_id, songlink_url
            else:
                raise Exception('No song link found')
