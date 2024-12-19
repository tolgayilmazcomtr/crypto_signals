from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .utils import get_crypto_prices
from .utils import get_crypto_prices, analyze_signals

class CryptoPricesAPIView(APIView):
    def get(self, request):
        prices = get_crypto_prices()
        return Response(prices)

class CryptoSignalsAPIView(APIView):
    def get(self, request):
        prices = get_crypto_prices()
        if "error" in prices:
            return Response(prices, status=400)
        signals = analyze_signals(prices)
        return Response(signals)
