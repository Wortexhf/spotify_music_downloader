import os
import logging
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp
import requests
from dotenv import load_dotenv
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

logger = logging.getLogger(__name__)

load_dotenv()
CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
FFMPEG_PATH = BASE_DIR

if CLIENT_ID and CLIENT_SECRET:
    auth_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    sp = spotipy.Spotify(auth_manager=auth_manager)
else:
    sp = None
    logger.warning("Spotify credentials not found in .env")


def resolve_url(url):
    try:
        if "spotify.link" in url or "spoti.fi" in url:
            resp = requests.head(url, allow_redirects=True)
            return resp.url
        return url
    except Exception as e:
        logger.warning(f"resolve_url error: {e}")
        return url


def get_track_info(spotify_url):
    if not sp:
        return None
    spotify_url = resolve_url(spotify_url)
    try:
        if "track" not in spotify_url:
            return None
        track = sp.track(spotify_url, market="US")
        name = track['name']
        artist = track['artists'][0]['name']
        isrc = track['external_ids'].get('isrc')
        cover_url = track['album']['images'][0]['url'] if track['album']['images'] else None
        full_name = f"{artist} - {name}"
        duration_sec = track['duration_ms'] // 1000

        logger.info(f"Track info fetched: {full_name} | duration={duration_sec}s | isrc={isrc}")

        return {
            "name": name,
            "artist": artist,
            "cover_url": cover_url,
            "full_name": full_name,
            "duration_sec": duration_sec,
            "isrc": isrc
        }
    except Exception as e:
        logger.error(f"Error fetching track: {e}")
        return None


def get_playlist_tracks(url):
    if not sp:
        return []
    url = resolve_url(url)
    try:
        if "album" in url:
            results = sp.album_tracks(url, market="US")
            album_info = sp.album(url, market="US")
            cover_url = album_info['images'][0]['url'] if album_info['images'] else None
            tracks_raw = results['items']
            is_album = True
        else:
            playlist_id = url.split("/playlist/")[1].split("?")[0]
            results = sp.playlist_tracks(playlist_id, market="US")
            tracks_raw = results['items']
            is_album = False
            cover_url = None

        while results['next']:
            results = sp.next(results)
            tracks_raw.extend(results['items'])

        final_data = []
        for item in tracks_raw:
            track = item if is_album else item['track']
            if not track:
                continue
            name = track['name']
            artist = track['artists'][0]['name']
            isrc = track.get('external_ids', {}).get('isrc')
            track_cover = cover_url if is_album else (
                track['album']['images'][0]['url'] if track['album']['images'] else None
            )
            final_data.append({
                "name": name,
                "artist": artist,
                "cover_url": track_cover,
                "full_name": f"{artist} - {name}",
                "duration_sec": track.get('duration_ms', 0) // 1000,
                "isrc": isrc
            })

        logger.info(f"Playlist/album fetched: {len(final_data)} tracks from {url}")
        return final_data
    except Exception as e:
        logger.error(f"Error fetching playlist/album: {e}")
        return []


def get_artist_top_tracks(url):
    if not sp:
        return []
    url = resolve_url(url)
    try:
        artist_id = url.split("/artist/")[1].split("?")[0]
        results = sp.artist_top_tracks(artist_id, country="US")
        final_data = []
        for track in results['tracks']:
            name = track['name']
            artist = track['artists'][0]['name']
            isrc = track.get('external_ids', {}).get('isrc')
            cover_url = track['album']['images'][0]['url'] if track['album']['images'] else None
            final_data.append({
                "name": name,
                "artist": artist,
                "cover_url": cover_url,
                "full_name": f"{artist} - {name}",
                "duration_sec": track.get('duration_ms', 0) // 1000,
                "isrc": isrc
            })

        logger.info(f"Artist top tracks fetched: {len(final_data)} tracks")
        return final_data
    except Exception as e:
        logger.error(f"Error fetching artist top tracks: {e}")
        return []


class MyLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        if "No supported JavaScript runtime" in msg:
            return
        logger.warning(f"yt-dlp: {msg}")

    def error(self, msg):
        logger.error(f"yt-dlp: {msg}")


UNWANTED_KEYWORDS = ['slowed', 'reverb', 'sped up', 'nightcore', 'remix', 'cover', 'karaoke', 'instrumental', 'ringtone']


def search_youtube(query, search_opts, count=5):
    with yt_dlp.YoutubeDL(search_opts) as ydl:
        info = ydl.extract_info(f"ytsearch{count}:{query}", download=False)
    if info and 'entries' in info:
        return [e for e in info['entries'] if e and not e.get('is_live')]
    return []


def title_matches(title, artist, track_name):
    title_lower = title.lower()
    artist_lower = artist.lower()
    track_lower = track_name.lower()
    return artist_lower in title_lower and track_lower in title_lower


def pick_best(entries, duration_hint, artist="", track_name=""):
    if not entries:
        return None

    track_name_lower = track_name.lower()
    is_special = any(w in track_name_lower for w in UNWANTED_KEYWORDS)

    if not is_special:
        filtered = [
            e for e in entries
            if not any(w in (e.get('title') or '').lower() for w in UNWANTED_KEYWORDS)
        ]
        if filtered:
            entries = filtered
            logger.debug(f"Filtered to {len(entries)} entries after removing slowed/remix/etc")

    # Пріоритет — entries де title містить і артиста і назву треку
    if artist and track_name:
        matched = [
            e for e in entries
            if title_matches(e.get('title', ''), artist, track_name)
        ]
        if matched:
            entries = matched
            logger.debug(f"Narrowed to {len(entries)} entries matching artist+track name")

    if duration_hint:
        return min(entries, key=lambda e: abs((e.get('duration') or 9999) - duration_hint))
    return entries[0]


def download_track(search_query, output_dir=DOWNLOAD_DIR, duration_hint=None, isrc=None, artist=None, track_name=None):
    os.makedirs(output_dir, exist_ok=True)
    outtmpl = os.path.join(output_dir, '%(title)s.%(ext)s')

    downloaded_file = []

    def progress_hook(d):
        if d['status'] == 'finished':
            path = d.get('filename', '')
            mp3_path = os.path.splitext(path)[0] + '.mp3'
            downloaded_file.append(mp3_path)
            logger.info(f"Download finished: {mp3_path}")

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': outtmpl,
        'quiet': True,
        'noplaylist': True,
        'ffmpeg_location': FFMPEG_PATH,
        'logger': MyLogger(),
        'progress_hooks': [progress_hook],
    }

    search_opts = {
        'quiet': True,
        'skip_download': True,
        'noplaylist': True,
        'logger': MyLogger(),
    }

    try:
        entries = []

        if isrc:
            logger.info(f"Searching by ISRC: {isrc}")
            entries = search_youtube(isrc, search_opts, count=3)
            if entries:
                logger.info(f"ISRC search found {len(entries)} result(s)")

        if not entries:
            query = f"{artist} {track_name} official audio" if artist and track_name else f"{search_query} official audio"
            logger.info(f"Searching by query: {query}")
            entries = search_youtube(query, search_opts, count=8)

        logger.info(f"Found {len(entries)} entries for '{search_query}':")
        for e in entries:
            logger.info(f"  - {e.get('title')} | {e.get('duration')}s | {e.get('webpage_url')}")

        best = pick_best(entries, duration_hint, artist=artist or "", track_name=track_name or search_query)

        if not best:
            logger.error("No suitable video found")
            return None

        best_url = best['webpage_url']
        logger.info(f"Selected: {best.get('title')} ({best.get('duration')}s)")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(best_url, download=True)

        if downloaded_file and os.path.exists(downloaded_file[0]):
            logger.info(f"Downloaded: {downloaded_file[0]}")
            return downloaded_file[0]

        all_mp3 = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith('.mp3')]
        if all_mp3:
            newest = max(all_mp3, key=os.path.getmtime)
            logger.info(f"Downloaded (fallback): {newest}")
            return newest

        logger.error("No file found after download.")
        return None

    except Exception as e:
        logger.error(f"Download error: {e}")
        return None


def download_cover(url, filename, output_dir=DOWNLOAD_DIR):
    try:
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            f.write(response.content)
        logger.debug(f"Cover downloaded: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Cover download error: {e}")
        return None


def set_mp3_cover(audio_path, cover_path):
    try:
        audio = MP3(audio_path, ID3=ID3)
        try:
            audio.add_tags()
        except error:
            pass
        with open(cover_path, 'rb') as albumart:
            audio.tags.add(APIC(
                encoding=3,
                mime='image/jpeg',
                type=3,
                desc=u'Cover',
                data=albumart.read()
            ))
        audio.save()
        logger.debug(f"Cover embedded into {audio_path}")
        return True
    except Exception as e:
        logger.error(f"Error embedding cover: {e}")
        return False