from aiogram.filters import Command
from aiogram import types
from core.bot import dp

@dp.message(F.text.contains("spotify"))
async def handle_spotify_link(message: types.Message):
    status_msg = await message.answer("🔎 Processing link...")

    raw_url = extract_url(message.text)
    real_url = await asyncio.to_thread(resolve_url, raw_url)
    print(f"DEBUG: Processing URL: {real_url}")

    if "/track/" in real_url:
        track_info = await asyncio.to_thread(spotifydata.get_track_info, real_url)
        if track_info:
            await download_and_send_track(message, track_info, status_msg=status_msg, send_photo_msg=True)
        else:
            await status_msg.edit_text("❌ Track not found or invalid link.")

    elif "/album/" in real_url:
        await status_msg.edit_text("🔍 Analyzing album...")

        tracks = await asyncio.to_thread(spotifydata.get_playlist_tracks, real_url)

        if not tracks:
            await status_msg.edit_text("❌ Failed to load album.")
            return