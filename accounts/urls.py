from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('google/start/', views.google_login_start_view, name='google_login_start'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    
    # Profile Management
    path('profile/', views.profile_view, name='profile'),
    
    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('patient-dashboard/', views.patient_dashboard_view, name='patient_dashboard'),
    
    # Admin URLs
    path('admin/dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin/dashboard/live-data/', views.admin_dashboard_live_data_view, name='admin_dashboard_live_data'),
    path('admin/add-user/', views.admin_add_user_view, name='admin_add_user'),
    path('admin/users/', views.admin_users_view, name='admin_users'),
    path('admin/users/export/', views.export_users_csv, name='export_users_csv'),
    path('admin/users/<int:user_id>/details/', views.user_details_view, name='admin_user_details'),
    path('admin/dashboard-users/', views.admin_dashboard_users_view, name='admin_dashboard_users'),
    path('admin/users/<int:user_id>/toggle/', views.toggle_user_status, name='toggle_user_status'),
    path('admin/users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    path('admin/doctors/pending/', views.pending_doctors_view, name='pending_doctors'),
    path('admin/doctors/<int:doctor_id>/approve/', views.approve_doctor_view, name='approve_doctor'),
    path('admin/doctors/<int:doctor_id>/reject/', views.reject_doctor_view, name='reject_doctor'),

    # Password Reset URLs (OTP Based)
    path('password-reset/', views.forgot_password_otp_view, name='forgot_password_otp'),
    path('password-reset/verify/', views.verify_otp_view, name='verify_otp'),
    path('password-reset/confirm/', views.reset_password_otp_view, name='reset_password_otp'),

    # Password Change URLs
    path('password-change/', 
         auth_views.PasswordChangeView.as_view(template_name='accounts/password_change.html'),
         name='password_change'),
    path('password-change/done/', 
         auth_views.PasswordChangeDoneView.as_view(template_name='accounts/password_change_done.html'),
         name='password_change_done'),
]
