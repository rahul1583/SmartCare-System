from django.urls import path
from . import views

app_name = 'medical_records'

urlpatterns = [
    # Medical Records
    path('', views.medical_record_list_view, name='medical_record_list'),
    path('<int:record_id>/', views.medical_record_detail_view, name='medical_record_detail'),
    path('create/', views.create_medical_record_view, name='create_medical_record'),
    path('<int:record_id>/update/', views.update_medical_record_view, name='update_medical_record'),
    
    # Lab Reports
    path('lab-reports/', views.lab_report_list_view, name='lab_report_list'),
    path('lab-reports/<int:report_id>/', views.lab_report_detail_view, name='lab_report_detail'),
    path('lab-reports/create/', views.create_lab_report_view, name='create_lab_report'),
    path('lab-reports/<int:report_id>/upload/', views.upload_lab_report_view, name='upload_lab_report'),
    
    # Vital Signs
    path('vital-signs/', views.vital_signs_list_view, name='vital_signs_list'),
    path('vital-signs/add/', views.add_vital_signs_view, name='add_vital_signs'),
    
    # Allergies
    path('allergies/', views.allergy_list_view, name='allergy_list'),
    path('allergies/add/', views.add_allergy_view, name='add_allergy'),
    path('allergies/<int:allergy_id>/update/', views.update_allergy_view, name='update_allergy'),
]
