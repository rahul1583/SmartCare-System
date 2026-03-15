"""
Utility script to create bills for existing appointments
Run this in Django shell: python manage.py shell
"""

from django.utils import timezone
from datetime import timedelta
from appointments.models import Appointment
from billing.models import Bill
from accounts.models import User

def create_test_bills():
    """Create bills for existing appointments that don't have bills"""
    
    # Get appointments without bills
    appointments_without_bills = Appointment.objects.filter(bill__isnull=True)
    
    print(f"Found {appointments_without_bills.count()} appointments without bills")
    
    for appointment in appointments_without_bills:
        try:
            # Get doctor's consultation fee
            consultation_fee = 50.00  # Default fee
            if hasattr(appointment.doctor, 'doctor_profile') and appointment.doctor.doctor_profile.consultation_fee:
                consultation_fee = appointment.doctor.doctor_profile.consultation_fee
            
            # Create bill
            bill = Bill.objects.create(
                appointment=appointment,
                patient=appointment.patient,
                doctor=appointment.doctor,
                consultation_fee=consultation_fee,
                additional_charges=0,
                discount_amount=0,
                tax_amount=consultation_fee * 0.13,  # 13% tax
                total_amount=consultation_fee * 1.13,  # Total with tax
                status='sent',
                due_date=timezone.now().date() + timedelta(days=7),
                notes=f"Bill for appointment on {appointment.date_time.strftime('%B %d, %Y')}"
            )
            
            print(f"Created bill #{bill.id} for appointment #{appointment.id}")
            
        except Exception as e:
            print(f"Error creating bill for appointment #{appointment.id}: {str(e)}")
    
    print("Bill creation completed!")

def create_sample_bills():
    """Create sample bills for testing"""
    
    # Get a patient and doctor
    try:
        patient = User.objects.filter(role='patient').first()
        doctor = User.objects.filter(role='doctor').first()
        
        if not patient or not doctor:
            print("No patient or doctor found. Please create users first.")
            return
        
        # Create a sample appointment if none exists
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            date_time=timezone.now() + timedelta(days=1),
            reason="General Checkup",
            symptoms="Headache and fever",
            status="confirmed"
        )
        
        # Create bill for the appointment
        consultation_fee = 75.00
        bill = Bill.objects.create(
            appointment=appointment,
            patient=patient,
            doctor=doctor,
            consultation_fee=consultation_fee,
            additional_charges=25.00,  # Additional services
            discount_amount=10.00,   # Discount
            tax_amount=9.00,         # Tax
            total_amount=99.00,      # Total amount
            status='sent',
            due_date=timezone.now().date() + timedelta(days=7),
            notes="Sample bill for testing payment functionality"
        )
        
        print(f"Created sample appointment #{appointment.id} and bill #{bill.id}")
        print(f"Patient: {patient.email}")
        print(f"Doctor: {doctor.email}")
        print(f"Amount: Rs. {bill.total_amount}")
        print(f"Payment URL: /billing/{bill.id}/pay/")
        
    except Exception as e:
        print(f"Error creating sample data: {str(e)}")

if __name__ == "__main__":
    print("Creating bills for existing appointments...")
    create_test_bills()
    
    print("\nCreating sample bills for testing...")
    create_sample_bills()
