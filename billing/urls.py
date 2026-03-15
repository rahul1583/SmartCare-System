from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    # Bill Management
    path('', views.bill_list_view, name='bill_list'),
    path('create/', views.create_bill_view, name='create_bill'),
    path('create/from-prescription/<int:prescription_id>/', views.create_bill_from_prescription_view, name='create_from_prescription'),
    path('<int:bill_id>/', views.bill_detail_view, name='bill_detail'),
    path('<int:bill_id>/update/', views.update_bill_view, name='update_bill'),
    
    # Payment Processing
    path('<int:bill_id>/pay/', views.payment_view, name='payment'),
    path('payment/success/', views.payment_success_view, name='payment_success'),
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
