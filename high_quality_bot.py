import asyncio
import os
import httpx
from flask import Flask
from threading import Thread
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes

# Flask app for Render (required to keep service alive)
app = Flask(__name__)

@app.route('/')
def home():
    return "High Quality Bot is running! 🎵 Send /start or audio links!"

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

class HighQualityBot:
    def __init__(self, application):
        self.application = application

    async def download_audio(self, url, update):
        async with httpx.AsyncClient() as client:
            try:
                await update.message.reply_text("⬇️ Downloading high quality audio...")
                response = await client.get(url)
                response.raise_for_status()
                
                with open('audio.mp3', 'wb') as audio_file:
                    audio_file.write(response.content)
                
                await update.message.reply_audio(audio=open('audio.mp3', 'rb'), title="High Quality Audio")
                os.remove('audio.mp3')  # Clean up
            except httpx.HTTPStatusError as e:
                await update.message.reply_text(f"❌ HTTP error: {e}")
            except Exception as e:
                await update.message.reply_text(f"❌ Error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎵 High Quality Bot ready!\nSend me any audio/video URL and I'll send high quality MP3!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    bot = HighQualityBot(context.application)
    await bot.download_audio(url, update)

def main():
    # Get bot token from environment (set in Render dashboard)
    TOKEN = os.getenv('TELEGRAM_TOKEN')
    if not TOKEN:
        print("❌ Set TELEGRAM_TOKEN environment variable in Render dashboard!")
        return

    # Create Telegram bot
    application = Application.builder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start Flask in background
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Start bot polling
    print("🚀 Bot started! Check https://your-render-url.onrender.com")
    application.run_polling()

if __name__ == "__main__":
    main()
