import os
import requests
from flask import Flask, request, jsonify
import tempfile
import threading

app = Flask(__name__)

TOKEN = os.getenv('TELEGRAM_TOKEN')
HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME')

@app.route('/')
@app.route('/health')
def health():
    return jsonify({
        "status": "High Quality Bot LIVE ✅",
        "token_set": bool(TOKEN),
        "hostname": HOSTNAME,
        "webhook_url": f"https://{HOSTNAME}/webhook" if HOSTNAME else None
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
            send_message(chat_id, "🎵 **High Quality Bot LIVE!**\nSend me any audio/MP3 URL!")
            return "OK"
        
        if text.startswith('http'):
            # Download & send in background
            threading.Thread(
                target=process_audio,
                args=(chat_id, text)
            ).start()
            send_message(chat_id, "⬇️ Downloading high quality audio...")
            return "OK"
        
        send_message(chat_id, "❌ Send me an audio/MP3 URL!")
        return "OK"
    
    except Exception as e:
        print(f"Webhook error: {e}")
        return "OK"

def send_message(chat_id, text):
    """Send Telegram message"""
    if not TOKEN:
        return
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    )

def process_audio(chat_id, url):
    """Download & send MP3"""
    try:
        send_message(chat_id, "🔄 Processing...")
        
        # Download
        resp = requests.get(url, timeout=60, stream=True)
        resp.raise_for_status()
        
        # Save temp
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
            for chunk in resp.iter_content(chunk_size=8192):
                tmp.write(chunk)
            tmp_path = tmp.name
        
        # Send MP3
        with open(tmp_path, 'rb') as audio:
            files = {'audio': ('high_quality.mp3', audio, 'audio/mpeg')}
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendAudio",
                data={'chat_id': chat_id, 'title': 'High Quality 🎵', 'performer': 'Bot'},
                files=files
            )
        
        # Cleanup
        os.unlink(tmp_path)
        send_message(chat_id, "✅ **High quality MP3 sent!** 🎉")
        
    except Exception as e:
        send_message(chat_id, f"❌ **Error:** {str(e)}")

def setup_webhook():
    """Auto setup webhook on startup"""
    if not TOKEN or not HOSTNAME:
        print("⚠️ Missing TOKEN or HOSTNAME")
        return
    
    # Delete old webhook
    requests.post(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook", 
                 json={"drop_pending_updates": True})
    
    # Set new webhook
    webhook_url = f"https://{HOSTNAME}/webhook"
    response = requests.post(f"https://api.telegram.org/bot{TOKEN}/setWebhook", 
                            json={"url": webhook_url})
    
    if response.json()['ok']:
        print(f"✅ Webhook LIVE: {webhook_url}")
    else:
        print(f"❌ Webhook failed: {response.json()}")

if __name__ == "__main__":
    print("🚀 Starting High Quality Bot...")
    setup_webhook()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
