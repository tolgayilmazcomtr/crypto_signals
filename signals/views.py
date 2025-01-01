from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Signal, CryptoPair, CustomUser
from .utils import (
    get_live_price,
    analyze_signals_advanced,
    update_crypto_pairs,
)
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.template.loader import get_template
from django.template import TemplateDoesNotExist
import os
from smtplib import SMTPAuthenticationError
from django.contrib.auth.views import PasswordResetConfirmView
from django.urls import reverse_lazy
from woocommerce import API
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import HttpResponse
import hmac
import hashlib

# WooCommerce API yapılandırması
wcapi = API(
    url=settings.WOOCOMMERCE_URL,
    consumer_key=settings.WOOCOMMERCE_CONSUMER_KEY,
    consumer_secret=settings.WOOCOMMERCE_CONSUMER_SECRET,
    version="wc/v3",
    wp_api=True,
    timeout=30
)

def login_view(request):
    # Zaten giriş yapmış kullanıcıyı yönlendir
    if request.user.is_authenticated:
        return redirect('signals:trade-signal')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('signals:trade-signal')
        else:
            messages.error(request, "Kullanıcı adı veya şifre hatalı.")
            return redirect('signals:login')
    
    return render(request, 'login.html')

@login_required(login_url='signals:login')
def trade_signal_view(request):
    # Kullanıcının paketine göre pariteleri filtrele
    if request.user.package == 'free':
        # Ücretsiz kullanıcılar için sadece BTC ve ETH
        pairs = CryptoPair.objects.filter(
            symbol__in=['BTCUSDT', 'ETHUSDT']
        ).order_by('-market_cap')
    else:
        # Premium kullanıcılar için tüm pariteler
        pairs = CryptoPair.objects.all().order_by('-market_cap')
    
    # Parite listesi boşsa veya 1 saatten eskiyse güncelle
    if not pairs.exists() or (timezone.now() - pairs.first().last_updated).total_seconds() > 3600:
        update_crypto_pairs()
        pairs = CryptoPair.objects.all().order_by('-market_cap')

    selected_pair = request.GET.get('pair', 'BTCUSDT')
    
    try:
        # Seçili paritenin detaylarını al
        selected_pair_info = CryptoPair.objects.get(symbol=selected_pair)
        
        live_price = get_live_price(selected_pair)
        if live_price is None:
            live_price = "Veri alınamadı"
            messages.warning(request, f"{selected_pair} için fiyat verisi alınamadı.")

        # Seçilen parite için analiz yap
        analysis = analyze_signals_advanced(selected_pair)
        
        # Analiz sonuçlarını ayır
        signal = analysis.get("signal", "Hold")
        
        # Kısa ve detaylı yorumları doğrudan al
        short_comment = analysis.get("short_comment", "Analiz yapılıyor...")
        detailed_comment = analysis.get("comment", "")

        # Kullanıcıya özel son 15 sinyali getir
        signals = Signal.objects.filter(user=request.user).order_by('-updated_at')[:15]

        # Yeni sinyal oluştur veya güncelle
        Signal.objects.update_or_create(
            user=request.user,
            pair=selected_pair,
            defaults={
                'signal': signal,
                'price_at_signal': live_price if live_price != "Veri alınamadı" else 0,
                'short_comment': short_comment,
                'detailed_comment': detailed_comment,
                'pair_icon': selected_pair_info.icon.url if selected_pair_info.icon else None
            }
        )
        
        context = {
            'pairs': pairs,
            'selected_pair': selected_pair,
            'selected_pair_info': selected_pair_info,
            'signal': signal,
            'short_comment': short_comment,
            'detailed_comment': detailed_comment,
            'live_price': live_price,
            'signals': signals
        }
        
        return render(request, 'trade_signal.html', context)

    except Exception as e:
        messages.error(request, f"Analiz sırasında bir hata oluştu: {str(e)}")
        return redirect('signals:trade-signal')

def logout_view(request):
    logout(request)
    return redirect('signals:logout_done')

def logout_done_view(request):
    return render(request, 'logout_done.html')

def packages_view(request):
    return render(request, 'packages.html')

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')

        if password != password2:
            messages.error(request, "Parolalar eşleşmiyor!")
            return redirect('signals:register')

        try:
            # Yeni kullanıcı oluştur
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            # Ücretsiz paket ata
            user.package = 'free'  # Bu zaten varsayılan değer ama açıkça belirtelim
            user.save()
            
            # Başarılı mesajı göster
            messages.success(request, "Hesabınız başarıyla oluşturuldu! Şimdi giriş yapabilirsiniz.")
            
            # Otomatik giriş yap
            login(request, user)
            
            # Ana sayfaya yönlendir
            return redirect('signals:trade-signal')
            
        except Exception as e:
            messages.error(request, f"Kayıt olurken bir hata oluştu: {str(e)}")
            return redirect('signals:register')

    return render(request, 'register.html')

def reset_password_view(request):
    if request.user.is_authenticated:
        return redirect('signals:trade-signal')
        
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = CustomUser.objects.get(email=email)
            token = default_token_generator.make_token(user)
            reset_url = request.build_absolute_uri(
                reverse('signals:password_reset_confirm', args=[user.pk, token])
            )
            
            try:
                # E-posta göndermeyi dene
                send_mail(
                    subject='Şifre Sıfırlama - Torypto',
                    message=f'''
                    Merhaba,
                    
                    Şifrenizi sıfırlamak için aşağıdaki bağlantıya tıklayın:
                    
                    {reset_url}
                    
                    Bu bağlantı 24 saat geçerlidir.
                    
                    Eğer şifre sıfırlama talebinde bulunmadıysanız, bu e-postayı dikkate almayın.
                    
                    Saygılarımızla,
                    Torypto Ekibi
                    ''',
                    from_email='info@torypto.com',
                    recipient_list=[email],
                    fail_silently=False,
                )
                messages.success(request, "Şifre sıfırlama bağlantısı e-posta adresinize gönderildi.")
                
            except SMTPAuthenticationError:
                messages.error(request, "E-posta gönderirken bir hata oluştu. Lütfen daha sonra tekrar deneyin.")
                print("SMTP Authentication Error: E-posta ayarlarını kontrol edin")
                
            except Exception as e:
                messages.error(request, "E-posta gönderirken bir hata oluştu. Lütfen daha sonra tekrar deneyin.")
                print(f"E-posta gönderme hatası: {str(e)}")
            
            return redirect('signals:login')
            
        except CustomUser.DoesNotExist:
            messages.error(request, "Bu e-posta adresiyle kayıtlı kullanıcı bulunamadı.")
    
    return render(request, 'registration/reset_password.html')

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'registration/reset_password_confirm.html'
    success_url = reverse_lazy('signals:login')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['validlink'] = self.validlink
        return context

@login_required
def upgrade_to_premium(request):
    if request.method == 'POST':
        user = request.user
        user.package = 'premium'
        user.save()
        messages.success(request, "Paketiniz Premium'a yükseltildi!")
        return redirect('signals:trade-signal')
    
    return render(request, 'upgrade.html')

@login_required
def process_payment(request):
    if request.method == 'POST':
        try:
            # Debug için
            print("WooCommerce URL:", settings.WOOCOMMERCE_URL)
            print("Product ID:", settings.PREMIUM_PRODUCT_ID)
            
            order_data = {
                "payment_method": "iyzico",
                "payment_method_title": "Kredi Kartı",
                "status": "pending",
                "customer_id": 0,
                "billing": {
                    "first_name": request.user.username,
                    "email": request.user.email,
                    "country": "TR"
                },
                "shipping": {
                    "first_name": request.user.username,
                    "country": "TR"
                },
                "line_items": [
                    {
                        "product_id": int(settings.PREMIUM_PRODUCT_ID),
                        "quantity": 1
                    }
                ],
                "meta_data": [
                    {
                        "key": "django_user_id",
                        "value": str(request.user.id)
                    }
                ],
                "return_url": f"{settings.WOOCOMMERCE_URL}/tesekkurler",  # Başarılı ödeme sonrası yönlendirme
            }
            
            response = wcapi.post("orders", order_data)
            
            if response.status_code in [200, 201]:
                order = response.json()
                payment_url = order.get('payment_url')
                
                if payment_url:
                    return redirect(payment_url)
                    
            # ... hata durumları aynı ...
            
            return redirect('signals:upgrade')
            
        except Exception as e:
            print("Hata Detayı:", str(e))
            messages.error(request, 'Ödeme işlemi başlatılırken bir hata oluştu.')
            return redirect('signals:upgrade')
            
    return redirect('signals:upgrade')

# WooCommerce webhook handler
@csrf_exempt
def woocommerce_webhook(request):
    if request.method == 'POST':
        # Webhook imzasını doğrula
        signature = request.headers.get('X-WC-Webhook-Signature')
        if not signature:
            return HttpResponse("İmza eksik", status=401)

        # Gelen veriyi imzala
        payload = request.body
        expected_signature = hmac.new(
            settings.WOOCOMMERCE_WEBHOOK_SECRET.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()

        # İmzaları karşılaştır
        if not hmac.compare_digest(signature, expected_signature):
            return HttpResponse("Geçersiz imza", status=401)

        try:
            # Webhook verisini al
            payload = json.loads(request.body)
            
            # Sipariş durumunu kontrol et
            if payload.get('status') == 'completed':
                # Meta datadan Django kullanıcı ID'sini al
                meta_data = payload.get('meta_data', [])
                django_user_id = None
                
                for meta in meta_data:
                    if meta.get('key') == 'django_user_id':
                        django_user_id = meta.get('value')
                        break
                
                if django_user_id:
                    try:
                        # Kullanıcıyı bul ve premium yap
                        user = CustomUser.objects.get(id=django_user_id)
                        user.package = 'premium'
                        user.save()
                        
                        # Başarılı mesaj gönder
                        messages.success(request, 'Premium pakete başarıyla geçiş yaptınız!')
                        
                        return HttpResponse(status=200)
                    except CustomUser.DoesNotExist:
                        return HttpResponse("Kullanıcı bulunamadı", status=404)
                
            return HttpResponse(status=200)
            
        except json.JSONDecodeError:
            return HttpResponse("Geçersiz JSON", status=400)
        except Exception as e:
            print(f"Webhook hatası: {str(e)}")
            return HttpResponse(str(e), status=500)
    
    return HttpResponse("Yalnızca POST istekleri kabul edilir", status=405)

def payment_success_view(request):
    return render(request, 'payment_success.html')
