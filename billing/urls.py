from django.urls import path
from django.shortcuts import render
from . import views
from . import simple_payment
from . import simple_views
from . import working_payment
from . import pay_views

app_name = 'billing'

urlpatterns = [
    # Bill Management
    path('', views.bill_list_view, name='bill_list'),
    path('create/', views.create_bill_view, name='create_bill'),
    path('create/from-prescription/<int:prescription_id>/', views.create_bill_from_prescription_view, name='create_from_prescription'),
    path('<int:bill_id>/', views.bill_detail_view, name='bill_detail'),
    path('<int:bill_id>/update/', views.update_bill_view, name='update_bill'),
    
    # Payment Processing - SIMPLE PAYMENT IS FIRST
    path('<int:bill_id>/pay/', pay_views.pay_view, name='pay'),
    path('<int:bill_id>/pay-fixed/', views.payment_view_fixed, name='payment_fixed'),
    path('<int:bill_id>/simple/', simple_views.simple_payment_view, name='simple_payment_new'),
    path('<int:bill_id>/simple-pay/', simple_payment.simple_payment_view, name='simple_payment'),
    path('<int:bill_id>/working/', working_payment.working_payment_view, name='working_payment'),
    path('test-payment/', views.test_payment_view, name='test_payment'),
    path('payment/success/', views.payment_success_view, name='payment_success'),
    path('payment/success/<int:payment_id>/<method>/<amount>/<transaction_id>/', pay_views.payment_success_with_details_view, name='payment_success_with_details'),
    path('payment/failed/', views.payment_failed_view, name='payment_failed'),
    
    # eSewa Payment Gateway
    path('esewa/success/', views.esewa_success_view, name='esewa_success'),
    path('esewa/failure/', views.esewa_failure_view, name='esewa_failure'),
    
    # Khalti Payment Gateway
    path('khalti/callback/', views.khalti_callback_view, name='khalti_callback'),
    path('khalti/webhook/', views.khalti_webhook_view, name='khalti_webhook'),
    
    # Payment History
    path('payments/', views.payment_history_view, name='payment_history'),
    path('payments/<int:payment_id>/', views.payment_detail_view, name='payment_detail'),
    
    # Refunds
    path('payments/<int:payment_id>/refund/', views.refund_request_view, name='refund_request'),
]
