import asyncio
import spotifydata

async def get_track_info(url: str):
    return await asyncio.to_thread(
        spotifydata.get_track_info,
        url
    )

async def get_album_tracks(url: str):
    return await asyncio.to_thread(
        spotifydata.get_playlist_tracks,
        url
    )