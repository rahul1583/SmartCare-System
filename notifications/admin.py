from django.contrib import admin
from .models import Notification, NotificationTemplate, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'recipient', 'notification_type', 'priority', 
        'is_read', 'created_at', 'get_action_text'
    ]
    list_filter = [
        'notification_type', 'priority', 'is_read', 'is_email_sent',
        'created_at', 'recipient__role'
    ]
    search_fields = ['title', 'message', 'recipient__email', 'recipient__first_name', 'recipient__last_name']
    readonly_fields = ['created_at', 'read_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('recipient', 'sender', 'notification_type', 'title', 'message', 'priority')
        }),
        ('Status', {
            'fields': ('is_read', 'is_email_sent', 'is_sms_sent', 'read_at')
        }),
        ('Related Objects', {
            'fields': ('appointment_id', 'bill_id', 'prescription_id', 'medical_record_id')
        }),
        ('Action', {
            'fields': ('action_url', 'action_text')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_action_text(self, obj):
        if obj.action_text:
            return obj.action_text
        return 'No Action'
    get_action_text.short_description = 'Action'


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['notification_type', 'email_subject', 'is_active', 'updated_at']
    list_filter = ['notification_type', 'is_active']
    search_fields = ['notification_type', 'email_subject', 'email_body']
    
    fieldsets = (
        ('Template Type', {
            'fields': ('notification_type', 'is_active')
        }),
        ('Email Template', {
            'fields': ('email_subject', 'email_body')
        }),
        ('SMS Template', {
            'fields': ('sms_message',)
        }),
        ('Push Notification Template', {
            'fields': ('push_title', 'push_body')
        }),
    )


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_appointments', 'sms_appointments', 'push_appointments', 'updated_at']
    list_filter = [
        'email_appointments', 'email_bills', 'email_prescriptions',
        'sms_appointments', 'sms_bills', 'sms_urgent',
        'push_appointments', 'push_bills', 'push_prescriptions'
    ]
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Email Preferences', {
            'fields': (
                'email_appointments', 'email_bills', 'email_prescriptions',
                'email_medical_records', 'email_system_updates'
            )
        }),
        ('SMS Preferences', {
            'fields': ('sms_appointments', 'sms_bills', 'sms_urgent')
        }),
        ('Push Notification Preferences', {
            'fields': ('push_appointments', 'push_bills', 'push_prescriptions')
        }),
        ('General Preferences', {
            'fields': ('quiet_hours_start', 'quiet_hours_end')
        }),
    )
