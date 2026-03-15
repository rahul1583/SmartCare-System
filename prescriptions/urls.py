from django.urls import path
from . import views

app_name = 'prescriptions'

urlpatterns = [
    # Prescription Management
    path('', views.prescription_list_view, name='list'),
    path('<int:prescription_id>/', views.prescription_detail_view, name='detail'),
    path('create/', views.create_prescription_view, name='create'),
    path('<int:prescription_id>/update/', views.update_prescription_view, name='update'),
    path('<int:prescription_id>/download/', views.download_prescription_view, name='download'),
    
    # Medication Management
    path('medicines/', views.medicine_list_view, name='medicine_list'),
    path('medicines/add/', views.add_medicine_view, name='add_medicine'),
    path('medicines/<int:medicine_id>/update/', views.update_medicine_view, name='update_medicine'),
]
