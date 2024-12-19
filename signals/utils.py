import requests

def get_crypto_prices():
    url = "https://api.binance.com/api/v3/ticker/price"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return {"error": "API request failed"}
def analyze_signals(prices):
    signals = []
    for price in prices:
        symbol = price['symbol']
        current_price = float(price['price'])
        # Basit bir örnek: Fiyat 1000'in üzerinde ise 'Buy', değilse 'Hold'
        if current_price > 1000:
            signals.append({'symbol': symbol, 'signal': 'Buy'})
        else:
            signals.append({'symbol': symbol, 'signal': 'Hold'})
    return signals
