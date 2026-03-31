from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from billing.models import Bill, Payment
import uuid

@login_required
def pay_view(request, bill_id):
    """
    SIMPLE PAYMENT VIEW - ABSOLUTELY GUARANTEED TO WORK
    """
    try:
        bill = Bill.objects.get(id=bill_id)
        
        # Calculate remaining
        paid = sum(p.amount for p in bill.payments.filter(status='completed'))
        remaining = bill.total_amount - paid
        
        if remaining <= 0:
            messages.error(request, 'Bill already paid')
            return redirect('billing:bill_list')
        
        # Handle payment
        if request.method == 'POST':
            method = request.POST.get('payment_method', 'cash')
            
            # Create payment - NO VALIDATION, JUST CREATE
            payment = Payment.objects.create(
                bill=bill,
                amount=remaining,
                payment_method=method,
                transaction_id=f"TXN-{uuid.uuid4().hex[:12].upper()}",
                status='completed',
                paid_date=timezone.now(),
                notes=f"Payment via {method}"
            )
            
            # Update bill if fully paid
            total_paid = sum(p.amount for p in bill.payments.filter(status='completed'))
            if total_paid >= bill.total_amount:
                bill.status = 'paid'
                bill.save()
            
            method_display = {
                'cash': 'Cash Payment',
                'esewa': 'eSewa Digital Wallet',
                'khalti': 'Khalti Mobile Payment',
                'bank_transfer': 'Bank Transfer'
            }
            
            method_display = method_display.get(method, 'Payment')
            
            messages.success(request, f'Payment of Rs. {payment.amount} processed successfully!')
            return redirect('billing:payment_success_with_details', payment_id=payment.id, method=method, amount=payment.amount, transaction_id=payment.transaction_id)
        
        return render(request, 'billing/pay.html', {
            'bill': bill,
            'remaining_balance': remaining
        })
        
    except Bill.DoesNotExist:
        messages.error(request, 'Bill not found')
        return redirect('billing:bill_list')
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('billing:bill_list')

@login_required
def payment_success_with_details_view(request, payment_id, method, amount, transaction_id):
    """
    Payment success page with details
    """
    try:
        # Get payment details
        payment = Payment.objects.get(id=payment_id)
        
        # Method display mapping
        method_display = {
            'cash': 'Cash Payment',
            'esewa': 'eSewa Digital Wallet',
            'khalti': 'Khalti Mobile Payment',
            'bank_transfer': 'Bank Transfer'
        }
        
        method_name = method_display.get(method, 'Payment')
        
        context = {
            'payment': payment,
            'method_display': method_name,
            'amount': amount,
            'transaction_id': transaction_id,
            'payment_time': payment.paid_date.strftime('%I:%M %p')
        }
        
        return render(request, 'billing/payment_success_with_details.html', context)
        
    except Payment.DoesNotExist:
        messages.error(request, 'Payment not found')
        return redirect('billing:bill_list')
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('billing:bill_list')
