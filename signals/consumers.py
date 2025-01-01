import json
import asyncio
import websockets
import aiohttp
from channels.generic.websocket import AsyncWebsocketConsumer
from .utils import convert_symbol_to_coingecko_id

class PriceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.symbol = None
        self.should_update = True
        self.current_source = 'binance'  # Varsayılan kaynak
        self.binance_socket = None
        await self.accept()

    async def disconnect(self, close_code):
        self.should_update = False
        if self.binance_socket:
            await self.binance_socket.close()

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data['type'] == 'subscribe':
            if self.symbol:  # Eğer önceki bir abonelik varsa iptal et
                self.should_update = False
                if self.binance_socket:
                    await self.binance_socket.close()
            
            self.symbol = data['symbol']
            self.should_update = True
            asyncio.create_task(self.price_stream())
        elif data['type'] == 'unsubscribe':
            self.should_update = False

    async def binance_price_stream(self):
        url = f"wss://stream.binance.com:9443/ws/{self.symbol.lower()}@ticker"
        try:
            async with websockets.connect(url) as ws:
                self.binance_socket = ws
                message = await ws.recv()
                data = json.loads(message)
                return float(data['c'])  # Güncel fiyat
        except Exception as e:
            print(f"Binance WebSocket Error: {e}")
            return None

    async def coingecko_price_stream(self):
        try:
            coin_id = convert_symbol_to_coingecko_id(self.symbol)
            url = "https://api.coingecko.com/api/v3/simple/price"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params={
                    'ids': coin_id,
                    'vs_currencies': 'usd'
                }) as response:
                    if response.status == 200:
                        data = await response.json()
                        return float(data[coin_id]['usd'])
            return None
        except Exception as e:
            print(f"CoinGecko API Error: {e}")
            return None

    async def switch_source(self):
        print(f"Switching source from {self.current_source}")
        if self.current_source == 'binance':
            self.current_source = 'coingecko'
        else:
            self.current_source = 'binance'
        print(f"to {self.current_source}")

    async def get_price(self):
        try:
            if self.current_source == 'binance':
                price = await self.binance_price_stream()
            else:
                price = await self.coingecko_price_stream()

            if price is None:
                await self.switch_source()
                return await self.get_price()
            return price
        except Exception as e:
            print(f"Price fetch error: {e}")
            await self.switch_source()
            return await self.get_price()

    async def price_stream(self):
        while self.should_update:
            try:
                price = await self.get_price()
                if price:
                    await self.send(json.dumps({
                        'type': 'price_update',
                        'data': {
                            self.symbol: price,
                            'source': self.current_source
                        }
                    }))
                await asyncio.sleep(1)  # 1 saniye bekle
            except Exception as e:
                print(f"Stream Error: {e}")
                await asyncio.sleep(5)  # Hata durumunda 5 saniye bekle 