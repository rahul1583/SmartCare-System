#!/usr/bin/env python
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SmartCareSystem.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
from appointments.models import Appointment
from prescriptions.models import Prescription
from billing.models import Bill

User = get_user_model()

def create_recent_activities():
    print("🔔 Creating Recent Activities for Dashboard")
    print("=" * 50)
    
    # Get or create test users
    doctor = User.objects.filter(role='doctor').first()
    patient = User.objects.filter(role='patient').first()
    
    if not doctor or not patient:
        print("❌ Need at least 1 doctor and 1 patient in database")
        return
    
    print(f"✅ Using doctor: {doctor.get_full_name()}")
    print(f"✅ Using patient: {patient.get_full_name()}")
    
    # Create today's appointment
    today = timezone.now().date()
    today_time = timezone.now().replace(hour=14, minute=30, second=0, microsecond=0)
    
    if today_time.date() != today:
        today_time = timezone.now().replace(hour=14, minute=30, second=0, microsecond=0)
    
    appointment, created = Appointment.objects.get_or_create(
        patient=patient,
        doctor=doctor,
        date_time=today_time,
        defaults={
            'reason': 'Regular checkup',
            'status': 'confirmed'
        }
    )
    
    if created:
        print(f"✅ Created today's appointment: {appointment.date_time.strftime('%Y-%m-%d %H:%M')}")
    else:
        print(f"📅 Today's appointment already exists")
    
    # Create recent prescription
    prescription, created = Prescription.objects.get_or_create(
        patient=patient,
        doctor=doctor,
        defaults={
            'diagnosis': 'General health checkup',
            'symptoms': 'Patient reports mild headache and fatigue',
            'notes': 'Prescribed rest and hydration'
        }
    )
    
    if created:
        diagnosis_text = prescription.diagnosis[:30] + '...' if len(prescription.diagnosis) > 30 else prescription.diagnosis
        print(f"✅ Created recent prescription: {diagnosis_text}")
    else:
        print(f"💊 Recent prescription already exists")
    
    # Create recent bill
    bill, created = Bill.objects.get_or_create(
        patient=patient,
        doctor=doctor,
        defaults={
            'consultation_fee': 300.00,
            'medicine_fee': 150.00,
            'total_amount': 450.00,
            'status': 'pending',
            'notes': 'Regular consultation fee'
        }
    )
    
    if created:
        print(f"✅ Created recent bill: Rs. {bill.total_amount}")
    else:
        print(f"💰 Recent bill already exists")
    
    # Show summary
    print("\n📊 Summary of Recent Activities:")
    print(f"📅 Today's Appointments: {Appointment.objects.filter(date_time__date=today).count()}")
    print(f"💊 Recent Prescriptions: {Prescription.objects.all().count()}")
    print(f"💰 Recent Bills: {Bill.objects.all().count()}")
    
    print("\n🌐 Visit the dashboard to see recent activities:")
    print("http://127.0.0.1:8000/accounts/admin/dashboard-users/")
    print("\n🎉 Recent Activities section is ready!")

if __name__ == '__main__':
    create_recent_activities()
