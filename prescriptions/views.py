from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import render_to_string
from .models import Prescription, Medication

@login_required
def prescription_list_view(request):
    # Get user's prescriptions based on role
    if request.user.is_patient:
        prescriptions = Prescription.objects.filter(patient=request.user).select_related('doctor', 'appointment').order_by('-created_at')
    elif request.user.is_doctor:
        prescriptions = Prescription.objects.filter(doctor=request.user).select_related('patient', 'appointment').order_by('-created_at')
    else:
        # Admin can see all prescriptions
        prescriptions = Prescription.objects.all().select_related('doctor', 'patient', 'appointment').order_by('-created_at')
    
    # Get today's prescriptions only
    from django.utils import timezone
    today = timezone.now().date()
    today_prescriptions = prescriptions.filter(created_at__date=today)
    
    context = {
        'prescriptions': prescriptions,
        'today_prescriptions': today_prescriptions,
        'total_prescriptions': prescriptions.count(),
    }
    return render(request, 'prescriptions/prescription_list.html', context)

@login_required
def prescription_detail_view(request, prescription_id):
    prescription = get_object_or_404(Prescription, id=prescription_id)
    
    # Check permissions
    if request.user.is_patient and prescription.patient != request.user:
        messages.error(request, 'You can only view your own prescriptions.')
        return redirect('prescriptions:list')
    elif request.user.is_doctor and prescription.doctor != request.user:
        messages.error(request, 'You can only view prescriptions you created.')
        return redirect('prescriptions:list')
    
    medications = prescription.medications.all()
    
    # Get associated bill if exists (but don't pass to template to avoid payment summary)
    associated_bill = None
    if prescription.appointment:
        try:
            from billing.models import Bill
            associated_bill = Bill.objects.filter(appointment=prescription.appointment).first()
        except:
            associated_bill = None
    
    context = {
        'prescription': prescription,
        'medications': medications,
        # Note: Not including bill to avoid payment summary display
    }
    return render(request, 'prescriptions/prescription_detail.html', context)

@login_required
def create_prescription_view(request):
    # Only doctors can create prescriptions
    if not request.user.is_doctor:
        messages.error(request, 'Only doctors can create prescriptions.')
        return redirect('prescriptions:list')
    
    if request.method == 'POST':
        try:
            # Get form data
            patient_id = request.POST.get('patient')
            appointment_id = request.POST.get('appointment')
            consultation_type = request.POST.get('consultation_type', 'physical_visit')
            diagnosis = request.POST.get('diagnosis')
            medicines = request.POST.get('medicines')
            instructions = request.POST.get('instructions')
            validity_days = request.POST.get('validity_days')
            follow_up_date = request.POST.get('follow_up_date')
            
            # Validate required fields
            if not patient_id or not diagnosis or not medicines:
                messages.error(request, 'Patient, diagnosis, and medicines are required fields.')
                return redirect('prescriptions:create')
            
            # Get patient
            from accounts.models import User
            patient = User.objects.get(id=patient_id)
            
            # Get appointment if provided
            appointment = None
            if appointment_id:
                from appointments.models import Appointment
                appointment = Appointment.objects.get(id=appointment_id)
            
            # Create prescription
            prescription = Prescription.objects.create(
                appointment=appointment,
                doctor=request.user,
                patient=patient,
                consultation_type=consultation_type if consultation_type in ('physical_visit', 'online_consultant') else 'physical_visit',
                diagnosis=diagnosis,
                notes=instructions,
                follow_up_date=follow_up_date if follow_up_date else None,
                is_active=True
            )
            
            # Parse medicines and create medication records
            medicines_list = [med.strip() for med in medicines.split('\n') if med.strip()]
            for medicine_line in medicines_list:
                # Create a simple medication record from the text
                Medication.objects.create(
                    prescription=prescription,
                    medicine_name=medicine_line,
                    dosage="As prescribed",
                    frequency="once",
                    duration=f"{validity_days or 30} days",
                    instructions=instructions or "Take as directed",
                    quantity=1
                )
            
            messages.success(request, f'Prescription created successfully for {patient.get_full_name() or patient.email}!')
            return redirect('prescriptions:detail', prescription_id=prescription.id)
            
        except Exception as e:
            messages.error(request, f'Error creating prescription: {str(e)}')
            return redirect('prescriptions:create')
    
    # GET request - show the form
    # Get all patients for selection
    from accounts.models import User
    patients = User.objects.filter(role='patient', is_active=True).order_by('first_name', 'last_name')
    
    # Get all appointments from all patients, but group by patient to avoid duplicates
    from appointments.models import Appointment
    from django.db.models import Max
    
    # Get the latest appointment for each patient
    latest_appointments = Appointment.objects.filter(
        patient__role='patient'
    ).values('patient_id').annotate(
        latest_date=Max('date_time')
    ).order_by('-latest_date')
    
    # Get the actual appointment objects for these latest appointments
    appointment_ids = [app['patient_id'] for app in latest_appointments]
    appointments = Appointment.objects.filter(
        patient_id__in=appointment_ids
    ).annotate(
        latest_date=Max('date_time')
    ).filter(
        date_time__in=[app['latest_date'] for app in latest_appointments]
    ).select_related('patient', 'doctor').order_by('-date_time')
    
    # Filter out appointments that already have prescriptions
    appointments_with_prescriptions = Appointment.objects.filter(
        prescription__isnull=False
    ).values_list('id', flat=True)
    
    # Show appointments without prescriptions, or all if none available
    if appointments_with_prescriptions.exists():
        appointments = appointments.exclude(id__in=appointments_with_prescriptions)
    
    print(f"DEBUG: Found {patients.count()} patients and {appointments.count()} unique latest appointments (without prescriptions)")
    
    context = {
        'patients': patients,
        'appointments': appointments,
    }
    return render(request, 'prescriptions/create_prescription.html', context)

@login_required
def update_prescription_view(request, prescription_id):
    # Get the prescription
    prescription = get_object_or_404(Prescription, id=prescription_id)
    
    # Check permissions - only doctors can update prescriptions they created
    if not request.user.is_doctor or prescription.doctor != request.user:
        messages.error(request, 'You can only update prescriptions you created.')
        return redirect('prescriptions:detail', prescription_id=prescription.id)
    
    if request.method == 'POST':
        try:
            # Get form data
            consultation_type = request.POST.get('consultation_type', 'physical_visit')
            diagnosis = request.POST.get('diagnosis')
            medicines = request.POST.get('medicines')
            instructions = request.POST.get('instructions')
            validity_days = request.POST.get('validity_days')
            follow_up_date = request.POST.get('follow_up_date')
            
            # Validate required fields
            if not diagnosis or not medicines:
                messages.error(request, 'Diagnosis and medicines are required fields.')
                return redirect('prescriptions:update', prescription_id=prescription.id)
            
            # Update prescription
            prescription.consultation_type = consultation_type if consultation_type in ('physical_visit', 'online_consultant') else prescription.consultation_type
            prescription.diagnosis = diagnosis
            prescription.notes = instructions
            prescription.follow_up_date = follow_up_date if follow_up_date else None
            prescription.save()
            
            # Remove existing medications
            prescription.medications.all().delete()
            
            # Parse medicines and create new medication records
            medicines_list = [med.strip() for med in medicines.split('\n') if med.strip()]
            for medicine_line in medicines_list:
                # Create a simple medication record from the text
                Medication.objects.create(
                    prescription=prescription,
                    medicine_name=medicine_line,
                    dosage="As prescribed",
                    frequency="once",
                    duration=f"{validity_days or 30} days",
                    instructions=instructions or "Take as directed",
                    quantity=1
                )
            
            messages.success(request, f'Prescription updated successfully for {prescription.patient.get_full_name() or prescription.patient.email}!')
            return redirect('prescriptions:detail', prescription_id=prescription.id)
            
        except Exception as e:
            messages.error(request, f'Error updating prescription: {str(e)}')
            return redirect('prescriptions:update', prescription_id=prescription.id)
    
    # GET request - show the form
    medications = prescription.medications.all()
    
    context = {
        'prescription': prescription,
        'medications': medications,
    }
    return render(request, 'prescriptions/update_prescription.html', context)

@login_required
def download_prescription_view(request, prescription_id):
    """Generate and download prescription as PDF"""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    
    # Check permissions
    if request.user.is_patient and prescription.patient != request.user:
        messages.error(request, 'You can only download your own prescriptions.')
        return redirect('prescriptions:list')
    elif request.user.is_doctor and prescription.doctor != request.user:
        messages.error(request, 'You can only download prescriptions you created.')
        return redirect('prescriptions:list')
    
    medications = prescription.medications.all()
    
    # Generate HTML content for PDF
    html_content = render_to_string('prescriptions/prescription_pdf.html', {
        'prescription': prescription,
        'medications': medications,
        'request': request,
    })
    
    # For now, return as HTML (can be extended to use ReportLab or WeasyPrint for actual PDF generation)
    response = HttpResponse(content_type='text/html')
    response['Content-Disposition'] = f'attachment; filename="prescription_{prescription.id}.html"'
    response.write(html_content)
    
    return response

@login_required
def medicine_list_view(request):
    return render(request, 'prescriptions/medicine_list.html')

@login_required
def add_medicine_view(request):
    return render(request, 'prescriptions/add_medicine.html')

@login_required
def update_medicine_view(request, medicine_id):
    return render(request, 'prescriptions/update_medicine.html')

@login_required
def download_prescription_view(request, prescription_id):
    """Generate and download prescription as PDF"""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    
    # Check permissions
    if request.user.is_patient and prescription.patient != request.user:
        messages.error(request, 'You can only download your own prescriptions.')
        return redirect('prescriptions:list')
    elif request.user.is_doctor and prescription.doctor != request.user:
        messages.error(request, 'You can only download prescriptions you created.')
        return redirect('prescriptions:list')
    
    medications = prescription.medications.all()
    
    # Generate HTML content for PDF
    html_content = render_to_string('prescriptions/prescription_pdf.html', {
        'prescription': prescription,
        'medications': medications,
        'request': request,
    })
    
    # For now, return as HTML (can be extended to use ReportLab or WeasyPrint for actual PDF generation)
    response = HttpResponse(content_type='text/html')
    response['Content-Disposition'] = f'attachment; filename="prescription_{prescription.id}.html"'
    response.write(html_content)
    
    return response
