import json
import asyncio
import websockets
import aiohttp
from channels.generic.websocket import AsyncWebsocketConsumer
from .utils import convert_symbol_to_coingecko_id
from .models import CryptoPair

class PriceConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = None  # aiohttp session'ı için
        self.cache = {}  # Fiyat önbelleği ekleyelim
        
    async def connect(self):
        self.symbol = None
        self.should_update = True
        self.session = aiohttp.ClientSession()  # Tek bir session oluştur
        await self.accept()

    async def disconnect(self, close_code):
        self.should_update = False
        if self.session:
            await self.session.close()  # Session'ı kapat

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data['type'] == 'subscribe':
            if self.symbol:  # Önceki aboneliği iptal et
                self.should_update = False
            
            self.symbol = data['symbol']
            self.should_update = True
            asyncio.create_task(self.price_stream())
        elif data['type'] == 'unsubscribe':
            self.should_update = False

    async def price_stream(self):
        while self.should_update:
            try:
                price = await self.get_binance_price()
                if price:
                    await self.send(json.dumps({
                        'type': 'price_update',
                        'data': {self.symbol: price}
                    }))
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Stream Error: {e}")
                await asyncio.sleep(5)

    async def get_binance_price(self):
        try:
            # Önbellekte varsa ve 1 saniyeden yeni ise, önbellekten döndür
            if self.symbol in self.cache:
                timestamp, price = self.cache[self.symbol]
                if (asyncio.get_event_loop().time() - timestamp) < 1:
                    return price

            url = f"https://api.binance.com/api/v3/ticker/price?symbol={self.symbol}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    price = float(data['price'])
                    # Önbelleğe al
                    self.cache[self.symbol] = (asyncio.get_event_loop().time(), price)
                    return price
            return None
        except Exception as e:
            print(f"Binance API Error: {e}")
            return None 