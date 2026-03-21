from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import Notification, NotificationPreference
from appointments.models import Appointment
from billing.models import Bill
from prescriptions.models import Prescription
from medical_records.models import MedicalRecord

User = get_user_model()


@receiver(post_save, sender=Appointment)
def appointment_notification_handler(sender, instance, created, **kwargs):
    """Handle appointment-related notifications"""
    
    if created:
        # New appointment booked
        title = "New Appointment Booked"
        message = f"Your appointment has been booked for {instance.date_time.strftime('%B %d, %Y at %I:%M %p')}."
        
        # Send to patient
        Notification.create_notification(
            recipient=instance.patient,
            notification_type='appointment_booked',
            title=title,
            message=message,
            appointment_id=instance.id,
            action_url=f'/appointments/detail/{instance.id}/',
            action_text='View Appointment',
            priority='high'
        )
        
        # Send to doctor
        doctor_title = "New Appointment Scheduled"
        doctor_message = f"New appointment scheduled with {instance.patient.get_full_name()} on {instance.date_time.strftime('%B %d, %Y at %I:%M %p')}."
        
        Notification.create_notification(
            recipient=instance.doctor,
            notification_type='doctor_assigned',
            title=doctor_title,
            message=doctor_message,
            sender=instance.patient,
            appointment_id=instance.id,
            action_url=f'/appointments/detail/{instance.id}/',
            action_text='View Appointment',
            priority='medium'
        )
    
    else:
        # Appointment status changed
        if hasattr(instance, '_original_status'):
            original_status = instance._original_status
            new_status = instance.status
            
            if original_status != new_status:
                if new_status == 'confirmed':
                    # Appointment confirmed
                    title = "Appointment Confirmed"
                    message = f"Your appointment on {instance.date_time.strftime('%B %d, %Y at %I:%M %p')} has been confirmed."
                    
                    Notification.create_notification(
                        recipient=instance.patient,
                        notification_type='appointment_confirmed',
                        title=title,
                        message=message,
                        sender=instance.doctor,
                        appointment_id=instance.id,
                        action_url=f'/appointments/detail/{instance.id}/',
                        action_text='View Appointment',
                        priority='high'
                    )
                    
                elif new_status == 'cancelled':
                    # Appointment cancelled
                    title = "Appointment Cancelled"
                    message = f"Your appointment scheduled for {instance.date_time.strftime('%B %d, %Y at %I:%M %p')} has been cancelled."
                    
                    Notification.create_notification(
                        recipient=instance.patient,
                        notification_type='appointment_cancelled',
                        title=title,
                        message=message,
                        sender=instance.doctor,
                        appointment_id=instance.id,
                        action_url=f'/appointments/detail/{instance.id}/',
                        action_text='View Details',
                        priority='high'
                    )
                    
                elif new_status == 'completed':
                    # Appointment completed
                    title = "Appointment Completed"
                    message = f"Your appointment on {instance.date_time.strftime('%B %d, %Y at %I:%M %p')} has been completed."
                    
                    Notification.create_notification(
                        recipient=instance.patient,
                        notification_type='appointment_completed',
                        title=title,
                        message=message,
                        sender=instance.doctor,
                        appointment_id=instance.id,
                        action_url=f'/appointments/detail/{instance.id}/',
                        action_text='View Details',
                        priority='medium'
                    )


@receiver(post_save, sender=Bill)
def bill_notification_handler(sender, instance, created, **kwargs):
    """Handle bill-related notifications"""
    
    if created:
        # New bill generated
        title = "New Bill Generated"
        message = f"A new bill of Rs. {instance.total_amount} has been generated for your appointment."
        
        Notification.create_notification(
            recipient=instance.patient,
            notification_type='bill_generated',
            title=title,
            message=message,
            bill_id=instance.id,
            action_url=f'/billing/detail/{instance.id}/',
            action_text='Pay Bill',
            priority='high'
        )
    
    else:
        # Bill status changed
        if hasattr(instance, '_original_status'):
            original_status = instance._original_status
            new_status = instance.status
            
            if original_status != new_status and new_status == 'paid':
                # Bill paid
                title = "Bill Payment Successful"
                message = f"Your payment of Rs. {instance.total_amount} has been received successfully."
                
                Notification.create_notification(
                    recipient=instance.patient,
                    notification_type='bill_paid',
                    title=title,
                    message=message,
                    bill_id=instance.id,
                    action_url=f'/billing/detail/{instance.id}/',
                    action_text='View Receipt',
                    priority='medium'
                )


@receiver(post_save, sender=Prescription)
def prescription_notification_handler(sender, instance, created, **kwargs):
    """Handle prescription-related notifications"""
    
    if created:
        # New prescription created
        title = "New Prescription"
        message = f"Dr. {instance.doctor.get_full_name()} has created a new prescription for you."
        
        Notification.create_notification(
            recipient=instance.patient,
            notification_type='prescription_created',
            title=title,
            message=message,
            sender=instance.doctor,
            prescription_id=instance.id,
            action_url=f'/prescriptions/detail/{instance.id}/',
            action_text='View Prescription',
            priority='medium'
        )


@receiver(post_save, sender=MedicalRecord)
def medical_record_notification_handler(sender, instance, created, **kwargs):
    """Handle medical record-related notifications"""
    
    if created:
        # New medical record created
        title = "Medical Record Updated"
        message = f"Your medical records have been updated by Dr. {instance.doctor.get_full_name()}."
        
        Notification.create_notification(
            recipient=instance.patient,
            notification_type='medical_record_created',
            title=title,
            message=message,
            sender=instance.doctor,
            medical_record_id=instance.id,
            action_url=f'/medical-records/detail/{instance.id}/',
            action_text='View Record',
            priority='medium'
        )


@receiver(post_save, sender=User)
def user_notification_handler(sender, instance, created, **kwargs):
    """Handle user-related notifications"""
    
    if created:
        # New user registered
        title = "Welcome to SmartCare"
        message = f"Welcome {instance.get_full_name()}! Your account has been created successfully."
        
        Notification.create_notification(
            recipient=instance,
            notification_type='user_registered',
            title=title,
            message=message,
            action_url='/dashboard/',
            action_text='Go to Dashboard',
            priority='medium'
        )
        
        # Notify admins about new user
        if instance.is_staff or instance.is_superuser:
            return  # Don't notify admins about other admins
            
        admins = User.objects.filter(is_superuser=True)
        if admins.exists():
            admin_title = "New User Registered"
            admin_message = f"{instance.get_full_name()} ({instance.email}) has registered as a {instance.get_role_display()}."
            
            Notification.create_bulk_notifications(
                recipients=admins,
                notification_type='user_registered',
                title=admin_title,
                message=admin_message,
                sender=instance,
                priority='low'
            )


@receiver(pre_save, sender=Appointment)
def track_original_appointment_status(sender, instance, **kwargs):
    """Track original appointment status for change detection"""
    if instance.pk:
        try:
            original = Appointment.objects.get(pk=instance.pk)
            instance._original_status = original.status
        except Appointment.DoesNotExist:
            pass


@receiver(pre_save, sender=Bill)
def track_original_bill_status(sender, instance, **kwargs):
    """Track original bill status for change detection"""
    if instance.pk:
        try:
            original = Bill.objects.get(pk=instance.pk)
            instance._original_status = original.status
        except Bill.DoesNotExist:
            pass


@receiver(post_save, sender=Notification)
def send_notification_emails(sender, instance, created, **kwargs):
    """Send email notifications when notification is created"""
    if created and not instance.is_email_sent:
        try:
            # Get user preferences
            preferences, _ = NotificationPreference.objects.get_or_create(user=instance.recipient)
            
            # Check if user wants email notifications for this type
            if preferences.can_send_notification(instance.notification_type, 'email'):
                subject = instance.title
                message = instance.message
                
                # Create HTML email template
                html_message = render_to_string('notifications/email_template.html', {
                    'notification': instance,
                    'user': instance.recipient,
                    'site_name': 'SmartCare System',
                })
                
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@smartcare.com'),
                    recipient_list=[instance.recipient.email],
                    html_message=html_message,
                    fail_silently=True,
                )
                
                # Mark as sent
                instance.is_email_sent = True
                instance.save(update_fields=['is_email_sent'])
                
        except Exception as e:
            # Log error but don't fail the notification creation
            print(f"Failed to send email notification: {e}")
