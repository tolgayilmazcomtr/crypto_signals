# signals/urls.py

from django.urls import path
from .views import (
    CryptoPricesAPIView,
    CryptoSignalsAPIView,
    LivePriceAPIView,
    SignalListAPIView,
    trade_signal_view,
    login_view,
    logout_view,
    logout_done_view
)

urlpatterns = [
    path('crypto-prices/', CryptoPricesAPIView.as_view(), name='crypto-prices'),
    path('crypto-signals/', CryptoSignalsAPIView.as_view(), name='crypto-signals'),
    path('live-price/', LivePriceAPIView.as_view(), name='live-price'),
    path('signals/', SignalListAPIView.as_view(), name='signal-list'),
    path('trade-signal/', trade_signal_view, name='trade-signal'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('logout_done/', logout_done_view, name='logout_done'),
    
]
