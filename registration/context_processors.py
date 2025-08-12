
from .models import Notification  # Make sure to import your Notification model

def notifications_processor(request):
    if request.user.is_authenticated:
        # Query the Notification model directly to avoid the slicing error
        notifications = Notification.objects.filter(user=request.user)
        unread_count = notifications.filter(is_read=False).count()
        
        return {
            # It's good practice to limit the notifications in the dropdown
            'notifications': notifications.order_by('-created_at')[:5], 
            'unread_count': unread_count
        }
    return {}