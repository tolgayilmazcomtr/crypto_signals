from django.shortcuts import render, redirect
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from rest_framework.permissions import IsAuthenticated
from .utils import (
    get_crypto_prices,
    get_live_price,
    get_historical_prices,
    analyze_signals_advanced
)
from .models import Signal
from .tasks import generate_signals
from decimal import Decimal
import numpy as np
import talib
def generate_signals():
    pairs = get_top_15_cryptos()
    signals_list = []

    for pair in pairs:
        live_price = get_live_price(pair)
        historical_prices = get_historical_prices(pair, interval='1h', limit=100)

        if live_price is None or len(historical_prices) < 20:
            continue

        close_prices = np.array(historical_prices)
        rsi = talib.RSI(close_prices, timeperiod=14)[-1]
        macd, macd_signal, _ = talib.MACD(close_prices)
        upper_band, _, _ = talib.BBANDS(close_prices, timeperiod=20)

        # Sinyal Üretme
        if rsi < 30 and macd[-1] > macd_signal[-1] and live_price < upper_band[-1]:
            signal = 'Buy'
        elif rsi > 70 and macd[-1] < macd_signal[-1] and live_price > upper_band[-1]:
            signal = 'Sell'
        else:
            signal = 'Hold'

        target_price = round(float(upper_band[-1]) * 0.98, 2)

        live_price = Decimal(str(live_price))
        target_price = Decimal(str(target_price))

        signals_list.append({
            'pair': pair,
            'signal': signal,
            'price_at_signal': live_price,
            'target_price': target_price,
            'updated_at': now()
        })

    return signals_list
class CryptoPricesAPIView(APIView):
    def get(self, request):
        prices = get_crypto_prices()
        return Response(prices)


class CryptoSignalsAPIView(APIView):
    def get(self, request):
        symbol = request.GET.get('symbol', 'BTCUSDT')
        analysis = analyze_signals_advanced(symbol)
        if analysis.get("signal") is None:
            return Response({"error": "Analiz yapılamadı"}, status=400)
        return Response(analysis)


class LivePriceAPIView(APIView):
    def get(self, request):
        symbol = request.GET.get('symbol', 'BTCUSDT')
        price = get_live_price(symbol)
        if price is None:
            return Response({"error": "Fiyat alınamadı"}, status=400)
        return Response({"price": price})


class SignalListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        signals = Signal.objects.all().values('pair', 'signal', 'timeframe', 'updated_at')
        return Response(list(signals))


@login_required
def trade_signal_view(request):
    # Binance'den parite listesi çek
    prices = get_crypto_prices()
    pairs = [price['symbol'] for price in prices if price['symbol'].endswith('USDT')]

    selected_pair = request.GET.get('pair', 'BTCUSDT')
    live_price = get_live_price(selected_pair)

    # Seçilen parite için analiz yap
    analysis = analyze_signals_advanced(selected_pair)
    signal = analysis.get("signal", "Hold")
    timeframe = analysis.get("timeframe", "Short")
    comment = analysis.get("comment", "Analiz yapılamadı.")

    # Mevcut sinyali veritabanında güncelle veya oluştur
    Signal.objects.update_or_create(
        pair=selected_pair,
        defaults={
            'signal': signal,
            'timeframe': timeframe
        }
    )

    # Tüm sinyalleri çek
    signals = Signal.objects.all().order_by('-updated_at')[:15]

    return render(request, 'trade_signal.html', {
        'pairs': pairs,
        'selected_pair': selected_pair,
        'live_price': live_price or "Veri alınamadı",
        'signal': signal,
        'comment': comment,
        'signals': signals,  # Tüm sinyalleri tabloya ekle
    })


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "Başarıyla giriş yapıldı.")
            return redirect('trade-signal')
        else:
            messages.error(request, "Kullanıcı adı veya şifre hatalı.")
            return redirect('login')

    return render(request, 'login.html', {})


def logout_view(request):
    logout(request)
    messages.success(request, "Çıkış yapıldı.")
    return redirect('logout_done')


def logout_done_view(request):
    return render(request, 'logout.html')
