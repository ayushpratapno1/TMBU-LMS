from django.urls import path
from . import views
urlpatterns=[
    path('',views.index,name='index'),
    path('aboutus/', views.aboutus,name='aboutus'),
    path('registration/', views.registration,name='registration'),
    path('login/', views.login,name='login'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('resend-otp/', views.resend_otp, name='resend_otp'),
    path('contactus/', views.contactus,name='contactus'),
]