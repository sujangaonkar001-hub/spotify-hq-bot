import os
import requests
from flask import Flask, request, jsonify
import threading
import yt_dlp
import re
import json

app = Flask(__name__)

TOKEN = os.getenv('TELEGRAM_TOKEN')
HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME')

@app.route('/')
@app.route('/health')
def health():
    return jsonify({
        "status": "🎵 ULTIMATE Music Bot - Spotify/YouTube/ALL ✅",
        "platforms": "Spotify🔥 YouTube TikTok SoundCloud Instagram",
        "webhook": f"https://{HOSTNAME}/webhook"
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if not data or 'message' not in data: return "OK"
        
        chat_id = data['message']['chat']['id']
        text = data['message'].get('text', '').strip()
        
        if text == '/start':
            send_message(chat_id, 
                       "🔥 **ULTIMATE Music Bot** ✅\n\n"
                       "🎵 **Spotify** → auto YouTube MP3\n"
                       "📺 **YouTube/TikTok/SoundCloud** → MP3\n\n"
                       "**Send ANY music URL!**")
            return "OK"
        
        if text.startswith('http'):
            threading.Thread(target=process_url, args=(chat_id, text)).start()
            return "OK"
        
        send_message(chat_id, "❌ Send music URL!")
        return "OK"
    
    except: return "OK"

def send_message(chat_id, text):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                     json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
    except: pass

def spotify_to_yt(spotify_url):
    """Convert Spotify → YouTube search URL"""
    try:
        # Extract Spotify track ID
        track_id = spotify_url.split('track/')[1].split('?')[0]
        
        # Spotify API (no auth needed for basic info)
        resp = requests.get(f"https://open.spotify.com/track/{track_id}")
        title_match = re.search(r'"name":"([^"]+)"', resp.text)
        artist_match = re.search(r'"name":"([^"]+)",\s*"type":"artist"', resp.text)
        
        title = title_match.group(1) if title_match else "Track"
        artist = artist_match.group(1) if artist_match else "Artist"
        
        # YouTube search: "Artist Title audio"
        query = f"{artist} {title} audio"
        yt_url = f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}"
        
        return yt_url, f"{title} - {artist}"
    except:
        return spotify_url, "Spotify Track"

def process_url(chat_id, url):
    try:
        send_message(chat_id, "🔍 **Analyzing...**")
        
        # Spotify → YouTube conversion
        if 'spotify.com/track/' in url:
            yt_url, display_title = spotify_to_yt(url)
            send_message(chat_id, f"🔥 **Spotify → YouTube**\n🎤 **{display_title[:60]}**")
            url = yt_url
        
        # Get info + download
        title, artist = get_song_info(url)
        send_message(chat_id, f"⬇️ **{title[:60]}**\n👤 **{artist[:40]}**")
        
        filename = download_audio(url)
        if filename:
            send_audio(chat_id, filename, title, artist)
        else:
            send_message(chat_id, "❌ **No audio found** - try another link")
            
    except Exception as e:
        send_message(chat_id, f"❌ **Error:** {str(e)[:80]}")

def get_song_info(url):
    ydl_opts = {'quiet': True, 'no_warnings': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('title', 'Track'), info.get('uploader', 'Artist')
    except:
        return "Music", "Web"

def download_audio(url):
    try:
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl': 'temp_%(id)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'noplaylist': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info).rstrip('.webm').rstrip('.m4a') + '.mp3'
            return filename if os.path.exists(filename) else None
    except:
        return None

def send_audio(chat_id, filename, title, artist):
    try:
        size = os.path.getsize(filename)
        if size > 50 * 1024 * 1024:  # 50MB
            os.unlink(filename)
            send_message(chat_id, "❌ **Too large** (>50MB)")
            return
        
        with open(filename, 'rb') as audio:
            files = {'audio': (f"{title}.mp3", audio, 'audio/mpeg')}
            resp = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendAudio",
                               data={'chat_id': chat_id, 'title': title[:100], 
                                    'performer': artist[:50], 'duration': 0},
                               files=files, timeout=180)
        
        os.unlink(filename)
        send_message(chat_id, f"✅ **{title[:60]}** 🎵 **({artist})**")
        
    except Exception as e:
        if os.path.exists(filename): os.unlink(filename)
        print(f"Send error: {e}")

def setup_webhook():
    requests.post(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook")
    webhook_url = f"https://{HOSTNAME}/webhook"
    resp = requests.post(f"https://api.telegram.org/bot{TOKEN}/setWebhook", 
                        json={"url": webhook_url})
    print(f"✅ Webhook: {resp.json()}")

if __name__ == "__main__":
    print("🚀 ULTIMATE Music Bot - Spotify Converter")
    setup_webhook()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
