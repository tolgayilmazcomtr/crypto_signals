from django.core.management.base import BaseCommand
from signals.utils import update_crypto_pairs

class Command(BaseCommand):
    help = 'CoinGecko\'dan parite verilerini çeker ve veritabanını günceller'

    def handle(self, *args, **kwargs):
        self.stdout.write('Pariteler çekiliyor...')
        
        success = update_crypto_pairs()
        
        if success:
            self.stdout.write(self.style.SUCCESS('Pariteler başarıyla güncellendi!'))
        else:
            self.stdout.write(self.style.ERROR('Parite güncellemesi başarısız oldu!')) 