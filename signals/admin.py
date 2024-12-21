from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Signal

@admin.register(Signal)
class SignalAdmin(admin.ModelAdmin):
    list_display = ('pair', 'signal', 'price_at_signal', 'target_price', 'updated_at')
    list_filter = ('signal', 'timeframe')
    search_fields = ('pair',)