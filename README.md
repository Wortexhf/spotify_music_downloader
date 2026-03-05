# 🎵 Spotify Downloader Bot

A Telegram bot that downloads tracks and albums from Spotify in MP3 format with embedded cover art.

## How it works

1. You send a Spotify link to the bot
2. The bot fetches track metadata from the Spotify API
3. Audio is downloaded from YouTube via yt-dlp
4. Cover art is embedded into the MP3 file
5. The bot sends you the audio file directly in Telegram

## Installation

### Requirements
- Python 3.10+
- FFmpeg (place in project folder, see below)
- Telegram Bot Token
- Spotify API credentials

### Dependencies

```bash
pip install aiogram spotipy yt-dlp requests mutagen python-dotenv
```

### FFmpeg setup

Download FFmpeg and place it in the project folder:

```
spotify_bot/
├── ffmpeg/
│   └── bin/
│       ├── ffmpeg.exe
│       └── ffprobe.exe
├── bot.py
├── spotifydata.py
└── ...
```

Download FFmpeg: https://ffmpeg.org/download.html

### Environment variables

Create a `.env` file in the project root:

```env
BOT_TOKEN=your_telegram_bot_token
SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
```

Get Telegram token: https://t.me/BotFather

Get Spotify credentials: https://developer.spotify.com/dashboard

## Usage

```bash
python bot.py
```

Then open your bot in Telegram and send a Spotify link.

## Supported link types

| Type | Example |
|------|---------|
| Track | `open.spotify.com/track/...` |
| Album | `open.spotify.com/album/...` |
| Short link | `spotify.link/...` or `spoti.fi/...` |

Playlists and artist profiles are not currently supported.

## Project structure

```
spotify_bot/
├── bot.py           # Telegram bot, message handlers
├── spotifydata.py   # Spotify API, yt-dlp download logic
├── ffmpeg/          # FFmpeg binaries (not in git)
├── downloads/       # Temporary download folder (auto-created, not in git)
└── .env             # Credentials (not in git)
```

## .gitignore

```
.venv/
downloads/
ffmpeg/
.env
__pycache__/
*.pyc
```

## Dependencies

| Library | Purpose |
|---------|---------|
| `aiogram` | Telegram bot framework |
| `spotipy` | Spotify API client |
| `yt-dlp` | Audio downloading from YouTube |
| `mutagen` | Embedding cover art into MP3 |
| `requests` | HTTP requests |
| `python-dotenv` | Loading `.env` variables |