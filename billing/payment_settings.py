"""
Payment Gateway Settings for SmartCare System

Add these settings to your Django settings.py file to configure payment gateways.
"""

# eSewa Payment Gateway Settings
ESEWA_MERCHANT_CODE = 'EPAYTEST'  # Use 'EPAYTEST' for testing, replace with actual merchant code for production
ESEWA_SUCCESS_URL = 'http://127.0.0.1:8000/billing/esewa/success/'
ESEWA_FAILURE_URL = 'http://127.0.0.1:8000/billing/esewa/failure/'

# Khalti Payment Gateway Settings
KHALTI_MERCHANT_ID = 'TEST_MERCHANT_ID'  # Replace with actual merchant ID for production
KHALTI_SECRET_KEY = 'TEST_SECRET_KEY'  # Replace with actual secret key for production
KHALTI_WEBSITE_URL = 'http://127.0.0.1:8000'

# General Payment Settings
SITE_URL = 'http://127.0.0.1:8000'  # Update with your actual site URL
PAYMENT_TIMEOUT = 300  # Payment timeout in seconds

# Security Settings
ALLOWED_PAYMENT_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    # Add your production domain here
]

# Payment Gateway URLs (for testing)
ESEWA_TEST_URL = 'https://uat.esewa.com.np/epay/main'
ESEWA_VERIFICATION_URL = 'https://uat.esewa.com.np/epay/transrec'

KHALTI_TEST_URL = 'https://a.khalti.com/api/v2/epayment/initiate/'
KHALTI_VERIFICATION_URL = 'https://a.khalti.com/api/v2/epayment/lookup/'

# Production URLs (uncomment for production)
# ESEWA_PRODUCTION_URL = 'https://esewa.com.np/epay/main'
# ESEWA_PRODUCTION_VERIFICATION_URL = 'https://esewa.com.np/epay/transrec'
# KHALTI_PRODUCTION_URL = 'https://khalti.com/api/v2/epayment/initiate/'
# KHALTI_PRODUCTION_VERIFICATION_URL = 'https://khalti.com/api/v2/epayment/lookup/'

# Payment Method Configuration
PAYMENT_METHODS = {
    'cash': {
        'name': 'Cash',
        'description': 'Pay with cash at the clinic',
        'enabled': True,
        'requires_redirect': False
    },
    'card': {
        'name': 'Credit/Debit Card',
        'description': 'Pay with credit or debit card',
        'enabled': True,
        'requires_redirect': False
    },
    'esewa': {
        'name': 'eSewa',
        'description': 'Pay using eSewa digital wallet',
        'enabled': True,
        'requires_redirect': True,
        'logo': 'https://esewa.com.np/esewa_web/img/esewa_logo.png'
    },
    'khalti': {
        'name': 'Khalti',
        'description': 'Pay using Khalti digital wallet',
        'enabled': True,
        'requires_redirect': True,
        'logo': 'https://khalti.com/static/images/khalti-logo.png'
    },
    'bank_transfer': {
        'name': 'Bank Transfer',
        'description': 'Transfer funds directly to our bank account',
        'enabled': True,
        'requires_redirect': False
    },
    'online': {
        'name': 'Online Payment',
        'description': 'Pay using other online payment methods',
        'enabled': False,  # Set to True when implemented
        'requires_redirect': True
    }
}

# Payment Status Configuration
PAYMENT_STATUS_PENDING = 'pending'
PAYMENT_STATUS_COMPLETED = 'completed'
PAYMENT_STATUS_FAILED = 'failed'
PAYMENT_STATUS_REFUNDED = 'refunded'

# Bill Status Configuration
BILL_STATUS_DRAFT = 'draft'
BILL_STATUS_SENT = 'sent'
BILL_STATUS_PAID = 'paid'
BILL_STATUS_OVERDUE = 'overdue'
BILL_STATUS_CANCELLED = 'cancelled'

# Payment Verification Settings
VERIFY_PAYMENT_ON_CALLBACK = True  # Verify payment when gateway returns
AUTO_UPDATE_BILL_STATUS = True  # Automatically update bill status when fully paid
PAYMENT_RETRY_ATTEMPTS = 3  # Number of payment retry attempts

# Email Notifications
SEND_PAYMENT_CONFIRMATION_EMAIL = True
SEND_BILL_GENERATION_EMAIL = True
PAYMENT_CONFIRMATION_EMAIL_SUBJECT = 'Payment Confirmation - SmartCare System'
BILL_GENERATION_EMAIL_SUBJECT = 'New Bill Generated - SmartCare System'

# Logging
LOG_PAYMENT_TRANSACTIONS = True
PAYMENT_LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR
