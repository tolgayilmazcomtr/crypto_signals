import requests
import talib
import numpy as np


# Binance API'den geçmiş fiyat verilerini çeker (hacim dahil)
def get_historical_prices(symbol, interval='1h', limit=200):
    url = "https://api.binance.com/api/v3/klines"
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': limit
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        close_prices = [float(c[4]) for c in data]  # Kapanış fiyatları
        high = [float(c[2]) for c in data]          # En yüksek fiyatlar
        low = [float(c[3]) for c in data]           # En düşük fiyatlar
        volume = [float(c[5]) for c in data]        # Hacim
        
        return {
            "close": np.array(close_prices),
            "high": np.array(high),
            "low": np.array(low),
            "volume": np.array(volume)
        }
    except requests.exceptions.RequestException as e:
        print(f"API Hatası: {e}")
        return {"close": [], "high": [], "low": [], "volume": []}


# Binance API'den belirli bir paritenin canlı fiyatını alır
def get_live_price(symbol):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return float(response.json()['price'])
    except requests.exceptions.RequestException as e:
        print(f"API Hatası: {e}")
        return None


# Binance API'den tüm kripto paraların fiyatlarını çeker
def get_crypto_prices():
    url = "https://api.binance.com/api/v3/ticker/price"
    try:
        response = requests.get(url)
        response.raise_for_status()
        all_prices = response.json()
        usdt_prices = [price for price in all_prices if price['symbol'].endswith('USDT')]
        return usdt_prices
    except requests.exceptions.RequestException as e:
        print(f"API Hatası: {e}")
        return {"error": "API request failed"}


# Stochastic RSI hesaplar
def calculate_stoch_rsi(close_prices, period=14, smoothK=3, smoothD=3):
    rsi = talib.RSI(close_prices, timeperiod=period)
    
    if len(rsi) < period:
        print("Yetersiz veri: StochRSI hesaplanamıyor.")
        return np.full_like(rsi, 50), np.full_like(rsi, 50)  # Yeterli veri yoksa nötr

    stoch_rsi = np.zeros_like(rsi)
    
    # Kapanış fiyatları değişimini analiz et
    price_change = np.ptp(close_prices[-period:])
    if price_change < 0.01:  # Fiyat değişimi çok küçükse
        print("Fiyat değişimi yetersiz. StochRSI hesaplanamıyor.")
        return np.full_like(rsi, 50), np.full_like(rsi, 50)  # Fiyatlar çok sabitse nötr

    for i in range(period, len(rsi)):
        window = rsi[i - period:i]
        rsi_min = np.min(window)
        rsi_max = np.max(window)
        
        if rsi_max == rsi_min:  # RSI min ve max aynıysa, nötr döndür
            stoch_rsi[i] = 50
        else:
            stoch_rsi[i] = ((rsi[i] - rsi_min) / (rsi_max - rsi_min)) * 100

    k = talib.SMA(stoch_rsi, timeperiod=smoothK)
    d = talib.SMA(k, timeperiod=smoothD)

    # NaN kontrolü
    if np.isnan(k[-1]):
        k[-1] = 50
    if np.isnan(d[-1]):
        d[-1] = 50

    return k, d





# Ichimoku Bulutu hesaplar (Conversion ve Base line)
def calculate_ichimoku(high, low):
    conversion_line = (talib.MAX(high, timeperiod=9) + talib.MIN(low, timeperiod=9)) / 2
    base_line = (talib.MAX(high, timeperiod=26) + talib.MIN(low, timeperiod=26)) / 2
    return conversion_line, base_line


# Hacim bazlı Money Flow Index (MFI) hesaplar
def calculate_mfi(high, low, close, volume, period=14):
    mfi = talib.MFI(high, low, close, volume, timeperiod=period)
    return mfi


# Teknik indikatörleri hesaplar
def calculate_technical_indicators(close, high, low, volume):
    rsi = talib.RSI(close, timeperiod=14)
    macd, macd_signal, _ = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    upper_band, middle_band, lower_band = talib.BBANDS(close, timeperiod=20)
    mfi = calculate_mfi(high, low, close, volume)
    
    return rsi, macd, macd_signal, upper_band, lower_band, middle_band, mfi


# İndikatörleri puanlar ve yorumlar
def score_and_comment_indicators(close, high, low, volume):
    rsi, macd, macd_signal, upper_band, lower_band, middle_band, mfi = calculate_technical_indicators(close, high, low, volume)
    stoch_k, _ = calculate_stoch_rsi(close)
    conversion_line, base_line = calculate_ichimoku(high, low)

    score = 0
    details = []
    indicators_used = 0  # Kaç indikatör sinyali etkiliyor
    latest = -1  # En son veri noktası

    # RSI Değerlendirmesi
    if len(rsi) > 0 and not np.isnan(rsi[latest]):
        if rsi[latest] < 20:
            score += 3
            indicators_used += 1
            details.append(f"RSI {rsi[latest]:.2f}: Aşırı satım (Güçlü alım fırsatı).")
        elif rsi[latest] < 30:
            score += 1
            indicators_used += 1
            details.append(f"RSI {rsi[latest]:.2f}: Alım fırsatı.")
        elif rsi[latest] > 70:
            score -= 2
            indicators_used += 1
            details.append(f"RSI {rsi[latest]:.2f}: Aşırı alım (Satış sinyali).")
        else:
            details.append(f"RSI {rsi[latest]:.2f}: Nötr bölgede.")

    # Bollinger Bands Değerlendirmesi
    if len(upper_band) > 0 and not np.isnan(upper_band[latest]):
        if close[latest] < lower_band[latest]:
            score += 2
            indicators_used += 1
            details.append("Fiyat alt Bollinger bandında: Al sinyali.")
        elif close[latest] > upper_band[latest]:
            score -= 2
            indicators_used += 1
            details.append("Fiyat üst Bollinger bandında: Sat sinyali.")
        elif close[latest] < middle_band[latest]:
            score += 1
            indicators_used += 1
            details.append("Fiyat orta Bollinger bandının altında: Potansiyel alım fırsatı.")
        else:
            details.append("Fiyat Bollinger bantları arasında: Nötr hareket.")

    # MFI Değerlendirmesi (Hacim Bazlı)
    if len(mfi) > 0 and not np.isnan(mfi[latest]):
        if mfi[latest] < 20:
            score += 2
            indicators_used += 1
            details.append(f"MFI {mfi[latest]:.2f}: Aşırı satım (Hacim bazlı alım sinyali).")
        elif mfi[latest] > 80:
            score -= 2
            indicators_used += 1
            details.append(f"MFI {mfi[latest]:.2f}: Aşırı alım (Sat sinyali).")
        else:
            details.append(f"MFI {mfi[latest]:.2f}: Nötr seviyede.")

    # StochRSI Değerlendirmesi
    if len(stoch_k) > 0 and not np.isnan(stoch_k[latest]):
        if stoch_k[latest] < 20:
            score += 2
            indicators_used += 1
            details.append(f"StochRSI {stoch_k[latest]:.2f}: Aşırı satım (Al sinyali).")
        elif stoch_k[latest] > 80:
            score -= 2
            indicators_used += 1
            details.append(f"StochRSI {stoch_k[latest]:.2f}: Aşırı alım (Sat sinyali).")
        else:
            details.append(f"StochRSI {stoch_k[latest]:.2f}: Nötr bölgede.")

    # MACD Değerlendirmesi
    if len(macd) > 0 and not np.isnan(macd[latest]):
        if macd[latest] > macd_signal[latest]:
            score += 2
            indicators_used += 1
            details.append("MACD > Sinyal: Yükseliş.")
        else:
            score -= 2
            indicators_used += 1
            details.append("MACD < Sinyal: Düşüş.")
    else:
        details.append("MACD hesaplanamadı.")

    # Sinyal Gücü Değerlendirmesi
    signal_strength = "Güçlü" if indicators_used >= 4 else "Zayıf" if indicators_used <= 2 else "Orta"
    details.append(f"Sinyal {indicators_used} indikatör tarafından destekleniyor. (Sinyal Gücü: {signal_strength})")

    return score, details




# Gelişmiş sinyal analizi (çoklu zaman dilimi)
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
        volume = data["volume"]

        if len(close) < 52:
            continue

        score, details = score_and_comment_indicators(close, high, low, volume)
        total_score += score
        all_details.append(f"{interval} zaman dilimi:\n" + "\n".join(details))
        latest_price = close[-1]

    # Dinamik eşik belirleme
    if total_score >= 3:
        signal = "Buy"
    elif total_score < 1:
        signal = "Sell"
    else:
        signal = "Hold"

    return {
        "symbol": symbol,
        "signal": signal,
        "current_price": latest_price,
        "comment": f"\n\nKısa, Orta ve Uzun Vade Analizleri:\n" + "\n\n".join(all_details)
    }


