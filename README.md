# Spotify Downloader Bot

A Telegram bot that downloads tracks and albums from Spotify as MP3 with embedded cover art.

## How it works

1. Send a Spotify link to the bot
2. Bot fetches track metadata from Spotify API (including ISRC)
3. Audio is found on YouTube via ISRC for accurate matching
4. Cover art is resized and embedded into the MP3
5. Bot sends you the audio file in Telegram

## Setup

### Requirements
- Python 3.12+
- FFmpeg (place `ffmpeg.exe` and `ffprobe.exe` in project folder)
- Telegram Bot Token
- Spotify API credentials

### Install dependencies

```bash
pip install -r requirements.txt
```

### Environment variables

Create a `.env` file:

```
BOT_TOKEN=your_telegram_bot_token
SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
```

- Telegram token: https://t.me/BotFather
- Spotify credentials: https://developer.spotify.com/dashboard

### Run

```bash
python main.py
```

## Supported links

| Type | Example |
|------|---------|
| Track | `open.spotify.com/track/...` |
| Album | `open.spotify.com/album/...` |
| Playlist | `open.spotify.com/playlist/...` |
| Short link | `spotify.link/...` |

## Project structure

```
spotify_music_downloader/
├── main.py          # Bot + handlers
├── downloader.py    # Spotify API + YouTube download logic
├── requirements.txt
├── .env             # Credentials (not in git)
├── ffmpeg.exe
├── ffprobe.exe
├── downloads/       # Temporary files (auto-created)
└── logs/            # Log files (auto-created)
```