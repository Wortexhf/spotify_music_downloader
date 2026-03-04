from aiogram.filters import Command
from aiogram import types
from core.bot import dp

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "❓ **Help**\n\n"
        "1. **Send a link:** Copy a link from Spotify (Track or Album) and paste it here.\n"
        "2. **Wait:** Albums may take some time to process.\n\n"
        "⚠️ **Note:** Playlists and Artist profiles are currently not supported.\n\n"
        "Commands:\n"
        "/start - Restart bot\n"
        "/help - Show this message"
    )
    await message.answer(help_text, parse_mode="Markdown")