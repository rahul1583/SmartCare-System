from django.urls import path
from . import views

app_name = 'appointments'

urlpatterns = [
    # Easy Appointments
    path('easy/', views.easy_appointments_view, name='easy_appointments'),
    
    # Appointment Management
    path('', views.appointment_list_view, name='appointment_list'),
    path('book/', views.book_appointment_view, name='book_appointment'),
    path('<int:appointment_id>/', views.appointment_detail_view, name='appointment_detail'),
    path('<int:appointment_id>/update/', views.update_appointment_view, name='update_appointment'),
    path('<int:appointment_id>/approve/', views.approve_appointment_view, name='approve_appointment'),
    path('<int:appointment_id>/complete/', views.complete_appointment_view, name='complete_appointment'),
    path('<int:appointment_id>/cancel/', views.cancel_appointment_view, name='cancel_appointment'),
    
    # Doctor Availability
    path('availability/', views.availability_list_view, name='availability_list'),
    path('availability/add/', views.add_availability_view, name='add_availability'),
    path('availability/<int:availability_id>/update/', views.update_availability_view, name='update_availability'),
    
    # Calendar View
    path('calendar/', views.calendar_view, name='calendar'),
    
    # Reviews
    path('<int:appointment_id>/review/', views.add_review_view, name='add_review'),
]
