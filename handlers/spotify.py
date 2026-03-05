import asyncio
from services.spotify_service import get_track_info, get_album_tracks
from utils.urls import extract_url, resolve_url
from aiogram import F
from core.bot import dp
from aiogram.types import Message
from services.track_sender import send_track

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