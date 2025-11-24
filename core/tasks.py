"""
Celery tasks for background processing.
"""

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


@shared_task
def send_review_notification_email(track_id, review_id):
    """
    Send email notification to track uploader when their track receives a review.
    """
    from core.models import Track, Review

    try:
        track = Track.objects.select_related('uploader').get(id=track_id)
        review = Review.objects.select_related('reviewer').get(id=review_id)

        subject = f"Your track '{track.title}' received a review on Masterswap"

        # Prepare context for email template
        context = {
            'track_title': track.title,
            'reviewer_email': review.reviewer.email,
            'equipment': review.equipment,
            'review_snippet': review.content[:200] + '...' if len(review.content) > 200 else review.content,
            'track_url': f"{settings.SITE_URL}/tracks/{track.id}/reviews" if hasattr(settings, 'SITE_URL') else '',
            'uploader_token_balance': track.uploader.token_balance,
        }

        # For now, send plain text email
        # In production, use HTML templates
        message = f"""
Hello,

Your track "{track.title}" has received a new review!

Reviewer: {review.reviewer.email}
Equipment used: {review.equipment}

Review (first 200 characters):
{context['review_snippet']}

Your current token balance: {track.uploader.token_balance} tokens

Log in to Masterswap to view the full review and continue exchanging feedback!
        """

        send_mail(
            subject=subject,
            message=message.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[track.uploader.email],
            fail_silently=False,
        )

        return f"Review notification sent to {track.uploader.email}"

    except Exception as e:
        # Log error but don't fail the task
        print(f"Error sending review notification: {str(e)}")
        raise


@shared_task
def send_magic_link_email(user_email, magic_link):
    """
    Send magic link for passwordless authentication.
    """
    subject = "Your Masterswap login link"

    message = f"""
Hello,

Click the link below to log in to Masterswap:

{magic_link}

This link will expire in 15 minutes and can only be used once.

For security, do not share this link with anyone.

If you didn't request this link, you can safely ignore this email.
    """

    send_mail(
        subject=subject,
        message=message.strip(),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user_email],
        fail_silently=False,
    )

    return f"Magic link sent to {user_email}"
