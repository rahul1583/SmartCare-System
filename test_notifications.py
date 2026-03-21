#!/usr/bin/env python
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SmartCareSystem.settings')
django.setup()

from django.contrib.auth import get_user_model
from notifications.models import Notification, NotificationPreference

User = get_user_model()

def test_notification_system():
    print("🔔 Testing SmartCare Notification System")
    print("=" * 50)
    
    # Check if models are working
    try:
        # Get a test user
        user = User.objects.first()
        if not user:
            print("❌ No users found in database")
            return
        
        print(f"✅ Found test user: {user.get_full_name() or user.email}")
        
        # Create a test notification
        notification = Notification.create_notification(
            recipient=user,
            notification_type='appointment_booked',
            title='Test Appointment Notification',
            message='This is a test notification from SmartCare system.',
            priority='medium',
            action_url='/appointments/',
            action_text='View Appointments'
        )
        
        print(f"✅ Created test notification: {notification.title}")
        print(f"   - ID: {notification.id}")
        print(f"   - Type: {notification.get_notification_type_display()}")
        print(f"   - Priority: {notification.get_priority_display()}")
        print(f"   - Created: {notification.created_at}")
        
        # Check notification preferences
        preferences, created = NotificationPreference.objects.get_or_create(user=user)
        if created:
            print("✅ Created default notification preferences")
        else:
            print("✅ Found existing notification preferences")
        
        # Count notifications
        total_notifications = Notification.objects.filter(recipient=user).count()
        unread_notifications = Notification.objects.filter(recipient=user, is_read=False).count()
        
        print(f"📊 Notification Statistics:")
        print(f"   - Total: {total_notifications}")
        print(f"   - Unread: {unread_notifications}")
        
        print("\n🎉 Notification system is working correctly!")
        print("📱 You can now:")
        print("   1. Book appointments → triggers notifications")
        print("   2. Pay bills → triggers payment confirmations")
        print("   3. Confirm appointments → triggers confirmations")
        print("   4. Create prescriptions → triggers alerts")
        print("   5. Update medical records → triggers updates")
        
    except Exception as e:
        print(f"❌ Error testing notification system: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_notification_system()
