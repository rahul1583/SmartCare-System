#!/usr/bin/env python
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SmartCareSystem.settings')
django.setup()

from django.contrib.auth import get_user_model
from notifications.models import Notification

User = get_user_model()

def create_test_notification():
    print("🔔 Creating test notification to show badge...")
    
    # Get a test user
    user = User.objects.first()
    if not user:
        print("❌ No users found")
        return
    
    # Create an unread notification
    notification = Notification.create_notification(
        recipient=user,
        notification_type='appointment_booked',
        title='Test Notification Badge',
        message='This is to test the notification badge showing "1"',
        priority='high',
        action_url='/notifications/',
        action_text='View Notifications'
    )
    
    print(f"✅ Created notification: {notification.id}")
    
    # Check unread count
    unread_count = Notification.objects.filter(recipient=user, is_read=False).count()
    print(f"📊 Unread notifications: {unread_count}")
    
    print("🎯 Now check the bell icon in your browser - it should show '{}'".format(unread_count))
    print("🌐 Refresh your browser page to see the badge!")

if __name__ == '__main__':
    create_test_notification()
