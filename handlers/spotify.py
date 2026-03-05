import asyncio
from services.spotify_service import get_track_info, get_album_tracks
from utils.urls import extract_url, resolve_url
from aiogram import F
from core.bot import dp
from aiogram.types import Message
from services.track_sender import send_track
from services.track_downloader import prepare_track
from config import DOWNLOAD_DIR

@dp.message(F.text.contains("spotify"))
async def handle_spotify_link(message: Message):
    status_msg = await message.answer("🔎 Processing link...")

    raw_url = extract_url(message.text)
    real_url = await asyncio.to_thread(resolve_url, raw_url)

    if "/track/" in real_url:
        track_info = await get_track_info(real_url)

        if track_info:
            await status_msg.edit_text("⏳ Downloading track...")
            audio_path, cover_path = await prepare_track(track_info, DOWNLOAD_DIR)

            if audio_path:
                await send_track(
                    message,
                    track_info,
                    audio_path,
                    cover_path,
                    status_msg=status_msg,
                    send_photo_msg=True
                )
            else:
                await status_msg.edit_text("❌ Failed to download track.")
        else:
            await status_msg.edit_text("❌ Track not found or invalid link.")

    elif "/album/" in real_url:
        await status_msg.edit_text("🔍 Analyzing album...")

        tracks = await get_album_tracks(real_url)

        if not tracks:
            await status_msg.edit_text("❌ Failed to load album.")
            return

        total = len(tracks)
        for i, track_info in enumerate(tracks, 1):
            await status_msg.edit_text(f"⏳ Downloading track {i}/{total}...")
            audio_path, cover_path = await prepare_track(track_info, DOWNLOAD_DIR)

            if audio_path:
                await send_track(
                    message,
                    track_info,
                    audio_path,
                    cover_path,
                    status_msg=None,  # Do not delete/update global status_msg in send_track for albums
                    send_photo_msg=False
                )
            else:
                await message.answer(f"❌ Failed to download: {track_info['full_name']}")

        await status_msg.edit_text(f"✅ Finished! Sent {total} tracks.")
 