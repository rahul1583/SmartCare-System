from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count
import json
from .models import Appointment, DoctorAvailability
from .forms import AppointmentBookingForm, DoctorAppointmentBookingForm
from .utils import cancel_expired_pending_appointments
from accounts.models import User

@login_required
def easy_appointments_view(request):
    # Automatically cancel expired pending appointments
    cancel_expired_pending_appointments()
    
    # Get user's appointments for statistics
    if request.user.is_patient:
        user_appointments = Appointment.objects.filter(patient=request.user)
    elif request.user.is_doctor:
        user_appointments = Appointment.objects.filter(doctor=request.user)
    else:
        user_appointments = Appointment.objects.all()
    
    # Calculate statistics
    today = timezone.now().date()
    today_appointments = user_appointments.filter(date_time__date=today).count()
    upcoming_appointments = user_appointments.filter(
        date_time__date__gt=today,
        status__in=['pending', 'confirmed']
    ).count()
    pending_appointments = user_appointments.filter(status='pending').count()
    
    # Get available doctors
    available_doctors = User.objects.filter(role='doctor', is_active=True).count()
    
    doctors_list = User.objects.filter(role='doctor', is_active=True)
    
    # Get today's appointments list
    today_appointments_list = user_appointments.filter(date_time__date=today).order_by('date_time')
    
    # Prepare appointments data for calendar (JSON format)
    appointments_data = []
    for apt in user_appointments.filter(date_time__year=today.year, date_time__month=today.month):
        appointments_data.append({
            'date': apt.date_time.strftime('%Y-%m-%d'),
            'time': apt.date_time.strftime('%H:%M'),
            'doctor': apt.doctor.get_full_name() or apt.doctor.email,
            'status': apt.status
        })
    
    context = {
        'today_appointments': today_appointments,
        'upcoming_appointments': upcoming_appointments,
        'pending_appointments': pending_appointments,
        'available_doctors': available_doctors,
        'doctors': doctors_list,
        'today_appointments_list': today_appointments_list,
        'appointments_json': json.dumps(appointments_data),
    }
    
    return render(request, 'appointments/easy_appointments.html', context)

# Placeholder views - to be implemented
@login_required
def appointment_list_view(request):
    # Automatically cancel expired pending appointments
    cancel_expired_pending_appointments()
    
    # Get user's appointments
    if request.user.is_patient:
        appointments = Appointment.objects.filter(patient=request.user).order_by('-date_time')
    elif request.user.is_doctor:
        appointments = Appointment.objects.filter(doctor=request.user).order_by('-date_time')
    else:
        # Admin can see all appointments
        appointments = Appointment.objects.all().order_by('-date_time')
    
    return render(request, 'appointments/appointment_list.html', {'appointments': appointments})

@login_required
def book_appointment_view(request):
    if request.method == 'POST':
        if request.user.is_doctor:
            form = DoctorAppointmentBookingForm(request.POST)
            if form.is_valid():
                try:
                    appointment = form.save(commit=False)
                    appointment.doctor = request.user
                    appointment.status = 'pending'
                    appointment.save()
                    
                    messages.success(request, 'Appointment booked successfully! Your appointment is scheduled and pending confirmation.')
                    return redirect('appointments:appointment_list')
                except Exception as e:
                    messages.error(request, f'Failed to book appointment: {str(e)}')
            else:
                # Display form errors
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
        else:
            form = AppointmentBookingForm(request.POST, user=request.user)
            if form.is_valid():
                try:
                    appointment = form.save(commit=False)
                    # Set patient based on user role
                    if request.user.is_patient:
                        appointment.patient = request.user
                        # Ensure patient_name is set from form data
                        if not appointment.patient_name:
                            appointment.patient_name = request.user.get_full_name() or request.user.username
                    else:
                        messages.error(request, 'You do not have permission to book appointments.')
                        return redirect('accounts:dashboard')
                    
                    appointment.status = 'pending'
                    appointment.save()
                    
                    messages.success(request, 'Appointment booked successfully! Your appointment is scheduled and pending confirmation.')
                    return redirect('appointments:appointment_list')
                except Exception as e:
                    messages.error(request, f'Failed to book appointment: {str(e)}')
            else:
                # Display form errors
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
    else:
        if request.user.is_doctor:
            form = DoctorAppointmentBookingForm()
        else:
            form = AppointmentBookingForm(user=request.user)
    
    return render(request, 'appointments/book_appointment.html', {'form': form})

@login_required
def appointment_detail_view(request, appointment_id):
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        
        # Check if user has permission to view this appointment
        if request.user.is_patient and appointment.patient != request.user:
            messages.error(request, 'You can only view your own appointments.')
            return redirect('appointments:appointment_list')
        elif request.user.is_doctor and appointment.doctor != request.user:
            messages.error(request, 'You can only view appointments assigned to you.')
            return redirect('appointments:appointment_list')
        
        return render(request, 'appointments/appointment_detail.html', {'appointment': appointment})
    except Appointment.DoesNotExist:
        messages.error(request, 'Appointment not found.')
        return redirect('appointments:appointment_list')

@login_required
def complete_appointment_view(request, appointment_id):
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        
        # Only doctors can complete appointments
        if not request.user.is_doctor:
            messages.error(request, 'Only doctors can complete appointments.')
            return redirect('appointments:appointment_list')
        
        # Check if appointment is assigned to this doctor
        if appointment.doctor != request.user:
            messages.error(request, 'You can only complete appointments assigned to you.')
            return redirect('appointments:appointment_list')
        
        # Check if appointment can be completed
        if appointment.status != 'confirmed':
            if appointment.status == 'completed':
                messages.info(request, 'This appointment has already been completed.')
            elif appointment.status == 'pending':
                messages.error(request, 'Please approve this appointment before marking it as complete.')
            elif appointment.status == 'cancelled':
                messages.error(request, 'Cannot complete a cancelled appointment.')
            else:
                messages.error(request, 'Cannot complete this appointment in its current status.')
            return redirect('appointments:appointment_detail', appointment_id=appointment.id)
        
        # Complete the appointment
        appointment.status = 'completed'
        appointment.save()
        
        messages.success(request, f'Appointment with {appointment.patient.get_full_name() or appointment.patient.email} has been marked as completed!')
        return redirect('accounts:dashboard')
        
    except Appointment.DoesNotExist:
        messages.error(request, 'Appointment not found.')
        return redirect('appointments:appointment_list')

@login_required
def approve_appointment_view(request, appointment_id):
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        
        # Only doctors can approve appointments
        if not request.user.is_doctor:
            messages.error(request, 'Only doctors can approve appointments.')
            return redirect('appointments:appointment_list')
        
        # Check if appointment is assigned to this doctor
        if appointment.doctor != request.user:
            messages.error(request, 'You can only approve appointments assigned to you.')
            return redirect('appointments:appointment_list')
        
        # Check if appointment can be approved
        if appointment.status != 'pending':
            if appointment.status == 'confirmed':
                messages.info(request, 'This appointment has already been confirmed.')
            elif appointment.status == 'cancelled':
                messages.error(request, 'Cannot approve a cancelled appointment.')
            elif appointment.status == 'completed':
                messages.error(request, 'Cannot approve a completed appointment.')
            return redirect('appointments:appointment_detail', appointment_id=appointment.id)
        
        # Check if appointment date has passed
        if appointment.date_time < timezone.now():
            appointment.status = 'cancelled'
            appointment.notes = f"Automatically cancelled on {timezone.now().strftime('%Y-%m-%d')} because the doctor tried to approve it after the scheduled date ({appointment.date_time.strftime('%Y-%m-%d')})."
            appointment.save()
            messages.error(request, 'This appointment has expired and has been automatically cancelled.')
            return redirect('appointments:appointment_detail', appointment_id=appointment.id)
        
        # Approve the appointment
        appointment.status = 'confirmed'
        appointment.save()
        
        patient_name = appointment.patient.get_full_name() or appointment.patient.email
        messages.success(request, f'Appointment with {patient_name} has been approved successfully!')
        return redirect('appointments:appointment_detail', appointment_id=appointment.id)
        
    except Appointment.DoesNotExist:
        messages.error(request, 'Appointment not found.')
        return redirect('appointments:appointment_list')

@login_required
def update_appointment_view(request, appointment_id):
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        
        # Only patients can update appointments
        if not request.user.is_patient:
            messages.error(request, 'Only patients can update appointments.')
            return redirect('appointments:appointment_list')
        
        # Check if appointment belongs to the patient
        if appointment.patient != request.user:
            messages.error(request, 'You can only update your own appointments.')
            return redirect('appointments:appointment_list')
        
        # Check if appointment can be updated
        if appointment.status == 'cancelled':
            messages.error(request, 'Cancelled appointments cannot be updated.')
            return redirect('appointments:appointment_detail', appointment_id=appointment.id)
        elif appointment.status == 'completed':
            messages.error(request, 'Completed appointments cannot be updated.')
            return redirect('appointments:appointment_detail', appointment_id=appointment.id)
        
        if request.method == 'POST':
            form = AppointmentBookingForm(request.POST, instance=appointment)
            if form.is_valid():
                try:
                    updated_appointment = form.save(commit=False)
                    
                    # Check if date/time is in the future
                    if updated_appointment.date_time <= timezone.now():
                        messages.error(request, 'Appointment date and time must be in the future.')
                    else:
                        updated_appointment.save()
                        messages.success(request, 'Appointment updated successfully!')
                        return redirect('appointments:appointment_detail', appointment_id=appointment.id)
                        
                except Exception as e:
                    messages.error(request, f'Failed to update appointment: {str(e)}')
            else:
                # Display form errors
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
        else:
            form = AppointmentBookingForm(instance=appointment)
        
        # Get available doctors for the form - include all doctors even if they don't have profiles
        doctors = User.objects.filter(role='doctor', is_active=True)
        print(f"DEBUG: Found {doctors.count()} doctors")
        for doctor in doctors:
            print(f"DEBUG: Doctor - {doctor.email} ({doctor.get_full_name()})")
        
        context = {
            'appointment': appointment,
            'form': form,
            'doctors': doctors,
        }
        return render(request, 'appointments/update_appointment.html', context)
        
    except Appointment.DoesNotExist:
        messages.error(request, 'Appointment not found.')
        return redirect('appointments:appointment_list')

@login_required
def cancel_appointment_view(request, appointment_id):
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        
        # Check if user has permission to cancel this appointment
        if request.user.is_patient and appointment.patient != request.user:
            messages.error(request, 'You can only cancel your own appointments.')
            return redirect('appointments:appointment_list')
        elif request.user.is_doctor and appointment.doctor != request.user:
            messages.error(request, 'You can only cancel appointments assigned to you.')
            return redirect('appointments:appointment_list')
        
        # Check if appointment can be cancelled
        if appointment.status == 'cancelled':
            messages.error(request, 'This appointment has already been cancelled.')
            return redirect('appointments:appointment_detail', appointment_id=appointment.id)
        elif appointment.status == 'completed':
            messages.error(request, 'Completed appointments cannot be cancelled.')
            return redirect('appointments:appointment_detail', appointment_id=appointment.id)
        
        if request.method == 'POST':
            cancellation_reason = request.POST.get('cancellation_reason')
            if not cancellation_reason:
                messages.error(request, 'Please provide a reason for cancellation.')
            else:
                # Update appointment status
                appointment.status = 'cancelled'
                appointment.notes = f"Cancellation reason: {cancellation_reason}\n\n" + (appointment.notes or "")
                appointment.save()
                
                messages.success(request, 'Appointment cancelled successfully.')
                return redirect('appointments:appointment_detail', appointment_id=appointment.id)
        
        return render(request, 'appointments/cancel_appointment.html', {'appointment': appointment})
    except Appointment.DoesNotExist:
        messages.error(request, 'Appointment not found.')
        return redirect('appointments:appointment_list')

@login_required
def availability_list_view(request):
    return render(request, 'appointments/availability_list.html')

@login_required
def add_availability_view(request):
    return render(request, 'appointments/add_availability.html')

@login_required
def update_availability_view(request, availability_id):
    return render(request, 'appointments/update_availability.html')

@login_required
def calendar_view(request):
    return render(request, 'appointments/calendar.html')

@login_required
def add_review_view(request, appointment_id):
    return render(request, 'appointments/add_review.html')
