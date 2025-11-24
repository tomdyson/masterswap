# ✅ Backend Updates COMPLETED

**Status**: All items completed on November 24, 2025

This document has been archived. All backend updates have been successfully implemented. See `BACKEND_INTEGRATION_COMPLETE.md` for full details of what was implemented.

## Quick Summary

All planned backend integration tasks have been completed:

- ✅ Model property methods added (duration_minutes, file_size_mb, review_count)
- ✅ Custom template filters created (duration_minutes, file_size_mb)
- ✅ Missing view functions added (logout_view, flag_review, delete_track)
- ✅ Missing URL patterns added
- ✅ Dashboard view updated with required context
- ✅ Browse tracks view updated with pagination and filtering
- ✅ Track detail view verified (already had required context)
- ✅ My tracks, my reviews, transaction history views updated with pagination
- ✅ User profile view updated with stats
- ✅ All authenticated views have @login_required decorators
- ✅ All system checks passing
- ✅ All URL patterns tested and working

## Original Document Preserved Below

---

# Backend Updates Needed for Frontend Integration

## Overview
The frontend templates are complete. This document outlines the backend updates needed to integrate them properly.

## 1. View Context Updates

Most Django views in `core/views.py` need to provide additional context variables that the templates expect.

### Dashboard View
```python
# Current: Needs to add context for recent_tracks, recent_transactions
def dashboard(request):
    # Add:
    - stats.can_use_cold_start
    - recent_tracks (last 3-5 tracks available to review)
    - recent_transactions (last 5 token transactions)
    - Calculate duration_minutes for tracks
```

### Browse Tracks View
```python
# Needs:
- track.duration_minutes (format seconds as "M:SS")
- track.review_count (count of reviews)
- track.uploader relationship
- Pagination support
- Sort and filter parameters (sort=newest/least_reviewed, unreviewed_only)
```

### Track Detail View
```python
# Needs:
- track.duration_minutes
- track.file_size_mb (file_size in MB format)
- reviews queryset with all reviews
- Check if user already reviewed (to prevent duplicate)
- Check if user owns track (to hide review form)
```

### My Tracks View
```python
# Needs:
- tracks with review_count annotation
- track.duration_minutes for each
- Pagination support
```

### My Reviews View
```python
# Needs:
- total_reviews count
- Pagination support
```

### User Profile View
```python
# Needs:
- user_stats dict with tracks_uploaded, reviews_given, reviews_received
- user_tracks queryset
- user_reviews queryset
```

### Transaction History View
```python
# Needs:
- total_earned (sum of positive amounts)
- total_spent (sum of negative amounts)
- net_change (total earned - total spent)
- reviews_count (count of REVIEW_EARNED transactions)
- uploads_count (count of UPLOAD_SPENT + COLD_START_UPLOAD)
- Pagination support
```

## 2. Missing URL Patterns

Add these URL patterns to `core/urls.py` or `masterswap/urls.py`:

```python
from django.urls import path
from core import views

urlpatterns = [
    # ... existing patterns ...

    # Missing patterns:
    path('logout/', views.logout_view, name='logout'),
    path('reviews/<uuid:review_id>/flag/', views.flag_review, name='flag_review'),
    path('tracks/<uuid:track_id>/delete/', views.delete_track, name='delete_track'),
]
```

## 3. Missing View Functions

Add these views to `core/views.py`:

### Logout View
```python
from django.contrib.auth import logout
from django.shortcuts import redirect

def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('landing')
    return redirect('dashboard')
```

### Flag Review View
```python
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404

def flag_review(request, review_id):
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
```

### Delete Track View
```python
def delete_track(request, track_id):
    if request.method == 'POST':
        track = get_object_or_404(Track, id=track_id, uploader=request.user)

        # Soft delete
        track.is_deleted = True
        track.deleted_at = timezone.now()
        track.save()

        messages.success(request, f"Track '{track.title}' has been deleted.")
        return redirect('my_tracks')

    return redirect('my_tracks')
```

## 4. Template Filters Needed

Add these custom template filters to `core/templatetags/custom_filters.py`:

```python
from django import template

register = template.Library()

@register.filter
def duration_minutes(seconds):
    """Convert seconds to M:SS format"""
    if not seconds:
        return "0:00"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"

@register.filter
def file_size_mb(bytes):
    """Convert bytes to MB with 2 decimals"""
    if not bytes:
        return "0.00"
    return f"{bytes / 1024 / 1024:.2f}"
```

Then in templates, load the filters:
```django
{% load custom_filters %}
{{ track.duration|duration_minutes }}
{{ track.file_size|file_size_mb }}
```

## 5. Model Property Methods

Add these methods to models in `core/models.py`:

### Track Model
```python
class Track(models.Model):
    # ... existing fields ...

    @property
    def duration_minutes(self):
        """Return duration as M:SS string"""
        if not self.duration:
            return "0:00"
        minutes = int(self.duration // 60)
        secs = int(self.duration % 60)
        return f"{minutes}:{secs:02d}"

    @property
    def file_size_mb(self):
        """Return file size in MB"""
        if not self.file_size:
            return "0.00"
        return f"{self.file_size / 1024 / 1024:.2f}"

    @property
    def review_count(self):
        """Get count of reviews for this track"""
        return self.review_set.filter(track__is_deleted=False).count()
```

## 6. View Decorators

Ensure all authenticated views use `@login_required`:

```python
from django.contrib.auth.decorators import login_required

@login_required
def dashboard(request):
    # ...

@login_required
def browse_tracks(request):
    # ...

# etc.
```

## 7. Settings Updates

### Add Template Tag Library
In `masterswap/settings.py`:

```python
INSTALLED_APPS = [
    # ... existing apps ...
    'core',
]

# If using custom template filters, create:
# core/templatetags/__init__.py
# core/templatetags/custom_filters.py
```

### Static Files Configuration
```python
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
```

### Template Settings
```python
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
```

## 8. Messages Framework

Ensure Django messages framework is set up in `settings.py`:

```python
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'error',
}
```

## 9. Pagination Helper

Add pagination logic to list views:

```python
from django.core.paginator import Paginator

def browse_tracks(request):
    tracks = Track.objects.filter(is_deleted=False).order_by('-uploaded_at')

    # Pagination
    paginator = Paginator(tracks, 20)  # 20 tracks per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'tracks': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
    }
    return render(request, 'browse_tracks.html', context)
```

## 10. Cold Start Logic in Views

Add cold start check to upload view:

```python
from core.utils import can_use_cold_start

def upload_track(request):
    is_cold_start = can_use_cold_start(request.user)

    context = {
        'is_cold_start': is_cold_start,
    }
    return render(request, 'upload_track.html', context)
```

## 11. URL Name Updates

Ensure all URL patterns have names matching the templates:

```python
urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('login/', views.login_page, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('tracks/', views.browse_tracks, name='browse_tracks'),
    path('tracks/<uuid:track_id>/', views.track_detail, name='track_detail'),
    path('tracks/<uuid:track_id>/reviews/', views.track_reviews, name='track_reviews'),
    path('tracks/<uuid:track_id>/delete/', views.delete_track, name='delete_track'),
    path('upload/', views.upload_track, name='upload_track'),
    path('my-tracks/', views.my_tracks, name='my_tracks'),
    path('my-reviews/', views.my_reviews, name='my_reviews'),
    path('reviews/<uuid:review_id>/flag/', views.flag_review, name='flag_review'),
    path('transactions/', views.transaction_history, name='transaction_history'),
    path('users/<uuid:user_id>/', views.user_profile, name='user_profile'),
]
```

## Testing Checklist

After making these updates, test:

- [x] All pages load without template errors
- [x] Navigation links work correctly
- [x] Forms submit successfully
- [x] File uploads work
- [x] Audio player loads and plays
- [x] Review submission works
- [x] Token balance updates correctly
- [x] Pagination works on list views
- [x] Error messages display properly
- [x] Success messages display
- [x] User authentication flow works
- [x] Magic link login works
- [x] Logout functionality works
- [x] Mobile responsive design works

## Priority Order

1. **High Priority** (Breaks functionality):
   - ✅ Add missing URL patterns (logout, flag_review, delete_track)
   - ✅ Add model properties (duration_minutes, file_size_mb, review_count)
   - ✅ Update view context for all pages

2. **Medium Priority** (Improves UX):
   - ✅ Add pagination to list views
   - ✅ Add template filters
   - ✅ Implement sort and filter logic

3. **Low Priority** (Nice to have):
   - ⏳ Optimize queries with select_related/prefetch_related
   - ⏳ Add caching for expensive queries
   - ⏳ Add more comprehensive error handling

---

**Note**: Most of these updates are straightforward and can be completed in 1-2 hours. The backend API is already complete, so this is primarily about connecting the views to the templates with the right context data.
