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
            await update.message.reply_text("✅ Done!")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎵 Send me YouTube/audio URLs!")

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    bot = HighQualityBot()
    await bot.process_audio(url, update)

async def main():
    """Main async bot runner - fixes threading conflicts"""
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        print("❌ No TELEGRAM_TOKEN!")
        return
    
    # Build app
    application = Application.builder().token(token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    
    print("🤖 Bot polling...")
    
    # FIXED: Proper polling with conflict resolution
    await application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
        poll_interval=1.0,
        timeout=10,
        bootstrap_retries=5
    )

def run_bot():
    """Sync wrapper for async main"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

if __name__ == "__main__":
    # Flask daemon thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    time.sleep(2)  # Let Flask start
    
    # Bot main thread
    run_bot()
