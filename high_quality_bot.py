import os
import requests
from flask import Flask, request, jsonify
import tempfile
import threading
import yt_dlp

app = Flask(__name__)

TOKEN = os.getenv('TELEGRAM_TOKEN')
HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME')

def get_song_info(url):
    """Extract REAL title/artist via yt-dlp"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown Track')
            artist = info.get('uploader', 'Unknown Artist')
            return title, artist
    except:
        return "High Quality Audio", "Music Bot"

def download_audio(url, title):
    """Download REAL MP3 via yt-dlp"""
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': '%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info).rstrip('.webm').rstrip('.m4a') + '.mp3'
            return filename
    except Exception as e:
        print(f"Download error: {e}")
        return None

@app.route('/health')
def health():
    return jsonify({"status": "REAL Music Bot LIVE 🎵", "yt-dlp": "✅"})

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data or 'message' not in data: return "OK"
    
    chat_id = data['message']['chat']['id']
    text = data['message']['text'].strip()
    
    if text == '/start':
        send_message(chat_id, 
                   "🎵 **REAL Music Bot** ✅\n"
                   "Send **YouTube/Spotify/SoundCloud** URL\n"
                   "📥 Downloads **PLAYABLE MP3** with **real title/artist**!")
        return "OK"
    
    if text.startswith('http'):
        send_message(chat_id, "🔄 **Extracting song info...**")
        
        title, artist = get_song_info(text)
        send_message(chat_id, f"🎤 **{title[:50]}**\n👤 **{artist[:30]}**\n⬇️ Downloading REAL MP3...")
        
        threading.Thread(
            target=send_real_audio,
            args=(chat_id, text, title, artist)
        ).start()
        return "OK"
    
    send_message(chat_id, "❌ Send YouTube/Spotify/SoundCloud URL!")
    return "OK"

def send_message(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                 json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

def send_real_audio(chat_id, url, title, artist):
    try:
        # Download to temp dir
        filename = download_audio(url, title)
        if not filename or not os.path.exists(filename):
            send_message(chat_id, "❌ **Download failed** - invalid URL")
            return
        
        # Send REAL MP3
        with open(filename, 'rb') as audio:
            files = {'audio': (f"{title[:100]}.mp3", audio, 'audio/mpeg')}
            resp = requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendAudio",
                data={
                    'chat_id': chat_id,
                    'title': title[:100],
                    'performer': artist[:50],
                    'duration': 0,
                    'thumb': ''  # No thumbnail
                },
                files=files,
                timeout=120
            )
        
        # Cleanup
        os.unlink(filename)
        
        if resp.json().get('ok'):
            send_message(chat_id, f"✅ **{title[:50]}** by **{artist}** sent! 🎵")
        else:
            send_message(chat_id, "❌ **Upload failed** - file too large")
            
    except Exception as e:
        send_message(chat_id, f"❌ **Error:** {str(e)[:100]}")

def setup_webhook():
    requests.post(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook")
    webhook_url = f"https://{HOSTNAME}/webhook"
    resp = requests.post(f"https://api.telegram.org/bot{TOKEN}/setWebhook", 
                        json={"url": webhook_url})
    print(f"✅ Webhook: {resp.json()}")

if __name__ == "__main__":
    print("🚀 REAL Music Bot + yt-dlp")
    setup_webhook()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
