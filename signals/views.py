# signals/views.py

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
    # Başlangıçta sinyalleri oluşturmak için görevi başlatın
    generate_signals()

    prices = get_crypto_prices()
    pairs = [price['symbol'] for price in prices if price['symbol'].endswith('USDT')]

    if not pairs:
        # Varsayılan pariteler
        pairs = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']

    selected_pair = request.GET.get('pair', 'BTCUSDT')
    live_price = get_live_price(selected_pair)
    historical_prices = get_historical_prices(selected_pair, interval='1h', limit=100)

    if not historical_prices or len(historical_prices.get('close', [])) == 0:
        return render(request, 'trade_signal.html', {
            'pairs': pairs,
            'selected_pair': selected_pair,
            'live_price': live_price or "Veri alınamadı",
            'signal': 'Hata',
            'comment': f"{selected_pair} için yeterli veri yok.",
            'chart_data': [],
            'buy_signals': [],
            'sell_signals': [],
        })

    analysis = analyze_signals_advanced(selected_pair)
    signal = analysis.get("signal", "Hold")
    timeframe = analysis.get("timeframe", "Short")
    comment = analysis.get("comment", "Analiz yapılamadı.")
    chart_data = historical_prices['close']

    return render(request, 'trade_signal.html', {
        'pairs': pairs,
        'selected_pair': selected_pair,
        'live_price': live_price or "Veri alınamadı",
        'signal': signal,
        'timeframe': timeframe,
        'comment': comment,
        'chart_data': chart_data,
        'buy_signals': [],
        'sell_signals': [],
    })

def login_view(request):
    """
    Kullanıcı girişini yönetir.
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "Başarıyla giriş yapıldı.")
            return redirect('trade-signal')  # Giriş sonrası yönlendirme
        else:
            messages.error(request, "Kullanıcı adı veya şifre hatalı.")
            return redirect('login')  # Hata durumunda login sayfasına yönlendir

    return render(request, 'login.html', {})

def logout_view(request):
    """
    Kullanıcı çıkışını yönetir.
    """
    logout(request)
    messages.success(request, "Çıkış yapıldı.")
    return redirect('logout_done')

def logout_done_view(request):
    """
    Çıkış sonrası sayfayı görüntüler.
    """
    return render(request, 'logout.html')
