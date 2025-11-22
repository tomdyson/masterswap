"""
API schemas for request/response validation using Pydantic.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from ninja import Schema, Field


# Authentication Schemas
class MagicLinkRequestSchema(Schema):
    email: str = Field(..., description="User email address")


class MagicLinkResponseSchema(Schema):
    message: str
    email: str


class LoginResponseSchema(Schema):
    message: str
    user_id: UUID
    email: str
    token_balance: int


# User Schemas
class UserProfileSchema(Schema):
    id: UUID
    email: str
    username: Optional[str] = None
    token_balance: int
    has_used_cold_start_upload: bool
    date_joined: datetime


class PublicUserProfileSchema(Schema):
    id: UUID
    email: str
    username: Optional[str] = None
    date_joined: datetime


# Track Schemas
class TrackUploadSchema(Schema):
    title: str = Field(..., max_length=200)
    feedback_request: Optional[str] = Field(None, max_length=1000)


class TrackListItemSchema(Schema):
    id: UUID
    title: str
    uploader_email: str
    duration: int
    review_count: int
    uploaded_at: datetime
    feedback_request: Optional[str] = None


class TrackDetailSchema(Schema):
    id: UUID
    title: str
    uploader_id: UUID
    uploader_email: str
    duration: int
    file_size: int
    feedback_request: Optional[str] = None
    uploaded_at: datetime
    review_count: int
    can_review: bool  # Whether current user can review this track
    user_has_reviewed: bool  # Whether current user has already reviewed


class TrackStreamSchema(Schema):
    url: str
    expires_in: int  # Seconds until URL expires


# Review Schemas
class ReviewCreateSchema(Schema):
    track_id: UUID
    equipment: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=200)
    listening_duration: int = Field(..., ge=0)  # Seconds listened


class ReviewSchema(Schema):
    id: UUID
    track_id: UUID
    track_title: str
    reviewer_id: UUID
    reviewer_email: str
    equipment: str
    content: str
    created_at: datetime
    is_flagged: bool


class ReviewListItemSchema(Schema):
    id: UUID
    track_id: UUID
    track_title: str
    reviewer_email: str
    equipment: str
    content_preview: str  # First 200 chars
    created_at: datetime


class FlagReviewSchema(Schema):
    reason: str = Field(..., min_length=10, max_length=1000)


# Transaction Schemas
class TransactionSchema(Schema):
    id: UUID
    amount: int
    transaction_type: str
    related_track_id: Optional[UUID] = None
    related_track_title: Optional[str] = None
    related_review_id: Optional[UUID] = None
    balance_after: int
    created_at: datetime


# Pagination Schemas
class PaginationSchema(Schema):
    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    total_pages: int
    current_page: int


class PaginatedTracksSchema(Schema):
    pagination: PaginationSchema
    results: List[TrackListItemSchema]


class PaginatedReviewsSchema(Schema):
    pagination: PaginationSchema
    results: List[ReviewListItemSchema]


class PaginatedTransactionsSchema(Schema):
    pagination: PaginationSchema
    results: List[TransactionSchema]


# Dashboard Schema
class DashboardStatsSchema(Schema):
    token_balance: int
    tracks_uploaded: int
    reviews_given: int
    reviews_received: int
    can_use_cold_start: bool
    reviewable_tracks_count: int


# Error Schemas
class ErrorSchema(Schema):
    detail: str


class ValidationErrorSchema(Schema):
    detail: str
    errors: Optional[dict] = None
