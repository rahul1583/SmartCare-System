from django.db import models
from django.conf import settings

class MedicalRecord(models.Model):
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='medical_records')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patient_records')
    appointment = models.ForeignKey('appointments.Appointment', on_delete=models.CASCADE, related_name='medical_records', blank=True, null=True)
    chief_complaint = models.TextField()
    history_of_present_illness = models.TextField(blank=True, null=True)
    past_medical_history = models.TextField(blank=True, null=True)
    family_history = models.TextField(blank=True, null=True)
    social_history = models.TextField(blank=True, null=True)
    physical_examination = models.TextField(blank=True, null=True)
    assessment = models.TextField()
    plan = models.TextField()
    vital_signs = models.JSONField(blank=True, null=True)  # Store BP, HR, RR, Temp, etc.
    is_confidential = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'medical_records'
        verbose_name = 'Medical Record'
        verbose_name_plural = 'Medical Records'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Medical Record for {self.patient.get_full_name()} on {self.created_at.date()}"

class LabReport(models.Model):
    REPORT_TYPE_CHOICES = (
        ('blood_test', 'Blood Test'),
        ('urine_test', 'Urine Test'),
        ('x_ray', 'X-Ray'),
        ('ultrasound', 'Ultrasound'),
        ('ct_scan', 'CT Scan'),
        ('mri', 'MRI'),
        ('ecg', 'ECG'),
        ('pathology', 'Pathology'),
        ('other', 'Other'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lab_reports')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ordered_reports')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    report_file = models.FileField(upload_to='lab_reports/', blank=True, null=True)
    results = models.TextField(blank=True, null=True)
    normal_range = models.TextField(blank=True, null=True)
    interpretation = models.TextField(blank=True, null=True)
    ordered_date = models.DateTimeField(auto_now_add=True)
    completed_date = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'lab_reports'
        verbose_name = 'Lab Report'
        verbose_name_plural = 'Lab Reports'
        ordering = ['-ordered_date']
    
    def __str__(self):
        return f"{self.get_report_type_display()} - {self.patient.get_full_name()}"

class VitalSigns(models.Model):
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vital_signs')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recorded_vitals')
    appointment = models.ForeignKey('appointments.Appointment', on_delete=models.CASCADE, related_name='vital_signs', blank=True, null=True)
    blood_pressure_systolic = models.PositiveIntegerField(blank=True, null=True)
    blood_pressure_diastolic = models.PositiveIntegerField(blank=True, null=True)
    heart_rate = models.PositiveIntegerField(blank=True, null=True)
    respiratory_rate = models.PositiveIntegerField(blank=True, null=True)
    temperature = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    oxygen_saturation = models.PositiveIntegerField(blank=True, null=True)
    height = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)  # in cm
    weight = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)  # in kg
    bmi = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'vital_signs'
        verbose_name = 'Vital Signs'
        verbose_name_plural = 'Vital Signs'
        ordering = ['-recorded_at']
    
    def __str__(self):
        return f"Vital Signs for {self.patient.get_full_name()} on {self.recorded_at.date()}"
    
    def save(self, *args, **kwargs):
        if self.height and self.weight:
            # Calculate BMI: weight (kg) / (height (m))^2
            height_in_meters = self.height / 100
            self.bmi = round(self.weight / (height_in_meters ** 2), 1)
        super().save(*args, **kwargs)

class Allergy(models.Model):
    SEVERITY_CHOICES = (
        ('mild', 'Mild'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
        ('life_threatening', 'Life Threatening'),
    )
    
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='allergies')
    allergen = models.CharField(max_length=200)
    allergy_type = models.CharField(max_length=100)  # e.g., "Drug", "Food", "Environmental"
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    reaction = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'allergies'
        verbose_name = 'Allergy'
        verbose_name_plural = 'Allergies'
    
    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.allergen} ({self.get_severity_display()})"
