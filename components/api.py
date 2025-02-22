import aiohttp
from typing import Dict
import logging

async def get_prayer_times(latitude: float, longitude: float) -> Dict[str, str]:
    """
    Get prayer times from the Aladhan API for given coordinates.
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
        
    Returns:
        Dict[str, str]: Dictionary containing prayer times
        
    Raises:
        Exception: If API request fails or returns invalid data
    """
    url = f"https://api.aladhan.com/v1/timings?latitude={latitude}&longitude={longitude}&method=2"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    logging.error(f"API request failed with status {response.status}")
                    raise Exception("Failed to fetch prayer times")
                
                data = await response.json()
                
                if not data.get('data') or not data['data'].get('timings'):
                    logging.error("Invalid data structure received from API")
                    raise Exception("Invalid data received from prayer times API")
                
                return data['data']['timings']
                
    except aiohttp.ClientError as e:
        logging.error(f"Network error occurred: {str(e)}")
        raise Exception("Network error occurred while fetching prayer times")
    except Exception as e:
        logging.error(f"Unexpected error occurred: {str(e)}")
        raise


async def get_address(latitude: float, longitude: float) -> str:
    """Get address from coordinates using Nominatim API"""
    url = f"https://nominatim.openstreetmap.org/reverse?lat={latitude}&lon={longitude}&format=json&accept-language=uz"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'address' in data:
                        address = data['address']
                        # Try to get city/town and state
                        city = address.get('city', address.get('town', address.get('village', '')))
                        state = address.get('state', '')
                        if city and state:
                            return f"{city}, {state}"
                        return city or state or "Noma'lum hudud"
                return "Noma'lum hudud"
    except Exception as e:
        print(f"Error getting address: {e}")
        return "Noma'lum hudud"