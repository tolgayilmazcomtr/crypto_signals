from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    is_premium = models.BooleanField(default=False)  # Premium kullanıcı kontrolü

class Signal(models.Model):
    SIGNAL_CHOICES = [
        ('Buy', 'Al'),
        ('Sell', 'Sat'),
        ('Hold', 'Bekle'),
    ]

    TIMEFRAME_CHOICES = [
        ('Short', 'Kısa Vade'),
        ('Medium', 'Orta Vade'),
        ('Long', 'Uzun Vade'),
    ]

    pair = models.CharField(max_length=20, unique=True)
    signal = models.CharField(max_length=4, choices=SIGNAL_CHOICES)
    timeframe = models.CharField(max_length=6, choices=TIMEFRAME_CHOICES)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.pair} - {self.signal} ({self.timeframe})"
