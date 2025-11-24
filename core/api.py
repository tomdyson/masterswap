"""
Main API router for Masterswap.
Combines all API endpoints using Django Ninja.
"""

from ninja import NinjaAPI
from core.api.auth import router as auth_router
from core.api.tracks import router as tracks_router
from core.api.reviews import router as reviews_router
from core.api.users import router as users_router

# Create API instance
api = NinjaAPI(
    title="Masterswap API",
    version="1.0.0",
    description="API for audio mix feedback exchange platform"
)

# Add routers
api.add_router("/auth/", auth_router, tags=["Authentication"])
api.add_router("/tracks/", tracks_router, tags=["Tracks"])
api.add_router("/reviews/", reviews_router, tags=["Reviews"])
api.add_router("/user/", users_router, tags=["Users"])


# Health check endpoint
@api.get("/health", tags=["System"])
def health_check(request):
    """Simple health check endpoint."""
    return {"status": "ok", "message": "Masterswap API is running"}
