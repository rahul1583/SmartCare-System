from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import TemplateView, ListView, UpdateView
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.db import models, transaction
from datetime import datetime, timedelta
from django.conf import settings
import logging
import random
import string
import os
from .models import User, PatientProfile, DoctorProfile, PasswordResetOTP
from .email_helpers import delivery_error_user_message, send_password_reset_otp_email
from notifications.models import Notification

logger = logging.getLogger(__name__)

def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

def forgot_password_otp_view(request):
    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip().lower()
        try:
            user = User.objects.get(email__iexact=email)
            otp_code = generate_otp()
            PasswordResetOTP.objects.create(user=user, otp=otp_code)

            subject = 'Password Reset OTP - SmartCare System'
            message = f'Your OTP for password reset is: {otp_code}. It is valid for 10 minutes.'

            try:
                send_password_reset_otp_email(email, subject, message)
            except Exception as exc:
                logger.exception('Password reset OTP email failed for %s', email)
                if (
                    settings.DEBUG
                    and getattr(settings, 'EMAIL_DEV_OTP_FALLBACK', True)
                ):
                    request.session['reset_email'] = email
                    request.session['dev_otp_display'] = otp_code
                    messages.success(
                        request,
                        'Use the verification code shown on the next page to continue.',
                    )
                    messages.warning(
                        request,
                        'Email could not be sent. Showing the code for local development only — '
                        'add RESEND_API_KEY to .env or fix Gmail App Password for real email.',
                    )
                    return redirect('accounts:verify_otp')
                PasswordResetOTP.objects.filter(user=user, otp=otp_code).delete()
                messages.error(request, delivery_error_user_message(exc))
                return render(request, 'accounts/password_reset_otp.html')

            request.session['reset_email'] = email
            request.session.pop('dev_otp_display', None)
            messages.success(request, 'OTP has been sent to your email.')
            if 'console' in (settings.EMAIL_BACKEND or '') and not getattr(
                settings, 'RESEND_API_KEY', ''
            ):
                messages.info(
                    request,
                    'Development mode: the message was printed to the server console, not sent to a real inbox.',
                )
            return redirect('accounts:verify_otp')
        except User.DoesNotExist:
            messages.error(request, 'No account found with this email address.')

    return render(request, 'accounts/password_reset_otp.html')

def verify_otp_view(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('accounts:forgot_password_otp')
        
    if request.method == 'POST':
        otp_entered = request.POST.get('otp', '')
        try:
            user = User.objects.get(email__iexact=email)
            otp_record = PasswordResetOTP.objects.filter(user=user, otp=otp_entered).last()
            
            if otp_record and otp_record.is_valid():
                otp_record.is_verified = True
                otp_record.save()
                request.session['otp_verified'] = True
                request.session.pop('dev_otp_display', None)
                return redirect('accounts:reset_password_otp')
            else:
                messages.error(request, 'Invalid or expired OTP.')
        except User.DoesNotExist:
            return redirect('accounts:forgot_password_otp')
            
    ctx = {'email': email}
    if settings.DEBUG and request.session.get('dev_otp_display'):
        ctx['dev_otp_code'] = request.session.get('dev_otp_display')
    return render(request, 'accounts/verify_otp.html', ctx)

def reset_password_otp_view(request):
    email = request.session.get('reset_email')
    is_verified = request.session.get('otp_verified')
    
    if not email or not is_verified:
        return redirect('accounts:forgot_password_otp')
        
    if request.method == 'POST':
        password = request.POST.get('password1', '')
        password_confirm = request.POST.get('password2', '')
        
        if password == password_confirm:
            if len(password) >= 8:
                try:
                    user = User.objects.get(email__iexact=email)
                    user.set_password(password)
                    user.save()
                    
                    # Clear session
                    del request.session['reset_email']
                    del request.session['otp_verified']
                    
                    messages.success(request, 'Password reset successful. You can now log in.')
                    return redirect('accounts:login')
                except User.DoesNotExist:
                    return redirect('accounts:forgot_password_otp')
            else:
                messages.error(request, 'Password must be at least 8 characters long.')
        else:
            messages.error(request, 'Passwords do not match.')
            
    return render(request, 'accounts/reset_password_otp.html')
from .forms import UserRegistrationForm, PatientProfileForm, DoctorProfileForm, UserUpdateForm
from appointments.models import Appointment
from prescriptions.models import Prescription
from billing.models import Bill

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

class CustomLoginView(SuccessMessageMixin, LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def get_success_message(self, cleaned_data):
        user = self.request.user
        if user.is_admin:
            return "Admin login successfully"
        elif user.is_doctor:
            return "Doctor login successfully"
        elif user.is_patient:
            return "Patient login successfully"
        return "User login successfully"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['google_login_enabled'] = _google_login_enabled()
        return context

    def form_invalid(self, form):
        # Get credentials from POST data directly as cleaned_data might be incomplete on failure
        email = self.request.POST.get('username', '')
        password = self.request.POST.get('password', '')
        
        # Check if user exists (case-insensitive)
        from accounts.models import User
        try:
            user = User.objects.get(email__iexact=email)
            if not user.check_password(password):
                messages.error(self.request, 'Wrong password. Please try again.')
            else:
                messages.error(self.request, 'Authentication failed. Please check your credentials.')
        except User.DoesNotExist:
            messages.error(self.request, 'No account found with this email address.')
        
        return super().form_invalid(form)
    
    def form_valid(self, form):
        remember_me = self.request.POST.get('remember_me')
        if not remember_me:
            # Session expires on browser close
            self.request.session.set_expiry(0)
        else:
            # Session expires in 2 weeks (default)
            self.request.session.set_expiry(1209600)
        return super().form_valid(form)

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

from functools import wraps
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib.auth import login as auth_login

def ajax_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
               'application/json' in request.headers.get('Accept', ''):
                return JsonResponse({'error': 'Session expired. Please log in again.'}, status=401)
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
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
                        # Get uploaded certificate
                        doctor_certificate = form.cleaned_data.get('doctor_certificate')
                        
                        DoctorProfile.objects.create(
                            user=user,
                            specialization='General Practice',
                            qualification='MBBS',
                            experience_years=0,
                            license_number='TEMP-' + str(user.id),
                            consultation_fee=500.00,
                            doctor_certificate=doctor_certificate,
                            is_approved=False
                        )
                    elif user.is_admin:
                        # Admin users don't need additional profiles by default
                        # They can access admin features directly
                        pass
                
                # Specify the backend when multiple are configured
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
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
    user_form = UserUpdateForm(instance=user)
    profile_form = None
    profile = None
    has_errors = False

    if user.is_patient:
        profile, created = PatientProfile.objects.get_or_create(
            user=user,
            defaults={
                'date_of_birth': '2000-01-01',
                'gender': 'M'
            }
        )
        profile_form = PatientProfileForm(instance=profile)
    elif user.is_doctor:
        profile, created = DoctorProfile.objects.get_or_create(
            user=user,
            defaults={
                'specialization': 'General Practice',
                'qualification': 'MBBS',
                'experience_years': 0,
                'license_number': f'TEMP-{user.id}',
                'consultation_fee': 500.00
            }
        )
        profile_form = DoctorProfileForm(instance=profile)

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, request.FILES, instance=user)
        forms_valid = user_form.is_valid()

        if user.is_patient:
            profile_form = PatientProfileForm(request.POST, instance=profile)
            forms_valid = forms_valid and profile_form.is_valid()
        elif user.is_doctor:
            profile_form = DoctorProfileForm(request.POST, instance=profile)
            forms_valid = forms_valid and profile_form.is_valid()

        if forms_valid:
            user_form.save()
            if profile_form:
                profile_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
        else:
            has_errors = True
            messages.error(request, 'Please correct the errors below.')

    context = {
        'user': user,
        'profile': profile,
        'user_form': user_form,
        'profile_form': profile_form,
        'has_errors': has_errors,
    }
    return render(request, 'accounts/profile.html', context)

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

    if user.is_admin:
        return redirect('accounts:admin_dashboard')

    if user.is_patient:
        return redirect('accounts:patient_dashboard')

    context = {}
    try:
        from datetime import date

        today = date.today()
        today_appointments = (
            Appointment.objects.filter(doctor=user, date_time__date=today)
            .select_related('patient')
            .order_by('date_time')
        )
        context['appointments'] = today_appointments

        today_appt_qs = Appointment.objects.filter(doctor=user, date_time__date=today)
        context['today_appointments_count'] = today_appt_qs.count()
        context['confirmed_appointments_count'] = today_appt_qs.filter(status='confirmed').count()
        context['pending_appointments_count'] = today_appt_qs.filter(status='pending').count()

        # Filter today's prescriptions only
        today_prescriptions = (
            Prescription.objects.filter(doctor=user, created_at__date=today)
            .select_related('patient')
            .prefetch_related('medications')
            .order_by('-created_at')
        )
        context['prescriptions'] = today_prescriptions

        # Filter today's bills only
        today_bill_qs = (
            Bill.objects.filter(doctor=user, created_at__date=today)
            .select_related('patient')
            .order_by('-created_at')
        )
        bills_with_payments = []
        for bill in today_bill_qs:
            paid = bill.get_paid_amount()
            remaining = bill.get_remaining_balance()
            bills_with_payments.append(
                {
                    'bill': bill,
                    'paid_amount': paid,
                    'remaining_balance': remaining,
                    'is_fully_paid': remaining <= 0,
                }
            )
        context['bills_with_payments'] = bills_with_payments

        context['total_appointments'] = Appointment.objects.filter(doctor=user).count()
        context['total_prescriptions'] = Prescription.objects.filter(doctor=user).count()

    except Exception:
        context.setdefault('appointments', Appointment.objects.none())
        context.setdefault('prescriptions', Prescription.objects.none())
        context.setdefault('bills_with_payments', [])
        context.setdefault('today_appointments_count', 0)
        context.setdefault('confirmed_appointments_count', 0)
        context.setdefault('pending_appointments_count', 0)

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
        is_active=True,
        doctor_profile__is_approved=True
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

    context = _get_admin_dashboard_context()
    context['user'] = request.user
    return render(request, 'accounts/admin_dashboard_professional.html', context)


def _get_admin_dashboard_context():
    """Collect reusable admin dashboard metrics for template and API."""
    # Core counts
    total_users = User.objects.count()
    total_doctors = User.objects.filter(role='doctor').count()
    total_patients = User.objects.filter(role='patient').count()
    total_prescriptions = Prescription.objects.count()

    # Revenue from billing (fallback to 0 on error)
    bills_with_payments = []
    recent_appointments = []
    appointments_today_count = 0
    paid_transactions_today_count = 0
    monthly_appointments_count = 0
    monthly_revenue = 0
    
    try:
        from billing.models import Bill
        from appointments.models import Appointment
        from django.db.models.functions import TruncMonth
        
        today = timezone.now().date()
        first_day_of_month = today.replace(day=1)
        
        total_revenue = Bill.objects.filter(status='paid').aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        # Monthly stats
        monthly_revenue = Bill.objects.filter(
            created_at__date__gte=first_day_of_month,
            status='paid'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        monthly_appointments_count = Appointment.objects.filter(
            date_time__date__gte=first_day_of_month
        ).count()
        
        # Get today's bills
        recent_bills = Bill.objects.filter(created_at__date=today).order_by('-created_at')[:5]
        paid_transactions_today_count = Bill.objects.filter(
            created_at__date=today, status='paid'
        ).count()
        for bill in recent_bills:
            remaining = bill.get_remaining_balance()
            bills_with_payments.append({
                'bill': bill,
                'is_fully_paid': remaining <= 0
            })
            
        # Get today's appointments
        recent_appointments = Appointment.objects.filter(
            date_time__date=today
        ).order_by('-date_time')[:5]
        appointments_today_count = Appointment.objects.filter(date_time__date=today).count()
        
        # Yearly trend data (last 6 months)
        six_months_ago = today - timedelta(days=180)
        revenue_trend = Bill.objects.filter(
            created_at__date__gte=six_months_ago,
            status='paid'
        ).annotate(month=TruncMonth('created_at')).values('month').annotate(
            total=Sum('total_amount')
        ).order_by('month')
        
        appointment_trend = Appointment.objects.filter(
            date_time__date__gte=six_months_ago
        ).annotate(month=TruncMonth('date_time')).values('month').annotate(
            total=Count('id')
        ).order_by('month')
        
    except Exception:
        total_revenue = 0
        revenue_trend = []
        appointment_trend = []

    # Get pending doctors
    pending_doctors = DoctorProfile.objects.filter(is_approved=False).select_related('user')

    context = {
        'total_users': total_users,
        'total_doctors': total_doctors,
        'total_patients': total_patients,
        'total_prescriptions': total_prescriptions,
        'total_revenue': total_revenue,
        'monthly_revenue': monthly_revenue,
        'monthly_appointments_count': monthly_appointments_count,
        'system_health': 'Healthy',
        'server_uptime': '99.9%',
        'pending_doctors': pending_doctors,
        'recent_appointments': recent_appointments,
        'bills_with_payments': bills_with_payments,
        'appointments_today_count': appointments_today_count,
        'paid_transactions_today_count': paid_transactions_today_count,
        'pending_doctors_count': pending_doctors.count(),
        'revenue_trend': list(revenue_trend) if hasattr(revenue_trend, '__iter__') else [],
        'appointment_trend': list(appointment_trend) if hasattr(appointment_trend, '__iter__') else [],
    }

    return context


@login_required
def admin_dashboard_live_data_view(request):
    """Return live dashboard data for periodic client-side refresh."""
    if not request.user.is_admin:
        return JsonResponse({'error': 'Access denied'}, status=403)

    context = _get_admin_dashboard_context()

    appointments_payload = []
    for appt in context['recent_appointments'][:4]:
        appointments_payload.append({
            'patient_initial': (appt.patient.username or 'U')[:1].upper(),
            'patient_name': appt.patient.get_full_name() or appt.patient.username,
            'doctor_name': appt.doctor.get_full_name() or appt.doctor.username,
            'time': appt.date_time.strftime('%I:%M %p').lstrip('0'),
            'status': appt.status,
        })

    transactions_payload = []
    for bill_data in context['bills_with_payments'][:4]:
        bill = bill_data['bill']
        transactions_payload.append({
            'id': bill.id,
            'patient_name': bill.patient.get_full_name() or bill.patient.username,
            'total_amount': str(bill.total_amount),
            'is_fully_paid': bill_data['is_fully_paid'],
        })

    return JsonResponse({
        'stats': {
            'total_users': context['total_users'],
            'total_doctors': context['total_doctors'],
            'total_patients': context['total_patients'],
            'total_prescriptions': context['total_prescriptions'],
            'total_revenue': str(context['total_revenue']),
            'pending_doctors_count': context['pending_doctors_count'],
            'appointments_today_count': context['appointments_today_count'],
            'paid_transactions_today_count': context['paid_transactions_today_count'],
        },
        'recent_appointments': appointments_payload,
        'recent_transactions': transactions_payload,
        'timestamp': timezone.now().strftime('%I:%M:%S %p').lstrip('0'),
    })

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
    
    role_filter = request.GET.get('role', 'all')
    
    if role_filter == 'all':
        users_list = User.objects.all().order_by('-date_joined')
    else:
        users_list = User.objects.filter(role=role_filter).order_by('-date_joined')
    
    paginator = Paginator(users_list, 5)  # Show 5 users per page
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)
        
    return render(request, 'accounts/admin_users.html', {'users': users, 'role_filter': role_filter})

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

def csrf_failure_view(request, reason=""):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
       'application/json' in request.headers.get('Accept', ''):
        return JsonResponse({
            'success': False,
            'error': f'CSRF verification failed: {reason}. Please refresh the page.'
        }, status=403)
    
    # Fallback to default behavior for non-AJAX
    from django.views.csrf import csrf_failure
    return csrf_failure(request, reason)

@ajax_login_required
def toggle_user_status(request, user_id):
    if not request.user.is_admin:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
            
        user.is_active = not user.is_active
        user.save()
        
        return JsonResponse({
            'success': True,
            'is_active': user.is_active,
            'message': f'User {"activated" if user.is_active else "deactivated"} successfully'
        })
    except Exception as e:
        logger.exception("Error in toggle_user_status")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@ajax_login_required
def delete_user(request, user_id):
    """Delete user functionality for admins"""
    if not request.user.is_admin:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method == 'POST':
        try:
            user = User.objects.filter(id=user_id).first()
            if not user:
                return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
            
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
            logger.exception("Error in delete_user")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def pending_doctors_view(request):
    """View list of doctors awaiting approval"""
    if not request.user.is_admin:
        messages.error(request, 'Access denied!')
        return redirect('accounts:dashboard')
    
    pending_doctors = DoctorProfile.objects.filter(is_approved=False).select_related('user')
    return render(request, 'accounts/pending_doctors.html', {'pending_doctors': pending_doctors})

@ajax_login_required
def approve_doctor_view(request, doctor_id):
    """Approve a doctor's registration"""
    if not request.user.is_admin:
        return JsonResponse({'error': 'Access denied'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    try:
        doctor_profile = DoctorProfile.objects.filter(id=doctor_id).first()
        if not doctor_profile:
            return JsonResponse({'success': False, 'error': 'Doctor profile not found'}, status=404)
            
        doctor_profile.is_approved = True
        doctor_profile.save()
        
        # Optionally notify the doctor here
        
        return JsonResponse({
            'success': True,
            'message': f'Dr. {doctor_profile.user.get_full_name()} approved successfully'
        })
    except Exception as e:
        logger.exception("Error in approve_doctor_view")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@ajax_login_required
def reject_doctor_view(request, doctor_id):
    """Reject and remove a doctor's registration"""
    if not request.user.is_admin:
        return JsonResponse({'error': 'Access denied'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    try:
        doctor_profile = DoctorProfile.objects.filter(id=doctor_id).first()
        if not doctor_profile:
            return JsonResponse({'success': False, 'error': 'Doctor profile not found'}, status=404)
            
        user = doctor_profile.user
        user_name = user.get_full_name()
        
        # Delete the user (this will also delete the doctor profile via CASCADE)
        user.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Registration for Dr. {user_name} rejected and removed'
        })
    except Exception as e:
        logger.exception("Error in reject_doctor_view")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """Professional password change view with notification"""
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:password_change_done')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Create notification for the user
        Notification.create_notification(
            recipient=self.request.user,
            notification_type='password_changed',
            title='Password Changed Successfully',
            message='Your account password has been updated successfully. If you did not perform this action, please contact support immediately.',
            priority='high'
        )
        
        messages.success(self.request, 'Your password has been updated successfully!')
        return response
