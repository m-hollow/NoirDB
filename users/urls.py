"""Define URL patterns for users app"""

from django.urls import path, include
from .views import RegisterView, CloseAccount, CloseSuccess

# the auth views for password reset will fail with the namespace
#app_name = 'users'
urlpatterns = [
    # Include default auth urls.
    path('', include('django.contrib.auth.urls')),
    # Registration page
    path('register/', RegisterView.as_view(), name='register'),

    # page to allow user to inactivate their account
    path('close_account/<int:pk>-<str:slug>/', CloseAccount.as_view(), name='close_account'),

    path('close_success/', CloseSuccess.as_view(), name='close_success'),
]
