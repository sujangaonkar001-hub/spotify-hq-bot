import os
import json
from flask import Flask, request, Response
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
import threading
import time

app = Flask(__name__)

# GLOBAL BOT
application = None

class HighQualityBot:
    @staticmethod
    def process_audio(bot_token: str, chat_id: int, url: str):
        """100% SYNC - no async issues"""
        try:
            bot = Bot(token=bot_token)
            
            # Send status
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": "⬇️ Downloading..."}
            )
            
            # Download
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            
            # Send audio
            files = {'audio': ('audio.mp3', resp.content, 'audio/mpeg')}
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendAudio",
                data={'chat_id': chat_id, 'title': 'High Quality 🎵'},
                files=files
            )
            
            # Success
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": "✅ Done!"}
            )
        except Exception as e:
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": f"❌ Error: {str(e)}"}
            )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎵 Send me audio URLs!")

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    token = context.bot.token
    threading.Thread(
        target=HighQualityBot.process_audio,
        args=(token, update.effective_chat.id, url)
    ).start()

@app.route('/')
@app.route('/health')
def health():
    return {"status": "High Quality Bot LIVE!", "time": time.time()}

@app.route('/webhook', methods=['POST'])
def webhook():
    global application
    if not application:
        return Response("Bot not ready", status=503)
    
    data = request.get_json()
    if not data:
        return Response("No data", status=400)
    
    update = Update.de_json(data, application.bot)
    if update:
        # Run in thread to avoid blocking
        threading.Thread(
            target=lambda: asyncio.run(application.process_update(update))
        ).start()
    
    return "OK"

def init_bot():
    global application
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        print("❌ No TELEGRAM_TOKEN!")
        return
    
    print("🧹 Initializing...")
    
    # DELETE WEBHOOK FIRST (sync)
    bot = Bot(token)
    requests.post(
        f"https://api.telegram.org/bot{token}/deleteWebhook",
        json={"drop_pending_updates": True}
    )
    
    # Create app
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    
    # SET WEBHOOK
    hostname = os.getenv('RENDER_EXTERNAL_HOSTNAME')
    if hostname:
        webhook_url = f"https://{hostname}/webhook"
        requests.post(
            f"https://api.telegram.org/bot{token}/setWebhook",
            json={"url": webhook_url}
        )
        print(f"✅ Webhook: {webhook_url}")
    else:
        print("⚠️ Set RENDER_EXTERNAL_HOSTNAME")

if __name__ == "__main__":
    init_bot()
    print("🚀 Bot LIVE!")
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
