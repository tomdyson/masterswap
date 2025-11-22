# Masterswap - Product Specification

## Overview

Masterswap is a web application for audio engineers to exchange mix feedback. Users earn tokens by reviewing others’ mixes and spend tokens to upload their own tracks for review. This creates a balanced community where everyone contributes.

## Core Concept

- **Earn tokens**: Listen to tracks on your equipment and write thoughtful reviews (1 token per review)
- **Spend tokens**: Upload your own tracks to receive feedback from the community (1 token per upload)
- **Starting balance**: 0 tokens (users must review before they can upload)
- **Cold start exception**: When there are fewer than 3 tracks available to review, new users can upload one track even with 0 tokens to seed the platform

## User Stories

### As a new user:

- I can sign up using magic link authentication
- I start with 0 tokens, encouraging me to review first
- If there are fewer than 3 tracks available to review, I can upload one track for free to help seed the platform
- I can browse available tracks to review
- I can see how the platform works

### As a reviewer:

- I can browse tracks that need reviews (sorted newest first, prioritizing unreviewed tracks)
- I can play a full track before submitting a review
- I must listen to the entire track before the review form unlocks
- I must specify the equipment I’m listening on (free-form text)
- I must write at least 200 characters of feedback
- I can optionally address specific feedback requests from the uploader
- I earn 1 token upon successful review submission
- I cannot review my own tracks
- I cannot review the same track multiple times

### As an uploader:

- I can spend 1 token to upload a track for review
- I can specify what kind of feedback I’m looking for (optional)
- I receive email notifications when my track is reviewed
- I can view all reviews on my track
- I can delete my uploads (reviews are lost but tokens aren’t refunded to reviewers)
- I can flag unhelpful reviews for moderation

### As any user:

- I can view my current token balance
- I can see my upload history
- I can see my review history
- I can view other users’ uploads and reviews (basic profile view)

## Technical Specifications

### Technology Stack

**Backend:**

- Django with Django Ninja (REST API)
- Python 3.11+
- PostgreSQL database
- Celery for background tasks (email notifications)
- Redis for Celery broker

**Frontend:**

- Django templates (initial implementation)
- Tailwind CSS for styling
- Vanilla JavaScript or Alpine.js for interactivity
- Architecture should support future migration to standalone React frontend

**Authentication:**

- django-sesame for magic link authentication
- Email-based passwordless login

**Storage:**

- Cloudflare R2 for audio file storage
- django-storages for S3-compatible storage interface

**Deployment:**

- Docker containerization
- Deployed on fly.io
- Docker Compose for local development

**Email:**

- Django email backend (configure for production email service)

### Audio File Requirements

- **Supported formats**: MP3, WAV, FLAC, AAC, OGG
- **Maximum file size**: 20MB
- **Maximum length**: 10 minutes
- Server-side validation for file type and size
- Audio duration validation using appropriate library (e.g., mutagen, pydub)

## Data Models

### User

```python
- id (UUID, primary key)
- email (unique, indexed)
- username (unique, optional for now)
- token_balance (integer, default=0)
- has_used_cold_start_upload (boolean, default=False)
- date_joined (datetime)
- is_active (boolean)
- is_staff (boolean)
```

### Track

```python
- id (UUID, primary key)
- uploader (ForeignKey to User)
- title (string, max 200 chars)
- file_url (string, R2 storage path)
- file_size (integer, bytes)
- duration (integer, seconds)
- feedback_request (text, optional, max 1000 chars)
- uploaded_at (datetime, indexed)
- is_deleted (boolean, soft delete)
- deleted_at (datetime, nullable)
```

### Review

```python
- id (UUID, primary key)
- track (ForeignKey to Track)
- reviewer (ForeignKey to User)
- equipment (string, max 500 chars)
- content (text, minimum 200 chars)
- created_at (datetime)
- is_flagged (boolean)
- flagged_by (ForeignKey to User, nullable)
- flagged_at (datetime, nullable)
- flag_reason (text, nullable)
- listening_duration (integer, seconds, tracked client-side)
```

**Constraints:**

- Unique together: (track, reviewer) - one review per user per track
- Index on track.uploaded_at for efficient querying
- Index on review.created_at

### Transaction (Token History)

```python
- id (UUID, primary key)
- user (ForeignKey to User)
- amount (integer, can be positive or negative)
- transaction_type (enum: REVIEW_EARNED, UPLOAD_SPENT, COLD_START_UPLOAD)
- related_review (ForeignKey to Review, nullable)
- related_track (ForeignKey to Track, nullable)
- created_at (datetime)
- balance_after (integer, snapshot)
```

## API Endpoints (Django Ninja)

### Authentication

- `POST /api/auth/request-magic-link` - Request magic link via email
- `GET /api/auth/verify/{token}` - Verify magic link and log in
- `POST /api/auth/logout` - Log out current user

### Tracks

- `GET /api/tracks/` - List tracks available for review (paginated)
  - Query params: `?sort=newest|least_reviewed`
  - Excludes user’s own tracks
  - Excludes tracks user has already reviewed
- `GET /api/tracks/{id}` - Get track details
- `POST /api/tracks/` - Upload new track (costs 1 token)
- `DELETE /api/tracks/{id}` - Delete own track
- `GET /api/tracks/{id}/reviews` - Get all reviews for a track

### Reviews

- `GET /api/reviews/` - List user’s own reviews
- `POST /api/reviews/` - Submit a review (earns 1 token)
- `POST /api/reviews/{id}/flag` - Flag a review for moderation

### User

- `GET /api/user/me` - Get current user info and token balance
- `GET /api/user/me/tracks` - Get user’s uploaded tracks
- `GET /api/user/me/reviews` - Get user’s submitted reviews
- `GET /api/user/me/transactions` - Get token transaction history
- `GET /api/user/{id}/profile` - Get public profile (tracks and reviews)

### Audio Playback

- `GET /api/tracks/{id}/stream` - Presigned URL for audio streaming
- Track playback progress on client-side to enforce full listen

## Frontend Pages (Django Templates)

### Public Pages

1. **Landing Page** (`/`)
- Explanation of how Masterswap works
- Sign up / login CTA
1. **Login Page** (`/login`)
- Email input for magic link
- Success message after email sent

### Authenticated Pages

1. **Dashboard** (`/dashboard`)
- Current token balance (prominent display)
- Quick stats: tracks uploaded, reviews given
- Recent activity feed
- CTAs: “Review a Track” and “Upload Track”
1. **Browse Tracks** (`/tracks`)
- List of tracks available to review
- Sort options (newest first by default, then by review count)
- Show: title, uploader, duration, review count, upload date
- Filter to show only unreviewed tracks
- Audio player for preview
- “Review This Track” button
1. **Track Detail & Review Page** (`/tracks/{id}`)
- Track information
- Audio player (must play full track to unlock review form)
- Progress indicator showing listening progress
- Feedback request from uploader (if provided)
- Review form (locked until full listen):
  - Equipment field (text input)
  - Review content (textarea, 200 char minimum)
  - Character counter
  - Submit button
- Existing reviews displayed below
1. **Upload Track** (`/upload`)
- File upload widget
- Title field
- Optional feedback request field
- Validation feedback
- Token cost displayed: “This will cost 1 token” (or “Free upload - helping seed the platform!” if cold start applies)
- Upload progress indicator
- If cold start exception applies, show banner explaining this is a one-time free upload
1. **My Tracks** (`/my-tracks`)
- List of user’s uploaded tracks
- Show review count for each
- Link to view reviews
- Delete button
1. **My Reviews** (`/my-reviews`)
- List of reviews user has submitted
- Link to original track
- Show equipment used
- Display review content
1. **Track Reviews Page** (`/tracks/{id}/reviews`)
- All reviews for a specific track
- Show reviewer name, equipment, date
- Full review content
- Flag button for track owner
1. **User Profile** (`/users/{id}`)
- Basic user info
- List of their uploads
- List of their reviews
1. **Transaction History** (`/transactions`)
- List of all token transactions
- Show: date, type (earned/spent), amount, related track/review

## Business Logic

### Token System

**Earning Tokens:**

- Submit a valid review: +1 token
- Transaction recorded immediately upon review submission
- Balance updates atomically with review creation

**Spending Tokens:**

- Upload a track: -1 token (normally)
- Cold start exception: If there are fewer than 3 tracks available to review platform-wide AND the user has not used their cold start upload yet, they can upload one track for free
- Check balance before allowing upload (unless cold start exception applies)
- Transaction recorded with track creation
- If upload fails, refund token

**Balance Rules:**

- Cannot upload if balance < 1 (unless cold start exception applies)
- Balance cannot go negative
- All token transactions are immutable once created
- Each user can only use the cold start exception once (tracked via has_used_cold_start_upload flag)

### Review Validation

**Server-side checks:**

- Track exists and is not deleted
- User hasn’t already reviewed this track
- User is not the track owner
- Review content is at least 200 characters
- Equipment field is not empty
- User’s client reported full playback (trust but verify)

**Client-side enforcement:**

- Audio player tracks playback progress
- Review form disabled until full track played
- Character counter for review content
- Show validation errors inline

### Track Upload Validation

**Server-side checks:**

- User has sufficient token balance OR qualifies for cold start exception
- Cold start exception criteria:
  - Fewer than 3 reviewable tracks exist (excluding user’s own tracks, deleted tracks)
  - User has not previously used their cold start upload (has_used_cold_start_upload == False)
- File type is in allowed list
- File size ≤ 20MB
- Audio duration ≤ 10 minutes (parsed from file)
- Title is provided and valid

**Upload process:**

1. Check if cold start exception applies (count reviewable tracks < 3 AND user hasn’t used cold start)
1. If no cold start: validate token balance
1. Validate file on upload
1. Upload to R2 storage
1. Extract audio metadata (duration)
1. Create Track record
1. If cold start used: set has_used_cold_start_upload = True
1. If not cold start: deduct token and create transaction
1. Return success with track ID

### Moderation System

**Review Flagging:**

- Track owners can flag reviews on their tracks
- Flagged reviews remain visible but marked for admin review
- Admin interface to review flagged content
- Admins can: remove review, warn/ban reviewer, dismiss flag

**Future considerations:**

- Auto-flag very short reviews
- Pattern detection for spam/abuse
- User reputation scoring

## Email Notifications

### Trigger: Track Receives Review

- **To**: Track uploader
- **Subject**: “Your track ‘[Track Title]’ received a review on Masterswap”
- **Content**:
  - Reviewer’s equipment
  - Snippet of review (first 200 chars)
  - Link to view full review
  - CTA to review more tracks if balance is low

### Trigger: Magic Link Login

- **To**: User requesting login
- **Subject**: “Your Masterswap login link”
- **Content**:
  - Magic link (expires in 15 minutes)
  - Security note about not sharing link

## Audio Playback Implementation

### Client-Side Player

- HTML5 audio element
- Custom controls with play/pause, progress bar, time display
- Progress tracking via `timeupdate` event
- Store highest playback position reached
- Only unlock review form when `currentTime >= duration - 5` (allowing for slight variance)
- Visual indicator of playback requirement

### Streaming

- Generate presigned URLs for R2 objects (1 hour expiration)
- Support range requests for seeking
- Track streaming via API endpoint that validates user access

## Security Considerations

- CSRF protection on all forms
- Rate limiting on API endpoints (especially upload and review submission)
- File type validation (magic bytes, not just extension)
- User input sanitization (prevent XSS in reviews)
- Presigned URLs for audio files (not publicly accessible)
- Magic link tokens expire after 15 minutes
- Session management with Django’s built-in security

## Performance Considerations

- Paginate track listings (20 per page)
- Index on Track.uploaded_at and Review.created_at
- Cache user token balance (invalidate on transaction)
- Use select_related/prefetch_related for queries with relationships
- Compress audio files on upload if over certain size (optional)
- CDN for static assets via fly.io

## Future Enhancements (Out of Scope for MVP)

1. **Comments on reviews** - Allow discussion threads on reviews
1. **Mobile app** - iOS/Android native apps
1. **Timestamped comments** - SoundCloud-style comments at specific moments
1. **Genres/categories** - Filter tracks by genre
1. **User profiles** - Detailed profiles with bio, equipment list, specialties
1. **Advanced token economy** - Premium reviews for more tokens, token purchases
1. **Social features** - Follow users, direct messaging
1. **Reputation system** - Rate reviewers, trusted reviewer badges
1. **Audio comparison tool** - A/B test different mixes
1. **Collaborative features** - Version control for tracks
1. **Advanced search** - Filter by equipment, genre, feedback type
1. **Analytics** - Detailed stats for users on their reviews’ helpfulness

## Development Phases

### Phase 1: Core MVP

- Django project setup with Ninja API
- User authentication with django-sesame
- Database models and migrations
- R2 storage integration
- Basic track upload/download

### Phase 2: Token System & Reviews

- Token balance and transaction system
- Review submission with validation
- Email notifications
- Track listing and filtering

### Phase 3: Frontend & UX

- Django templates for all pages
- Tailwind CSS styling
- Audio player with progress tracking
- Responsive design

### Phase 4: Polish & Deploy

- Review flagging and moderation
- Error handling and user feedback
- Testing (unit, integration)
- Docker setup
- fly.io deployment
- Documentation

## Success Metrics

- User sign-ups
- Reviews submitted per day
- Tracks uploaded per day
- Average review length
- User retention (return visits)
- Token velocity (how quickly tokens circulate)
- Review-to-upload ratio (should trend toward 1:1)

## Open Questions / Decisions Needed

1. Should there be a maximum token balance to encourage spending?
1. How to handle disputes over “unfair” reviews?
1. Should we allow private/unlisted tracks for specific reviewers?
1. Minimum reputation before users can upload? (Or just 0-token start is enough?)
1. What happens to orphaned reviews when tracks are deleted? (Display “Track deleted” placeholder?)

-----

**Document Version**: 1.0  
**Last Updated**: November 22, 2025  
**Owner**: Product Team
