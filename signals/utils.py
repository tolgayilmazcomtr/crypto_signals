import requests
import talib
import numpy as np
from time import sleep
from django.db import models
from pathlib import Path
import os
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from urllib.parse import urlparse
from django.conf import settings

# CoinGecko API endpoint'leri
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

def convert_symbol_to_coingecko_id(symbol):
    """Binance sembolünü (BTCUSDT) CoinGecko ID'sine çevirir"""
    # USDT'yi kaldır
    base_symbol = symbol.replace('USDT', '').lower()
    
    # Önce yaygın sembolleri kontrol et
    common_symbols = {
        'btc': 'bitcoin',
        'eth': 'ethereum',
        'bnb': 'binancecoin',
        'xrp': 'ripple',
        'doge': 'dogecoin',
        'ada': 'cardano',
        'sol': 'solana',
        'dot': 'polkadot',
        'avax': 'avalanche-2',
        'matic': 'matic-network',
        'link': 'chainlink',
        'uni': 'uniswap',
        'atom': 'cosmos',
        'ltc': 'litecoin',
        'etc': 'ethereum-classic'
    }
    
    # Önce yaygın sembollerden kontrol et
    if base_symbol in common_symbols:
        return common_symbols[base_symbol]
    
    # Sonra global symbol map'ten kontrol et
    if base_symbol in SYMBOL_MAP:
        return SYMBOL_MAP[base_symbol]
    
    # Bulunamazsa sembolün kendisini kullan
    return base_symbol

def get_historical_prices(symbol, interval='1h', limit=200):
    """CoinGecko'dan geçmiş fiyat verilerini çeker"""
    try:
        coin_id = convert_symbol_to_coingecko_id(symbol)
        print(f"Coin ID: {coin_id} için veri çekiliyor...")
        
        # Zaman aralığına göre gün sayısını ayarla
        if interval == '1h':
            days = max(limit // 24 + 1, 3)  # En az 3 gün
        elif interval == '4h':
            days = max(limit // 6 + 1, 7)   # En az 7 gün
        else:  # Günlük veri için
            days = max(limit, 30)  # En az 30 gün
        
        url = f"{COINGECKO_BASE_URL}/coins/{coin_id}/market_chart"
        params = {
            'vs_currency': 'usd',
            'days': str(days),
            'interval': 'hourly' if interval in ['1h', '4h'] else 'daily'
        }
        
        print(f"API İsteği: {url} - Parametreler: {params}")
        
        # Rate limit kontrolü
        rate_limit_check()
        
        response = requests.get(url, params=params)
        print(f"API Yanıt Kodu: {response.status_code}")
        
        if response.status_code == 429:
            print("Rate limit aşıldı, bekleniyor...")
            smart_rate_limit_handler(response)
            response = requests.get(url, params=params)
        
        response.raise_for_status()
        data = response.json()
        
        if not data or 'prices' not in data:
            print(f"Veri alınamadı: {coin_id}")
            return None

        prices = data['prices']
        volumes = data.get('total_volumes', [])
        
        if not prices:
            print(f"Fiyat verisi boş: {coin_id}")
            return None

        print(f"Çekilen veri sayısı: {len(prices)}")
        
        # Veriyi numpy dizilerine dönüştür
        close_prices = np.array([float(price[1]) for price in prices])
        volumes = np.array([float(volume[1]) for volume in volumes]) if volumes else np.zeros_like(close_prices)
        
        # 4 saatlik veri için örnekleme
        if interval == '4h':
            close_prices = close_prices[::4]
            volumes = volumes[::4]
        
        # High ve low değerleri için yaklaşık değerler
        high_prices = close_prices * 1.002
        low_prices = close_prices * 0.998
        
        # Son limit kadar veriyi al
        close_prices = close_prices[-limit:]
        high_prices = high_prices[-limit:]
        low_prices = low_prices[-limit:]
        volumes = volumes[-limit:]
        
        print(f"İşlenen veri sayısı: {len(close_prices)}")
        
        return {
            "close": close_prices,
            "high": high_prices,
            "low": low_prices,
            "volume": volumes
        }
    except Exception as e:
        print(f"Veri çekme hatası ({symbol}): {str(e)}")
        return None

def get_live_price(symbol):
    """CoinGecko'dan anlık fiyat çeker"""
    coin_id = convert_symbol_to_coingecko_id(symbol)
    url = f"{COINGECKO_BASE_URL}/simple/price"
    params = {
        'ids': coin_id,
        'vs_currencies': 'usd'
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return float(data[coin_id]['usd'])
    except requests.exceptions.RequestException as e:
        print(f"CoinGecko API Hatası: {e}")
        return None

def get_crypto_prices():
    """CoinGecko'dan tüm kripto para fiyatlarını çeker"""
    url = f"{COINGECKO_BASE_URL}/coins/markets"
    all_coins = []
    page = 1
    
    try:
        # İlk sayfa için deneme
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 250,
            'page': page,
            'sparkline': False
        }
        
        response = requests.get(url, params=params)
        print(f"API Yanıt Kodu: {response.status_code}")  # Debug için
        
        if response.status_code == 429:  # Rate limit aşıldı
            print("Rate limit aşıldı. 60 saniye bekleniyor...")
            sleep(60)  # 1 dakika bekle
            response = requests.get(url, params=params)  # Tekrar dene
        
        response.raise_for_status()
        data = response.json()
        
        if not data:
            print("API'den veri alınamadı")
            return {"error": "Veri alınamadı"}
            
        # Gelen verileri formatlayıp listeye ekle
        formatted_coins = [
            {
                'symbol': f"{coin['symbol'].upper()}USDT",
                'price': str(coin.get('current_price', 0)),
                'name': coin.get('name', ''),
                'id': coin.get('id', ''),
                'market_cap': coin.get('market_cap', 0),
                'volume': coin.get('total_volume', 0)
            }
            for coin in data
            if coin.get('symbol') and coin.get('current_price')  # Sadece geçerli verileri al
        ]
        
        all_coins.extend(formatted_coins)
        
        # Market cap'e göre sırala
        all_coins.sort(key=lambda x: float(x.get('market_cap', 0)), reverse=True)
        
        if not all_coins:  # Hiç coin bulunamadıysa
            return {"error": "Kripto para listesi alınamadı"}
            
        return all_coins

    except requests.exceptions.RequestException as e:
        print(f"CoinGecko API Hatası: {e}")  # Debug için
        return {"error": f"API bağlantı hatası: {str(e)}"}
    except ValueError as e:  # JSON parse hatası
        print(f"JSON Parse Hatası: {e}")  # Debug için
        return {"error": "API yanıtı işlenemedi"}
    except Exception as e:
        print(f"Beklenmeyen Hata: {e}")  # Debug için
        return {"error": f"Beklenmeyen hata: {str(e)}"}

# Symbol map'i güncelleyen yardımcı fonksiyon
def update_symbol_map():
    """CoinGecko'dan tüm coin listesini çeker ve symbol map'i günceller"""
    url = f"{COINGECKO_BASE_URL}/coins/list"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        coins = response.json()
        
        # Symbol map'i güncelle
        symbol_map = {
            coin['symbol'].lower(): coin['id']
            for coin in coins
        }
        
        return symbol_map
    except requests.exceptions.RequestException as e:
        print(f"CoinGecko API Hatası: {e}")
        return {}

# Global symbol map'i oluştur
SYMBOL_MAP = update_symbol_map()

# Rate limiting için yardımcı fonksiyon
def rate_limit_check():
    """CoinGecko rate limit'ini aşmamak için bekleme"""
    sleep(1.2)  # Her istekten sonra 1.2 saniye bekle

# Stochastic RSI hesaplar
def calculate_stoch_rsi(close, period=14, smoothk=3, smoothd=3):
    """StochRSI hesaplar"""
    try:
        # Önce RSI hesapla
        rsi = talib.RSI(close, timeperiod=period)
        
        # RSI değerlerinden StochRSI hesapla
        stoch_k, stoch_d = talib.STOCH(rsi, rsi, rsi, 
                                      fastk_period=period,
                                      slowk_period=smoothk,
                                      slowk_matype=0,
                                      slowd_period=smoothd,
                                      slowd_matype=0)
        
        return stoch_k, stoch_d
    except Exception as e:
        print(f"StochRSI hesaplama hatası: {e}")
        return np.array([]), np.array([])

# Ichimoku Bulutu hesaplar (Conversion ve Base line)
def calculate_ichimoku(high, low, tenkan=9, kijun=26):
    """Ichimoku bulutunun Tenkan-sen ve Kijun-sen çizgilerini hesaplar"""
    try:
        period9_high = talib.MAX(high, timeperiod=tenkan)
        period9_low = talib.MIN(low, timeperiod=tenkan)
        tenkan_sen = (period9_high + period9_low) / 2

        period26_high = talib.MAX(high, timeperiod=kijun)
        period26_low = talib.MIN(low, timeperiod=kijun)
        kijun_sen = (period26_high + period26_low) / 2

        return tenkan_sen, kijun_sen
    except Exception as e:
        print(f"Ichimoku hesaplama hatası: {e}")
        return np.array([]), np.array([])

# Hacim bazlı Money Flow Index (MFI) hesaplar
def calculate_mfi(high, low, close, volume, period=14):
    mfi = talib.MFI(high, low, close, volume, timeperiod=period)
    return mfi

# Teknik indikatörleri hesaplar
def calculate_technical_indicators(close, high, low, volume):
    """Gelişmiş teknik indikatörleri hesaplar"""
    try:
        # Temel indikatörler
        rsi = talib.RSI(close, timeperiod=14)
        macd, macd_signal, macd_hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
        upper_band, middle_band, lower_band = talib.BBANDS(close, timeperiod=20)
        
        # Yeni indikatörler
        stoch_k, stoch_d = talib.STOCH(high, low, close, 
                                      fastk_period=14, 
                                      slowk_period=3,
                                      slowk_matype=0,
                                      slowd_period=3,
                                      slowd_matype=0)
        
        mfi = talib.MFI(high, low, close, volume, timeperiod=14)
        
        # Trend indikatörleri
        ema_9 = talib.EMA(close, timeperiod=9)
        ema_21 = talib.EMA(close, timeperiod=21)
        
        # Momentum indikatörleri
        roc = talib.ROC(close, timeperiod=10)  # Rate of Change
        cci = talib.CCI(high, low, close, timeperiod=20)  # Commodity Channel Index
        
        # Volatilite indikatörü
        atr = talib.ATR(high, low, close, timeperiod=14)  # Average True Range

        return {
            'rsi': rsi,
            'macd': macd,
            'macd_signal': macd_signal,
            'macd_hist': macd_hist,
            'upper_band': upper_band,
            'middle_band': middle_band,
            'lower_band': lower_band,
            'stoch_k': stoch_k,
            'stoch_d': stoch_d,
            'mfi': mfi,
            'ema_9': ema_9,
            'ema_21': ema_21,
            'roc': roc,
            'cci': cci,
            'atr': atr
        }
    except Exception as e:
        print(f"İndikatör hesaplama hatası: {e}")
        return None

# İndikatörleri puanlar ve yorumlar
def score_and_comment_indicators(close, high, low, volume):
    """Gelişmiş teknik analiz ve puanlama sistemi"""
    indicators = calculate_technical_indicators(close, high, low, volume)
    if not indicators:
        return 0, ["Teknik indikatörler hesaplanamadı."]

    score = 0
    details = []
    indicators_used = 0
    latest = -1
    
    try:
        # RSI Analizi (Ağırlık: 3)
        current_rsi = float(indicators['rsi'][latest])
        if not np.isnan(current_rsi):
            if current_rsi < 20:
                score += 3
                details.append(f"• RSI ({current_rsi:.1f}): Aşırı satım, güçlü alım fırsatı")
            elif current_rsi < 30:
                score += 2
                details.append(f"• RSI ({current_rsi:.1f}): Satım bölgesi, alım fırsatı")
            elif current_rsi > 80:
                score -= 3
                details.append(f"• RSI ({current_rsi:.1f}): Aşırı alım, güçlü satış sinyali")
            elif current_rsi > 70:
                score -= 2
                details.append(f"• RSI ({current_rsi:.1f}): Alım bölgesi, satış fırsatı")
            indicators_used += 1

        # MACD Analizi (Ağırlık: 2)
        current_macd = float(indicators['macd'][latest])
        current_signal = float(indicators['macd_signal'][latest])
        current_hist = float(indicators['macd_hist'][latest])
        
        if not np.isnan(current_macd) and not np.isnan(current_signal):
            if current_macd > current_signal:
                if current_hist > 0 and current_hist > indicators['macd_hist'][-2]:
                    score += 2  # Güçlenen yükseliş trendi
                    details.append("• MACD: Güçlü yükseliş trendi")
                else:
                    score += 1  # Normal yükseliş trendi
                    details.append("• MACD: Yükseliş trendi")
            else:
                if current_hist < 0 and current_hist < indicators['macd_hist'][-2]:
                    score -= 2  # Güçlenen düşüş trendi
                    details.append("• MACD: Güçlü düşüş trendi")
                else:
                    score -= 1  # Normal düşüş trendi
                    details.append("• MACD: Düşüş trendi")
            indicators_used += 1

        # Bollinger Bands Analizi (Ağırlık: 2)
        current_price = float(close[latest])
        current_upper = float(indicators['upper_band'][latest])
        current_lower = float(indicators['lower_band'][latest])
        current_middle = float(indicators['middle_band'][latest])
        
        if not np.isnan(current_upper) and not np.isnan(current_lower):
            bb_range = current_upper - current_lower
            position = (current_price - current_lower) / bb_range * 100
            
            if position < 0:  # Fiyat alt bandın altında
                score += 2
                details.append("• Bollinger: Güçlü aşırı satım bölgesi")
            elif position < 20:
                score += 1
                details.append("• Bollinger: Satım bölgesi")
            elif position > 100:  # Fiyat üst bandın üstünde
                score -= 2
                details.append("• Bollinger: Güçlü aşırı alım bölgesi")
            elif position > 80:
                score -= 1
                details.append("• Bollinger: Alım bölgesi")
            indicators_used += 1

        # Stochastic Analizi (Ağırlık: 1.5)
        current_k = float(indicators['stoch_k'][latest])
        current_d = float(indicators['stoch_d'][latest])
        
        if not np.isnan(current_k) and not np.isnan(current_d):
            if current_k < 20 and current_d < 20:
                score += 1.5
                details.append(f"• Stochastic ({current_k:.1f}/{current_d:.1f}): Aşırı satım bölgesi")
            elif current_k > 80 and current_d > 80:
                score -= 1.5
                details.append(f"• Stochastic ({current_k:.1f}/{current_d:.1f}): Aşırı alım bölgesi")
            indicators_used += 1

        # MFI Analizi (Ağırlık: 1.5)
        current_mfi = float(indicators['mfi'][latest])
        
        if not np.isnan(current_mfi):
            if current_mfi < 20:
                score += 1.5
                details.append(f"• MFI ({current_mfi:.1f}): Aşırı satım bölgesi")
            elif current_mfi > 80:
                score -= 1.5
                details.append(f"• MFI ({current_mfi:.1f}): Aşırı alım bölgesi")
            indicators_used += 1

        # Trend Analizi - EMA (Ağırlık: 2)
        current_ema9 = float(indicators['ema_9'][latest])
        current_ema21 = float(indicators['ema_21'][latest])
        
        if not np.isnan(current_ema9) and not np.isnan(current_ema21):
            if current_ema9 > current_ema21:
                if current_price > current_ema9:
                    score += 2
                    details.append("• EMA: Güçlü yükseliş trendi")
                else:
                    score += 1
                    details.append("• EMA: Yükseliş trendi")
            else:
                if current_price < current_ema9:
                    score -= 2
                    details.append("• EMA: Güçlü düşüş trendi")
                else:
                    score -= 1
                    details.append("• EMA: Düşüş trendi")
            indicators_used += 1

        # Momentum Analizi - ROC ve CCI
        current_roc = float(indicators['roc'][latest])
        current_cci = float(indicators['cci'][latest])
        
        if not np.isnan(current_roc):
            if current_roc > 2:
                score += 1
                details.append(f"• ROC ({current_roc:.1f}): Pozitif momentum")
            elif current_roc < -2:
                score -= 1
                details.append(f"• ROC ({current_roc:.1f}): Negatif momentum")
            indicators_used += 1

        if not np.isnan(current_cci):
            if current_cci > 100:
                score -= 1
                details.append(f"• CCI ({current_cci:.1f}): Aşırı alım bölgesi")
            elif current_cci < -100:
                score += 1
                details.append(f"• CCI ({current_cci:.1f}): Aşırı satım bölgesi")
            indicators_used += 1

        # Volatilite Analizi - ATR
        current_atr = float(indicators['atr'][latest])
        avg_price = current_price
        atr_percent = (current_atr / avg_price) * 100
        
        if atr_percent > 5:  # Yüksek volatilite
            details.append(f"• Volatilite: Yüksek (ATR: {atr_percent:.1f}%)")
        else:
            details.append(f"• Volatilite: Normal (ATR: {atr_percent:.1f}%)")

        # Sinyal Güvenilirliği
        reliability = min((indicators_used / 8) * 100, 100)
        details.append(f"\n• Sinyal Güvenilirliği: {reliability:.0f}% ({indicators_used} indikatör)")

        # Normalize edilmiş toplam skor
        max_possible_score = indicators_used * 2
        normalized_score = (score / max_possible_score) * 10

        return normalized_score, details

    except Exception as e:
        print(f"Sinyal analiz hatası: {e}")
        return 0, [f"Analiz hatası: {str(e)}"]

# Gelişmiş sinyal analizi (çoklu zaman dilimi)
def analyze_signals_advanced(symbol):
    intervals = ['1h', '4h', '1d']
    total_score = 0
    all_details = []  # Detaylı analiz için
    latest_price = None
    analyzed_intervals = 0
    positive_signals = 0
    total_signals = 0

    try:
        detailed_analysis = []  # Detaylı analiz için
        total_score = 0
        analyzed_intervals = 0
        positive_signals = 0
        total_signals = 0
        latest_price = None

        for interval in intervals:
            # Önce Binance'den veri çekmeyi dene
            data = get_binance_historical_prices(symbol, interval=interval)
            
            # Binance'den veri alınamazsa CoinGecko'yu dene
            if not data:
                print(f"Binance'den veri alınamadı, CoinGecko deneniyor...")
                data = get_historical_prices(symbol, interval=interval, limit=200)
            
            if not data or len(data["close"]) == 0:
                print(f"{interval} için veri alınamadı")
                continue

            close = data["close"]
            high = data["high"]
            low = data["low"]
            volume = data["volume"]

            if len(close) < 52:
                print(f"{interval} için yetersiz veri")
                continue

            score, indicator_details = score_and_comment_indicators(close, high, low, volume)
            
            # Her interval için sinyal sayılarını hesapla
            if score > 0:
                positive_signals += 1
            total_signals += 1
            
            total_score += score
            analyzed_intervals += 1

            # Detaylı analiz için period_summary oluştur
            interval_name = {
                '1h': '🕐 Kısa Vadeli (1 Saat)',
                '4h': '🕓 Orta Vadeli (4 Saat)',
                '1d': '📅 Uzun Vadeli (Günlük)'
            }

            trend_direction = "YÜKSELIŞ" if score > 0 else "DÜŞÜŞ" if score < 0 else "YATAY"
            trend_emoji = "📈" if score > 0 else "📉" if score < 0 else "↔️"

            # İndikatör yorumlarını grupla
            trend_signals = []
            momentum_signals = []
            volume_signals = []
            
            for detail in indicator_details:
                if "RSI" in detail or "EMA" in detail or "Bollinger" in detail:
                    trend_signals.append(detail)
                elif "MACD" in detail or "Stochastic" in detail or "CCI" in detail or "ROC" in detail:
                    momentum_signals.append(detail)
                elif "MFI" in detail or "Volatilite" in detail:
                    volume_signals.append(detail)

            # Her zaman dilimi için detaylı analiz
            period_analysis = [
                f"\n{interval_name[interval]} {trend_emoji}",
                f"Trend Yönü: {trend_direction}",
                "──────────────────"
            ]

            if trend_signals:
                period_analysis.append("\n📊 Trend Göstergeleri:")
                period_analysis.extend(trend_signals)
            
            if momentum_signals:
                period_analysis.append("\n💫 Momentum Göstergeleri:")
                period_analysis.extend(momentum_signals)
            
            if volume_signals:
                period_analysis.append("\n📊 Hacim ve Volatilite:")
                period_analysis.extend(volume_signals)

            detailed_analysis.append("\n".join(period_analysis))
            latest_price = float(close[-1])

        # Kısa yorum oluştur (sadece genel durum)
        if total_score >= 3:
            signal = "Buy"
            signal_text = "AL SİNYALİ"
            short_summary = f"💹 {signal_text}\n➤ Analiz edilen göstergelerin çoğunluğu alım yönünde sinyal veriyor.\n➤ Sinyal Fiyatı: ${latest_price:.2f}"
        elif total_score < 1:
            signal = "Sell"
            signal_text = "SAT SİNYALİ"
            short_summary = f"📉 {signal_text}\n➤ Analiz edilen göstergelerin çoğunluğu satış yönünde sinyal veriyor.\n➤ Sinyal Fiyatı: ${latest_price:.2f}"
        else:
            signal = "Hold"
            signal_text = "BEKLE"
            short_summary = f"⏳ {signal_text}\n➤ Göstergeler kararsız, pozisyon almadan bekleyin.\n➤ Sinyal Fiyatı: ${latest_price:.2f}"

        return {
            "symbol": symbol,
            "signal": signal,
            "current_price": latest_price,
            "short_comment": short_summary,
            "comment": "\n\n".join(detailed_analysis)
        }

    except Exception as e:
        print(f"Analiz hatası ({symbol}): {str(e)}")
        return {
            "symbol": symbol,
            "signal": "Hold",
            "current_price": None,
            "short_comment": "⚠️ Analiz yapılırken bir hata oluştu.",
            "comment": f"Hata detayı: {str(e)}"
        }

def download_pair_icon(pair_id, icon_url):
    """CoinGecko'dan parite ikonunu indir"""
    try:
        response = requests.get(icon_url)
        if response.status_code == 200:
            # Media klasörü altında pair_icons klasörü oluştur
            icon_dir = settings.MEDIA_ROOT / 'pair_icons'
            icon_dir.mkdir(parents=True, exist_ok=True)
            
            # İkon dosyasını kaydet
            icon_path = icon_dir / f"{pair_id}.png"
            with open(icon_path, 'wb') as f:
                f.write(response.content)
            
            # Modele kaydetmek için Django File objesi oluştur
            return f'pair_icons/{pair_id}.png'
    except Exception as e:
        print(f"İkon indirme hatası ({pair_id}): {str(e)}")
    return None

def update_crypto_pairs():
    """CoinGecko'dan parite verilerini güncelle"""
    try:
        url = f"{COINGECKO_BASE_URL}/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 100,
            'sparkline': False
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        pairs_data = response.json()
        
        for pair_data in pairs_data:
            try:
                # İkonu indir
                icon_path = download_pair_icon(pair_data['id'], pair_data['image'])
                
                # Paritenin USDT sembolünü oluştur
                symbol = f"{pair_data['symbol'].upper()}USDT"
                
                # Paritenin veritabanı kaydını güncelle
                CryptoPair.objects.update_or_create(
                    symbol=symbol,
                    defaults={
                        'name': pair_data['name'],
                        'icon': icon_path,
                        'market_cap': pair_data['market_cap'],
                        'last_price': pair_data['current_price']
                    }
                )
            except Exception as e:
                print(f"Parite güncelleme hatası ({pair_data['id']}): {str(e)}")
                continue
        
        return True
    except Exception as e:
        print(f"Beklenmeyen hata: {e}")
        return False

def get_binance_historical_prices(symbol, interval='1h', limit=200):
    """Binance'den geçmiş fiyat verilerini çeker"""
    try:
        url = "https://api.binance.com/api/v3/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        print(f"Binance API isteği: {symbol} - {interval}")
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        klines = response.json()
        
        if not klines:
            print(f"Veri bulunamadı: {symbol}")
            return None
            
        # Veriyi numpy dizilerine dönüştür
        close_prices = np.array([float(k[4]) for k in klines])  # 4: close price
        high_prices = np.array([float(k[2]) for k in klines])   # 2: high price
        low_prices = np.array([float(k[3]) for k in klines])    # 3: low price
        volumes = np.array([float(k[5]) for k in klines])       # 5: volume
        
        print(f"Veri alındı: {len(close_prices)} kayıt")
        
        return {
            "close": close_prices,
            "high": high_prices,
            "low": low_prices,
            "volume": volumes
        }
    except Exception as e:
        print(f"Binance veri çekme hatası ({symbol}): {str(e)}")
        return None


