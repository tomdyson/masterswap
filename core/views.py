"""
Views for Masterswap frontend pages.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from django.db.models import Count
from django.utils import timezone
from django.core.paginator import Paginator
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

    # Recent tracks available to review
    recent_tracks = Track.objects.filter(
        is_deleted=False
    ).exclude(
        uploader=user
    ).exclude(
        reviews__reviewer=user
    ).annotate(
        review_count=Count('reviews')
    ).select_related('uploader').order_by('-uploaded_at')[:5]

    # Create stats object with can_use_cold_start
    stats = {
        'tracks_uploaded': tracks_uploaded,
        'reviews_given': reviews_given,
        'reviews_received': reviews_received,
        'can_use_cold_start': can_cold_start,
        'reviewable_count': reviewable_count,
    }

    context = {
        'user': user,
        'token_balance': user.token_balance,
        'stats': stats,
        'tracks_uploaded': tracks_uploaded,
        'reviews_given': reviews_given,
        'reviews_received': reviews_received,
        'can_cold_start': can_cold_start,
        'reviewable_count': reviewable_count,
        'recent_transactions': recent_transactions,
        'recent_tracks': recent_tracks,
    }

    return render(request, 'dashboard.html', context)


@login_required
def browse_tracks(request):
    """Browse tracks available for review."""
    user = request.user

    # Get sorting and filter parameters
    sort = request.GET.get('sort', 'newest')
    unreviewed_only = request.GET.get('unreviewed_only', False)

    # Base queryset (exclude user's own and already reviewed)
    tracks = Track.objects.filter(
        is_deleted=False
    ).exclude(
        uploader=user
    ).exclude(
        reviews__reviewer=user
    ).annotate(
        review_count=Count('reviews')
    ).select_related('uploader')

    # Apply sorting
    if sort == 'least_reviewed':
        tracks = tracks.order_by('review_count', '-uploaded_at')
    else:  # newest (default)
        tracks = tracks.order_by('-uploaded_at')

    # Apply filter for unreviewed only
    if unreviewed_only:
        tracks = tracks.filter(review_count=0)

    # Pagination
    paginator = Paginator(tracks, 20)  # 20 tracks per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'tracks': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'sort': sort,
        'unreviewed_only': unreviewed_only,
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

    # Pagination
    paginator = Paginator(tracks, 20)  # 20 tracks per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'tracks': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
    }

    return render(request, 'my_tracks.html', context)


@login_required
def my_reviews(request):
    """User's submitted reviews."""
    user = request.user

    reviews = Review.objects.filter(
        reviewer=user
    ).select_related('track').order_by('-created_at')

    # Get total count
    total_reviews = reviews.count()

    # Pagination
    paginator = Paginator(reviews, 20)  # 20 reviews per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'reviews': page_obj,
        'total_reviews': total_reviews,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
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
    user_tracks = Track.objects.filter(
        uploader=profile_user,
        is_deleted=False
    ).annotate(
        review_count=Count('reviews')
    ).order_by('-uploaded_at')[:10]

    # Get user's reviews
    user_reviews = Review.objects.filter(
        reviewer=profile_user
    ).select_related('track').order_by('-created_at')[:10]

    # Calculate user stats
    tracks_uploaded = Track.objects.filter(
        uploader=profile_user,
        is_deleted=False
    ).count()

    reviews_given = Review.objects.filter(
        reviewer=profile_user
    ).count()

    reviews_received = Review.objects.filter(
        track__uploader=profile_user,
        track__is_deleted=False
    ).count()

    user_stats = {
        'tracks_uploaded': tracks_uploaded,
        'reviews_given': reviews_given,
        'reviews_received': reviews_received,
    }

    context = {
        'profile_user': profile_user,
        'user_tracks': user_tracks,
        'user_reviews': user_reviews,
        'user_stats': user_stats,
    }

    return render(request, 'user_profile.html', context)


@login_required
def transaction_history(request):
    """User's transaction history."""
    user = request.user

    transactions = Transaction.objects.filter(
        user=user
    ).select_related('related_track', 'related_review').order_by('-created_at')

    # Calculate summary stats
    from django.db.models import Sum, Q
    earned_sum = transactions.filter(amount__gt=0).aggregate(Sum('amount'))['amount__sum'] or 0
    spent_sum = abs(transactions.filter(amount__lt=0).aggregate(Sum('amount'))['amount__sum'] or 0)
    net_change = earned_sum - spent_sum

    reviews_count = transactions.filter(
        transaction_type=Transaction.TransactionType.REVIEW_EARNED
    ).count()

    uploads_count = transactions.filter(
        Q(transaction_type=Transaction.TransactionType.UPLOAD_SPENT) |
        Q(transaction_type=Transaction.TransactionType.COLD_START_UPLOAD)
    ).count()

    # Pagination
    paginator = Paginator(transactions, 50)  # 50 transactions per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'transactions': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'total_earned': earned_sum,
        'total_spent': spent_sum,
        'net_change': net_change,
        'reviews_count': reviews_count,
        'uploads_count': uploads_count,
    }

    return render(request, 'transaction_history.html', context)


def logout_view(request):
    """Logout the user."""
    if request.method == 'POST':
        logout(request)
        messages.success(request, "You've been successfully logged out.")
        return redirect('landing')
    return redirect('dashboard')


@login_required
def flag_review(request, review_id):
    """Flag a review for moderation."""
    if request.method == 'POST':
        review = get_object_or_404(Review, id=review_id)

        # Only track owner can flag
        if request.user != review.track.uploader:
            messages.error(request, "You can only flag reviews on your own tracks.")
            return redirect('track_detail', track_id=review.track.id)

        review.is_flagged = True
        review.flagged_by = request.user
        review.flagged_at = timezone.now()
        review.save()

        messages.success(request, "Review has been flagged for moderation.")
        return redirect('track_reviews', track_id=review.track.id)

    return redirect('dashboard')


@login_required
def delete_track(request, track_id):
    """Delete a track (soft delete)."""
    if request.method == 'POST':
        track = get_object_or_404(Track, id=track_id, uploader=request.user)

        # Soft delete
        track.is_deleted = True
        track.deleted_at = timezone.now()
        track.save()

        messages.success(request, f"Track '{track.title}' has been deleted.")
        return redirect('my_tracks')

    return redirect('my_tracks')
