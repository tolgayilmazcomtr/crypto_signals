from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.username


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

    pair = models.CharField(max_length=20, unique=False)
    signal = models.CharField(max_length=4, choices=SIGNAL_CHOICES)
    timeframe = models.CharField(max_length=6, choices=TIMEFRAME_CHOICES)
    price_at_signal = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    target_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.pair} - {self.signal} ({self.timeframe})"
