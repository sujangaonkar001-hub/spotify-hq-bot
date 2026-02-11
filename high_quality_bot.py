import os
import requests
from flask import Flask, request, jsonify
import tempfile
import threading
import re
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

TOKEN = os.getenv('TELEGRAM_TOKEN')
HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME')

def get_song_info(url):
    """Extract REAL title/artist from URL"""
    try:
        # Spotify
        if 'spotify.com/track/' in url:
            track_id = url.split('track/')[1].split('?')[0]
            sp_resp = requests.get(f"https://open.spotify.com/track/{track_id}")
            title = re.search(r'"name":"([^"]+)"', sp_resp.text)
            artist = re.search(r'"name":"([^"]+)",\s+"type":"artist"', sp_resp.text)
            return (title.group(1) if title else "Spotify Track"), \
                   (artist.group(1) if artist else "Spotify Artist")
        
        # YouTube
        elif 'youtube.com' in url or 'youtu.be' in url:
            yt_id = parse_qs(urlparse(url).query).get('v', [None])[0]
            if not yt_id:
                yt_id = url.split('youtu.be/')[1].split('?')[0]
            yt_resp = requests.get(f"https://noembed.com/embed?url={url}")
            if yt_resp.json().get('title'):
                return yt_resp.json()['title'], "YouTube"
        
        # SoundCloud
        elif 'soundcloud.com' in url:
            sc_resp = requests.get(f"https://soundcloud.com/oembed", 
                                 params={'url': url, 'format': 'json'})
            if sc_resp.json().get('title'):
                return sc_resp.json()['title'], sc_resp.json().get('author_name', 'SoundCloud')
        
        # Generic - filename or URL
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)
        if filename.endswith('.mp3'):
            return filename.replace('.mp3', ''), "Audio File"
        
        return "High Quality Audio", "Web"
        
    except:
        return "High Quality Audio", "Music"

@app.route('/')
@app.route('/health')
def health():
    return jsonify({
        "status": "Real Song Bot LIVE ✅",
        "token_set": bool(TOKEN),
        "hostname": HOSTNAME
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return "OK"
        
        chat_id = data['message']['chat']['id']
        text = data['message']['text'].strip()
        
        if text == '/start':
            send_message(chat_id, 
                       "🎵 **Real Song Bot**\n"
                       "Send Spotify/YouTube/SoundCloud/MP3 URL\n"
                       "📱 Gets **REAL** title + artist!")
            return "OK"
        
        if text.startswith('http'):
            title, artist = get_song_info(text)
            send_message(chat_id, f"🎤 **{title}**\n👤 **{artist}**\n⬇️ Downloading...")
            
            threading.Thread(
                target=process_audio,
                args=(chat_id, text, title, artist)
            ).start()
            return "OK"
        
        send_message(chat_id, "❌ Send Spotify/YouTube/SoundCloud/MP3 URL!")
        return "OK"
    
    except Exception as e:
        print(f"Error: {e}")
        return "OK"

def send_message(chat_id, text):
    if not TOKEN: return
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True}
    )

def process_audio(chat_id, url, title, artist):
    try:
        resp = requests.get(url, timeout=90, stream=True)
        resp.raise_for_status()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    tmp.write(chunk)
            tmp_path = tmp.name
        
        with open(tmp_path, 'rb') as audio:
            files = {'audio': (f"{title}.mp3", audio, 'audio/mpeg')}
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendAudio",
                data={
                    'chat_id': chat_id,
                    'title': title,
                    'performer': artist,
                    'duration': 0  # Auto-detect
                },
                files=files
            )
        
        os.unlink(tmp_path)
        send_message(chat_id, f"✅ **{title}** by **{artist}** sent! 🎵")
        
    except Exception as e:
        send_message(chat_id, f"❌ **Download failed:** {str(e)}")

def setup_webhook():
    if not TOKEN or not HOSTNAME:
        print("⚠️ Set TELEGRAM_TOKEN + RENDER_EXTERNAL_HOSTNAME")
        return
    
    requests.post(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook", 
                 json={"drop_pending_updates": True})
    
    webhook_url = f"https://{HOSTNAME}/webhook"
    resp = requests.post(f"https://api.telegram.org/bot{TOKEN}/setWebhook", 
                        json={"url": webhook_url})
    
    if resp.json()['ok']:
        print(f"✅ Webhook LIVE: {webhook_url}")
    else:
        print(f"❌ Webhook error: {resp.json()}")

if __name__ == "__main__":
    print("🚀 Real Song Bot Starting...")
    setup_webhook()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
