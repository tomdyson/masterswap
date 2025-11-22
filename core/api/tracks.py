"""
Tracks API endpoints.
"""

from ninja import Router, File
from ninja.files import UploadedFile
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q, Exists, OuterRef
from django.http import HttpRequest
from typing import List
from core.models import Track, Review, Transaction
from core.api.schemas import (
    TrackUploadSchema,
    TrackListItemSchema,
    TrackDetailSchema,
    TrackStreamSchema,
    PaginatedTracksSchema,
    PaginationSchema,
    ErrorSchema
)
from core.utils import (
    validate_audio_file,
    can_use_cold_start,
    create_transaction,
    get_presigned_url
)
from ninja.security import django_auth

router = Router()


@router.get("/", response=List[TrackListItemSchema], auth=django_auth)
def list_tracks(
    request,
    page: int = 1,
    page_size: int = 20,
    sort: str = "newest"
):
    """
    List tracks available for review.
    Excludes user's own tracks and tracks they've already reviewed.
    """
    user = request.user

    # Subquery to check if user has reviewed a track
    user_reviewed = Review.objects.filter(
        track=OuterRef('pk'),
        reviewer=user
    )

    # Base queryset: exclude user's own tracks, deleted tracks, and already reviewed
    tracks = Track.objects.filter(
        is_deleted=False
    ).exclude(
        uploader=user
    ).exclude(
        Exists(user_reviewed)
    ).annotate(
        review_count=Count('reviews')
    ).select_related('uploader')

    # Sort
    if sort == "least_reviewed":
        tracks = tracks.order_by('review_count', '-uploaded_at')
    else:  # newest (default)
        tracks = tracks.order_by('-uploaded_at')

    # Pagination
    start = (page - 1) * page_size
    end = start + page_size
    tracks_page = tracks[start:end]

    # Format response
    return [
        TrackListItemSchema(
            id=track.id,
            title=track.title,
            uploader_email=track.uploader.email,
            duration=track.duration,
            review_count=track.review_count,
            uploaded_at=track.uploaded_at,
            feedback_request=track.feedback_request
        )
        for track in tracks_page
    ]


@router.get("/{track_id}", response={200: TrackDetailSchema, 404: ErrorSchema}, auth=django_auth)
def get_track(request, track_id: str):
    """
    Get track details.
    """
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

    return 200, TrackDetailSchema(
        id=track.id,
        title=track.title,
        uploader_id=track.uploader.id,
        uploader_email=track.uploader.email,
        duration=track.duration,
        file_size=track.file_size,
        feedback_request=track.feedback_request,
        uploaded_at=track.uploaded_at,
        review_count=track.review_count,
        can_review=can_review,
        user_has_reviewed=user_has_reviewed
    )


@router.post("/", response={201: TrackDetailSchema, 400: ErrorSchema, 403: ErrorSchema}, auth=django_auth)
def upload_track(
    request,
    file: UploadedFile = File(...),
    title: str = None,
    feedback_request: str = None
):
    """
    Upload a new track.
    Costs 1 token unless user qualifies for cold start.
    """
    user = request.user

    # Validate title
    if not title or len(title) > 200:
        return 400, {"detail": "Title is required and must be max 200 characters"}

    # Check if user can use cold start
    using_cold_start = can_use_cold_start(user)

    # Check token balance if not using cold start
    if not using_cold_start and user.token_balance < 1:
        return 403, {"detail": "Insufficient tokens. You need 1 token to upload a track. Review tracks to earn tokens!"}

    # Validate audio file
    validation = validate_audio_file(file)
    if not validation['valid']:
        return 400, {"detail": "; ".join(validation['errors'])}

    # Create track
    track = Track(
        uploader=user,
        title=title,
        file=file,
        file_size=file.size,
        duration=validation['duration'],
        feedback_request=feedback_request
    )
    track.save()

    # Handle token transaction
    if using_cold_start:
        # Mark user as having used cold start
        user.has_used_cold_start_upload = True
        user.save(update_fields=['has_used_cold_start_upload'])

        # Create cold start transaction (no cost)
        create_transaction(
            user=user,
            amount=0,
            transaction_type=Transaction.TransactionType.COLD_START_UPLOAD,
            related_track=track
        )
    else:
        # Deduct 1 token
        create_transaction(
            user=user,
            amount=-1,
            transaction_type=Transaction.TransactionType.UPLOAD_SPENT,
            related_track=track
        )

    return 201, TrackDetailSchema(
        id=track.id,
        title=track.title,
        uploader_id=user.id,
        uploader_email=user.email,
        duration=track.duration,
        file_size=track.file_size,
        feedback_request=track.feedback_request,
        uploaded_at=track.uploaded_at,
        review_count=0,
        can_review=False,
        user_has_reviewed=False
    )


@router.delete("/{track_id}", response={200: dict, 403: ErrorSchema, 404: ErrorSchema}, auth=django_auth)
def delete_track(request, track_id: str):
    """
    Delete a track (soft delete).
    Only track owner can delete.
    """
    user = request.user

    track = get_object_or_404(Track, id=track_id, is_deleted=False)

    # Check ownership
    if track.uploader != user:
        return 403, {"detail": "You can only delete your own tracks"}

    # Soft delete
    track.soft_delete()

    return 200, {"message": "Track deleted successfully"}


@router.get("/{track_id}/stream", response={200: TrackStreamSchema, 404: ErrorSchema}, auth=django_auth)
def stream_track(request, track_id: str):
    """
    Get presigned URL for streaming a track.
    """
    track = get_object_or_404(Track, id=track_id, is_deleted=False)

    # Generate presigned URL
    url = get_presigned_url(track.file.name)

    return 200, TrackStreamSchema(
        url=url,
        expires_in=3600  # 1 hour
    )


@router.get("/{track_id}/reviews", response=List[dict], auth=django_auth)
def get_track_reviews(request, track_id: str):
    """
    Get all reviews for a track.
    """
    track = get_object_or_404(Track, id=track_id, is_deleted=False)

    reviews = Review.objects.filter(track=track).select_related('reviewer').order_by('-created_at')

    return [
        {
            "id": str(review.id),
            "reviewer_email": review.reviewer.email,
            "equipment": review.equipment,
            "content": review.content,
            "created_at": review.created_at.isoformat(),
            "is_flagged": review.is_flagged
        }
        for review in reviews
    ]
