import asyncio
import os
import spotifydata

async def prepare_track(track_info: dict, download_dir: str) -> tuple[str|None|str|None]:
    safe_name = "".join(
        c for c in track_info['name']
        if c.isalnum() or c in (' ', '.', '_')
    ).strip()

    cover_filename = f"{safe_name}_cover.jpg"

    cover_path = None
    if track_info.get('cover_url'):
        cover_path = await asyncio.to_thread(
            spotifydata.download_cover,
            track_info['cover_url'],
            cover_filename,
            download_dir
        )

    search_query = f"{track_info['artist']} - {track_info['name']}"

    audio_path = await asyncio.to_thread(
        spotifydata.download_track,
        search_query,
        download_dir
    )

    if cover_path and os.path.exists(cover_path):
        await asyncio.to_thread(
            spotifydata.set_mp3_cover,
            audio_path,
            cover_path
        )

    return audio_path, cover_path