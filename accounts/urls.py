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
    path('profile/update/', views.profile_update_view, name='profile_update'),
    
    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('patient-dashboard/', views.patient_dashboard_view, name='patient_dashboard'),
    
    # Admin URLs
    path('admin/dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin/add-user/', views.admin_add_user_view, name='admin_add_user'),
    path('admin/users/', views.admin_users_view, name='admin_users'),
    path('admin/dashboard-users/', views.admin_dashboard_users_view, name='admin_dashboard_users'),
    path('admin/users/<int:user_id>/toggle/', views.toggle_user_status, name='toggle_user_status'),
    path('admin/users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
]
