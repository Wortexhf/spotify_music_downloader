from aiogram.filters import CommandStart
from aiogram import types
from core.bot import dp

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    welcome_text = (
        f"👋 **Hello, {message.from_user.first_name}!**\n\n"
        "I am a **Spotify Downloader Bot**. 🎵\n"
        "I can download music in high quality with cover art.\n\n"
        "**Supported links:**\n"
        "🔹 **Track:** `open.spotify.com/track/...`\n"
        "🔹 **Album:** `open.spotify.com/album/...`\n\n"
        "🚀 **Just send me a link to start!**"
    )
    await message.answer(welcome_text, parse_mode="Markdown")