from django import forms
from django.forms.widgets import DateTimeInput, Select, Textarea
from .models import Appointment
from accounts.models import User

class AppointmentBookingForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = [
            'doctor', 'date_time', 'reason', 'symptoms', 'notes',
            'patient_name', 'age', 'gender', 'blood_group', 'phone', 'email', 'address',
            'appointment_type', 'priority'
        ]
        widgets = {
            'date_time': DateTimeInput(attrs={'type': 'datetime-local', 'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'doctor': Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'reason': Textarea(attrs={'rows': 3, 'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'symptoms': Textarea(attrs={'rows': 3, 'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'notes': Textarea(attrs={'rows': 3, 'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'address': Textarea(attrs={'rows': 2, 'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'gender': Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'blood_group': Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'appointment_type': Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'priority': Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter doctors only
        self.fields['doctor'].queryset = User.objects.filter(role='doctor', is_active=True)
        
        # If user is a doctor, pre-select them and make the field readonly
        if user and user.is_doctor:
            self.fields['doctor'].initial = user
            self.fields['doctor'].widget.attrs['readonly'] = True
        
        # Pre-fill user information if available
        if user:
            if 'patient_name' not in self.initial or not self.initial['patient_name']:
                self.initial['patient_name'] = user.get_full_name() or user.username
            if 'email' not in self.initial or not self.initial['email']:
                self.initial['email'] = user.email
            if hasattr(user, 'patient_profile'):
                profile = user.patient_profile
                if 'phone' not in self.initial or not self.initial['phone']:
                    self.initial['phone'] = getattr(profile, 'phone', '')
                if 'address' not in self.initial or not self.initial['address']:
                    self.initial['address'] = getattr(profile, 'address', '')
        
        # Add placeholder text
        self.fields['reason'].widget.attrs['placeholder'] = 'Describe the reason for your visit in detail...'
        self.fields['symptoms'].widget.attrs['placeholder'] = 'Describe your symptoms in detail (when they started, severity, frequency)...'
        self.fields['notes'].widget.attrs['placeholder'] = 'Any additional information...'
        self.fields['address'].widget.attrs['placeholder'] = 'Enter your complete address...'
        
        # Set required fields
        required_fields = ['reason', 'age', 'gender', 'blood_group', 'phone', 'email', 'address']
        # Only make patient_name required if not pre-filled (for admin/doctor bookings)
        if not (user and user.is_patient and (user.get_full_name() or user.username)):
            required_fields.append('patient_name')
        
        for field in required_fields:
            if field in self.fields:
                self.fields[field].required = True

class DoctorAppointmentBookingForm(forms.ModelForm):
    patient = forms.ModelChoiceField(
        queryset=User.objects.filter(role='patient', is_active=True),
        widget=forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
        empty_label="Select a patient"
    )
    
    class Meta:
        model = Appointment
        fields = ['patient', 'date_time', 'reason', 'symptoms', 'notes']
        widgets = {
            'date_time': DateTimeInput(attrs={'type': 'datetime-local', 'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'reason': Textarea(attrs={'rows': 3, 'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'symptoms': Textarea(attrs={'rows': 3, 'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'notes': Textarea(attrs={'rows': 3, 'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
        }
    
    def __init__(self, *args, **kwargs):
        doctor = kwargs.pop('doctor', None)
        super().__init__(*args, **kwargs)
        
        # Add placeholder text
        self.fields['reason'].widget.attrs['placeholder'] = 'Describe the reason for visit...'
        self.fields['symptoms'].widget.attrs['placeholder'] = 'Describe symptoms in detail...'
        self.fields['notes'].widget.attrs['placeholder'] = 'Any additional information...'
        
        # Make patient and reason required
        self.fields['patient'].required = True
        self.fields['reason'].required = True
    
    def save(self, commit=True):
        appointment = super().save(commit=False)
        # Set the doctor when saving
        if hasattr(self, 'doctor'):
            appointment.doctor = self.doctor
        if commit:
            appointment.save()
        return appointment
    
    def clean(self):
        cleaned_data = super().clean()
        doctor = cleaned_data.get('doctor')
        date_time = cleaned_data.get('date_time')
        
        # Check if doctor is available at the selected time
        if doctor and date_time:
            # Check if there's already an appointment at this time (within 1 hour window)
            from django.utils import timezone
            import datetime
            
            # Check for appointments within 1 hour before or after
            time_window = datetime.timedelta(hours=1)
            start_time = date_time - time_window
            end_time = date_time + time_window
            
            existing_appointment = Appointment.objects.filter(
                doctor=doctor,
                date_time__gte=start_time,
                date_time__lte=end_time,
                status__in=['pending', 'confirmed']
            ).exists()
            
            if existing_appointment:
                raise forms.ValidationError(
                    'This doctor already has an appointment scheduled around this time. Please choose a different time.'
                )
        
        return cleaned_data
