from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.views.generic import TemplateView, ListView, UpdateView
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.db import models
from datetime import datetime, timedelta
from .models import User, PatientProfile, DoctorProfile
from .forms import UserRegistrationForm, PatientProfileForm, DoctorProfileForm, UserUpdateForm
from appointments.models import Appointment
from prescriptions.models import Prescription
from billing.models import Bill
import os

def _google_login_enabled():
    google_client_id = os.getenv('GOOGLE_CLIENT_ID', '').strip()
    google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()
    if google_client_id and google_client_secret:
        return True

    try:
        from django.conf import settings
        from allauth.socialaccount.models import SocialApp

        return SocialApp.objects.filter(provider='google', sites__id=settings.SITE_ID).exists()
    except Exception:
        return False

def _ensure_google_social_app_from_env():
    """
    Ensure a SocialApp for Google exists in the database using credentials from .env.
    This provides a fallback in case settings-based configuration is not picked up.
    """
    google_client_id = os.getenv('GOOGLE_CLIENT_ID', '').strip()
    google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()

    if not google_client_id or not google_client_secret:
        return

    try:
        from allauth.socialaccount.models import SocialApp
        from django.contrib.sites.models import Site
        from django.conf import settings

        site = Site.objects.get(id=settings.SITE_ID)
        
        # Try to find existing app
        app = SocialApp.objects.filter(provider='google').first()
        
        if app:
            # Update existing app
            app.client_id = google_client_id
            app.secret = google_client_secret
            app.name = 'Google'
            app.save()
        else:
            # Create new app
            app = SocialApp.objects.create(
                provider='google',
                name='Google',
                client_id=google_client_id,
                secret=google_client_secret
            )
        
        # Ensure it's attached to the correct site
        if not app.sites.filter(id=settings.SITE_ID).exists():
            app.sites.add(site)
            
    except Exception as e:
        print(f"Error ensuring Google SocialApp: {e}")

def google_login_start_view(request):
    _ensure_google_social_app_from_env()

    if not _google_login_enabled():
        messages.error(
            request,
            'Google sign-in is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET, or create a Google SocialApp in Django Admin and attach it to the current Site.',
        )
        return redirect('accounts:login')

    return redirect(reverse('google_login'))

def logout_view(request):
    """Custom logout view that accepts both GET and POST requests"""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('home')

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['google_login_enabled'] = _google_login_enabled()
        return context

    def form_invalid(self, form):
        # Add debugging to see why login failed
        email = form.cleaned_data.get('username', '')
        password = form.cleaned_data.get('password', '')
        
        # Check if user exists
        from accounts.models import User
        try:
            user = User.objects.get(email=email)
            if not user.check_password(password):
                messages.error(self.request, 'Invalid password. Please try again.')
            else:
                messages.error(self.request, 'Authentication failed. Please check your credentials.')
        except User.DoesNotExist:
            messages.error(self.request, 'No account found with this email address.')
        
        return super().form_invalid(form)
    
    def get_success_url(self):
        user = self.request.user
        if user.is_admin:
            return reverse_lazy('accounts:admin_dashboard')
        elif user.is_doctor:
            return reverse_lazy('accounts:dashboard')
        elif user.is_patient:
            return reverse_lazy('accounts:patient_dashboard')
        else:
            return reverse_lazy('accounts:dashboard')

def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                
                # Create appropriate profile based on role
                if user.is_patient:
                    # Create profile with minimal required data
                    PatientProfile.objects.create(
                        user=user,
                        date_of_birth='2000-01-01',  # Default date
                        gender='M'  # Default gender
                    )
                elif user.is_doctor:
                    DoctorProfile.objects.create(
                        user=user,
                        specialization='General Practice',
                        qualification='MBBS',
                        experience_years=0,
                        license_number='TEMP-' + str(user.id),
                        consultation_fee=500.00
                    )
                elif user.is_admin:
                    # Admin users don't need additional profiles by default
                    # They can access admin features directly
                    pass
                
                login(request, user)
                messages.success(request, 'Registration successful! Welcome to SmartCare.')
                if user.is_patient:
                    return redirect('accounts:patient_dashboard')
                elif user.is_admin:
                    return redirect('accounts:admin_dashboard')
                else:
                    return redirect('accounts:dashboard')
            except Exception as e:
                messages.error(request, f'Registration failed: {str(e)}')
        else:
            # Display form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})

@login_required
def profile_view(request):
    user = request.user
    if user.is_patient:
        profile = getattr(user, 'patient_profile', None)
        form_class = PatientProfileForm
    elif user.is_doctor:
        profile = getattr(user, 'doctor_profile', None)
        form_class = DoctorProfileForm
    else:
        # For admin users, create a simple profile-like object
        profile = type('Profile', (), {
            'profile_image': getattr(user, 'profile_image', None)
        })()
        form_class = None
    
    context = {
        'user': user,
        'profile': profile,
        'form_class': form_class,
    }
    return render(request, 'accounts/profile.html', context)

@login_required
def profile_update_view(request):
    user = request.user
    user_form = UserUpdateForm(instance=user)
    profile_form = None

    if user.is_patient:
        try:
            profile = user.patient_profile
        except PatientProfile.DoesNotExist:
            profile = None
        profile_form = PatientProfileForm(instance=profile)
    elif user.is_doctor:
        try:
            profile = user.doctor_profile
        except DoctorProfile.DoesNotExist:
            profile = None
        profile_form = DoctorProfileForm(instance=profile)

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, request.FILES, instance=user)
        forms_valid = user_form.is_valid()

        if user.is_patient and profile_form:
            try:
                prof = user.patient_profile
            except PatientProfile.DoesNotExist:
                prof = None
            profile_form = PatientProfileForm(request.POST, instance=prof)
            forms_valid = forms_valid and profile_form.is_valid()
        elif user.is_doctor and profile_form:
            try:
                prof = user.doctor_profile
            except DoctorProfile.DoesNotExist:
                prof = None
            profile_form = DoctorProfileForm(request.POST, instance=prof)
            forms_valid = forms_valid and profile_form.is_valid()

        if forms_valid:
            user_form.save()
            if profile_form and profile_form.has_changed():
                profile = profile_form.save(commit=False)
                profile.user = user
                profile.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:dashboard')

    return render(request, 'accounts/profile_update.html', {'user_form': user_form, 'profile_form': profile_form})

class DashboardView(LoginRequiredMixin, TemplateView):
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        
        # Redirect patients to their specific dashboard
        if user.is_patient:
            return redirect('accounts:patient_dashboard')
        
        # Use the generic dashboard for doctors and admins
        self.template_name = 'accounts/dashboard.html'
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        from django.utils import timezone
        today = timezone.now().date()
        
        # Only process for doctors and admins (patients are redirected above)
        if user.is_doctor:
            # Get today's items only
            today_appointments = user.doctor_appointments.filter(date_time__date=today)
            today_prescriptions = user.prescriptions.filter(created_at__date=today)
            today_bills = user.doctor_bills.filter(created_at__date=today)
            
            context['appointments'] = today_appointments
            context['prescriptions'] = today_prescriptions
            
            # Get bills with payment information
            bills_with_payments = []
            for bill in today_bills:
                paid_amount = bill.get_paid_amount()
                remaining_balance = bill.get_remaining_balance()
                bills_with_payments.append({
                    'bill': bill,
                    'paid_amount': paid_amount,
                    'remaining_balance': remaining_balance,
                    'is_fully_paid': remaining_balance <= 0
                })
            context['bills_with_payments'] = bills_with_payments
            
            # Add today's statistics for doctors
            context['today_appointments_count'] = today_appointments.count()
            context['confirmed_appointments_count'] = today_appointments.filter(status='confirmed').count()
            context['pending_appointments_count'] = today_appointments.filter(status='pending').count()
            
            # Add today's billing statistics
            context['today_bills_count'] = today_bills.count()
            context['today_paid_bills_count'] = today_bills.filter(status='paid').count()
            
            # Calculate today's paid amount
            today_paid_amount = 0
            paid_bills = today_bills.filter(status='paid')
            for bill in paid_bills:
                today_paid_amount += bill.total_amount
            context['today_paid_amount'] = today_paid_amount
            
            # Add available doctors (excluding current user)
            context['available_doctors'] = User.objects.filter(role='doctor').exclude(id=user.id).select_related('doctor_profile')[:5]
            
        elif user.is_admin:
            context['total_users'] = User.objects.count()
            context['total_patients'] = User.objects.filter(role='patient').count()
            context['total_doctors'] = User.objects.filter(role='doctor').count()
            context['today_appointments'] = user.patient_appointments.filter(date_time__date=today)
        
        return context

@login_required
def dashboard_view(request):
    user = request.user
    
    # Debug: Print user role information
    print(f"DashboardView - User: {user.email}, Role: {user.role}, is_admin: {user.is_admin}")
    
    # Redirect admin to admin dashboard
    if user.is_admin:
        print(f"Redirecting admin {user.email} to admin dashboard")
        return redirect('accounts:admin_dashboard')
    
    # Redirect patients to their specific dashboard
    if user.is_patient:
        print(f"Redirecting patient {user.email} to patient dashboard")
        return redirect('accounts:patient_dashboard')
    
    # Use the generic dashboard for doctors
    print(f"Showing doctor dashboard for {user.email}")
    
    # Get dashboard context for doctors
    context = {}
    try:
        # Get today's appointments for the dashboard
        from datetime import date
        today = date.today()
        today_appointments = Appointment.objects.filter(
            doctor=user,
            date_time__date=today
        ).order_by('date_time')
        context['appointments'] = today_appointments
        
        # Get recent appointments for sidebar
        recent_appointments = Appointment.objects.filter(
            doctor=user
        ).order_by('-date_time')[:5]
        context['recent_appointments'] = recent_appointments
        
        # Get recent prescriptions
        recent_prescriptions = Prescription.objects.filter(
            doctor=user
        ).order_by('-created_at')[:5]
        context['recent_prescriptions'] = recent_prescriptions
        
        # Get statistics
        total_appointments = Appointment.objects.filter(doctor=user).count()
        total_prescriptions = Prescription.objects.filter(doctor=user).count()
        today_appointments_count = Appointment.objects.filter(
            doctor=user,
            date_time__date=today
        ).count()
        
        context['total_appointments'] = total_appointments
        context['total_prescriptions'] = total_prescriptions
        context['today_appointments'] = today_appointments_count
        
    except Exception as e:
        print(f"Error getting dashboard data: {e}")
    
    return render(request, 'accounts/dashboard.html', context)

@login_required
def patient_dashboard_view(request):
    if not request.user.is_patient:
        messages.error(request, 'Access denied. This page is for patients only.')
        return redirect('accounts:dashboard')
    
    # Get upcoming appointments
    now = timezone.now()
    upcoming_appointments = Appointment.objects.filter(
        patient=request.user,
        date_time__gt=now,
        status__in=['pending', 'confirmed']
    ).select_related('doctor', 'doctor__doctor_profile').order_by('date_time')[:5]
    
    # Get available doctors
    available_doctors = User.objects.filter(
        role='doctor',
        is_active=True
    ).select_related('doctor_profile').order_by('doctor_profile__specialization')[:6]
    
    # Get recent prescriptions
    recent_prescriptions = Prescription.objects.filter(
        patient=request.user
    ).select_related('doctor').order_by('-created_at')[:3]
    
    # Get patient profile
    try:
        profile = request.user.patient_profile
    except:
        profile = None
    
    # Calculate statistics
    total_appointments = Appointment.objects.filter(patient=request.user).count()
    completed_appointments = Appointment.objects.filter(patient=request.user, status='completed').count()
    pending_appointments = Appointment.objects.filter(patient=request.user, status='pending').count()
    confirmed_appointments = Appointment.objects.filter(patient=request.user, status='confirmed').count()
    cancelled_appointments = Appointment.objects.filter(patient=request.user, status='cancelled').count()
    total_prescriptions = Prescription.objects.filter(patient=request.user).count()
    
    context = {
        'upcoming_appointments': upcoming_appointments,
        'available_doctors': available_doctors,
        'recent_prescriptions': recent_prescriptions,
        'profile': profile,
        'total_appointments': total_appointments,
        'completed_appointments': completed_appointments,
        'pending_appointments': pending_appointments,
        'confirmed_appointments': confirmed_appointments,
        'cancelled_appointments': cancelled_appointments,
        'total_prescriptions': total_prescriptions,
    }
    
    return render(request, 'accounts/patient_dashboard.html', context)

@login_required
def admin_dashboard_view(request):
    """Professional admin dashboard view."""
    if not request.user.is_admin:
        messages.error(request, 'Access denied! Admin access required.')
        return redirect('accounts:dashboard')

    # Core counts
    total_users = User.objects.count()
    total_doctors = User.objects.filter(role='doctor').count()
    total_patients = User.objects.filter(role='patient').count()

    # Revenue from billing (fallback to 0 on error)
    try:
        from billing.models import Bill
        total_revenue = Bill.objects.filter(status='paid').aggregate(
            total=Sum('total_amount')
        )['total'] or 0
    except Exception:
        total_revenue = 0

    context = {
        'total_users': total_users,
        'total_doctors': total_doctors,
        'total_patients': total_patients,
        'total_revenue': total_revenue,
        'system_health': 'Healthy',
        'server_uptime': '99.9%',
        'user': request.user,
    }

    return render(request, 'accounts/admin_dashboard_professional.html', context)

@login_required
def admin_add_user_view(request):
    """Admin view to add new users (patient, doctor, admin)"""
    if not request.user.is_admin:
        messages.error(request, 'Access denied! Admin access required.')
        return redirect('accounts:admin_dashboard')
    
    form = UserRegistrationForm()
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                
                # Create appropriate profile based on role
                if user.is_patient:
                    PatientProfile.objects.create(
                        user=user,
                        date_of_birth='2000-01-01',  # Default date
                        gender='M'  # Default gender
                    )
                    messages.success(request, f'Patient {user.get_full_name()} created successfully!')
                    
                elif user.is_doctor:
                    DoctorProfile.objects.create(
                        user=user,
                        specialization='General Practice',
                        qualification='MBBS',
                        experience_years=0,
                        license_number='TEMP-' + str(user.id),
                        consultation_fee=500.00
                    )
                    messages.success(request, f'Dr. {user.get_full_name()} created successfully!')
                    
                elif user.is_admin:
                    # Admin users don't need additional profiles by default
                    messages.success(request, f'Admin {user.get_full_name()} created successfully!')
                
                return redirect('accounts:admin_users')
                
            except Exception as e:
                messages.error(request, f'Error creating user: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    
    return render(request, 'accounts/admin_add_user.html', {'form': form})

@login_required
def admin_users_view(request):
    if not request.user.is_admin:
        messages.error(request, 'Access denied!')
        return redirect('accounts:dashboard')
    
    users = User.objects.all()
    return render(request, 'accounts/admin_users_new.html', {'users': users})

@login_required
def admin_dashboard_users_view(request):
    """Dashboard users page with notification counts"""
    if not request.user.is_admin:
        messages.error(request, 'Access denied!')
        return redirect('accounts:dashboard')
    
    from notifications.models import Notification
    
    # Get all users with their notification counts
    users = User.objects.all()
    
    # Add notification count to each user
    for user in users:
        user.unread_notifications = Notification.objects.filter(
            recipient=user, 
            is_read=False
        ).count()
    
    context = {
        'users': users,
    }
    
    return render(request, 'accounts/admin_dashboard_users.html', context)

@login_required
def user_details_view(request, user_id):
    """View detailed information about a specific user"""
    if not request.user.is_admin:
        messages.error(request, 'Access denied!')
        return redirect('accounts:dashboard')
    
    try:
        user = get_object_or_404(User, id=user_id)
        
        # Get additional context data
        context = {
            'user': user,
        }
        
        # Add role-specific statistics and data
        if user.role == 'doctor':
            # Get doctor's appointments where they are the doctor
            context['total_appointments'] = Appointment.objects.filter(doctor=user).count()
            context['total_prescriptions'] = Prescription.objects.filter(doctor=user).count()
            context['total_patients'] = Appointment.objects.filter(doctor=user).values('patient').distinct().count()
            
        elif user.role == 'patient':
            # Get patient's appointments where they are the patient
            context['total_appointments'] = Appointment.objects.filter(patient=user).count()
            context['total_prescriptions'] = Prescription.objects.filter(patient=user).count()
            context['total_bills'] = Bill.objects.filter(patient=user).count()
            
            # Get medical records and lab reports for patient
            try:
                context['total_medical_records'] = user.medical_records_as_patient.count()
            except:
                context['total_medical_records'] = 0
            try:
                context['total_lab_reports'] = user.lab_reports.count()
            except:
                context['total_lab_reports'] = 0
            
            # Calculate total billing amount
            billing_data = Bill.objects.filter(patient=user).aggregate(
                total=Sum('total_amount'),
                paid=Sum('total_amount', filter=Q(status='paid'))
            )
            context['total_billing_amount'] = billing_data['total'] or 0
            context['paid_amount'] = billing_data['paid'] or 0
            context['pending_amount'] = context['total_billing_amount'] - context['paid_amount']
            
        else:  # admin user
            context['total_users_managed'] = User.objects.count() - 1  # exclude self
            context['total_appointments_system'] = Appointment.objects.count()
            context['total_prescriptions_system'] = Prescription.objects.count()
            context['total_bills_system'] = Bill.objects.count()
            
            # Get system statistics
            today = timezone.now().date()
            context['today_appointments'] = Appointment.objects.filter(date_time__date=today).count()
            context['active_users'] = User.objects.filter(is_active=True).count()
            context['total_patients_system'] = User.objects.filter(role='patient').count()
            context['total_doctors_system'] = User.objects.filter(role='doctor').count()
        
        # Calculate account age and activity
        context['account_age_days'] = (timezone.now().date() - user.date_joined.date()).days
        context['days_since_last_login'] = (timezone.now() - user.last_login).days if user.last_login else None
        
        # Check if it's an AJAX request to return a partial
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            context['is_modal'] = True
            return render(request, 'accounts/user_details_partial.html', context)
            
        return render(request, 'accounts/user_details.html', context)
        
    except Exception as e:
        import traceback
        error_message = f'Error retrieving user details: {str(e)}'
        print(f"DEBUG: {error_message}")
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        messages.error(request, error_message)
        return redirect('accounts:admin_dashboard_users')

@login_required
def export_users_csv(request):
    """Export all users and their details to CSV"""
    if not request.user.is_admin:
        messages.error(request, 'Access denied!')
        return redirect('accounts:dashboard')
    
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="users_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Email', 'Full Name', 'Role', 'Phone', 'Is Active', 
        'Date Joined', 'Last Login', 'Specialization (Doctor)', 
        'License (Doctor)', 'Gender (Patient)', 'DOB (Patient)'
    ])
    
    users = User.objects.all().select_related('doctor_profile', 'patient_profile')
    for u in users:
        doctor_spec = u.doctor_profile.specialization if u.role == 'doctor' and hasattr(u, 'doctor_profile') else ''
        doctor_license = u.doctor_profile.license_number if u.role == 'doctor' and hasattr(u, 'doctor_profile') else ''
        patient_gender = u.patient_profile.get_gender_display() if u.role == 'patient' and hasattr(u, 'patient_profile') else ''
        patient_dob = u.patient_profile.date_of_birth if u.role == 'patient' and hasattr(u, 'patient_profile') else ''
        
        writer.writerow([
            u.id, u.email, u.get_full_name(), u.get_role_display(), u.phone,
            'Yes' if u.is_active else 'No',
            u.date_joined.strftime('%Y-%m-%d %H:%M'),
            u.last_login.strftime('%Y-%m-%d %H:%M') if u.last_login else 'Never',
            doctor_spec, doctor_license, patient_gender, patient_dob
        ])
    
    return response

@login_required
def toggle_user_status(request, user_id):
    if not request.user.is_admin:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active
    user.save()
    
    return JsonResponse({
        'success': True,
        'is_active': user.is_active,
        'message': f'User {"activated" if user.is_active else "deactivated"} successfully'
    })

@login_required
def delete_user(request, user_id):
    """Delete user functionality for admins"""
    if not request.user.is_admin:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method == 'POST':
        try:
            user = get_object_or_404(User, id=user_id)
            
            # Prevent admin from deleting themselves
            if user.id == request.user.id:
                return JsonResponse({'error': 'Cannot delete your own account'}, status=400)
            
            user_name = user.get_full_name() or user.email
            
            # Delete user and related profiles
            user.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'User {user_name} deleted successfully'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)
