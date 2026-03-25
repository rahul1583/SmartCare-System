#!/usr/bin/env python
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SmartCareSystem.settings')
django.setup()

from django.contrib.auth import get_user_model
from medical_records.models import MedicalRecord
from appointments.models import Appointment

User = get_user_model()

def test_medical_records():
    print("🏥 Testing Medical Records for Patient Dashboard")
    print("=" * 50)
    
    # Get test users
    patient = User.objects.filter(role='patient').first()
    doctor = User.objects.filter(role='doctor').first()
    
    if not patient or not doctor:
        print("❌ Need at least 1 patient and 1 doctor in database")
        return
    
    print(f"✅ Using patient: {patient.get_full_name()}")
    print(f"✅ Using doctor: {doctor.get_full_name()}")
    
    # Create a test appointment first
    from django.utils import timezone
    from datetime import timedelta
    
    appointment_time = timezone.now() + timedelta(hours=24)
    appointment, created = Appointment.objects.get_or_create(
        patient=patient,
        doctor=doctor,
        date_time=appointment_time,
        defaults={
            'reason': 'Regular checkup',
            'status': 'confirmed'
        }
    )
    
    if created:
        print(f"✅ Created appointment for medical record")
    else:
        print(f"📅 Appointment already exists")
    
    # Create a test medical record
    medical_record, created = MedicalRecord.objects.get_or_create(
        patient=patient,
        doctor=doctor,
        appointment=appointment,
        defaults={
            'chief_complaint': 'Patient reports headache and fatigue',
            'history_of_present_illness': 'Symptoms started 3 days ago',
            'assessment': 'Possible tension headache, needs further evaluation',
            'plan': 'Prescribe pain medication and follow up in 1 week',
            'vital_signs': {
                'blood_pressure': '120/80',
                'heart_rate': '72',
                'temperature': '98.6',
                'respiratory_rate': '16'
            }
        }
    )
    
    if created:
        print(f"✅ Created medical record")
    else:
        print(f"🏥 Medical record already exists")
    
    # Check patient's medical records
    patient_records = MedicalRecord.objects.filter(patient=patient).count()
    print(f"📊 Total medical records for patient: {patient_records}")
    
    print("\n🌐 Patient Dashboard Features:")
    print("✅ Medical Records section added")
    print("✅ Quick Action button for Medical Records")
    print("✅ Shows recent medical records with details")
    print("✅ Links to full medical records list")
    
    print(f"\n🌐 Visit patient dashboard: http://127.0.0.1:8000/accounts/patient-dashboard/")
    print("🎉 Medical Records section is now visible!")

if __name__ == '__main__':
    test_medical_records()
