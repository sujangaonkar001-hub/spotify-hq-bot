import os
import requests
from flask import Flask, request, jsonify
import threading
import yt_dlp
import glob
import time

app = Flask(__name__)

TOKEN = os.getenv('TELEGRAM_TOKEN')
HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME')

@app.route('/')
@app.route('/health')
def health():
    return jsonify({"status": "🎵 BULLETPROOF Music Bot ✅", "debug": "logs now"})

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data or 'message' not in data: return "OK"
    
    chat_id = data['message']['chat']['id']
    text = data['message'].get('text', '').strip()
    
    if text == '/start':
        send_message(chat_id, "🔥 **Music Bot** - Send ANY URL!\nSpotify/YouTube/TikTok")
        return "OK"
    
    if text.startswith('http'):
        threading.Thread(target=process_url, args=(chat_id, text)).start()
        send_message(chat_id, "🔍 **Searching audio...**")
        return "OK"
    
    return "OK"

def send_message(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                 json={"chat_id": chat_id, "text": text})

def process_url(chat_id, url):
    print(f"🔍 Processing: {url[:80]}")
    
    try:
        # Spotify conversion
        if 'spotify.com/track/' in url:
            url, title = spotify_to_yt(url)
            send_message(chat_id, f"🔥 **Spotify found:** {title}")
        
        # Get metadata
        info = extract_info(url)
        if not info:
            send_message(chat_id, "❌ **No video/audio found**")
            return
        
        title = info.get('title', 'Track')
        artist = info.get('uploader', 'Artist')
        print(f"📺 Title: {title}")
        
        send_message(chat_id, f"⬇️ **{title[:60]}** by **{artist}**")
        
        # Download
        if download_and_send(chat_id, url, title, artist):
            send_message(chat_id, f"✅ **{title[:50]}** 🎵")
        else:
            send_message(chat_id, "❌ **Download failed** - try YouTube")
            
    except Exception as e:
        print(f"ERROR: {e}")
        send_message(chat_id, f"❌ **Error:** {str(e)[:60]}")

def extract_info(url):
    """Extract video info safely"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    except:
        return None

def spotify_to_yt(spotify_url):
    """Spotify → YouTube search"""
    try:
        track_id = spotify_url.split('track/')[1].split('?')[0]
        resp = requests.get(f"https://open.spotify.com/track/{track_id}")
        
        title = re.search(r'"name":"([^"]+?)"', resp.text, re.DOTALL)
        artist = re.search(r'"name":"([^"]+?)"\s*,\s*"type":"artist"', resp.text)
        
        title = title.group(1) if title else "Spotify Track"
        artist = artist.group(1) if artist else "Artist"
        
        query = f'{artist} {title} official audio'
        yt_search = f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}"
        return yt_search, title
    except:
        return spotify_url, "Music Track"

def download_and_send(chat_id, url, title, artist):
    """Download + send with DEBUG"""
    temp_dir = 'temp_downloads'
    os.makedirs(temp_dir, exist_ok=True)
    
    ydl_opts = {
        'format': 'bestaudio/best[height<=480]/best',
        'outtmpl': f'{temp_dir}/%(uploader)s - %(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'postprocessor_args': ['-y'],  # Overwrite
        'quiet': False,  # SHOW logs
        'noplaylist': True,
    }
    
    try:
        print("⬇️ Starting yt-dlp...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Find MP3 file
        mp3_files = glob.glob(f'{temp_dir}/*.mp3')
        if mp3_files:
            filename = mp3_files[0]
            print(f"✅ Found MP3: {os.path.basename(filename)} ({os.path.getsize(filename)/1024/1024:.1f}MB)")
            
            if os.path.getsize(filename) > 48 * 1024 * 1024:
                send_message(chat_id, "❌ **File too big** (>48MB)")
                cleanup(temp_dir)
                return False
            
            # Send!
            with open(filename, 'rb') as audio:
                files = {'audio': (f"{title[:80]}.mp3", audio, 'audio/mpeg')}
                resp = requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendAudio",
                    data={
                        'chat_id': chat_id,
                        'title': title[:100],
                        'performer': artist[:50]
                    },
                    files=files,
                    timeout=300
                )
            
            print(f"📤 Telegram response: {resp.json()}")
            cleanup(temp_dir)
            return resp.json().get('ok', False)
        
        print("❌ No MP3 found")
        cleanup(temp_dir)
        return False
        
    except Exception as e:
        print(f"Download error: {e}")
        cleanup(temp_dir)
        return False

def cleanup(temp_dir):
    """Clean temp files"""
    for f in glob.glob('temp_downloads/*'):
        try: os.unlink(f)
        except: pass
    try: os.rmdir(temp_dir)
    except: pass

def setup_webhook():
    requests.post(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook")
    webhook_url = f"https://{HOSTNAME}/webhook"
    resp = requests.post(f"https://api.telegram.org/bot{TOKEN}/setWebhook", json={"url": webhook_url})
    print(f"✅ Webhook: {resp.json()}")

if __name__ == "__main__":
    print("🚀 BULLETPROOF Music Bot")
    setup_webhook()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
