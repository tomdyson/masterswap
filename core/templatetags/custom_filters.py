"""
Custom template filters for Masterswap.
"""

from django import template

register = template.Library()


@register.filter
def duration_minutes(seconds):
    """Convert seconds to M:SS format."""
    if not seconds:
        return "0:00"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


@register.filter
def file_size_mb(bytes_value):
    """Convert bytes to MB with 2 decimals."""
    if not bytes_value:
        return "0.00"
    return f"{bytes_value / 1024 / 1024:.2f}"
