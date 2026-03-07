import os
import re
import logging
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp
from dotenv import load_dotenv
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error as ID3Error

load_dotenv()

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
FFMPEG_PATH = BASE_DIR

CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")

if CLIENT_ID and CLIENT_SECRET:
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    ))
else:
    sp = None
    logger.warning("Spotify credentials not found in .env")

UNWANTED = [
    'slowed', 'reverb', 'sped up', 'nightcore', 'remix',
    'cover', 'karaoke', 'instrumental', 'ringtone', 'loop', '1 hour'
]


# ── URL helpers ────────────────────────────────────────────────────────────────

def extract_url(text: str) -> str:
    match = re.search(r"(https?://[^\s]+)", text)
    return match.group(0) if match else text.strip()


def resolve_url(url: str) -> str:
    try:
        if "spotify.link" in url or "spoti.fi" in url:
            return requests.head(url, allow_redirects=True).url
        return url
    except Exception as e:
        logger.warning(f"resolve_url error: {e}")
        return url


def _track_to_dict(track: dict, cover_url: str | None) -> dict:
    name = track['name']
    artists = [a['name'] for a in track['artists']]
    isrc = track.get('external_ids', {}).get('isrc')
    track_cover = cover_url or (
        track.get('album', {}).get('images', [{}])[0].get('url') if track.get('album') else None
    )
    return {
        "name": name,
        "artist": artists[0],
        "artists": artists,
        "cover_url": track_cover,
        "full_name": f"{artists[0]} - {name}",
        "duration_sec": track.get('duration_ms', 0) // 1000,
        "isrc": isrc
    }


# ── Spotify ────────────────────────────────────────────────────────────────────

def get_track_info(spotify_url: str) -> dict | None:
    if not sp:
        return None
    spotify_url = resolve_url(spotify_url)
    try:
        track = sp.track(spotify_url, market="US")
        result = _track_to_dict(track, None)
        logger.info(f"Track fetched: {result['full_name']} | {result['duration_sec']}s | isrc={result['isrc']}")
        return result
    except Exception as e:
        logger.error(f"get_track_info error: {e}")
        return None


def get_collection_tracks(url: str) -> list:
    if not sp:
        return []
    url = resolve_url(url)
    try:
        if "/album/" in url:
            album_id = url.split("/album/")[1].split("?")[0]
            album_info = sp.album(album_id, market="US")
            cover_url = album_info['images'][0]['url'] if album_info['images'] else None

            # Збираємо всі треки з пагінацією
            tracks_raw = album_info['tracks']['items']
            next_page = album_info['tracks'].get('next')
            while next_page:
                page = sp.next(album_info['tracks'])
                tracks_raw.extend(page['items'])
                next_page = page.get('next')

            # album_tracks не має external_ids — запитуємо кожен трек окремо через sp.track()
            final = []
            for t in tracks_raw:
                if not t:
                    continue
                try:
                    full_track = sp.track(t['id'], market="US")
                    final.append(_track_to_dict(full_track, cover_url))
                except Exception as e:
                    logger.warning(f"Failed to fetch track {t.get('name')}: {e}")
                    # Fallback без ISRC
                    final.append(_track_to_dict(t, cover_url))

        else:
            playlist_id = url.split("/playlist/")[1].split("?")[0]
            results = sp.playlist_tracks(playlist_id, market="US")
            tracks_raw = results['items']
            while results['next']:
                results = sp.next(results)
                tracks_raw.extend(results['items'])

            final = []
            for item in tracks_raw:
                track = item.get('track')
                if not track:
                    continue
                final.append(_track_to_dict(track, None))

        logger.info(f"Collection fetched: {len(final)} tracks from {url}")
        return final
    except Exception as e:
        logger.error(f"get_collection_tracks error: {e}")
        return []


# ── YouTube search ─────────────────────────────────────────────────────────────

class _YTLogger:
    def debug(self, msg): pass
    def warning(self, msg):
        if "No supported JavaScript runtime" not in msg:
            logger.warning(f"yt-dlp: {msg}")
    def error(self, msg):
        logger.error(f"yt-dlp: {msg}")


def _search_youtube(query: str, count: int = 8) -> list:
    opts = {'quiet': True, 'skip_download': True, 'noplaylist': True, 'logger': _YTLogger()}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch{count}:{query}", download=False)
    if info and 'entries' in info:
        return [e for e in info['entries'] if e and not e.get('is_live')]
    return []


def _pick_best(entries: list, artist: str, track_name: str, duration_hint: int | None):
    if not entries:
        return None

    track_lower = track_name.lower()
    artist_lower = artist.lower()
    is_special = any(w in track_lower for w in UNWANTED)

    if not is_special:
        filtered = [e for e in entries if not any(w in (e.get('title') or '').lower() for w in UNWANTED)]
        if filtered:
            entries = filtered
            logger.debug(f"After unwanted filter: {len(entries)} entries")

    matched = [
        e for e in entries
        if track_lower in (e.get('title') or '').lower()
        and artist_lower in (e.get('title') or '').lower()
    ]
    if matched:
        entries = matched
        logger.debug(f"After artist+track match: {len(entries)} entries")

    if duration_hint:
        return min(entries, key=lambda e: abs((e.get('duration') or 9999) - duration_hint))
    return entries[0]


# ── Download ───────────────────────────────────────────────────────────────────

def download_audio(track_info: dict, output_dir: str = DOWNLOAD_DIR) -> str | None:
    os.makedirs(output_dir, exist_ok=True)

    name = track_info['name']
    artist = track_info['artist']
    duration_hint = track_info.get('duration_sec')
    isrc = track_info.get('isrc')

    downloaded_file = []

    def progress_hook(d):
        if d['status'] == 'finished':
            mp3 = os.path.splitext(d.get('filename', ''))[0] + '.mp3'
            downloaded_file.append(mp3)
            logger.info(f"Download finished: {mp3}")

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'quiet': True,
        'noplaylist': True,
        'ffmpeg_location': FFMPEG_PATH,
        'logger': _YTLogger(),
        'progress_hooks': [progress_hook],
    }

    try:
        entries = []

        if isrc:
            logger.info(f"Searching by ISRC: {isrc}")
            entries = _search_youtube(isrc, count=5)
            if entries:
                logger.info(f"ISRC found {len(entries)} result(s)")

        if not entries:
            query = f"{artist} {name} official audio"
            logger.info(f"Searching by query: {query}")
            entries = _search_youtube(query, count=8)

        logger.info(f"Found {len(entries)} entries for '{artist} - {name}':")
        for e in entries:
            logger.info(f"  [{e.get('duration')}s] {e.get('title')} | {e.get('webpage_url')}")

        best = _pick_best(entries, artist, name, duration_hint)
        if not best:
            logger.error(f"No suitable video found for '{artist} - {name}'")
            return None

        logger.info(f"Selected: {best.get('title')} ({best.get('duration')}s)")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(best['webpage_url'], download=True)

        if downloaded_file and os.path.exists(downloaded_file[0]):
            return downloaded_file[0]

        all_mp3 = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith('.mp3')]
        return max(all_mp3, key=os.path.getmtime) if all_mp3 else None

    except Exception as e:
        logger.error(f"download_audio error: {e}")
        return None


def download_cover(url: str, filename: str, output_dir: str = DOWNLOAD_DIR) -> str | None:
    try:
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        with open(filepath, 'wb') as f:
            f.write(r.content)
        return filepath
    except Exception as e:
        logger.error(f"download_cover error: {e}")
        return None


def embed_cover(audio_path: str, cover_path: str) -> bool:
    try:
        audio = MP3(audio_path, ID3=ID3)
        try:
            audio.add_tags()
        except ID3Error:
            pass
        with open(cover_path, 'rb') as f:
            audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=f.read()))
        audio.save()
        return True
    except Exception as e:
        logger.error(f"embed_cover error: {e}")
        return False


def prepare_track(track_info: dict, output_dir: str = DOWNLOAD_DIR) -> tuple[str | None, str | None]:
    safe_name = "".join(c for c in track_info['name'] if c.isalnum() or c in (' ', '.', '_')).strip()

    cover_path = None
    if track_info.get('cover_url'):
        cover_path = download_cover(track_info['cover_url'], f"{safe_name}_cover.jpg", output_dir)

    audio_path = download_audio(track_info, output_dir)

    if audio_path and cover_path and os.path.exists(cover_path):
        embed_cover(audio_path, cover_path)

    return audio_path, cover_path