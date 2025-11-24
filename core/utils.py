"""
Utility functions for Masterswap core functionality.
"""

from django.db import transaction
from mutagen import File as MutagenFile
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.wave import WAVE
from mutagen.mp4 import MP4
import magic


def get_audio_duration(file_path):
    """
    Extract audio duration from file using mutagen.

    Args:
        file_path: Path to the audio file

    Returns:
        int: Duration in seconds

    Raises:
        ValueError: If file cannot be read or is not a valid audio file
    """
    try:
        audio = MutagenFile(file_path)
        if audio is None:
            raise ValueError("Could not read audio file")

        if not hasattr(audio.info, 'length'):
            raise ValueError("Audio file does not have duration information")

        return int(audio.info.length)
    except Exception as e:
        raise ValueError(f"Error reading audio file: {str(e)}")


def validate_audio_file(file_obj):
    """
    Validate audio file type, size, and duration.

    Args:
        file_obj: Django UploadedFile object

    Returns:
        dict: {'valid': bool, 'errors': list, 'duration': int or None}
    """
    from core.models import Track

    errors = []
    duration = None

    # Check file size
    if file_obj.size > Track.MAX_FILE_SIZE:
        errors.append(f"File size exceeds maximum of {Track.MAX_FILE_SIZE // (1024 * 1024)}MB")

    # Check file extension
    file_extension = file_obj.name.split('.')[-1].lower()
    if file_extension not in Track.ALLOWED_EXTENSIONS:
        errors.append(f"File type .{file_extension} not allowed. Allowed types: {', '.join(Track.ALLOWED_EXTENSIONS)}")

    # Validate MIME type using python-magic
    try:
        file_obj.seek(0)
        mime = magic.Magic(mime=True)
        file_type = mime.from_buffer(file_obj.read(2048))
        file_obj.seek(0)

        allowed_mime_types = [
            'audio/mpeg',  # MP3
            'audio/flac',  # FLAC
            'audio/ogg',   # OGG
            'audio/wav',   # WAV
            'audio/wave',  # WAV alternative
            'audio/x-wav', # WAV alternative
            'audio/mp4',   # AAC/M4A
            'audio/x-m4a', # M4A alternative
        ]

        if file_type not in allowed_mime_types:
            errors.append(f"Invalid file type detected: {file_type}")
    except Exception as e:
        errors.append(f"Error validating file type: {str(e)}")

    # If basic validation passed, try to get duration
    if not errors:
        try:
            # Save file temporarily to read with mutagen
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as tmp_file:
                file_obj.seek(0)
                tmp_file.write(file_obj.read())
                tmp_file_path = tmp_file.name

            try:
                duration = get_audio_duration(tmp_file_path)

                # Check duration
                if duration > Track.MAX_DURATION:
                    errors.append(f"Audio duration exceeds maximum of {Track.MAX_DURATION // 60} minutes")

            finally:
                # Clean up temp file
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
                file_obj.seek(0)

        except ValueError as e:
            errors.append(str(e))
        except Exception as e:
            errors.append(f"Error processing audio file: {str(e)}")

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'duration': duration
    }


def can_use_cold_start(user):
    """
    Check if user can use the cold start mechanism to upload for free.

    Args:
        user: User instance

    Returns:
        bool: True if user can use cold start
    """
    from core.models import Track

    # Check if user has already used cold start
    if user.has_used_cold_start_upload:
        return False

    # Count tracks available for review (excluding user's own tracks and deleted tracks)
    available_tracks = Track.objects.filter(
        is_deleted=False
    ).exclude(
        uploader=user
    ).count()

    # Cold start available if fewer than 3 tracks
    return available_tracks < 3


@transaction.atomic
def create_transaction(user, amount, transaction_type, related_review=None, related_track=None):
    """
    Create a token transaction and update user balance.

    Args:
        user: User instance
        amount: Integer amount (positive for earning, negative for spending)
        transaction_type: Transaction type from Transaction.TransactionType
        related_review: Optional Review instance
        related_track: Optional Track instance

    Returns:
        Transaction instance
    """
    from core.models import Transaction

    # Update user balance
    user.token_balance += amount
    user.save(update_fields=['token_balance'])

    # Create transaction record
    transaction_obj = Transaction.objects.create(
        user=user,
        amount=amount,
        transaction_type=transaction_type,
        related_review=related_review,
        related_track=related_track,
        balance_after=user.token_balance
    )

    return transaction_obj


def count_reviewable_tracks(user):
    """
    Count how many tracks are available for a user to review.

    Args:
        user: User instance

    Returns:
        int: Number of reviewable tracks
    """
    from core.models import Track

    return Track.objects.filter(
        is_deleted=False
    ).exclude(
        uploader=user
    ).exclude(
        reviews__reviewer=user
    ).count()


def get_presigned_url(file_path, expiration=3600):
    """
    Generate a presigned URL for accessing a file in R2 storage.

    Args:
        file_path: Path to the file in storage
        expiration: URL expiration time in seconds (default 1 hour)

    Returns:
        str: Presigned URL
    """
    from django.conf import settings
    from django.core.files.storage import default_storage

    if settings.USE_R2_STORAGE:
        # Generate presigned URL for R2
        return default_storage.url(file_path)
    else:
        # For local storage, return regular URL
        return default_storage.url(file_path)
