from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Notification views
    path('', views.notification_list, name='list'),
    path('<int:notification_id>/', views.notification_detail, name='detail'),
    
    # AJAX actions
    path('<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_read'),
    path('mark-all-read/', views.mark_all_notifications_read, name='mark_all_read'),
    path('<int:notification_id>/delete/', views.delete_notification, name='delete'),
    
    # Preferences
    path('preferences/', views.notification_preferences, name='preferences'),
    
    # Widget and stats
    path('widget/', views.notification_widget, name='widget'),
    path('stats/', views.notification_stats, name='stats'),
]
