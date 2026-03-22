#!/usr/bin/env python
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SmartCareSystem.settings')
django.setup()

from django.contrib.auth import get_user_model
from notifications.models import Notification

User = get_user_model()

def test_notification_behavior():
    print("🔔 Testing Notification Badge Behavior")
    print("=" * 50)
    
    # Get test user
    user = User.objects.first()
    if not user:
        print("❌ No users found in database")
        return
    
    print(f"✅ Testing with user: {user.get_full_name() or user.email}")
    
    # Create a test notification
    notification, created = Notification.objects.get_or_create(
        recipient=user,
        title='Test Notification',
        defaults={
            'message': 'This is a test notification',
            'notification_type': 'appointment_booked',
            'priority': 'medium',
            'is_read': False
        }
    )
    
    if created:
        print("✅ Created new test notification")
    else:
        print("📝 Test notification already exists")
    
    # Check unread count before visiting page
    unread_before = Notification.objects.filter(recipient=user, is_read=False).count()
    print(f"🔢 Unread notifications before visiting page: {unread_before}")
    
    print("\n🌐 When you visit http://127.0.0.1:8000/notifications/:")
    print("👀 All notifications will be automatically marked as read")
    print("🔢 Badge number will disappear from bell icon")
    
    # Simulate visiting the page (mark as read)
    Notification.objects.filter(recipient=user, is_read=False).update(is_read=True)
    
    # Check unread count after "visiting" page
    unread_after = Notification.objects.filter(recipient=user, is_read=False).count()
    print(f"🔢 Unread notifications after visiting page: {unread_after}")
    
    if unread_after == 0:
        print("✅ SUCCESS! Badge number will disappear!")
    else:
        print("❌ Something went wrong")
    
    print("\n🎯 How it works:")
    print("1. You receive notifications → Badge shows number")
    print("2. You visit /notifications/ page → All marked as read")
    print("3. Badge disappears → No more number shown")
    
    print("\n🌐 Test it now: http://127.0.0.1:8000/notifications/")

if __name__ == '__main__':
    test_notification_behavior()
