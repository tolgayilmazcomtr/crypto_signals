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
    analyze_signals_advanced
)
from .models import Signal
from .tasks import generate_signals
from django.utils.timezone import localtime


# Kripto Para Fiyatlarını Getiren API Endpoint
class CryptoPricesAPIView(APIView):
    def get(self, request):
        prices = get_crypto_prices()
        return Response(prices)


# Sinyal Analizi Yapan API Endpoint
class CryptoSignalsAPIView(APIView):
    def get(self, request):
        symbol = request.GET.get('symbol', 'BTCUSDT')
        try:
            analysis = analyze_signals_advanced(symbol)
            if analysis.get("signal") is None:
                raise ValueError("Analiz yapılamadı.")
            return Response(analysis)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Canlı Fiyatları Döndüren API Endpoint
class LivePriceAPIView(APIView):
    def get(self, request):
        symbol = request.GET.get('symbol', 'BTCUSDT')
        price = get_live_price(symbol)
        if price is None:
            return Response({"error": "Fiyat alınamadı"}, status=400)
        return Response({"price": price})


# Tüm Sinyalleri Listeleyen API Endpoint
class SignalListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        signals = [
            {
                **signal,
                'updated_at': localtime(signal['updated_at']).strftime('%d %B %Y, %H:%M')
            }
            for signal in Signal.objects.all().values('pair', 'signal', 'timeframe', 'updated_at')
        ]
        return Response(signals)


# Kullanıcı Girişi Görünümü
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

    return render(request, 'login.html')


# Kullanıcı Çıkışı Görünümü
def logout_view(request):
    logout(request)
    messages.success(request, "Çıkış yapıldı.")
    return redirect('logout_done')


# Çıkış Sonrası Görünüm
def logout_done_view(request):
    return render(request, 'logout.html')


# Sinyal Analizi Sayfası
@login_required
def trade_signal_view(request):
    # Binance'den parite listesi çek
    prices = get_crypto_prices()
    pairs = [price['symbol'] for price in prices if price['symbol'].endswith('USDT')]

    # Seçilen pariteyi al (Varsayılan: BTCUSDT)
    selected_pair = request.GET.get('pair', 'BTCUSDT')
    live_price = get_live_price(selected_pair)
    analysis = analyze_signals_advanced(selected_pair)

    # Sinyal analizi ve yorum
    signal = analysis.get("signal", "Hold")
    timeframe = analysis.get("timeframe", "Short")
    comment = analysis.get("comment", "Analiz yapılamadı.")

    # Sinyali veritabanında güncelle veya oluştur
    Signal.objects.update_or_create(
        pair=selected_pair,
        defaults={
            'signal': signal,
            'timeframe': timeframe
        }
    )

    # Tüm sinyalleri çek
    signals = Signal.objects.all()
    return render(request, 'trade_signal.html', {
        'pairs': pairs,
        'selected_pair': selected_pair,
        'live_price': live_price or "Veri alınamadı",
        'signal': signal,
        'comment': comment,
        'signals': signals,
    })
