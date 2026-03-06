import asyncio
from services.spotify_service import get_track_info, get_album_tracks
from utils.urls import extract_url, resolve_url
from aiogram import F
from core.bot import dp
from aiogram.types import Message
from services.track_sender import send_track
import spotifydata

@dp.message(F.text.contains("spotify"))
async def handle_spotify_link(message: Message):
    status_msg = await message.answer("🔎 Processing link...")

    raw_url = extract_url(message.text)
    real_url = await asyncio.to_thread(resolve_url, raw_url)

    if "/track/" in real_url:
        track_info = await get_track_info(real_url)

        if track_info:
            await send_track(
                message,
                track_info,
                audio_path=track_info.get('file_path'),
                cover_path=track_info.get('cover_path'),
                status_msg=status_msg,
                send_photo_msg=True
            )
        else:
            await status_msg.edit_text("❌ Track not found or invalid link.")

    elif "/album/" in real_url:
        await status_msg.edit_text("🔍 Analyzing album...")

        tracks = await get_album_tracks(real_url)

        if not tracks:
            await status_msg.edit_text("❌ Failed to load album.")
            return

        await status_msg.edit_text(f"📀 Found {len(tracks)} tracks. Downloading...")

        for i, track in enumerate(tracks, 1):
            try:
                await status_msg.edit_text(f"⬇️ Downloading {i}/{len(tracks)}: {track['full_name']}")

                file_path = await asyncio.to_thread(
                    spotifydata.download_track,
                    track['full_name']
                )

                cover_path = None
                if track.get('cover_url'):
                    cover_filename = f"cover_{track['name'][:30].replace(' ', '_')}.jpg"
                    cover_path = await asyncio.to_thread(
                        spotifydata.download_cover,
                        track['cover_url'],
                        cover_filename
                    )

                if file_path and cover_path:
                    await asyncio.to_thread(spotifydata.set_mp3_cover, file_path, cover_path)

                await send_track(
                    message,
                    track,
                    audio_path=file_path,
                    cover_path=cover_path,
                    status_msg=None,
                    send_photo_msg=True
                )

            except Exception as e:
                print(f"Error sending track {track['full_name']}: {e}")
                continue

        await status_msg.edit_text(f"✅ Album sent! ({len(tracks)} tracks)")