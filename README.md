# Masterswap

A web application for audio engineers to exchange mix feedback. Users earn tokens by reviewing others' mixes and spend tokens to upload their own tracks for review.

## Features

- **Token Economy**: Earn 1 token per review, spend 1 token to upload
- **Cold Start Mechanism**: New users can upload one track for free when platform has < 3 tracks
- **Magic Link Authentication**: Passwordless email-based login
- **Audio File Support**: MP3, WAV, FLAC, AAC, OGG (max 20MB, 10 minutes)
- **Full Track Listening Requirement**: Users must listen to entire track before reviewing
- **Review Moderation**: Track owners can flag unhelpful reviews
- **Email Notifications**: Async email notifications when tracks receive reviews

## Technology Stack

- **Backend**: Django 5.0 + Django Ninja (REST API)
- **Database**: PostgreSQL (production) / SQLite (development)
- **Storage**: Cloudflare R2 (S3-compatible) for audio files
- **Authentication**: django-sesame for magic links
- **Background Tasks**: Celery + Redis
- **Frontend**: Django templates + Tailwind CSS + Alpine.js + WaveSurfer.js

## Project Structure

```
masterswap/
├── core/                   # Main Django app
│   ├── api/               # Django Ninja API endpoints
│   │   ├── auth.py       # Authentication endpoints
│   │   ├── tracks.py     # Track management endpoints
│   │   ├── reviews.py    # Review endpoints
│   │   ├── users.py      # User profile endpoints
│   │   └── schemas.py    # Pydantic schemas for validation
│   ├── models.py         # Data models (User, Track, Review, Transaction)
│   ├── admin.py          # Django admin configuration
│   ├── views.py          # Frontend views
│   ├── utils.py          # Utility functions (token management, audio validation)
│   └── tasks.py          # Celery tasks (email notifications)
├── masterswap/           # Django project settings
│   ├── settings.py       # Configuration
│   ├── urls.py           # URL routing
│   └── celery.py         # Celery configuration
├── templates/            # Django templates (13 complete)
├── static/               # Static files (CSS, JS, images)
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variables template
└── README.md            # This file
```

## Setup Instructions

### 1. Prerequisites

- Python 3.11+
- PostgreSQL (for production)
- Redis (for Celery and caching)

### 2. Local Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd masterswap

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your settings
# For local development, defaults should work (uses SQLite, console email)

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### 3. Running Celery (for background tasks)

In a separate terminal:

```bash
# Make sure Redis is running first
redis-server

# Start Celery worker
celery -A masterswap worker -l info
```

### 4. Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `SECRET_KEY`: Django secret key (generate a secure one for production)
- `DEBUG`: Set to `False` in production
- `DATABASE_URL`: PostgreSQL connection string (optional, uses SQLite if not set)
- `USE_R2_STORAGE`: Set to `True` to use Cloudflare R2 for file storage
- `R2_*`: Cloudflare R2 credentials
- `EMAIL_*`: Email service configuration
- `REDIS_URL`: Redis connection string

## API Documentation

Once the server is running, visit:
- API docs: `http://localhost:8000/api/docs`
- API schema: `http://localhost:8000/api/openapi.json`

### Main API Endpoints

**Authentication**
- `POST /api/auth/request-magic-link` - Request magic link
- `POST /api/auth/logout` - Logout
- `GET /api/auth/verify-status` - Check auth status

**Tracks**
- `GET /api/tracks/` - List reviewable tracks
- `GET /api/tracks/{id}` - Get track details
- `POST /api/tracks/` - Upload track (costs 1 token)
- `DELETE /api/tracks/{id}` - Delete track
- `GET /api/tracks/{id}/stream` - Get streaming URL
- `GET /api/tracks/{id}/reviews` - Get track reviews

**Reviews**
- `GET /api/reviews/` - List my reviews
- `POST /api/reviews/` - Submit review (earns 1 token)
- `POST /api/reviews/{id}/flag` - Flag review
- `GET /api/reviews/{id}` - Get review details

**Users**
- `GET /api/user/me` - Current user profile
- `GET /api/user/me/dashboard` - Dashboard stats
- `GET /api/user/me/tracks` - My tracks
- `GET /api/user/me/reviews` - My reviews
- `GET /api/user/me/transactions` - Transaction history
- `GET /api/user/{id}/profile` - Public user profile

## Data Models

### User
- Email-based authentication
- Token balance tracking
- Cold start upload flag

### Track
- Audio file with metadata
- Soft delete support
- File validation (format, size, duration)

### Review
- 200+ character minimum
- Equipment description required
- Unique constraint (one review per user per track)
- Flagging system for moderation

### Transaction
- Immutable transaction log
- Token earning/spending history
- Balance snapshots

## Business Logic

### Token System
- Start with 0 tokens
- Earn 1 token per review
- Spend 1 token per upload
- Cold start exception: First upload free if < 3 reviewable tracks exist

### Audio File Validation
- Supported formats: MP3, WAV, FLAC, AAC, OGG
- Max file size: 20MB
- Max duration: 10 minutes
- Server-side validation using mutagen

### Review Requirements
- Must listen to full track (client-side tracking)
- Minimum 200 characters
- Equipment description required
- Cannot review own tracks
- Cannot review same track twice

## Development Tasks Completed

✅ Django project setup with Django Ninja
✅ Data models (User, Track, Review, Transaction)
✅ Custom user model with token balance
✅ Complete REST API with all endpoints
✅ Magic link authentication
✅ Token transaction system
✅ Cold start mechanism
✅ Cloudflare R2 storage integration
✅ Audio file validation
✅ Celery + Redis setup
✅ Email notifications
✅ Admin interface configuration
✅ All Django templates (13 pages)
✅ Tailwind CSS styling (via CDN)
✅ WaveSurfer.js audio player with waveform visualization
✅ Alpine.js interactive components
✅ File upload with client-side validation
✅ Responsive mobile-first design

## Next Steps (Backend Integration Needed)

- [ ] Update Django views with correct context variables
- [ ] Add missing URL patterns (logout, flag_review, delete_track)
- [ ] Add model property methods (duration_minutes, file_size_mb, review_count)
- [ ] Add comprehensive testing
- [ ] Implement rate limiting
- [ ] Add pagination logic to views

See `BACKEND_UPDATES_NEEDED.md` for complete integration checklist.

## Deployment

### Docker

Create `Dockerfile` and `docker-compose.yml` for containerization.

### fly.io

1. Install flyctl: `curl -L https://fly.io/install.sh | sh`
2. Login: `fly auth login`
3. Launch: `fly launch`
4. Set secrets: `fly secrets set SECRET_KEY=...`
5. Deploy: `fly deploy`

### Environment Setup

Ensure these are configured in production:
- Set `DEBUG=False`
- Configure PostgreSQL database
- Set up Cloudflare R2 bucket
- Configure email service (Mailgun, etc.)
- Set up Redis instance
- Generate secure `SECRET_KEY`

## Contributing

This project follows the specification in the product requirements document.

## License

[Specify license]

## Support

For issues and questions, please open a GitHub issue.
