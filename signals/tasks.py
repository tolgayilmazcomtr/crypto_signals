from .utils import get_live_price, get_historical_prices, update_crypto_pairs
from django.utils.timezone import now
import requests
from decimal import Decimal
import numpy as np
import talib
from background_task import background

def get_top_15_cryptos():
    url = "https://api.binance.com/api/v3/ticker/24hr"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        sorted_data = sorted(
            [item for item in data if item['symbol'].endswith('USDT')],
            key=lambda x: float(x['quoteVolume']),
            reverse=True
        )
        top_15_pairs = [item['symbol'] for item in sorted_data[:15]]
        return top_15_pairs
    else:
        print("Binance API'den veri alınamadı.")
        return []

def generate_signals():
    pairs = get_top_15_cryptos()
    signals_list = []

    for pair in pairs:
        live_price = get_live_price(pair)
        historical_prices = get_historical_prices(pair, interval='1h', limit=100)

        if live_price is None or len(historical_prices) < 20:
            print(f"{pair} için yeterli veri yok.")
            continue

        # Algoritmaya göre sinyal üretme (RSI, Bollinger, MACD)
        close_prices = np.array(historical_prices)
        rsi = talib.RSI(close_prices, timeperiod=14)[-1]
        macd, macd_signal, _ = talib.MACD(close_prices, fastperiod=12, slowperiod=26, signalperiod=9)
        upper_band, _, _ = talib.BBANDS(close_prices, timeperiod=20)

        # Sinyal üretme mantığı
        if rsi < 30 and live_price < upper_band[-1]:
            signal = 'Buy'
        elif rsi > 70 and live_price > upper_band[-1]:
            signal = 'Sell'
        else:
            signal = 'Hold'

        # Hedef fiyat belirleme (Direnç seviyesi simülasyonu)
        target_price = round(float(upper_band[-1]) * 0.98, 2)  # Direncin %2 altı hedef fiyat

        # Decimal dönüşümü
        live_price = Decimal(str(live_price))
        target_price = Decimal(str(target_price))

        # Veriyi listeye ekle
        signals_list.append({
            'pair': pair,
            'signal': signal,
            'timeframe': '1H',
            'price_at_signal': live_price,
            'target_price': target_price,
            'updated_at': now()
        })

        print(f"{pair} için sinyal üretildi: {signal} - Fiyat: {live_price}, Hedef: {target_price}")
    
    return signals_list

@background(schedule=3600)  # Her saat başı
def update_pairs_task():
    update_crypto_pairs()
