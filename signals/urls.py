from django.urls import path
from .views import CryptoPricesAPIView
from .views import CryptoPricesAPIView, CryptoSignalsAPIView  # CryptoSignalsAPIView eklendi

urlpatterns = [
    path('crypto-prices/', CryptoPricesAPIView.as_view(), name='crypto-prices'),
    path('crypto-signals/', CryptoSignalsAPIView.as_view(), name='crypto-signals'),
]

