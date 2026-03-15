from django.contrib.auth import authenticate
from accounts.models import User
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SmartCareSystem.settings')
import django
django.setup()

# Test authentication
try:
    user = authenticate(username='testpatient@gmail.com', password='test123')
    if user:
        print('Authentication SUCCESS: User found and authenticated')
        print(f'User: {user.email}, Role: {user.role}')
    else:
        print('Authentication FAILED: User not found or wrong password')
except Exception as e:
    print(f'Error: {e}')
