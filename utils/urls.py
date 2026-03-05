import re 
import requests

def extract_url(text):
    url_pattern = r"(https?://[^\s]+)"
    match = re.search(url_pattern, text)
    if match:
        return match.group(0)
    return text.strip()

def resolve_url(url):
    try:
        if "spotify.link" in url or "spoti.fi" in url:
            resp = requests.head(url, allow_redirects=True)
            return resp.url
        return url
    except:
        return url