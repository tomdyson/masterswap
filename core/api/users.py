"""
User API endpoints.
"""

from ninja import Router
from django.shortcuts import get_object_or_404
from django.db.models import Count
from typing import List
from core.models import User, Track, Review, Transaction
from core.api.schemas import (
    UserProfileSchema,
    PublicUserProfileSchema,
    TransactionSchema,
    DashboardStatsSchema,
    TrackListItemSchema,
    ReviewListItemSchema,
    ErrorSchema
)
from core.utils import can_use_cold_start, count_reviewable_tracks
from ninja.security import django_auth

router = Router()


@router.get("/me", response=UserProfileSchema, auth=django_auth)
def get_current_user(request):
    """
    Get current user profile information.
    """
    user = request.user

    return UserProfileSchema(
        id=user.id,
        email=user.email,
        username=user.username,
        token_balance=user.token_balance,
        has_used_cold_start_upload=user.has_used_cold_start_upload,
        date_joined=user.date_joined
    )


@router.get("/me/dashboard", response=DashboardStatsSchema, auth=django_auth)
def get_dashboard_stats(request):
    """
    Get dashboard statistics for current user.
    """
    user = request.user

    # Count user's uploads
    tracks_uploaded = Track.objects.filter(uploader=user, is_deleted=False).count()

    # Count reviews given
    reviews_given = Review.objects.filter(reviewer=user).count()

    # Count reviews received on user's tracks
    reviews_received = Review.objects.filter(track__uploader=user, track__is_deleted=False).count()

    # Check if can use cold start
    can_cold_start = can_use_cold_start(user)

    # Count reviewable tracks
    reviewable_count = count_reviewable_tracks(user)

    return DashboardStatsSchema(
        token_balance=user.token_balance,
        tracks_uploaded=tracks_uploaded,
        reviews_given=reviews_given,
        reviews_received=reviews_received,
        can_use_cold_start=can_cold_start,
        reviewable_tracks_count=reviewable_count
    )


@router.get("/me/tracks", response=List[TrackListItemSchema], auth=django_auth)
def get_my_tracks(request, page: int = 1, page_size: int = 20):
    """
    Get tracks uploaded by current user.
    """
    user = request.user

    tracks = Track.objects.filter(
        uploader=user,
        is_deleted=False
    ).annotate(
        review_count=Count('reviews')
    ).order_by('-uploaded_at')

    # Pagination
    start = (page - 1) * page_size
    end = start + page_size
    tracks_page = tracks[start:end]

    return [
        TrackListItemSchema(
            id=track.id,
            title=track.title,
            uploader_email=user.email,
            duration=track.duration,
            review_count=track.review_count,
            uploaded_at=track.uploaded_at,
            feedback_request=track.feedback_request
        )
        for track in tracks_page
    ]


@router.get("/me/reviews", response=List[ReviewListItemSchema], auth=django_auth)
def get_my_reviews(request, page: int = 1, page_size: int = 20):
    """
    Get reviews submitted by current user.
    """
    user = request.user

    reviews = Review.objects.filter(
        reviewer=user
    ).select_related('track').order_by('-created_at')

    # Pagination
    start = (page - 1) * page_size
    end = start + page_size
    reviews_page = reviews[start:end]

    return [
        ReviewListItemSchema(
            id=review.id,
            track_id=review.track.id,
            track_title=review.track.title,
            reviewer_email=user.email,
            equipment=review.equipment,
            content_preview=review.content[:200] + '...' if len(review.content) > 200 else review.content,
            created_at=review.created_at
        )
        for review in reviews_page
    ]


@router.get("/me/transactions", response=List[TransactionSchema], auth=django_auth)
def get_my_transactions(request, page: int = 1, page_size: int = 20):
    """
    Get transaction history for current user.
    """
    user = request.user

    transactions = Transaction.objects.filter(
        user=user
    ).select_related(
        'related_track',
        'related_review'
    ).order_by('-created_at')

    # Pagination
    start = (page - 1) * page_size
    end = start + page_size
    transactions_page = transactions[start:end]

    return [
        TransactionSchema(
            id=txn.id,
            amount=txn.amount,
            transaction_type=txn.transaction_type,
            related_track_id=txn.related_track.id if txn.related_track else None,
            related_track_title=txn.related_track.title if txn.related_track else None,
            related_review_id=txn.related_review.id if txn.related_review else None,
            balance_after=txn.balance_after,
            created_at=txn.created_at
        )
        for txn in transactions_page
    ]


@router.get("/{user_id}/profile", response={200: PublicUserProfileSchema, 404: ErrorSchema}, auth=django_auth)
def get_user_profile(request, user_id: str):
    """
    Get public profile of a user.
    """
    user = get_object_or_404(User, id=user_id)

    return 200, PublicUserProfileSchema(
        id=user.id,
        email=user.email,
        username=user.username,
        date_joined=user.date_joined
    )


@router.get("/{user_id}/tracks", response=List[TrackListItemSchema], auth=django_auth)
def get_user_tracks(request, user_id: str, page: int = 1, page_size: int = 20):
    """
    Get tracks uploaded by a specific user.
    """
    user = get_object_or_404(User, id=user_id)

    tracks = Track.objects.filter(
        uploader=user,
        is_deleted=False
    ).annotate(
        review_count=Count('reviews')
    ).order_by('-uploaded_at')

    # Pagination
    start = (page - 1) * page_size
    end = start + page_size
    tracks_page = tracks[start:end]

    return [
        TrackListItemSchema(
            id=track.id,
            title=track.title,
            uploader_email=user.email,
            duration=track.duration,
            review_count=track.review_count,
            uploaded_at=track.uploaded_at,
            feedback_request=track.feedback_request
        )
        for track in tracks_page
    ]


@router.get("/{user_id}/reviews", response=List[ReviewListItemSchema], auth=django_auth)
def get_user_reviews(request, user_id: str, page: int = 1, page_size: int = 20):
    """
    Get reviews submitted by a specific user.
    """
    user = get_object_or_404(User, id=user_id)

    reviews = Review.objects.filter(
        reviewer=user
    ).select_related('track').order_by('-created_at')

    # Pagination
    start = (page - 1) * page_size
    end = start + page_size
    reviews_page = reviews[start:end]

    return [
        ReviewListItemSchema(
            id=review.id,
            track_id=review.track.id,
            track_title=review.track.title,
            reviewer_email=user.email,
            equipment=review.equipment,
            content_preview=review.content[:200] + '...' if len(review.content) > 200 else review.content,
            created_at=review.created_at
        )
        for review in reviews_page
    ]
