#!/usr/bin/env python
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SmartCareSystem.settings')
django.setup()

from django.contrib.auth import get_user_model
from notifications.models import Notification

User = get_user_model()

def test_notification_badge_numbers():
    print("🔔 Testing Notification Badge Numbers")
    print("=" * 40)
    
    # Get a test user
    user = User.objects.first()
    if not user:
        print("❌ No users found")
        return
    
    # Clear existing notifications for this user
    Notification.objects.filter(recipient=user).delete()
    print("🗑️ Cleared existing notifications")
    
    # Test 1: Create 1 notification
    print("\n📝 Test 1: Creating 1 notification...")
    Notification.create_notification(
        recipient=user,
        notification_type='appointment_booked',
        title='Single Notification Test',
        message='This is test notification #1',
        priority='high'
    )
    
    unread_count = Notification.objects.filter(recipient=user, is_read=False).count()
    print(f"✅ Unread notifications: {unread_count}")
    print(f"🎯 Badge should show: '{unread_count}'")
    
    # Test 2: Create another notification (total 2)
    print("\n📝 Test 2: Creating 2nd notification...")
    Notification.create_notification(
        recipient=user,
        notification_type='bill_generated',
        title='Second Notification Test',
        message='This is test notification #2',
        priority='medium'
    )
    
    unread_count = Notification.objects.filter(recipient=user, is_read=False).count()
    print(f"✅ Unread notifications: {unread_count}")
    print(f"🎯 Badge should show: '{unread_count}'")
    
    # Test 3: Create another notification (total 3)
    print("\n📝 Test 3: Creating 3rd notification...")
    Notification.create_notification(
        recipient=user,
        notification_type='prescription_created',
        title='Third Notification Test',
        message='This is test notification #3',
        priority='low'
    )
    
    unread_count = Notification.objects.filter(recipient=user, is_read=False).count()
    print(f"✅ Unread notifications: {unread_count}")
    print(f"🎯 Badge should show: '{unread_count}'")
    
    # Test 4: Mark one as read
    print("\n📝 Test 4: Marking 1 notification as read...")
    first_notification = Notification.objects.filter(recipient=user, is_read=False).first()
    first_notification.mark_as_read()
    
    unread_count = Notification.objects.filter(recipient=user, is_read=False).count()
    print(f"✅ Unread notifications: {unread_count}")
    print(f"🎯 Badge should show: '{unread_count}'")
    
    print("\n🎉 Badge Test Complete!")
    print("🌐 Refresh your browser to see the badge update in real-time!")
    print("📱 The bell icon will show the exact number of unread notifications")

if __name__ == '__main__':
    test_notification_badge_numbers()
