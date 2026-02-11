import os
from flask import Flask, request
import threading
import time
import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update
import httpx

app = Flask(__name__)

class HighQualityBot:
    async def process_audio(self, url: str, update: Update):
        try:
            await update.message.reply_text("⬇️ Downloading...")
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=60.0)
                resp.raise_for_status()
            
            with open('temp.mp3', 'wb') as f:
                f.write(resp.content)
            
            with open('temp.mp3', 'rb') as audio:
                await update.message.reply_audio(audio=audio, title="High Quality 🎵")
            
            os.remove('temp.mp3')
            await update.message.reply_text("✅ Done!")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎵 Send me YouTube/audio URLs!")

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    bot = HighQualityBot()
    await bot.process_audio(url, update)

# GLOBAL BOT INSTANCE
bot_app = None

@app.route('/', methods=['GET'])
@app.route('/health', methods=['GET'])
def health():
    return {"status": "High Quality Bot running!", "time": time.time()}

@app.route(f"/{os.getenv('TELEGRAM_TOKEN', 'webhook')}", methods=['POST'])
async def webhook():
    global bot_app
    if not bot_app:
        return "Bot not initialized", 503
    
    update = Update.de_json(request.get_json(), bot_app.bot)
    await bot_app.process_update(update)
    return "OK"

def init_bot():
    """Initialize bot with webhook"""
    global bot_app
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        print("❌ No TELEGRAM_TOKEN!")
        return
    
    bot_app = Application.builder().token(token).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    
    # Set webhook
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{token}"
    asyncio.run(bot_app.bot.set_webhook(webhook_url))
    print(f"✅ Webhook set: {webhook_url}")

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    # Initialize bot first
    init_bot()
    app.run(host="0.0.0.0", port=port, debug=False)

if __name__ == "__main__":
    run_flask()
