from django.db import models
from django.conf import settings

class Prescription(models.Model):
    CONSULTATION_TYPE_CHOICES = (
        ('physical_visit', 'Physical Visit'),
        ('online_consultant', 'Online Consultant'),
    )
    
    appointment = models.OneToOneField('appointments.Appointment', on_delete=models.CASCADE, related_name='prescription', blank=True, null=True)
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='prescriptions')
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patient_prescriptions')
    consultation_type = models.CharField(max_length=20, choices=CONSULTATION_TYPE_CHOICES, default='physical_visit')
    diagnosis = models.TextField()
    symptoms = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    follow_up_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'prescriptions'
        verbose_name = 'Prescription'
        verbose_name_plural = 'Prescriptions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Prescription for {self.patient.get_full_name()} by Dr. {self.doctor.get_full_name()} on {self.created_at.date()}"

class Medication(models.Model):
    FREQUENCY_CHOICES = (
        ('once', 'Once daily'),
        ('twice', 'Twice daily'),
        ('thrice', 'Thrice daily'),
        ('four_times', 'Four times daily'),
        ('sos', 'SOS (as needed)'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    )
    
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='medications')
    medicine_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100)  # e.g., "500mg", "10ml"
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    duration = models.CharField(max_length=50)  # e.g., "7 days", "2 weeks"
    instructions = models.TextField(blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'medications'
        verbose_name = 'Medication'
        verbose_name_plural = 'Medications'
    
    def __str__(self):
        return f"{self.medicine_name} - {self.dosage} ({self.get_frequency_display()})"

class MedicineMaster(models.Model):
    CATEGORY_CHOICES = (
        ('antibiotic', 'Antibiotic'),
        ('painkiller', 'Pain Killer'),
        ('vitamin', 'Vitamin'),
        ('supplement', 'Supplement'),
        ('chronic', 'Chronic Disease'),
        ('acute', 'Acute Disease'),
        ('other', 'Other'),
    )
    
    name = models.CharField(max_length=200, unique=True)
    generic_name = models.CharField(max_length=200, blank=True, null=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True, null=True)
    manufacturer = models.CharField(max_length=200, blank=True, null=True)
    side_effects = models.TextField(blank=True, null=True)
    contraindications = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'medicine_master'
        verbose_name = 'Medicine Master'
        verbose_name_plural = 'Medicine Masters'
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"
