"""
Reviews API endpoints.
"""

from ninja import Router
from django.shortcuts import get_object_or_404
from django.db import transaction
from typing import List
from core.models import Review, Track, Transaction
from core.api.schemas import (
    ReviewCreateSchema,
    ReviewSchema,
    ReviewListItemSchema,
    FlagReviewSchema,
    ErrorSchema
)
from core.utils import create_transaction
from core.tasks import send_review_notification_email
from ninja.security import django_auth

router = Router()


@router.get("/", response=List[ReviewListItemSchema], auth=django_auth)
def list_my_reviews(request, page: int = 1, page_size: int = 20):
    """
    List reviews submitted by the current user.
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
            reviewer_email=review.reviewer.email,
            equipment=review.equipment,
            content_preview=review.content[:200] + '...' if len(review.content) > 200 else review.content,
            created_at=review.created_at
        )
        for review in reviews_page
    ]


@router.post("/", response={201: ReviewSchema, 400: ErrorSchema, 403: ErrorSchema}, auth=django_auth)
@transaction.atomic
def create_review(request, payload: ReviewCreateSchema):
    """
    Submit a review for a track.
    Earns 1 token upon successful submission.
    """
    user = request.user

    # Get track
    track = get_object_or_404(Track, id=payload.track_id, is_deleted=False)

    # Validation: Can't review own track
    if track.uploader == user:
        return 403, {"detail": "You cannot review your own track"}

    # Validation: Can't review same track twice
    if Review.objects.filter(track=track, reviewer=user).exists():
        return 400, {"detail": "You have already reviewed this track"}

    # Validation: Equipment required
    if not payload.equipment or len(payload.equipment.strip()) == 0:
        return 400, {"detail": "Equipment description is required"}

    # Validation: Content minimum length (200 chars)
    if len(payload.content) < 200:
        return 400, {"detail": "Review must be at least 200 characters"}

    # Validation: Should have listened to most of the track
    # Allow some leeway (at least 80% or minimum 30 seconds)
    min_listening = min(track.duration * 0.8, track.duration - 10)
    if payload.listening_duration < min_listening:
        return 400, {"detail": "Please listen to the entire track before submitting a review"}

    # Create review
    review = Review.objects.create(
        track=track,
        reviewer=user,
        equipment=payload.equipment,
        content=payload.content,
        listening_duration=payload.listening_duration
    )

    # Award 1 token
    create_transaction(
        user=user,
        amount=1,
        transaction_type=Transaction.TransactionType.REVIEW_EARNED,
        related_review=review,
        related_track=track
    )

    # Send email notification to track uploader
    send_review_notification_email.delay(str(track.id), str(review.id))

    return 201, ReviewSchema(
        id=review.id,
        track_id=track.id,
        track_title=track.title,
        reviewer_id=user.id,
        reviewer_email=user.email,
        equipment=review.equipment,
        content=review.content,
        created_at=review.created_at,
        is_flagged=review.is_flagged
    )


@router.post("/{review_id}/flag", response={200: dict, 400: ErrorSchema, 403: ErrorSchema}, auth=django_auth)
def flag_review(request, review_id: str, payload: FlagReviewSchema):
    """
    Flag a review for moderation.
    Only track owners can flag reviews on their tracks.
    """
    user = request.user

    review = get_object_or_404(Review, id=review_id)

    # Check if user is the track owner
    if review.track.uploader != user:
        return 403, {"detail": "You can only flag reviews on your own tracks"}

    # Check if already flagged
    if review.is_flagged:
        return 400, {"detail": "This review is already flagged"}

    # Flag the review
    review.flag(user, payload.reason)

    return 200, {"message": "Review flagged for moderation"}


@router.get("/{review_id}", response={200: ReviewSchema, 404: ErrorSchema}, auth=django_auth)
def get_review(request, review_id: str):
    """
    Get a specific review.
    """
    review = get_object_or_404(
        Review.objects.select_related('track', 'reviewer'),
        id=review_id
    )

    return 200, ReviewSchema(
        id=review.id,
        track_id=review.track.id,
        track_title=review.track.title,
        reviewer_id=review.reviewer.id,
        reviewer_email=review.reviewer.email,
        equipment=review.equipment,
        content=review.content,
        created_at=review.created_at,
        is_flagged=review.is_flagged
    )
