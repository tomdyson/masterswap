"""
URL Configuration for core app.
"""

from django.urls import path
from core import views

urlpatterns = [
    # Public pages
    path('', views.landing_page, name='landing'),
    path('login/', views.login_page, name='login'),
    path('auth/verify/', views.auth_verify, name='auth_verify'),

    # Authenticated pages
    path('dashboard/', views.dashboard, name='dashboard'),
    path('tracks/', views.browse_tracks, name='browse_tracks'),
    path('tracks/<uuid:track_id>/', views.track_detail, name='track_detail'),
    path('tracks/<uuid:track_id>/reviews/', views.track_reviews, name='track_reviews'),
    path('upload/', views.upload_track, name='upload_track'),
    path('my-tracks/', views.my_tracks, name='my_tracks'),
    path('my-reviews/', views.my_reviews, name='my_reviews'),
    path('users/<uuid:user_id>/', views.user_profile, name='user_profile'),
    path('transactions/', views.transaction_history, name='transactions'),
]
