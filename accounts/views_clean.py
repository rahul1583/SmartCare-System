from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from accounts.models import User

@login_required
def admin_dashboard_view(request):
    """Professional admin dashboard view"""
    if not request.user.is_admin:
        messages.error(request, 'Access denied! Admin access required.')
        return redirect('accounts:dashboard')
    
    # Get statistics
    total_users = User.objects.count()
    total_doctors = User.objects.filter(role='doctor').count()
    total_patients = User.objects.filter(role='patient').count()
    total_revenue = 125000  # Mock data - replace with actual revenue calculation
    
    context = {
        'total_users': total_users,
        'total_doctors': total_doctors,
        'total_patients': total_patients,
        'total_revenue': total_revenue,
        'system_health': 'Healthy',
        'server_uptime': '99.9%',
        'user': request.user,
    }
    
    return render(request, 'accounts/admin_dashboard_professional.html', context)
