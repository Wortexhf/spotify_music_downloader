import os
import asyncio
from aiogram.types import FSInputFile

async def send_track(
    message,
    track_info,
    audio_path,
    cover_path,
    status_msg=None,
    send_photo_msg=True
):
    if not audio_path or not os.path.exists(audio_path):
        if status_msg:
            await status_msg.edit_text("❌ Download failed.")
        return False

    if status_msg:
        await status_msg.edit_text("🚀 Uploading...")

    if send_photo_msg and cover_path and os.path.exists(cover_path):
        await message.answer_photo(FSInputFile(cover_path))

    await message.answer_audio(
        FSInputFile(audio_path),
        caption=f"🎧 {track_info['full_name']}",
        performer=track_info['artist'],
        title=track_info['name'],
        thumbnail=FSInputFile(cover_path) if cover_path else None
    )

    if status_msg:
        await status_msg.delete()

    await asyncio.sleep(1)

    try:
        if os.path.exists(audio_path):
            os.remove(audio_path)
        if cover_path and os.path.exists(cover_path):
            os.remove(cover_path)
    except Exception:
        pass

    return True