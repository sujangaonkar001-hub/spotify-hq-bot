import os
import re
import logging
import asyncio
import base64
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import ChatAction
import yt_dlp
import requests
from bs4 import BeautifulSoup
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HighQualitySpotifyBot:
    def __init__(self, token):
        self.token = token
        self.download_path = "/tmp/downloads"  # Render tmp dir
        os.makedirs(self.download_path, exist_ok=True)

    def extract_spotify_info(self, url):
        track_match = re.search(r'spotify\.com/track/([a-zA-Z0-9]+)', url)
        if track_match:
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                response = requests.get(f"https://open.spotify.com/track/{track_match.group(1)}", 
                                      headers=headers, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                title_tag = soup.find('meta', property='og:title')
                if title_tag and ' - ' in title_tag['content']:
                    song, artist = title_tag['content'].rsplit(' - ', 1)
                    return {'title': song.strip(), 'artist': artist.strip()}
            except:
                pass
        return {'title': 'Track', 'artist': 'Artist'}

    async def download_audio(self, update, search_query, info):
        await update.callback_query_edit_message_text("⬇️ Downloading 320kbps...")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{self.download_path}/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'quiet': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(f"ytsearch1:{search_query}", download=True)
                filename = ydl.prepare_filename(info_dict).rsplit('.', 1)[0] + '.mp3'
                return filename if os.path.exists(filename) else None
        except:
            return None

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        url = update.message.text.strip()
        await context.bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.UPLOAD_AUDIO)
        
        info = self.extract_spotify_info(url)
        search_query = f"{info['title']} {info['artist']} audio 320kbps"
        
        await update.message.reply_text(f"🎵 **{info['title']} - {info['artist']}**\n⬇️ HQ Download...", 
                                       parse_mode='Markdown')
        
        filename = await self.download_audio(update, search_query, info)
        
        if filename and os.path.exists(filename):
            try:
                with open(filename, 'rb') as audio:
                    await update.message.reply_audio(
                        audio=audio,
                        title=info['title'],
                        performer=info['artist'],
                        caption="🔥 320kbps HQ • Album Ready!"
                    )
                os.remove(filename)
                await update.message.reply_text("✅ Next track? 🎧")
            except:
                await update.message.reply_text("❌ File too big (50MB limit)")
        else:
            await update.message.reply_text("❌ No results. Try another!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 **HQ Spotify Bot**\n\n"
        "Paste Spotify track link → **320kbps MP3** instant!\n\n"
        "👇 https://open.spotify.com/track/ABC123",
        parse_mode='Markdown'
    )

def main():
    load_dotenv()
    encoded_token = os.getenv('SPOTIFY_BOT_TOKEN')
    
    if not encoded_token:
        print("❌ SPOTIFY_BOT_TOKEN missing!")
        return
    
    try:
        TOKEN = base64.b64decode(encoded_token).decode('utf-8')
    except:
        print("❌ Invalid SPOTIFY_BOT_TOKEN!")
        return
    
    bot = HighQualitySpotifyBot(TOKEN)
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    
    print("🚀 HQ Spotify Bot LIVE!")
    app.run_polling()

if __name__ == '__main__':
    main()
