from django.utils import timezone
from appointments.models import Appointment

def cancel_expired_pending_appointments():
    """
    Finds all pending appointments whose scheduled time has passed
    and cancels them automatically.
    """
    now = timezone.now()
    
    # We target pending appointments where the date_time is in the past
    expired_appointments = Appointment.objects.filter(
        status='pending',
        date_time__lt=now
    )
    
    for appointment in expired_appointments:
        appointment.status = 'cancelled'
        cancellation_note = f"Automatically cancelled on {now.strftime('%Y-%m-%d')} because the doctor did not respond by the scheduled date ({appointment.date_time.strftime('%Y-%m-%d')})."
        
        if appointment.notes:
            appointment.notes = f"{cancellation_note}\n\n{appointment.notes}"
        else:
            appointment.notes = cancellation_note
        
        appointment.save()
    
    return expired_appointments.count()
