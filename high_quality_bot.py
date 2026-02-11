import os
import json
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import httpx
import threading
import time

app = Flask(__name__)

class HighQualityBot:
    @staticmethod
    def process_audio(bot: Bot, chat_id: int, url: str):
        try:
            # Sync download
            with httpx.Client(timeout=60.0) as client:
                resp = client.get(url)
                resp.raise_for_status()
            
            with open('temp.mp3', 'wb') as f:
                f.write(resp.content)
            
            with open('temp.mp3', 'rb') as audio:
                bot.send_audio(chat_id=chat_id, audio=audio, title="High Quality 🎵")
            
            os.remove('temp.mp3')
            bot.send_message(chat_id=chat_id, text="✅ Done!")
        except Exception as e:
            bot.send_message(chat_id=chat_id, text=f"❌ Error: {str(e)}")

# GLOBAL APP
application = None

@app.route('/')
@app.route('/health')
def health():
    return {"status": "High Quality Bot running!", "time": time.time()}

@app.route('/webhook', methods=['POST'])  # Fixed: /webhook not /token
def webhook():
    global application
    if application is None:
        return "Bot not ready", 503
    
    update = Update.de_json(request.get_json(), application.bot)
    if update:
        # Process SYNC
        asyncio.run(application.process_update(update))
    return "OK"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎵 Send me audio URLs!")

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    bot_obj = HighQualityBot()
    bot_obj.process_audio(context.bot, update.effective_chat.id, url)

def init_bot():
    """Clean init - delete webhook first"""
    global application
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        print("❌ No TELEGRAM_TOKEN!")
        return
    
    # DELETE ANY EXISTING WEBHOOK
    bot = Bot(token)
    asyncio.run(bot.delete_webhook(drop_pending_updates=True))
    print("🧹 Cleared old webhook")
    
    # Create app
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    
    # SET WEBHOOK
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
    asyncio.run(bot.set_webhook(webhook_url))
    print(f"✅ Webhook: {webhook_url}")

@app.before_first_request
def startup():
    init_bot()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
