"""
Views for Masterswap frontend pages.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.db.models import Count
from sesame.utils import get_user
from core.models import Track, Review, Transaction
from core.utils import can_use_cold_start, count_reviewable_tracks


def landing_page(request):
    """Landing page explaining how Masterswap works."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'landing.html')


def login_page(request):
    """Magic link login page."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'login.html')


def auth_verify(request):
    """
    Verify magic link token and log in user.
    Uses sesame to validate the token from URL params.
    """
    token = request.GET.get('token')
    if not token:
        return render(request, 'auth_error.html', {
            'error': 'Invalid or missing token'
        })

    # Get user from token
    user = get_user(request)

    if user is None:
        return render(request, 'auth_error.html', {
            'error': 'Invalid or expired magic link. Please request a new one.'
        })

    # Log in the user
    login(request, user)

    return redirect('dashboard')


@login_required
def dashboard(request):
    """User dashboard showing stats and recent activity."""
    user = request.user

    # Get stats
    tracks_uploaded = Track.objects.filter(uploader=user, is_deleted=False).count()
    reviews_given = Review.objects.filter(reviewer=user).count()
    reviews_received = Review.objects.filter(track__uploader=user, track__is_deleted=False).count()

    # Check if can use cold start
    can_cold_start = can_use_cold_start(user)

    # Count reviewable tracks
    reviewable_count = count_reviewable_tracks(user)

    # Recent transactions
    recent_transactions = Transaction.objects.filter(
        user=user
    ).select_related('related_track', 'related_review')[:5]

    context = {
        'user': user,
        'token_balance': user.token_balance,
        'tracks_uploaded': tracks_uploaded,
        'reviews_given': reviews_given,
        'reviews_received': reviews_received,
        'can_cold_start': can_cold_start,
        'reviewable_count': reviewable_count,
        'recent_transactions': recent_transactions,
    }

    return render(request, 'dashboard.html', context)


@login_required
def browse_tracks(request):
    """Browse tracks available for review."""
    user = request.user

    # Get tracks (exclude user's own and already reviewed)
    tracks = Track.objects.filter(
        is_deleted=False
    ).exclude(
        uploader=user
    ).exclude(
        reviews__reviewer=user
    ).annotate(
        review_count=Count('reviews')
    ).select_related('uploader').order_by('-uploaded_at')

    context = {
        'tracks': tracks,
    }

    return render(request, 'browse_tracks.html', context)


@login_required
def track_detail(request, track_id):
    """Track detail and review submission page."""
    user = request.user

    track = get_object_or_404(
        Track.objects.annotate(review_count=Count('reviews')).select_related('uploader'),
        id=track_id,
        is_deleted=False
    )

    # Check if user has reviewed this track
    user_has_reviewed = Review.objects.filter(track=track, reviewer=user).exists()

    # User can review if: not their track and haven't reviewed yet
    can_review = track.uploader != user and not user_has_reviewed

    # Get existing reviews
    reviews = Review.objects.filter(track=track).select_related('reviewer').order_by('-created_at')

    context = {
        'track': track,
        'can_review': can_review,
        'user_has_reviewed': user_has_reviewed,
        'reviews': reviews,
    }

    return render(request, 'track_detail.html', context)


@login_required
def upload_track(request):
    """Track upload page."""
    user = request.user

    # Check if user can use cold start
    can_cold_start = can_use_cold_start(user)

    context = {
        'token_balance': user.token_balance,
        'can_cold_start': can_cold_start,
    }

    return render(request, 'upload_track.html', context)


@login_required
def my_tracks(request):
    """User's uploaded tracks."""
    user = request.user

    tracks = Track.objects.filter(
        uploader=user,
        is_deleted=False
    ).annotate(
        review_count=Count('reviews')
    ).order_by('-uploaded_at')

    context = {
        'tracks': tracks,
    }

    return render(request, 'my_tracks.html', context)


@login_required
def my_reviews(request):
    """User's submitted reviews."""
    user = request.user

    reviews = Review.objects.filter(
        reviewer=user
    ).select_related('track').order_by('-created_at')

    context = {
        'reviews': reviews,
    }

    return render(request, 'my_reviews.html', context)


@login_required
def track_reviews(request, track_id):
    """All reviews for a specific track."""
    track = get_object_or_404(Track, id=track_id)

    reviews = Review.objects.filter(
        track=track
    ).select_related('reviewer').order_by('-created_at')

    # Check if current user is track owner (can flag reviews)
    is_owner = track.uploader == request.user

    context = {
        'track': track,
        'reviews': reviews,
        'is_owner': is_owner,
    }

    return render(request, 'track_reviews.html', context)


@login_required
def user_profile(request, user_id):
    """Public user profile."""
    from core.models import User

    profile_user = get_object_or_404(User, id=user_id)

    # Get user's tracks
    tracks = Track.objects.filter(
        uploader=profile_user,
        is_deleted=False
    ).annotate(
        review_count=Count('reviews')
    ).order_by('-uploaded_at')[:10]

    # Get user's reviews
    reviews = Review.objects.filter(
        reviewer=profile_user
    ).select_related('track').order_by('-created_at')[:10]

    context = {
        'profile_user': profile_user,
        'tracks': tracks,
        'reviews': reviews,
    }

    return render(request, 'user_profile.html', context)


@login_required
def transaction_history(request):
    """User's transaction history."""
    user = request.user

    transactions = Transaction.objects.filter(
        user=user
    ).select_related('related_track', 'related_review').order_by('-created_at')

    context = {
        'transactions': transactions,
    }

    return render(request, 'transaction_history.html', context)
