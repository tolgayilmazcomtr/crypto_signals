# your_app/tasks.py

from background_task import background
from .models import Signal
from .utils import analyze_signals_advanced

@background(schedule=60)  # İlk çalıştırma 60 saniye sonra
def generate_signals():
    """
    30 parite için rastgele sinyal ve timeframe belirler.
    Her parite için 10 Buy, 10 Sell ve 10 Hold sinyali oluşturur.
    """
    # Sabit pariteler listesi
    all_pairs = [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT',
        'XRPUSDT', 'DOGEUSDT', 'DOTUSDT', 'AVAXUSDT', 'LTCUSDT',
        'BCHUSDT', 'LINKUSDT', 'XLMUSDT', 'ETCUSDT', 'TRXUSDT',
        'UNIUSDT', 'XMRUSDT', 'EOSUSDT', 'FILUSDT', 'AAVEUSDT',
        'MATICUSDT', 'VETUSDT', 'THETAUSDT', 'CROUSDT', 'KSMUSDT',
        'SUSHIUSDT', 'ALGOUSDT', 'NEARUSDT', 'XTZUSDT', 'ATOMUSDT'
    ]

    # Sadece 30 pariteyi kullanıyoruz
    all_pairs = all_pairs[:30]

    # Her parite için rastgele sinyal ve timeframe belirle
    for pair in all_pairs:
        analysis = analyze_signals_advanced(pair)
        signal = analysis.get("signal", "Hold")
        timeframe = analysis.get("timeframe", "Short")

        # Sinyali güncelle veya oluştur
        Signal.objects.update_or_create(
            pair=pair,
            defaults={
                'signal': signal,
                'timeframe': timeframe,
            }
        )

    # Görevi tekrar periyodik olarak çalıştır
    generate_signals(repeat=60)  # 60 dakika (1 saat) periyodik olarak çalışacak şekilde ayarlayabilirsiniz
