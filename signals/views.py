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
    return render(request, 'logout.html')

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
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            user.package = 'free'
            user.save()
            
            messages.success(request, "Hesabınız başarıyla oluşturuldu!")
            return redirect('signals:login')
            
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
def connect_telegram(request):
    if request.method == 'POST':
        telegram_id = request.POST.get('telegram_id')
        
        try:
            # Telegram ID'yi doğrula
            bot = TryptoBot()
            await bot.send_message(
                telegram_id,
                "Torypto bot bağlantınız başarıyla kuruldu! "
                "Artık sinyalleri ve fiyat alarmlarını Telegram üzerinden alabilirsiniz."
            )
            
            # Kullanıcı bilgilerini güncelle
            request.user.telegram_id = telegram_id
            request.user.telegram_notifications = True
            request.user.save()
            
            messages.success(request, "Telegram bağlantınız başarıyla kuruldu!")
            
        except Exception as e:
            messages.error(request, "Telegram bağlantısı kurulamadı. Lütfen ID'nizi kontrol edin.")
            
    return render(request, 'connect_telegram.html')
