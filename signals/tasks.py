from .models import Signal
from .utils import get_live_price
from django.utils.timezone import now
import requests
import random
from decimal import Decimal

def get_top_15_cryptos():
    url = "https://api.binance.com/api/v3/ticker/24hr"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        # Hacme göre sıralama (USDT çiftleri)
        sorted_data = sorted(
            [item for item in data if item['symbol'].endswith('USDT')],
            key=lambda x: float(x['quoteVolume']),
            reverse=True
        )
        # En yüksek hacimli ilk 15 kriptoyu al
        top_15_pairs = [item['symbol'] for item in sorted_data[:15]]
        return top_15_pairs
    else:
        print("Binance API'den veri alınamadı.")
        return []


def generate_signals():
    pairs = get_top_15_cryptos()

    for pair in pairs:
        live_price = get_live_price(pair)

        if live_price is None:
            print(f"{pair} için fiyat alınamadı.")
            continue

        print(f"{pair} için çekilen fiyat: {live_price}")

        signal = random.choice(['Buy', 'Sell', 'Hold'])
        timeframe = random.choice(['Short', 'Medium', 'Long'])

        if signal == 'Buy':
            target_price = round(live_price * random.uniform(1.05, 1.20), 2)
        elif signal == 'Sell':
            target_price = round(live_price * random.uniform(0.85, 0.95), 2)
        else:
            target_price = live_price

        # Decimal dönüşümü
        live_price = Decimal(str(live_price))
        target_price = Decimal(str(target_price))

        # Veritabanına sinyal ekle veya güncelle
        Signal.objects.update_or_create(
            pair=pair,
            defaults={
                'signal': signal,
                'timeframe': timeframe,
                'price_at_signal': live_price,
                'target_price': target_price,
                'updated_at': now()
            }
        )
        print(f"{pair} için sinyal üretildi: {signal} - {live_price} - Hedef: {target_price}")
