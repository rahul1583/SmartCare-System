from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.http import JsonResponse
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta

from .models import Notification, NotificationPreference


@login_required
def notification_list(request):
    """View all notifications for the user"""
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    
    # Mark all notifications as read when user visits the page
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    
    context = {
        'notifications': notifications,
    }
    
    return render(request, 'notifications/notification_list.html', context)


@login_required
def notification_detail(request, notification_id):
    """View notification details and mark as read"""
    notification = Notification.objects.get(id=notification_id, recipient=request.user)
    
    # Mark as read
    notification.mark_as_read()
    
    context = {
        'notification': notification,
    }
    
    return render(request, 'notifications/notification_detail.html', context)


@login_required
def mark_notification_read(request, notification_id):
    """Mark notification as read (AJAX)"""
    if request.method == 'POST':
        try:
            notification = Notification.objects.get(id=notification_id, recipient=request.user)
            notification.mark_as_read()
            
            return JsonResponse({
                'success': True,
                'unread_count': Notification.objects.filter(recipient=request.user, is_read=False).count()
            })
        except Notification.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Notification not found'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read (AJAX)"""
    if request.method == 'POST':
        unread_notifications = Notification.objects.filter(recipient=request.user, is_read=False)
        count = unread_notifications.count()
        
        unread_notifications.update(is_read=True, read_at=timezone.now())
        
        return JsonResponse({
            'success': True,
            'marked_count': count,
            'unread_count': 0
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def delete_notification(request, notification_id):
    """Delete notification (AJAX)"""
    if request.method == 'POST':
        try:
            notification = Notification.objects.get(id=notification_id, recipient=request.user)
            notification.delete()
            
            return JsonResponse({
                'success': True,
                'unread_count': Notification.objects.filter(recipient=request.user, is_read=False).count()
            })
        except Notification.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Notification not found'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def notification_preferences(request):
    """View and update notification preferences"""
    preferences, created = NotificationPreference.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Update preferences
        preferences.email_appointments = request.POST.get('email_appointments') == 'on'
        preferences.email_bills = request.POST.get('email_bills') == 'on'
        preferences.email_prescriptions = request.POST.get('email_prescriptions') == 'on'
        preferences.email_medical_records = request.POST.get('email_medical_records') == 'on'
        preferences.email_system_updates = request.POST.get('email_system_updates') == 'on'
        
        preferences.sms_appointments = request.POST.get('sms_appointments') == 'on'
        preferences.sms_bills = request.POST.get('sms_bills') == 'on'
        preferences.sms_urgent = request.POST.get('sms_urgent') == 'on'
        
        preferences.push_appointments = request.POST.get('push_appointments') == 'on'
        preferences.push_bills = request.POST.get('push_bills') == 'on'
        preferences.push_prescriptions = request.POST.get('push_prescriptions') == 'on'
        
        # Handle quiet hours
        quiet_hours_start = request.POST.get('quiet_hours_start')
        quiet_hours_end = request.POST.get('quiet_hours_end')
        
        preferences.quiet_hours_start = quiet_hours_start if quiet_hours_start else None
        preferences.quiet_hours_end = quiet_hours_end if quiet_hours_end else None
        
        preferences.save()
        
        return redirect('notifications:preferences')
    
    context = {
        'preferences': preferences,
    }
    
    return render(request, 'notifications/preferences.html', context)


@login_required
def notification_widget(request):
    """Notification widget for header (AJAX)"""
    notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).order_by('-created_at')[:5]
    
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count,
    }
    
    return render(request, 'notifications/widget.html', context)


class NotificationListView(LoginRequiredMixin, ListView):
    """Class-based view for notification list"""
    model = Notification
    template_name = 'notifications/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Notification.objects.filter(recipient=self.request.user)
        
        # Apply filters
        is_read = self.request.GET.get('is_read')
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read == 'true')
        
        notification_type = self.request.GET.get('type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        priority = self.request.GET.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unread_count'] = Notification.objects.filter(
            recipient=self.request.user, 
            is_read=False
        ).count()
        return context


@login_required
def notification_stats(request):
    """Get notification statistics (AJAX)"""
    stats = {
        'total': Notification.objects.filter(recipient=request.user).count(),
        'unread': Notification.objects.filter(recipient=request.user, is_read=False).count(),
        'by_type': list(
            Notification.objects.filter(recipient=request.user)
            .values('notification_type')
            .annotate(count=Count('id'))
            .order_by('-count')
        ),
        'by_priority': {
            'urgent': Notification.objects.filter(recipient=request.user, priority='urgent').count(),
            'high': Notification.objects.filter(recipient=request.user, priority='high').count(),
            'medium': Notification.objects.filter(recipient=request.user, priority='medium').count(),
            'low': Notification.objects.filter(recipient=request.user, priority='low').count(),
        },
        'recent': Notification.objects.filter(
            recipient=request.user,
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()
    }
    
    return JsonResponse(stats)
