import asyncio
import httpx

class HighQualityBot:
    async def download_audio(self, url):
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url)
                response.raise_for_status()  # Raises an error for bad responses
                with open('audio.mp3', 'wb') as audio_file:
                    audio_file.write(response.content)
            except httpx.HTTPStatusError as e:
                print(f"HTTP error occurred: {e}")  # Handle HTTP errors
            except Exception as e:
                print(f"An error occurred: {e}")  # Handle other errors

async def main():
    bot = HighQualityBot()
    await bot.download_audio('https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3')

if __name__ == "__main__":
    asyncio.run(main())
