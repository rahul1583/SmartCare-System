try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: requests module not available. Payment gateway functionality will be limited.")

import uuid
from django.conf import settings
from django.urls import reverse
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from .models import Payment, Bill

class PaymentGateway:
    """Base class for payment gateways"""
    
    def __init__(self, bill, amount, return_url=None):
        self.bill = bill
        self.amount = amount
        self.return_url = return_url or reverse('billing:payment_success')
        self.transaction_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
    
    def initiate_payment(self):
        """Initiate payment process"""
        raise NotImplementedError("Subclasses must implement initiate_payment")
    
    def verify_payment(self, payment_data):
        """Verify payment completion"""
        raise NotImplementedError("Subclasses must implement verify_payment")

class EsewaPayment(PaymentGateway):
    """eSewa payment gateway integration"""
    
    def __init__(self, bill, amount, return_url=None):
        super().__init__(bill, amount, return_url)
        self.merchant_code = getattr(settings, 'ESEWA_MERCHANT_CODE', 'EPAYTEST')
        self.success_url = getattr(settings, 'ESEWA_SUCCESS_URL', 
                                f"{settings.SITE_URL}{reverse('billing:esewa_success')}")
        self.failure_url = getattr(settings, 'ESEWA_FAILURE_URL', 
                                f"{settings.SITE_URL}{reverse('billing:esewa_failure')}")
    
    def initiate_payment(self):
        """Initiate eSewa payment"""
        # Create pending payment record
        payment = Payment.objects.create(
            bill=self.bill,
            amount=self.amount,
            payment_method='esewa',
            transaction_id=self.transaction_id,
            status='pending'
        )
        
        # eSewa payment URL (for testing environment)
        esewa_url = "https://uat.esewa.com.np/epay/main"
        
        # Payment parameters
        params = {
            'amt': self.amount,
            'pdc': 0,  # delivery charge
            'psc': 0,  # service charge
            'txAmt': 0,  # tax amount
            'tAmt': self.amount,  # total amount
            'pid': self.transaction_id,
            'scd': self.merchant_code,
            'su': self.success_url,
            'fu': self.failure_url
        }
        
        return esewa_url, params
    
    def verify_payment(self, payment_data):
        """Verify eSewa payment"""
        if not REQUESTS_AVAILABLE:
            return False, "Payment gateway not available - requests module missing"
        
        try:
            # Get payment record
            payment = Payment.objects.get(transaction_id=payment_data.get('pid'))
            
            # Verify with eSewa API
            verification_url = "https://uat.esewa.com.np/epay/transrec"
            
            verification_data = {
                'scd': self.merchant_code,
                'rid': payment_data.get('refId'),  # reference ID from eSewa
                'pid': payment_data.get('pid'),
                'amt': payment_data.get('amt')
            }
            
            response = requests.post(verification_url, data=verification_data)
            
            if response.status_code == 200 and 'Success' in response.text:
                # Update payment status
                payment.status = 'completed'
                payment.paid_date = timezone.now()
                payment.save()
                
                # Update bill status
                self._update_bill_status()
                
                return True, "Payment successful"
            else:
                payment.status = 'failed'
                payment.save()
                return False, "Payment verification failed"
                
        except Exception as e:
            return False, f"Payment verification error: {str(e)}"
    
    def _update_bill_status(self):
        """Update bill status if fully paid"""
        total_paid = sum(p.amount for p in self.bill.payments.filter(status='completed'))
        if total_paid >= self.bill.total_amount:
            self.bill.status = 'paid'
            self.bill.save()
        elif self.bill.status == 'draft':
            self.bill.status = 'sent'
            self.bill.save()

class KhaltiPayment(PaymentGateway):
    """Khalti payment gateway integration"""
    
    def __init__(self, bill, amount, return_url=None):
        super().__init__(bill, amount, return_url)
        self.merchant_id = getattr(settings, 'KHALTI_MERCHANT_ID', 'TEST_MERCHANT_ID')
        self.secret_key = getattr(settings, 'KHALTI_SECRET_KEY', 'TEST_SECRET_KEY')
        self.return_url = return_url or reverse('billing:khalti_callback')
    
    def initiate_payment(self):
        """Initiate Khalti payment"""
        if not REQUESTS_AVAILABLE:
            return None, "Payment gateway not available - requests module missing"
        
        # Create pending payment record
        payment = Payment.objects.create(
            bill=self.bill,
            amount=self.amount,
            payment_method='khalti',
            transaction_id=self.transaction_id,
            status='pending'
        )
        
        # Khalti payment initiation
        khalti_url = "https://a.khalti.com/api/v2/epayment/initiate/"
        
        headers = {
            'Authorization': f'Key {self.secret_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'return_url': f"{settings.SITE_URL}{self.return_url}",
            'website_url': settings.SITE_URL,
            'amount': int(self.amount * 100),  # Khalti expects amount in paisa
            'purchase_order_id': self.transaction_id,
            'purchase_order_name': f"SmartCare Bill #{self.bill.id}",
            'customer_info': {
                'name': self.bill.patient.get_full_name() or self.bill.patient.email,
                'email': self.bill.patient.email,
                'phone': self.bill.patient.phone or ''
            }
        }
        
        try:
            response = requests.post(khalti_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('payment_url'), {}
                else:
                    return None, data.get('detail', 'Payment initiation failed')
            else:
                return None, f"Payment initiation failed: {response.text}"
                
        except Exception as e:
            return None, f"Payment initiation error: {str(e)}"
    
    def verify_payment(self, payment_data):
        """Verify Khalti payment"""
        if not REQUESTS_AVAILABLE:
            return False, "Payment gateway not available - requests module missing"
        
        try:
            # Get payment record
            payment = Payment.objects.get(transaction_id=payment_data.get('pidx'))
            
            # Verify with Khalti API
            verification_url = "https://a.khalti.com/api/v2/epayment/lookup/"
            
            headers = {
                'Authorization': f'Key {self.secret_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'pidx': payment_data.get('pidx')
            }
            
            response = requests.post(verification_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'Completed':
                    # Update payment status
                    payment.status = 'completed'
                    payment.paid_date = timezone.now()
                    payment.save()
                    
                    # Update bill status
                    self._update_bill_status()
                    
                    return True, "Payment successful"
                else:
                    payment.status = 'failed'
                    payment.save()
                    return False, f"Payment not completed: {data.get('status')}"
            else:
                payment.status = 'failed'
                payment.save()
                return False, "Payment verification failed"
                
        except Exception as e:
            return False, f"Payment verification error: {str(e)}"
    
    def _update_bill_status(self):
        """Update bill status if fully paid"""
        total_paid = sum(p.amount for p in self.bill.payments.filter(status='completed'))
        if total_paid >= self.bill.total_amount:
            self.bill.status = 'paid'
            self.bill.save()
        elif self.bill.status == 'draft':
            self.bill.status = 'sent'
            self.bill.save()

def get_payment_gateway(method, bill, amount, return_url=None):
    """Factory function to get appropriate payment gateway"""
    if method == 'esewa':
        return EsewaPayment(bill, amount, return_url)
    elif method == 'khalti':
        return KhaltiPayment(bill, amount, return_url)
    else:
        raise ValueError(f"Unsupported payment method: {method}")
