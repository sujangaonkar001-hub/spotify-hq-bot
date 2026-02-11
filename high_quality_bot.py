import os
import json
import asyncio
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import httpx

app = Flask(__name__)

# GLOBAL STATE
application = None

class HighQualityBot:
    @staticmethod
    def process_audio(bot: Bot, chat_id: int, url: str):
        try:
            bot.send_message(chat_id=chat_id, text="⬇️ Downloading...")
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎵 Send me audio URLs!")

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    HighQualityBot.process_audio(context.bot, update.effective_chat.id, url)

@app.route('/')
@app.route('/health')
def health():
    return {"status": "High Quality Bot running!", "time": time.time()}

@app.route('/webhook', methods=['POST'])
def webhook():
    global application
    if application is None:
        return "Bot not ready", 503
    
    # Process update
    update = Update.de_json(request.get_json(), application.bot)
    if update:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(application.process_update(update))
        finally:
            loop.close()
    
    return "OK"

def init_bot():
    """Initialize on startup"""
    global application
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        print("❌ No TELEGRAM_TOKEN!")
        return
    
    print("🧹 Clearing webhook...")
    bot = Bot(token)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(bot.delete_webhook(drop_pending_updates=True))
    finally:
        loop.close()
    
    # Build app
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    
    # Set webhook
    hostname = os.getenv('RENDER_EXTERNAL_HOSTNAME')
    if hostname:
        webhook_url = f"https://{hostname}/webhook"
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(bot.set_webhook(webhook_url))
            print(f"✅ Webhook set: {webhook_url}")
        finally:
            loop.close()
    else:
        print("⚠️ No RENDER_EXTERNAL_HOSTNAME - manual webhook needed")

if __name__ == "__main__":
    # INIT BOT ON STARTUP
    init_bot()
    print("🚀 Server starting...")
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
