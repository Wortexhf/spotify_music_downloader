import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, FSInputFile
from dotenv import load_dotenv
import downloader

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "bot.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"Hey, {message.from_user.first_name}!\n\n"
        "I'm a Spotify Downloader Bot\n"
        "I download music in high quality with cover art.\n\n"
        "Supported links:\n"
        "- Track: open.spotify.com/track/...\n"
        "- Album: open.spotify.com/album/...\n"
        "- Playlist: open.spotify.com/playlist/...\n\n"
        "Just send me a link!"
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Help\n\n"
        "Send a Spotify link and I'll download it as MP3 with cover art.\n\n"
        "Commands:\n"
        "/start - restart the bot\n"
        "/help - show this message"
    )


@dp.message(F.text.contains("spotify"))
async def handle_spotify(message: Message):
    url = downloader.extract_url(message.text)
    url = await asyncio.to_thread(downloader.resolve_url, url)

    if "/track/" in url:
        status = await message.answer("Processing link...")
        track_info = await asyncio.to_thread(downloader.get_track_info, url)

        if not track_info:
            await status.edit_text("Track not found or invalid link.")
            return

        await status.edit_text(f"Downloading: {track_info['full_name']}")
        audio_path, cover_path = await asyncio.to_thread(downloader.prepare_track, track_info, DOWNLOAD_DIR)
        await send_track(message, track_info, audio_path, cover_path, status)

    elif "/album/" in url or "/playlist/" in url:
        status = await message.answer("Analyzing...")
        tracks = await asyncio.to_thread(downloader.get_collection_tracks, url)

        if not tracks:
            await status.edit_text("Failed to load album/playlist.")
            return

        await status.edit_text(f"Found {len(tracks)} tracks. Downloading...")

        for i, track in enumerate(tracks, 1):
            try:
                await status.edit_text(f"{i}/{len(tracks)}: {track['full_name']}")
                audio_path, cover_path = await asyncio.to_thread(downloader.prepare_track, track, DOWNLOAD_DIR)
                await send_track(message, track, audio_path, cover_path, status_msg=None)
            except Exception as e:
                logger.error(f"Error on track {track['full_name']}: {e}")
                continue

        await status.edit_text(f"Done! ({len(tracks)} tracks)")

    else:
        await message.answer("Unknown link. Only track, album and playlist links are supported.")


async def send_track(message: Message, track_info: dict, audio_path: str, cover_path: str, status_msg=None):
    if not audio_path or not os.path.exists(audio_path):
        if status_msg:
            await status_msg.edit_text("Download failed.")
        return

    if status_msg:
        await status_msg.edit_text("Uploading...")

    if cover_path and os.path.exists(cover_path):
        await message.answer_photo(
            FSInputFile(cover_path),
            caption=f"{track_info['full_name']}"
        )

    await message.answer_audio(
        FSInputFile(audio_path),
        performer=track_info['artist'],
        title=track_info['name'],
        thumbnail=FSInputFile(cover_path) if cover_path and os.path.exists(cover_path) else None
    )

    if status_msg:
        await status_msg.delete()

    await asyncio.sleep(1)

    for path in [audio_path, cover_path]:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception:
            pass


async def main():
    logger.info("Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())