from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect
from django.contrib import messages
from .models import PatientProfile, DoctorProfile

class SmartCareSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        Invoked just after a user successfully authenticates via a social provider,
        but before the login is actually processed.
        """
        # Ensure only Gmail accounts are allowed
        email = sociallogin.account.extra_data.get('email', '').lower()
        if not email.endswith('@gmail.com'):
            messages.error(request, "Only Gmail accounts are allowed for SmartCare.")
            raise ImmediateHttpResponse(redirect('accounts:login'))

    def save_user(self, request, sociallogin, form=None):
        """
        Saves a newly signed up social login user.
        """
        user = super().save_user(request, sociallogin, form)
        
        # Default role for social signup is patient
        if not user.role:
            user.role = 'patient'
            user.save()
            
        # Create Patient Profile if it doesn't exist
        if user.role == 'patient' and not hasattr(user, 'patient_profile'):
            PatientProfile.objects.get_or_create(
                user=user,
                defaults={
                    'date_of_birth': '2000-01-01',
                    'gender': 'M',
                }
            )
        elif user.role == 'doctor' and not hasattr(user, 'doctor_profile'):
            DoctorProfile.objects.get_or_create(
                user=user,
                defaults={
                    'specialization': 'General Practice',
                    'qualification': 'MBBS',
                    'experience_years': 0,
                    'license_number': f'SOCIAL-{user.id}',
                    'consultation_fee': 500.00,
                }
            )
            
        return user
