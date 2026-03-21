from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Notification(models.Model):
    """Notification system for SmartCare users"""
    
    NOTIFICATION_TYPES = [
        ('appointment_booked', 'Appointment Booked'),
        ('appointment_confirmed', 'Appointment Confirmed'),
        ('appointment_cancelled', 'Appointment Cancelled'),
        ('appointment_completed', 'Appointment Completed'),
        ('bill_paid', 'Bill Paid'),
        ('bill_generated', 'Bill Generated'),
        ('prescription_created', 'Prescription Created'),
        ('medical_record_created', 'Medical Record Created'),
        ('lab_report_uploaded', 'Lab Report Uploaded'),
        ('doctor_assigned', 'Doctor Assigned'),
        ('payment_reminder', 'Payment Reminder'),
        ('appointment_reminder', 'Appointment Reminder'),
        ('system_update', 'System Update'),
        ('user_registered', 'New User Registered'),
        ('profile_updated', 'Profile Updated'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications')
    
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    
    is_read = models.BooleanField(default=False)
    is_email_sent = models.BooleanField(default=False)
    is_sms_sent = models.BooleanField(default=False)
    
    # Related objects for easy reference
    appointment_id = models.PositiveIntegerField(null=True, blank=True)
    bill_id = models.PositiveIntegerField(null=True, blank=True)
    prescription_id = models.PositiveIntegerField(null=True, blank=True)
    medical_record_id = models.PositiveIntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Action URLs
    action_url = models.CharField(max_length=500, blank=True)
    action_text = models.CharField(max_length=50, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['priority']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.get_full_name()}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def get_absolute_url(self):
        """Get URL for notification action"""
        if self.action_url:
            return self.action_url
        
        # Default URLs based on notification type
        url_mapping = {
            'appointment_booked': f'/appointments/detail/{self.appointment_id}/',
            'appointment_confirmed': f'/appointments/detail/{self.appointment_id}/',
            'appointment_cancelled': f'/appointments/detail/{self.appointment_id}/',
            'appointment_completed': f'/appointments/detail/{self.appointment_id}/',
            'bill_paid': f'/billing/detail/{self.bill_id}/',
            'bill_generated': f'/billing/detail/{self.bill_id}/',
            'prescription_created': f'/prescriptions/detail/{self.prescription_id}/',
            'medical_record_created': f'/medical-records/detail/{self.medical_record_id}/',
        }
        
        return url_mapping.get(self.notification_type, '/dashboard/')
    
    @classmethod
    def create_notification(cls, recipient, notification_type, title, message, 
                          sender=None, priority='medium', **kwargs):
        """Create a new notification"""
        notification = cls.objects.create(
            recipient=recipient,
            sender=sender,
            notification_type=notification_type,
            title=title,
            message=message,
            priority=priority,
            **kwargs
        )
        return notification
    
    @classmethod
    def create_bulk_notifications(cls, recipients, notification_type, title, message, 
                                sender=None, priority='medium', **kwargs):
        """Create notifications for multiple recipients"""
        notifications = []
        for recipient in recipients:
            notifications.append(cls(
                recipient=recipient,
                sender=sender,
                notification_type=notification_type,
                title=title,
                message=message,
                priority=priority,
                **kwargs
            ))
        return cls.objects.bulk_create(notifications)

class NotificationTemplate(models.Model):
    """Email and SMS templates for notifications"""
    
    notification_type = models.CharField(max_length=50, choices=Notification.NOTIFICATION_TYPES, unique=True)
    
    # Email template
    email_subject = models.CharField(max_length=200)
    email_body = models.TextField()
    
    # SMS template
    sms_message = models.CharField(max_length=160)
    
    # Push notification template
    push_title = models.CharField(max_length=100)
    push_body = models.CharField(max_length=200)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['notification_type']
    
    def __str__(self):
        return f"Template for {self.get_notification_type_display()}"

class NotificationPreference(models.Model):
    """User notification preferences"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Email preferences
    email_appointments = models.BooleanField(default=True)
    email_bills = models.BooleanField(default=True)
    email_prescriptions = models.BooleanField(default=True)
    email_medical_records = models.BooleanField(default=True)
    email_system_updates = models.BooleanField(default=True)
    
    # SMS preferences
    sms_appointments = models.BooleanField(default=False)
    sms_bills = models.BooleanField(default=True)
    sms_urgent = models.BooleanField(default=True)
    
    # Push notification preferences
    push_appointments = models.BooleanField(default=True)
    push_bills = models.BooleanField(default=True)
    push_prescriptions = models.BooleanField(default=True)
    
    # General preferences
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Notification Preference"
        verbose_name_plural = "Notification Preferences"
    
    def __str__(self):
        return f"Preferences for {self.user.get_full_name()}"
    
    def can_send_notification(self, notification_type, channel='email'):
        """Check if notification can be sent for specific channel"""
        # Check quiet hours
        if self.quiet_hours_start and self.quiet_hours_end:
            now = timezone.now().time()
            if self.quiet_hours_start <= now <= self.quiet_hours_end:
                return False
        
        # Check channel preferences
        channel_mapping = {
            'email': {
                'appointment_booked': self.email_appointments,
                'appointment_confirmed': self.email_appointments,
                'appointment_cancelled': self.email_appointments,
                'appointment_completed': self.email_appointments,
                'bill_paid': self.email_bills,
                'bill_generated': self.email_bills,
                'prescription_created': self.email_prescriptions,
                'medical_record_created': self.email_medical_records,
                'system_update': self.email_system_updates,
            },
            'sms': {
                'appointment_booked': self.sms_appointments,
                'bill_paid': self.sms_bills,
                'bill_generated': self.sms_bills,
            },
            'push': {
                'appointment_booked': self.push_appointments,
                'appointment_confirmed': self.push_appointments,
                'appointment_cancelled': self.push_appointments,
                'appointment_completed': self.push_appointments,
                'bill_paid': self.push_bills,
                'bill_generated': self.push_bills,
                'prescription_created': self.push_prescriptions,
            }
        }
        
        channel_prefs = channel_mapping.get(channel, {})
        return channel_prefs.get(notification_type, True)
