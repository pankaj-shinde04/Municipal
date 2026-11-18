from .models import Notification

def notifications_context(request):
    """
    Exposes user notifications and unread badge count globally to all templates.
    """
    if request.user.is_authenticated:
        user_notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:15]
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        return {
            'notifications': user_notifications,
            'unread_count': unread_count,
        }
    return {
        'notifications': [],
        'unread_count': 0,
    }
