import os
import django
from django.utils import timezone
from datetime import timedelta

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SmartCareSystem.settings')
django.setup()

from appointments.models import Appointment
from appointments.utils import cancel_expired_pending_appointments
from accounts.models import User

def verify_automatic_cancellation():
    print("Verifying Automatic Cancellation of Expired Appointments")
    print("=" * 60)
    
    # Get or create test users
    doctor = User.objects.filter(role='doctor').first()
    patient = User.objects.filter(role='patient').first()
    
    if not doctor or not patient:
        print("Need at least 1 doctor and 1 patient in database")
        return
    
    print(f"Using doctor: {doctor.email}")
    print(f"Using patient: {patient.email}")
    
    # 1. Create an expired pending appointment (yesterday)
    yesterday = timezone.now() - timedelta(days=1)
    
    expired_appointment = Appointment.objects.create(
        patient=patient,
        doctor=doctor,
        date_time=yesterday,
        status='pending',
        reason='Test expired appointment',
        patient_name=patient.get_full_name() or patient.username
    )
    
    print(f"Created expired appointment (ID: {expired_appointment.id}) for {yesterday}")
    print(f"   Status: {expired_appointment.status}")
    
    # 2. Trigger cancellation logic
    print("\nTriggering cancellation logic...")
    cancelled_count = cancel_expired_pending_appointments()
    print(f"Cancelled {cancelled_count} appointments")
    
    # 3. Verify the appointment is now cancelled
    updated_appointment = Appointment.objects.get(id=expired_appointment.id)
    print(f"\nVerification:")
    print(f"   Appointment ID: {updated_appointment.id}")
    print(f"   New Status: {updated_appointment.status}")
    print(f"   Notes: {updated_appointment.notes[:100]}...")
    
    if updated_appointment.status == 'cancelled':
        print("\nSUCCESS: Expired appointment was automatically cancelled!")
    else:
        print("\nFAILURE: Expired appointment was NOT cancelled.")

if __name__ == "__main__":
    verify_automatic_cancellation()
