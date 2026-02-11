import os
import requests
from flask import Flask, request, jsonify
import threading
import yt_dlp
import glob
import re

app = Flask(__name__)

TOKEN = os.getenv('TELEGRAM_TOKEN')
HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME')

@app.route('/')
@app.route('/health')
def health():
    return jsonify({"status": "⚡ ULTRA-FAST Music Bot ✅"})

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data: return "OK"
    
    chat_id = data['message']['chat']['id']
    text = data['message'].get('text', '').strip()
    
    if text == '/start':
        send_message(chat_id, "⚡ **FAST Music Bot**\nSend URL → MP3 in 10s!")
        return "OK"
    
    if 'http' in text:
        threading.Thread(target=fast_download, args=(chat_id, text)).start()
        send_message(chat_id, "⚡ **Downloading...**")
        return "OK"
    
    return "OK"

def send_message(chat_id, text):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                     json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True})
    except: pass

def fast_download(chat_id, url):
    print(f"⚡ {url[:60]}")
    
    # Spotify → YouTube
    if 'spotify.com/track/' in url:
        url = spotify_search(url)
    
    try:
        # ULTRA-FAST download settings
        ydl_opts = {
            'format': 'bestaudio/best',  # FASTEST audio
            'outtmpl': 'audio.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',  # Smaller = FASTER
            }],
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 10,  # 10s timeout
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract FIRST (fast)
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Music')[:80]
            artist = info.get('uploader', 'Artist')[:40]
            
            print(f"🎵 {title} - {artist}")
            send_message(chat_id, f"⚡ **{title}**\n👤 **{artist}**")
            
            # Download (5-10s)
            ydl.download([url])
        
        # Send MP3
        mp3_file = glob.glob("audio.*.mp3")
        if mp3_file:
            send_mp3(chat_id, mp3_file[0], title, artist)
        else:
            send_message(chat_id, "❌ No audio")
            
    except Exception as e:
        print(f"Error: {e}")
        send_message(chat_id, "❌ Failed - try YouTube")

def spotify_search(spotify_url):
    """Fast Spotify → YouTube"""
    try:
        track_id = spotify_url.split('track/')[1].split('?')[0]
        resp = requests.get(f"https://open.spotify.com/track/{track_id}", timeout=5)
        
        title = re.search(r'"name":"(.+?)"', resp.text)
        artist = re.search(r'"name":"(.+?)"\s*,\s*"type":"artist"', resp.text)
        
        query = f"{artist.group(1) if artist else ''} {title.group(1) if title else ''} audio"
        return f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}"
    except:
        return "https://www.youtube.com/results?search_query=music"

def send_mp3(chat_id, filename, title, artist):
    try:
        filesize = os.path.getsize(filename)
        if filesize > 45 * 1024 * 1024:  # 45MB
            os.unlink(filename)
            send_message(chat_id, "❌ Too big")
            return
        
        with open(filename, 'rb') as f:
            files = {'audio': (f"{title}.mp3", f, 'audio/mpeg')}
            resp = requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendAudio",
                data={'chat_id': chat_id, 'title': title, 'performer': artist},
                files=files,
                timeout=60
            )
        
        os.unlink(filename)
        if resp.json().get('ok'):
            print("✅ SENT")
        else:
            print(f"Telegram error: {resp.text}")
            
    except Exception as e:
        print(f"Send error: {e}")
        try: os.unlink(filename)
        except: pass

def setup_webhook():
    if TOKEN and HOSTNAME:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook")
        requests.post(f"https://api.telegram.org/bot{TOKEN}/setWebhook", 
                     json={"url": f"https://{HOSTNAME}/webhook"})
        print("✅ Webhook OK")

if __name__ == "__main__":
    setup_webhook()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
