from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from decimal import Decimal
import uuid
from .models import Bill, Payment
from .forms import PaymentForm
from .payment_gateways import get_payment_gateway
from prescriptions.models import Prescription

@login_required
def bill_list_view(request):
    """List bills for the current user"""
    if request.user.is_patient:
        bills = Bill.objects.filter(patient=request.user).select_related('doctor', 'appointment').order_by('-created_at')
    elif request.user.is_doctor:
        bills = Bill.objects.filter(doctor=request.user).select_related('patient', 'appointment').order_by('-created_at')
    else:
        bills = Bill.objects.all().select_related('patient', 'doctor', 'appointment').order_by('-created_at')
    
    # Calculate statistics
    total_bills = bills.count()
    paid_bills = bills.filter(status='paid').count()
    pending_bills = bills.filter(status='pending').count()
    total_amount = sum(bill.total_amount for bill in bills if bill.total_amount)
    
    context = {
        'bills': bills,
        'total_bills': total_bills,
        'paid_bills': paid_bills,
        'pending_bills': pending_bills,
        'total_amount': total_amount,
    }
    return render(request, 'billing/bill_list.html', context)

@login_required
def bill_detail_view(request, bill_id):
    """View bill details"""
    try:
        bill = Bill.objects.get(id=bill_id)
        
        # Check permissions
        if request.user.is_patient and bill.patient != request.user:
            messages.error(request, 'You can only view your own bills.')
            return redirect('billing:bill_list')
        elif request.user.is_doctor and bill.doctor != request.user:
            messages.error(request, 'You can only view bills for your appointments.')
            return redirect('billing:bill_list')
        
        # Get payments for this bill
        payments = bill.payments.all().order_by('-created_at')
        
        context = {
            'bill': bill,
            'payments': payments,
            'paid_amount': bill.get_paid_amount(),
            'remaining_balance': bill.get_remaining_balance(),
        }
        return render(request, 'billing/bill_detail.html', context)
        
    except Bill.DoesNotExist:
        messages.error(request, 'Bill not found.')
        return redirect('billing:bill_list')

@login_required
def create_bill_view(request):
    """Create a new bill (for doctors/admins)"""
    if request.user.is_patient:
        messages.error(request, 'You cannot create bills.')
        return redirect('billing:bill_list')
    
    if request.method == 'POST':
        appointment_id = request.POST.get('appointment_id')
        consultation_fee = float(request.POST.get('consultation_fee', 0))
        additional_charges = float(request.POST.get('additional_charges', 0))
        discount_amount = float(request.POST.get('discount_amount', 0))
        tax_amount = float(request.POST.get('tax_amount', 0))
        notes = request.POST.get('notes', '')
        
        try:
            from appointments.models import Appointment
            appointment = Appointment.objects.get(id=appointment_id)
            
            # Check if doctor is assigned to this appointment
            if request.user.is_doctor and appointment.doctor != request.user:
                messages.error(request, 'You can only create bills for your own appointments.')
                return redirect('billing:create_bill')
            
            # Check if bill already exists
            if hasattr(appointment, 'bill'):
                messages.error(request, 'A bill already exists for this appointment.')
                return redirect('billing:bill_detail', appointment.bill.id)
            
            # Calculate total amount
            total_amount = consultation_fee + additional_charges - discount_amount + tax_amount
            
            # Create bill
            bill = Bill.objects.create(
                appointment=appointment,
                patient=appointment.patient,
                doctor=appointment.doctor,
                consultation_fee=consultation_fee,
                additional_charges=additional_charges,
                discount_amount=discount_amount,
                tax_amount=tax_amount,
                total_amount=total_amount,
                status='sent',
                due_date=timezone.now().date() + timezone.timedelta(days=7),
                notes=notes
            )
            
            messages.success(request, f'Bill #{bill.id} created successfully!')
            return redirect('billing:bill_detail', bill.id)
            
        except Appointment.DoesNotExist:
            messages.error(request, 'Appointment not found.')
        except Exception as e:
            messages.error(request, f'Error creating bill: {str(e)}')
    
    # Get available appointments for bill creation
    try:
        from appointments.models import Appointment
        
        if request.user.is_doctor:
            appointments = Appointment.objects.filter(
                doctor=request.user,
                status='completed'
            ).select_related('patient').order_by('-date_time')
        else:  # Admin
            appointments = Appointment.objects.filter(
                status='completed'
            ).select_related('patient', 'doctor').order_by('-date_time')
        
        # Filter out appointments that already have bills
        appointments = appointments.filter(bill__isnull=True)
        
    except Exception as e:
        print(f"Error fetching appointments: {e}")
        appointments = Appointment.objects.none()
    
    context = {
        'appointments': appointments,
    }
    return render(request, 'billing/create_bill.html', context)

@login_required
def update_bill_view(request, bill_id):
    """Update an existing bill (for doctors/admins)"""
    if request.user.is_patient:
        messages.error(request, 'You cannot update bills.')
        return redirect('billing:bill_list')
    
    # Implementation would go here
    messages.info(request, 'Bill update feature coming soon.')
    return redirect('billing:bill_list')

@login_required
def refund_request_view(request, payment_id):
    """Request a refund for a payment"""
    try:
        payment = Payment.objects.get(id=payment_id)
        
        # Check permissions
        if request.user.is_patient and payment.bill.patient != request.user:
            messages.error(request, 'You can only request refunds for your own payments.')
            return redirect('billing:payment_history')
        
        # Implementation would go here
        messages.info(request, 'Refund request feature coming soon.')
        return redirect('billing:payment_detail', payment_id=payment_id)
        
    except Payment.DoesNotExist:
        messages.error(request, 'Payment not found.')
        return redirect('billing:payment_history')

@login_required
def payment_view(request, bill_id):
    try:
        bill = Bill.objects.get(id=bill_id)
        
        # Only patients can make payments
        if not request.user.is_patient:
            messages.error(request, 'Only patients can make payments.')
            return redirect('billing:bill_list')
        
        # Check if bill belongs to the patient
        if bill.patient != request.user:
            messages.error(request, 'You can only pay your own bills.')
            return redirect('billing:bill_list')
        
        # Calculate remaining balance
        paid_amount = sum(payment.amount for payment in bill.payments.filter(status='completed'))
        remaining_balance = bill.total_amount - paid_amount
        
        if request.method == 'POST':
            payment_method = request.POST.get('payment_method')
            amount = float(request.POST.get('amount', 0))
            
            if payment_method in ['esewa', 'khalti']:
                # Handle digital payments
                try:
                    gateway = get_payment_gateway(payment_method, bill, amount)
                    payment_url, params = gateway.initiate_payment()
                    
                    if payment_url:
                        if payment_method == 'esewa':
                            # Redirect to eSewa with form POST
                            return render(request, 'billing/esewa_redirect.html', {
                                'payment_url': payment_url,
                                'params': params
                            })
                        elif payment_method == 'khalti':
                            # Redirect to Khalti payment URL
                            return redirect(payment_url)
                    else:
                        messages.error(request, f'Payment initiation failed: {params}')
                        
                except Exception as e:
                    messages.error(request, f'Payment error: {str(e)}')
            
            else:
                # Handle traditional payment methods (cash, card, bank_transfer, online)
                form = PaymentForm(request.POST, bill=bill)
                if form.is_valid():
                    try:
                        with transaction.atomic():
                            payment = form.save(commit=False)
                            payment.bill = bill
                            payment.transaction_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
                            payment.status = 'completed'
                            payment.paid_date = timezone.now()
                            payment.save()
                            
                            # Update bill status if fully paid
                            total_paid = sum(p.amount for p in bill.payments.filter(status='completed'))
                            if total_paid >= bill.total_amount:
                                bill.status = 'paid'
                                bill.save()
                            elif bill.status == 'draft':
                                bill.status = 'sent'
                                bill.save()
                            
                            messages.success(request, f'Payment of Rs. {payment.amount} processed successfully!')
                            return redirect('billing:payment_success')
                            
                    except Exception as e:
                        messages.error(request, f'Payment processing failed: {str(e)}')
                else:
                    # Display form errors
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f'{field}: {error}')
        else:
            form = PaymentForm(bill=bill)
        
        context = {
            'bill': bill,
            'form': form,
            'remaining_balance': remaining_balance,
        }
        return render(request, 'billing/payment.html', context)
        
    except Bill.DoesNotExist:
        messages.error(request, 'Bill not found.')
        return redirect('billing:bill_list')

@login_required
def esewa_success_view(request):
    """Handle eSewa payment success callback"""
    try:
        payment_data = {
            'pid': request.GET.get('pid'),
            'refId': request.GET.get('refId'),
            'amt': request.GET.get('amt')
        }
        
        # Get payment record
        payment = Payment.objects.get(transaction_id=payment_data['pid'])
        gateway = get_payment_gateway('esewa', payment.bill, payment.amount)
        
        success, message = gateway.verify_payment(payment_data)
        
        if success:
            messages.success(request, 'Payment completed successfully via eSewa!')
            return redirect('billing:payment_success')
        else:
            messages.error(request, f'Payment verification failed: {message}')
            return redirect('billing:payment_failed')
            
    except Exception as e:
        messages.error(request, f'Payment processing error: {str(e)}')
        return redirect('billing:payment_failed')

@login_required
def esewa_failure_view(request):
    """Handle eSewa payment failure callback"""
    messages.error(request, 'Payment was cancelled or failed. Please try again.')
    return redirect('billing:payment_failed')

@login_required
def khalti_callback_view(request):
    """Handle Khalti payment callback"""
    try:
        if request.method == 'GET':
            payment_data = {
                'pidx': request.GET.get('pidx'),
                'transaction_id': request.GET.get('transaction_id'),
                'amount': request.GET.get('amount')
            }
            
            # Get payment record
            payment = Payment.objects.get(transaction_id=payment_data['transaction_id'])
            gateway = get_payment_gateway('khalti', payment.bill, payment.amount)
            
            success, message = gateway.verify_payment(payment_data)
            
            if success:
                messages.success(request, 'Payment completed successfully via Khalti!')
                return redirect('billing:payment_success')
            else:
                messages.error(request, f'Payment verification failed: {message}')
                return redirect('billing:payment_failed')
                
    except Exception as e:
        messages.error(request, f'Payment processing error: {str(e)}')
        return redirect('billing:payment_failed')

@csrf_exempt
def khalti_webhook_view(request):
    """Handle Khalti webhook notifications"""
    try:
        if request.method == 'POST':
            data = request.json()
            
            # Verify webhook signature if needed
            # Process payment completion
            payment_data = {
                'pidx': data.get('pidx'),
                'transaction_id': data.get('transaction_id'),
                'amount': data.get('amount')
            }
            
            payment = Payment.objects.get(transaction_id=payment_data['transaction_id'])
            gateway = get_payment_gateway('khalti', payment.bill, payment.amount)
            gateway.verify_payment(payment_data)
            
            return JsonResponse({'status': 'success'})
            
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
def payment_success_view(request):
    return render(request, 'billing/payment_success.html')

@login_required
def payment_failed_view(request):
    return render(request, 'billing/payment_failed.html')

@login_required
def payment_history_view(request):
    # Only patients can view payment history
    if not request.user.is_patient:
        messages.error(request, 'Only patients can view payment history.')
        return redirect('billing:bill_list')
    
    payments = Payment.objects.filter(bill__patient=request.user).select_related('bill', 'bill__doctor').order_by('-created_at')
    
    # Calculate statistics
    total_paid = sum(payment.amount for payment in payments if payment.amount)
    completed_payments = payments.filter(status='completed').count()
    pending_payments = payments.filter(status='pending').count()
    failed_payments = payments.filter(status='failed').count()
    
    context = {
        'payments': payments,
        'total_paid': total_paid,
        'completed_payments': completed_payments,
        'pending_payments': pending_payments,
        'failed_payments': failed_payments,
    }
    return render(request, 'billing/payment_history.html', context)

@login_required
def payment_detail_view(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    
    # Only patients can view payment details
    if not request.user.is_patient:
        messages.error(request, 'Only patients can view payment details.')
        return redirect('billing:payment_history')
    
    # Check if payment belongs to the patient
    if payment.bill.patient != request.user:
        messages.error(request, 'You can only view your own payments.')
        return redirect('billing:payment_history')
    
    context = {
        'payment': payment,
    }
    return render(request, 'billing/payment_detail.html', context)

@login_required
def create_bill_from_prescription_view(request, prescription_id):
    """Create a bill from a prescription"""
    # Only doctors can create bills
    if not request.user.is_doctor:
        messages.error(request, 'Only doctors can create bills.')
        return redirect('prescriptions:detail', prescription_id=prescription_id)
    
    try:
        prescription = get_object_or_404(Prescription, id=prescription_id)
        
        # Check if doctor created this prescription
        if prescription.doctor != request.user:
            messages.error(request, 'You can only create bills for prescriptions you created.')
            return redirect('prescriptions:detail', prescription_id=prescription_id)
        
        # Check if bill already exists for this prescription
        if Bill.objects.filter(prescription=prescription).exists():
            messages.error(request, 'A bill already exists for this prescription.')
            return redirect('prescriptions:detail', prescription_id=prescription_id)
        
        if request.method == 'POST':
            try:
                # Get form data
                consultation_fee = Decimal(request.POST.get('consultation_fee', 500))
                lab_fee = Decimal(request.POST.get('lab_fee', 0))
                other_fee = Decimal(request.POST.get('other_fee', 0))
                notes = request.POST.get('notes', '')
                
                # Calculate medicine fees from form
                medicine_fee = Decimal('0')
                medications = prescription.medications.all()
                
                for medication in medications:
                    price_key = f'medicine_price_{medication.id}'
                    medicine_price = request.POST.get(price_key, '0')
                    medicine_fee += Decimal(medicine_price or '0')
                
                # Calculate total amount (medicine_fee excluded from total_amount)
                total_amount = consultation_fee + lab_fee + other_fee
                
                # Create bill from prescription
                with transaction.atomic():
                    bill = Bill.objects.create(
                        patient=prescription.patient,
                        doctor=prescription.doctor,
                        appointment=prescription.appointment,
                        prescription=prescription,
                        consultation_fee=consultation_fee,
                        medicine_fee=medicine_fee,
                        lab_fee=lab_fee,
                        other_fee=other_fee,
                        total_amount=total_amount,
                        notes=notes,
                        status='pending'
                    )
                
                messages.success(request, f'Bill created successfully for {prescription.patient.get_full_name() or prescription.patient.email}!')
                return redirect('billing:bill_detail', bill_id=bill.id)
                
            except Exception as e:
                messages.error(request, f'Error creating bill: {str(e)}')
                return render(request, 'billing/create_bill_from_prescription.html', {'prescription': prescription})
        
        # GET request - show the form
        context = {
            'prescription': prescription,
        }
        return render(request, 'billing/create_bill_from_prescription.html', context)
        
    except Exception as e:
        messages.error(request, f'Error creating bill: {str(e)}')
        return redirect('prescriptions:detail', prescription_id=prescription_id)
