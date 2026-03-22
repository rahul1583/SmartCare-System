from django.contrib.auth import get_user_model
from notifications.models import Notification

User = get_user_model()

def notification_context(request):
    """Add notification count to all templates"""
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return {
            'unread_count': unread_count,
        }
    return {}
