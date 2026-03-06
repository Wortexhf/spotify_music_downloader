import os
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
    print("WARNING: Spotify credentials not found in .env")


def resolve_url(url):
    try:
        if "spotify.link" in url or "spoti.fi" in url:
            resp = requests.head(url, allow_redirects=True)
            return resp.url
        return url
    except:
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
        cover_url = track['album']['images'][0]['url'] if track['album']['images'] else None
        full_name = f"{artist} - {name}"
        duration_sec = track['duration_ms'] // 1000

        file_path = download_track(full_name, duration_hint=duration_sec)

        cover_path = None
        if cover_url:
            cover_filename = f"cover_{name[:30].replace(' ', '_')}.jpg"
            cover_path = download_cover(cover_url, cover_filename)

        if file_path and cover_path:
            set_mp3_cover(file_path, cover_path)

        return {
            "name": name,
            "artist": artist,
            "cover_url": cover_url,
            "full_name": full_name,
            "file_path": file_path,
            "cover_path": cover_path
        }
    except Exception as e:
        print(f"Error fetching track: {e}")
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
            track_cover = cover_url if is_album else (
                track['album']['images'][0]['url'] if track['album']['images'] else None
            )
            final_data.append({
                "name": name,
                "artist": artist,
                "cover_url": track_cover,
                "full_name": f"{artist} - {name}",
                "duration_sec": track.get('duration_ms', 0) // 1000
            })
        return final_data
    except Exception as e:
        print(f"Error fetching playlist/album: {e}")
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
            cover_url = track['album']['images'][0]['url'] if track['album']['images'] else None
            final_data.append({
                "name": name,
                "artist": artist,
                "cover_url": cover_url,
                "full_name": f"{artist} - {name}",
                "duration_sec": track.get('duration_ms', 0) // 1000
            })
        return final_data
    except Exception as e:
        print(f"Error fetching artist top tracks: {e}")
        return []


class MyLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        if "No supported JavaScript runtime" in msg:
            return
        try:
            print(f"WARNING: {msg}")
        except UnicodeEncodeError:
            print("WARNING: [non-printable characters]")

    def error(self, msg):
        try:
            print(f"ERROR: {msg}")
        except UnicodeEncodeError:
            print("ERROR: [non-printable characters]")


def download_track(search_query, output_dir=DOWNLOAD_DIR, duration_hint=None):
    os.makedirs(output_dir, exist_ok=True)
    outtmpl = os.path.join(output_dir, '%(title)s.%(ext)s')

    downloaded_file = []

    def progress_hook(d):
        if d['status'] == 'finished':
            path = d.get('filename', '')
            mp3_path = os.path.splitext(path)[0] + '.mp3'
            downloaded_file.append(mp3_path)
            print(f"HOOK: finished -> {mp3_path}")

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': outtmpl,
        'quiet': False,  # <-- змінили на False щоб бачити все
        'noplaylist': True,
        'ffmpeg_location': FFMPEG_PATH,
        'logger': MyLogger(),
        'progress_hooks': [progress_hook],
    }

    try:
        search_query_clean = f"{search_query} official audio"
        print(f"SEARCH: {search_query_clean}, duration_hint={duration_hint}")

        search_opts = {
            'quiet': False,
            'skip_download': True,
            'noplaylist': True,
            'logger': MyLogger(),
        }

        with yt_dlp.YoutubeDL(search_opts) as ydl:
            info = ydl.extract_info(f"ytsearch5:{search_query_clean}", download=False)

        best_url = None
        if info and 'entries' in info:
            entries = [e for e in info['entries'] if e and not e.get('is_live')]
            print(f"FOUND {len(entries)} entries:")
            for e in entries:
                print(f"  - {e.get('title')} | {e.get('duration')}s | {e.get('webpage_url')}")

            if duration_hint and entries:
                best = min(entries, key=lambda e: abs((e.get('duration') or 9999) - duration_hint))
            elif entries:
                best = entries[0]
            else:
                best = None

            if best:
                best_url = best['webpage_url']
                print(f"SELECTED: {best.get('title')} ({best.get('duration')}s)")

        if not best_url:
            print("ERROR: No suitable video found")
            return None

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(best_url, download=True)

        if downloaded_file and os.path.exists(downloaded_file[0]):
            print(f"Downloaded: {downloaded_file[0]}")
            return downloaded_file[0]

        all_mp3 = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith('.mp3')]
        if all_mp3:
            newest = max(all_mp3, key=os.path.getmtime)
            print(f"Downloaded (fallback): {newest}")
            return newest

        print("ERROR: No file found after download.")
        return None

    except Exception as e:
        print(f"Download error: {e}")
        return None


def download_cover(url, filename, output_dir=DOWNLOAD_DIR):
    try:
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            f.write(response.content)
        return filepath
    except Exception as e:
        print(f"Cover download error: {e}")
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
        return True
    except Exception as e:
        print(f"Error embedding cover: {e}")
        return False