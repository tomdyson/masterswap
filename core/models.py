import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import MinLengthValidator, FileExtensionValidator
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model with token balance for the Masterswap platform."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    username = models.CharField(max_length=150, blank=True, null=True)
    token_balance = models.IntegerField(default=0)
    has_used_cold_start_upload = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'users'
        verbose_name = 'user'
        verbose_name_plural = 'users'

    def __str__(self):
        return self.email


class Track(models.Model):
    """Audio track uploaded for review."""

    ALLOWED_EXTENSIONS = ['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a']
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB in bytes
    MAX_DURATION = 600  # 10 minutes in seconds

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uploader = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tracks')
    title = models.CharField(max_length=200)
    file = models.FileField(
        upload_to='tracks/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=ALLOWED_EXTENSIONS)]
    )
    file_size = models.IntegerField()  # Size in bytes
    duration = models.IntegerField()  # Duration in seconds
    feedback_request = models.TextField(max_length=1000, blank=True, null=True)
    uploaded_at = models.DateTimeField(default=timezone.now, db_index=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'tracks'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['-uploaded_at']),
            models.Index(fields=['is_deleted']),
        ]

    def __str__(self):
        return f"{self.title} by {self.uploader.email}"

    def soft_delete(self):
        """Soft delete the track."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    @property
    def duration_minutes(self):
        """Return duration as M:SS string."""
        if not self.duration:
            return "0:00"
        minutes = int(self.duration // 60)
        secs = int(self.duration % 60)
        return f"{minutes}:{secs:02d}"

    @property
    def file_size_mb(self):
        """Return file size in MB."""
        if not self.file_size:
            return "0.00"
        return f"{self.file_size / 1024 / 1024:.2f}"

    @property
    def review_count(self):
        """Get count of reviews for this track."""
        return self.reviews.filter(is_flagged=False).count()


class Review(models.Model):
    """Review submitted for a track."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    equipment = models.CharField(max_length=500)
    content = models.TextField(validators=[MinLengthValidator(200)])
    listening_duration = models.IntegerField(default=0)  # Duration user listened in seconds
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    is_flagged = models.BooleanField(default=False)
    flagged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='flagged_reviews'
    )
    flagged_at = models.DateTimeField(null=True, blank=True)
    flag_reason = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'reviews'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['track', 'reviewer'],
                name='unique_track_reviewer'
            )
        ]
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['track', 'reviewer']),
        ]

    def __str__(self):
        return f"Review by {self.reviewer.email} on {self.track.title}"

    def flag(self, user, reason):
        """Flag this review for moderation."""
        self.is_flagged = True
        self.flagged_by = user
        self.flagged_at = timezone.now()
        self.flag_reason = reason
        self.save()


class Transaction(models.Model):
    """Token transaction history."""

    class TransactionType(models.TextChoices):
        REVIEW_EARNED = 'REVIEW_EARNED', 'Review Earned'
        UPLOAD_SPENT = 'UPLOAD_SPENT', 'Upload Spent'
        COLD_START_UPLOAD = 'COLD_START_UPLOAD', 'Cold Start Upload'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    amount = models.IntegerField()  # Positive for earning, negative for spending
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    related_review = models.ForeignKey(
        Review,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    related_track = models.ForeignKey(
        Track,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    balance_after = models.IntegerField()  # Snapshot of balance after transaction
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} tokens for {self.user.email}"
