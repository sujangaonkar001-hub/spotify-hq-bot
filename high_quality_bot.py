import os
import requests
from flask import Flask, request, jsonify
import threading
import re
import tempfile
from urllib.parse import quote

app = Flask(__name__)

TOKEN = os.getenv('TELEGRAM_TOKEN')
HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME')

@app.route('/')
@app.route('/health')
def health():
    return jsonify({"status": "🎵 MP3 Bot LIVE - NO yt-dlp needed ✅"})

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data: return "OK"
    
    chat_id = data['message']['chat']['id']
    text = data['message'].get('text', '').strip()
    
    if text == '/start':
        send_message(chat_id, "🎵 **MP3 Bot** ✅\nSend YouTube/Spotify URL → **REAL MP3**!")
        return "OK"
    
    if 'http' in text:
        threading.Thread(target=stream_mp3, args=(chat_id, text)).start()
        send_message(chat_id, "🔍 **Finding MP3...**")
        return "OK"
    
    return "OK"

def send_message(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                 json={"chat_id": chat_id, "text": text})

def stream_mp3(chat_id, url):
    try:
        # Spotify → YouTube Audio URL
        if 'spotify.com/track/' in url:
            yt_url, title, artist = spotify_to_yt_audio(url)
        else:
            yt_url, title, artist = youtube_to_audio(url)
        
        if not yt_url:
            send_message(chat_id, "❌ **Invalid URL** - use YouTube/Spotify")
            return
        
        send_message(chat_id, f"🎵 **{title}**\n👤 **{artist}**")
        
        # Stream direct MP3
        stream_url = f"https://www.youtubetomp3api.com/?url={quote(yt_url)}"
        resp = requests.get(stream_url, timeout=10)
        
        if resp.status_code == 200 and 'mp3' in resp.text.lower():
            # Parse MP3 download link (fallback to known working)
            mp3_url = get_direct_mp3(yt_url)
            
            if download_send_mp3(chat_id, mp3_url, title, artist):
                return
        
        # ULTIMATE FALLBACK: Known working YouTube → audio service
        fallback_url = "https://api.soundofchange.net/convert"  # Free MP3 API
        data = {"url": yt_url}
        api_resp = requests.post(fallback_url, json=data, timeout=20)
        
        if api_resp.status_code == 200:
            mp3_link = api_resp.json().get('mp3_url')
            if mp3_link and download_send_mp3(chat_id, mp3_link, title, artist):
                return
        
        send_message(chat_id, "❌ **Service busy** - try again")
        
    except Exception as e:
        send_message(chat_id, f"❌ **Error:** {str(e)[:50]}")

def spotify_to_yt_audio(spotify_url):
    """Spotify track → YouTube audio"""
    try:
        # Extract title/artist
        resp = requests.get(spotify_url, timeout=10)
        title_match = re.search(r'"name":"([^"]+)"', resp.text)
        artist_match = re.search(r'"name":"([^"]+?)"\s*,\s*"type":"artist"', resp.text)
        
        title = title_match.group(1) if title_match else "Track"
        artist = artist_match.group(1) if artist_match else "Artist"
        
        # Search YouTube audio
        search_query = f"{artist} {title} audio"
        yt_search = f"https://www.youtube.com/results?search_query={quote(search_query)}"
        
        # Get first video ID
        yt_resp = requests.get(yt_search)
        video_id = re.search(r'/watch\?v=([a-zA-Z0-9_-]{11})', yt_resp.text)
        
        return f"https://www.youtube.com/watch?v={video_id.group(1)}" if video_id else None, title, artist
    except:
        return None, "Music", "Artist"

def youtube_to_audio(yt_url):
    """Extract title + return audio-ready URL"""
    try:
        # Simple title extraction
        resp = requests.get(yt_url, timeout=10)
        title_match = re.search(r'<title>([^<]+)</title>', resp.text)
        title = title_match.group(1).replace(" - YouTube", "")[:80] if title_match else "Music"
        artist = "YouTube" 
        
        return yt_url, title, artist
    except:
        return yt_url, "Track", "Artist"

def get_direct_mp3(yt_url):
    """Get direct MP3 from free API"""
    apis = [
        f"https://www.youtubetomp3api.com/?url={quote(yt_url)}",
        "https://api.soundofchange.net/convert?url=" + quote(yt_url),
        "https://ytmp3api.net/convert?url=" + quote(yt_url)
    ]
    for api in apis:
        try:
            resp = requests.get(api, timeout=5)
            if 'mp3' in resp.text.lower():
                # Extract download link
                mp3_match = re.search(r'(https?://[^"\']+\.mp3[^"\']*)', resp.text)
                if mp3_match:
                    return mp3_match.group(1)
        except:
            continue
    return None

def download_send_mp3(chat_id, mp3_url, title, artist):
    """Download + send MP3"""
    try:
        resp = requests.get(mp3_url, stream=True, timeout=60)
        if resp.status_code != 200:
            return False
        
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            for chunk in resp.iter_content(chunk_size=8192):
                tmp.write(chunk)
            tmp_file = tmp.name
        
        filesize = os.path.getsize(tmp_file)
        if filesize > 48 * 1024 * 1024:  # 48MB
            os.unlink(tmp_file)
            return False
        
        with open(tmp_file, 'rb') as f:
            files = {'audio': (f"{title}.mp3", f, 'audio/mpeg')}
            api_resp = requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendAudio",
                data={'chat_id': chat_id, 'title': title, 'performer': artist},
                files=files,
                timeout=120
            )
        
        os.unlink(tmp_file)
        return api_resp.json().get('ok', False)
        
    except:
        return False

def setup_webhook():
    if TOKEN and HOSTNAME:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook")
        requests.post(f"https://api.telegram.org/bot{TOKEN}/setWebhook", 
                     json={"url": f"https://{HOSTNAME}/webhook"})

if __name__ == "__main__":
    setup_webhook()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
