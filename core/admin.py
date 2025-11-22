from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Track, Review, Transaction


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for User model."""

    list_display = ('email', 'username', 'token_balance', 'has_used_cold_start_upload', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_active', 'has_used_cold_start_upload', 'date_joined')
    search_fields = ('email', 'username')
    ordering = ('-date_joined',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('username',)}),
        ('Token info', {'fields': ('token_balance', 'has_used_cold_start_upload')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    """Admin configuration for Track model."""

    list_display = ('title', 'uploader', 'duration', 'file_size', 'review_count', 'uploaded_at', 'is_deleted')
    list_filter = ('is_deleted', 'uploaded_at')
    search_fields = ('title', 'uploader__email')
    readonly_fields = ('uploaded_at', 'file_size', 'duration', 'deleted_at')
    ordering = ('-uploaded_at',)

    fieldsets = (
        (None, {'fields': ('title', 'uploader', 'file')}),
        ('Metadata', {'fields': ('file_size', 'duration', 'feedback_request')}),
        ('Status', {'fields': ('is_deleted', 'deleted_at', 'uploaded_at')}),
    )

    def review_count(self, obj):
        return obj.reviews.count()
    review_count.short_description = 'Reviews'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """Admin configuration for Review model."""

    list_display = ('reviewer', 'track', 'equipment_short', 'created_at', 'is_flagged')
    list_filter = ('is_flagged', 'created_at')
    search_fields = ('reviewer__email', 'track__title', 'content', 'equipment')
    readonly_fields = ('created_at', 'flagged_at')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {'fields': ('track', 'reviewer')}),
        ('Review Content', {'fields': ('equipment', 'content', 'listening_duration')}),
        ('Moderation', {'fields': ('is_flagged', 'flagged_by', 'flagged_at', 'flag_reason')}),
        ('Timestamps', {'fields': ('created_at',)}),
    )

    def equipment_short(self, obj):
        return obj.equipment[:50] + '...' if len(obj.equipment) > 50 else obj.equipment
    equipment_short.short_description = 'Equipment'

    actions = ['approve_flagged_reviews', 'flag_reviews']

    def approve_flagged_reviews(self, request, queryset):
        """Approve flagged reviews (unflag them)."""
        queryset.update(is_flagged=False, flagged_by=None, flagged_at=None, flag_reason=None)
        self.message_user(request, f'{queryset.count()} reviews approved.')
    approve_flagged_reviews.short_description = 'Approve selected flagged reviews'

    def flag_reviews(self, request, queryset):
        """Flag selected reviews for moderation."""
        from django.utils import timezone
        queryset.update(is_flagged=True, flagged_at=timezone.now())
        self.message_user(request, f'{queryset.count()} reviews flagged.')
    flag_reviews.short_description = 'Flag selected reviews'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Admin configuration for Transaction model."""

    list_display = ('user', 'transaction_type', 'amount', 'balance_after', 'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('user__email',)
    readonly_fields = ('created_at', 'balance_after')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {'fields': ('user', 'transaction_type', 'amount', 'balance_after')}),
        ('Related Objects', {'fields': ('related_review', 'related_track')}),
        ('Timestamps', {'fields': ('created_at',)}),
    )

    def has_add_permission(self, request):
        """Disable manual transaction creation in admin."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Disable transaction deletion in admin."""
        return False
