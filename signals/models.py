from django.db import models
from django.contrib.auth.models import AbstractUser
import os
from django.conf import settings

class CustomUser(AbstractUser):
    PACKAGE_CHOICES = [
        ('free', 'Ücretsiz'),
        ('premium', 'Premium'),
    ]
    
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    package = models.CharField(
        max_length=10, 
        choices=PACKAGE_CHOICES,
        default='free',
        verbose_name='Paket'
    )

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

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    pair = models.CharField(max_length=20)
    signal = models.CharField(max_length=4, choices=SIGNAL_CHOICES)
    price_at_signal = models.DecimalField(max_digits=20, decimal_places=8)
    short_comment = models.CharField(max_length=200)
    detailed_comment = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)
    pair_icon = models.URLField(null=True, blank=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.pair} - {self.signal} ({self.timeframe})"


class CryptoPair(models.Model):
    symbol = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    icon = models.ImageField(upload_to='pair_icons/', null=True, blank=True)
    market_cap = models.DecimalField(max_digits=20, decimal_places=2)
    last_price = models.DecimalField(max_digits=20, decimal_places=8)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-market_cap']

    def save(self, *args, **kwargs):
        # Eski ikonu sil (varsa)
        if self.pk:
            old_instance = CryptoPair.objects.get(pk=self.pk)
            if old_instance.icon and old_instance.icon != self.icon:
                if os.path.isfile(old_instance.icon.path):
                    os.remove(old_instance.icon.path)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.symbol})"
