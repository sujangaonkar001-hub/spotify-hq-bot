import os
import re
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import time

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class HighQualitySpotifyBot:
    def __init__(self, token):
        self.token = token
        self.download_path = "./downloads"
        os.makedirs(self.download_path, exist_ok=True)
    
    def extract_spotify_info(self, url):
        """Extract song info from Spotify URL"""
        # Track pattern
        track_match = re.search(r'spotify\.com/track/([a-zA-Z0-9]+)', url)
        if track_match:
            spotify_id = track_match.group(1)
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(f"https://open.spotify.com/track/{spotify_id}", 
                                      headers=headers, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                title_tag = soup.find('meta', property='og:title')
                if title_tag:
                    title = title_tag['content']
                    if ' - ' in title:
                        song, artist = title.rsplit(' - ', 1)
                        return {'title': song.strip(), 'artist': artist.strip()}
            except:
                pass
        
        # Fallback parsing from URL or basic search
        if 'track/' in url:
            parts = url.split('/')[-1].split('?')[0]
            return {'title': f'Track {parts[:10]}', 'artist': 'Artist'}
        
        return None

    async def search_best_youtube(self, query):
        """Search YouTube for HIGHEST quality audio"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Try multiple search variants for best quality
            searches = [
                f"ytsearch1:{query} 320kbps",
                f"ytsearch1:{query} high quality audio",
                f"ytsearch1:{query} official audio"
            ]
            
            for search_query in searches:
                try:
                    results = await loop.run_in_executor(
                        None, lambda: ydl.extract_info(search_query, download=False)
                    )
                    if results and 'entries' in results and results['entries']:
                        best = results['entries'][0]
                        if best.get('duration', 0) < 600:  # Skip super long videos
                            return best['url']
                except:
                    continue
        return None

    async def download_high_quality(self, youtube_url, filename):
        """Download 320kbps MP3 with max quality"""
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',  # Prefer m4a for quality
            'outtmpl': f'{self.download_path}/{filename}.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',  # MAX QUALITY
            }],
            'postprocessors': [{
                'key': 'FFmpegMetadata',  # Embed metadata
            }],
            'embed_thumbnail': True,
            'writethumbnail': True,
            'ignoreerrors': False,
        }
        
        loop = asyncio.get_event_loop()
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                await loop.run_in_executor(None, ydl.download, [youtube_url])
            
            # Find MP3 file
            time.sleep(2)  # Wait for processing
            for file in os.listdir(self.download_path):
                if file.startswith(filename) and file.endswith('.mp3'):
                    return os.path.join(self.download_path, file)
        except Exception as e:
            logger.error(f"High quality download failed: {e}")
        
        return None

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message
        url = message.text.strip()
        
        await message.reply_chat_action("upload_document")
        await message.reply_text("🔍 Detecting Spotify track...")
        
        info = self.extract_spotify_info(url)
        if not info:
            await message.reply_text(
                "❌ **Invalid Spotify link!**\n\n"
                "📎 Send a **track** link:\n"
                "`https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC`\n\n"
                "✨ Or paste track name + artist",
                parse_mode='Markdown'
            )
            return
        
        await message.reply_text(
            f"🎵 **{info['title']}**\n"
            f"👤 **{info['artist']}**\n\n"
            f"⬇️ Downloading **320kbps HQ** MP3...",
            parse_mode='Markdown'
        )
        
        # Enhanced search query
        search_query = f'"{info["title"]}" "{info["artist"]}" audio high quality 320kbps'
        youtube_url = await self.search_best_youtube(search_query)
        
        if not youtube_url:
            await message.reply_text("❌ No high-quality source found 😞\nTry another track!")
            return
        
        # Safe filename (Telegram friendly)
        safe_name = re.sub(r'[^\w\s\-]', '_', f"{info['title'][:60]} - {info['artist'][:30]}")
        safe_name = re.sub(r'\s+', '_', safe_name)
        
        audio_path = await self.download_high_quality(youtube_url, safe_name)
        
        if audio_path and os.path.exists(audio_path):
            file_size = os.path.getsize(audio_path) / (1024*1024)  # MB
            if file_size > 50:
                os.remove(audio_path)
                await message.reply_text("❌ File too large (Telegram 50MB limit)\nTry a shorter track!")
                return
            
            try:
                with open(audio_path, 'rb') as audio:
                    await message.reply_chat_action("upload_audio")
                    await message.reply_audio(
                        chat_id=message.chat_id,
                        audio=audio,
                        title=info['title'],
                        performer=info['artist'],
                        duration=180,  # 3 min max
                        caption=f"🔥 **320kbps HQ**\n{info['title']} • {info['artist']}\n\n"
                                f"💎 High Quality • Album Art Embedded"
                    )
                
                # Cleanup
                os.remove(audio_path)
                await message.reply_text("✅ **Download Complete!** 🎧\nSend next track!")
                
            except Exception as e:
                logger.error(f"Send failed: {e}")
                await message.reply_text("❌ Send failed. Try again!")
        else:
            await message.reply_text("❌ Download failed. Server busy? Try later!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 **HQ Spotify Downloader** 🎵\n\n"
        "🔥 **320kbps High Quality MP3**\n"
        "✨ Album art + metadata\n"
        "⚡ Instant downloads\n\n"
        "**Just paste Spotify track link!**\n\n"
        "👇 Example:\n"
        "`https://open.spotify.com/track/ABC123`",
        parse_mode='Markdown'
    )

def main():
    # ⚠️ GET NEW TOKEN FROM @BotFather!
    TOKEN = os.getenv('BOT_TOKEN') or "PASTE_YOUR_NEW_TOKEN_HERE"
    
    if TOKEN == "PASTE_YOUR_NEW_TOKEN_HERE":
        print("❌ ADD YOUR NEW BOT TOKEN!")
        print("1. Message @BotFather")
        print("2. /mybots → your bot → API Token → Revoke → New token")
        print("3. Replace TOKEN above or use .env file")
        return
    
    bot = HighQualitySpotifyBot(TOKEN)
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    
    print("🚀 HQ Bot Started! High Quality 320kbps 🔥")
    app.run_polling()

if __name__ == '__main__':
    main()
