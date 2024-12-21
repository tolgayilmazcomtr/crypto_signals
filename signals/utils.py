import requests
import talib
import numpy as np

def get_historical_prices(symbol, interval='1h', limit=200):
    url = "https://api.binance.com/api/v3/klines"
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': limit,
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        close_prices = [float(c[4]) for c in data]
        high = [float(c[2]) for c in data]
        low = [float(c[3]) for c in data]
        return {
            "close": np.array(close_prices),
            "high": np.array(high),
            "low": np.array(low)
        }
    return {"close": [], "high": [], "low": []}

def calculate_stoch_rsi(close_prices, period=14, smoothK=3, smoothD=3):
    rsi = talib.RSI(close_prices, timeperiod=period)
    stoch_rsi = np.zeros_like(rsi)
    for i in range(period, len(rsi)):
        window = rsi[i-period:i]
        rsi_min = np.min(window)
        rsi_max = np.max(window)
        if rsi_max != rsi_min:
            stoch_rsi[i] = (rsi[i] - rsi_min) / (rsi_max - rsi_min) * 100
        else:
            stoch_rsi[i] = 50
    k = talib.SMA(stoch_rsi, timeperiod=smoothK)
    d = talib.SMA(k, timeperiod=smoothD)
    return k, d

def calculate_ichimoku(high, low, close):
    conversion_line = (talib.MAX(high, timeperiod=9) + talib.MIN(low, timeperiod=9)) / 2
    base_line = (talib.MAX(high, timeperiod=26) + talib.MIN(low, timeperiod=26)) / 2
    return conversion_line, base_line

def calculate_technical_indicators(close):
    rsi = talib.RSI(close, timeperiod=14)
    macd, macd_signal, macd_hist = talib.MACD(close)
    upper_band, middle_band, lower_band = talib.BBANDS(close, timeperiod=20)
    # Ek indikatör: MFI (Money Flow Index)
    # MFI için ayrıca high, low, volume lazım, burada volume olmadığından skip edilebilir ya da başka bir API kullandığınız varsayılabilir.
    return rsi, macd, macd_signal, upper_band, lower_band

def score_and_comment_indicators(close, high, low):
    rsi, macd, macd_signal, upper_band, lower_band = calculate_technical_indicators(close)
    stoch_k, stoch_d = calculate_stoch_rsi(close)
    conversion_line, base_line = calculate_ichimoku(high, low, close)

    latest = -1
    score = 0
    details = []

    # RSI
    if rsi[latest] < 30:
        score += 1
        details.append(f"RSI {rsi[latest]:.2f}: Aşırı satım bölgesi (Alım fırsatı).")
    elif rsi[latest] > 70:
        score -= 1
        details.append(f"RSI {rsi[latest]:.2f}: Aşırı alım bölgesi (Satış sinyali).")
    else:
        details.append(f"RSI {rsi[latest]:.2f}: Nötr bölge.")

    # Bollinger
    if close[latest] < lower_band[latest]:
        score += 1
        details.append("Fiyat alt Bollinger bandının altında: Olası alım fırsatı.")
    elif close[latest] > upper_band[latest]:
        score -= 1
        details.append("Fiyat üst Bollinger bandının üzerinde: Olası satış sinyali.")
    else:
        details.append("Fiyat Bollinger bantları arasında: Yatay seyir.")

    # MACD
    if macd[latest] > macd_signal[latest]:
        score += 1
        details.append("MACD > Sinyal: Yükseliş eğilimi.")
    else:
        score -= 1
        details.append("MACD < Sinyal: Düşüş eğilimi.")

    # StochRSI
    if stoch_k[latest] < 20:
        score += 1
        details.append("StochRSI düşük: Aşırı satım bölgesi, alım sinyali.")
    elif stoch_k[latest] > 80:
        score -= 1
        details.append("StochRSI yüksek: Aşırı alım bölgesi, satış sinyali.")
    else:
        details.append("StochRSI nötr seviyelerde.")

    # Ichimoku
    if close[latest] > conversion_line[latest] and close[latest] > base_line[latest]:
        score += 1
        details.append("Fiyat Ichimoku çizgilerinin üzerinde: Pozitif trend.")
    elif close[latest] < conversion_line[latest] and close[latest] < base_line[latest]:
        score -= 1
        details.append("Fiyat Ichimoku çizgilerinin altında: Negatif trend.")
    else:
        details.append("Fiyat Ichimoku çizgileri çevresinde: Belirsiz trend.")

    return score, details

def analyze_signals_advanced(symbol):
    intervals = ['1h', '4h', '1d']
    total_score = 0
    all_details = []
    latest_price = None

    for interval in intervals:
        data = get_historical_prices(symbol, interval=interval, limit=200)
        close = data["close"]
        high = data["high"]
        low = data["low"]

        if len(close) < 52:
            continue

        score, details = score_and_comment_indicators(close, high, low)
        total_score += score
        all_details.append(f"{interval} zaman dilimi:\n" + "\n".join(details))
        latest_price = close[-1]

    if total_score > 0:
        signal = "Buy"
        comment = "Genel eğilim yukarı yönlü. Alım sinyalleri ağırlıkta."
    elif total_score < 0:
        signal = "Sell"
        comment = "Genel eğilim aşağı yönlü. Satış sinyalleri baskın."
    else:
        signal = "Hold"
        comment = "Sinyaller karışık, net bir yön yok."

    # Tüm detayları tek bir metinde toplayalım
    full_comment = comment + "\n\nDetaylı İnceleme:\n" + "\n\n".join(all_details)

    return {
        "symbol": symbol,
        "signal": signal,
        "current_price": latest_price,
        "comment": full_comment
    }

def get_crypto_prices():
    url = "https://api.binance.com/api/v3/ticker/price"
    response = requests.get(url)
    if response.status_code == 200:
        all_prices = response.json()
        usdt_prices = [price for price in all_prices if price['symbol'].endswith('USDT')]
        return usdt_prices
    return {"error": "API request failed"}

def get_live_price(symbol):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    response = requests.get(url)
    if response.status_code == 200:
        return float(response.json()['price'])
    return None
