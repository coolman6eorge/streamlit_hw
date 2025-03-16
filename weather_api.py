import requests
import aiohttp
import asyncio
import time

class WeatherAPI:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
    
    def set_api_key(self, api_key):
        self.api_key = api_key
    
    def get_current_temperature_sync(self, city):
        if not self.api_key:
            raise ValueError("API key not set")
        
        params = {
            'q': city,
            'appid': self.api_key,
            'units': 'metric'
        }
        
        start_time = time.time()
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            temp = data['main']['temp']
            
            end_time = time.time()
            
            return {
                'temperature': temp,
                'description': data['weather'][0]['description'],
                'city': data['name'],
                'request_time': end_time - start_time
            }
            
        except requests.exceptions.RequestException as e:
            if hasattr(e.response, 'status_code') and e.response.status_code == 401:
                raise ValueError(response.json())
            else:
                raise ValueError(f"Error fetching weather data: {str(e)}")
    
    async def get_current_temperature_async(self, city):
        if not self.api_key:
            raise ValueError("API key not set")
        
        params = {
            'q': city,
            'appid': self.api_key,
            'units': 'metric'
        }
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 401:
                        raise ValueError("Invalid API key")
                    elif response.status != 200:
                        raise ValueError(f"Error fetching weather data: {response.status}")
                    
                    data = await response.json()
                    temp = data['main']['temp']
                    
                    end_time = time.time()
                    
                    return {
                        'temperature': temp,
                        'description': data['weather'][0]['description'],
                        'city': data['name'],
                        'request_time': end_time - start_time
                    }
        
        except aiohttp.ClientError as e:
            raise ValueError(f"Error fetching weather data: {str(e)}")

    async def get_multiple_temperatures_async(self, cities):
        tasks = [self.get_current_temperature_async(city) for city in cities]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results = {}
        for city, result in zip(cities, results):
            if isinstance(result, Exception):
                processed_results[city] = {'error': str(result)}
            else:
                processed_results[city] = result
        
        return processed_results