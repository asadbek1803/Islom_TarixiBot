import aiohttp

async def get_prayer_times(latitude: float, longitude: float):
    url = f"https://api.aladhan.com/v1/timings?latitude={latitude}&longitude={longitude}&method=2"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            return data['data']['timings']