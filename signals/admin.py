from django.contrib import admin
from .models import CustomUser, Signal, CryptoPair

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_active', 'is_staff')
    search_fields = ('username', 'email')
    list_filter = ('is_active', 'is_staff')

@admin.register(Signal)
class SignalAdmin(admin.ModelAdmin):
    list_display = ('pair', 'signal', 'price_at_signal', 'user', 'updated_at')
    list_filter = ('signal', 'user')
    search_fields = ('pair', 'user__username')
    ordering = ('-updated_at',)

@admin.register(CryptoPair)
class CryptoPairAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'name', 'last_price', 'market_cap', 'last_updated')
    search_fields = ('symbol', 'name')
    ordering = ('-market_cap',)