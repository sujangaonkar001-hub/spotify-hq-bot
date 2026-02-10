import os
from flask import Flask
import threading
import time
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update
import httpx
import asyncio

app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return {"status": "High Quality Bot running!", "time": time.time()}

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
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎵 Send me YouTube/audio URLs!")

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    bot = HighQualityBot()
    await bot.process_audio(url, update)

def run_bot():
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        print("No TELEGRAM_TOKEN!")
        return
    
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    
    print("🤖 Bot polling...")
    app.run_polling(drop_pending_updates=True)

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    run_bot()
