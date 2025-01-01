# signals/urls.py

from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'signals'

urlpatterns = [
    path('', views.trade_signal_view, name='trade-signal'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('logout/done/', views.logout_done_view, name='logout_done'),
    path('packages/', views.packages_view, name='packages'),
    path('reset-password/', views.reset_password_view, name='reset-password'),
    path('reset-password/confirm/<uidb64>/<token>/', 
         views.CustomPasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),
    path('upgrade/', views.upgrade_to_premium, name='upgrade'),
]
