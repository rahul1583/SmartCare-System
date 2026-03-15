from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

class Appointment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('no_show', 'No Show'),
    )
    
    APPOINTMENT_TYPE_CHOICES = (
        ('consultation', 'General Consultation'),
        ('followup', 'Follow-up Visit'),
        ('emergency', 'Emergency'),
        ('checkup', 'Routine Check-up'),
        ('specialist', 'Specialist Consultation'),
        ('vaccination', 'Vaccination'),
    )
    
    PRIORITY_CHOICES = (
        ('low', 'Low - Routine check-up'),
        ('medium', 'Medium - Non-urgent medical issue'),
        ('high', 'High - Urgent but not emergency'),
        ('critical', 'Critical - Emergency'),
    )
    
    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    )
    
    BLOOD_GROUP_CHOICES = (
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
    )
    
    # Basic Appointment Fields
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patient_appointments')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_appointments')
    date_time = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reason = models.TextField()
    symptoms = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Enhanced Patient Information (nullable for existing records)
    patient_name = models.CharField(max_length=100, blank=True, null=True)
    age = models.PositiveIntegerField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUP_CHOICES, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    # Medical Information (nullable for existing records)
    allergies = models.TextField(blank=True, null=True, help_text="List any allergies")
    current_medications = models.TextField(blank=True, null=True, help_text="Current medications")
    medical_conditions = models.TextField(blank=True, null=True, help_text="Previous medical conditions")
    emergency_contact = models.CharField(max_length=100, blank=True, null=True)
    emergency_phone = models.CharField(max_length=20, blank=True, null=True)
    emergency_relationship = models.CharField(max_length=20, blank=True, null=True)
    
    # Appointment Details (nullable for existing records)
    appointment_type = models.CharField(max_length=20, choices=APPOINTMENT_TYPE_CHOICES, default='consultation', blank=True, null=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', blank=True, null=True)
    
    # Additional Information (nullable for existing records)
    insurance_provider = models.CharField(max_length=100, blank=True, null=True)
    policy_number = models.CharField(max_length=50, blank=True, null=True)
    payment_method = models.CharField(max_length=20, blank=True, null=True, 
                                     choices=[('cash', 'Cash'), ('card', 'Credit/Debit Card'), 
                                             ('insurance', 'Insurance'), ('online', 'Online Payment')])
    previous_visits = models.CharField(max_length=20, blank=True, null=True,
                                     choices=[('first_time', 'First Time Visit'), ('returning', 'Returning Patient'), 
                                             ('followup', 'Follow-up Visit')])
    special_requests = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'appointments'
        verbose_name = 'Appointment'
        verbose_name_plural = 'Appointments'
        ordering = ['date_time']
    
    def __str__(self):
        return f"Appointment: {self.patient.get_full_name()} with Dr. {self.doctor.get_full_name()} on {self.date_time}"

class DoctorAvailability(models.Model):
    DAY_CHOICES = (
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    )
    
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='availability')
    day_of_week = models.CharField(max_length=10, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    max_patients = models.PositiveIntegerField(default=10)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'doctor_availability'
        verbose_name = 'Doctor Availability'
        verbose_name_plural = 'Doctor Availabilities'
        unique_together = ['doctor', 'day_of_week']
    
    def __str__(self):
        return f"Dr. {self.doctor.get_full_name()} - {self.get_day_of_week_display()} ({self.start_time} to {self.end_time})"

class AppointmentReview(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='review')
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'appointment_reviews'
        verbose_name = 'Appointment Review'
        verbose_name_plural = 'Appointment Reviews'
    
    def __str__(self):
        return f"Review for {self.appointment} - Rating: {self.rating}/5"
