from django.core.management.base import BaseCommand
import requests

class Command(BaseCommand):
    help = 'CoinGecko API bağlantısını test eder'

    def handle(self, *args, **kwargs):
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 10,  # Test için sadece 10 parite
            'sparkline': False
        }

        try:
            self.stdout.write('CoinGecko API\'ye bağlanılıyor...')
            response = requests.get(url, params=params)
            self.stdout.write(f'API Yanıt Kodu: {response.status_code}')
            
            if response.status_code == 200:
                data = response.json()
                self.stdout.write(f'Başarıyla {len(data)} parite çekildi.')
                for coin in data:
                    self.stdout.write(f"Parite: {coin['symbol']} - {coin['name']} - ${coin.get('current_price', 0)}")
            else:
                self.stdout.write(self.style.ERROR(f'API yanıt hatası: {response.text}'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Hata: {str(e)}')) 