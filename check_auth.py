from django.contrib.auth import authenticate
from accounts.models import User

# Test authentication
user = authenticate(username='testpatient@gmail.com', password='test123')
if user:
    print('Authentication SUCCESS')
    print(f'User: {user.email}, Role: {user.role}')
else:
    print('Authentication FAILED')

# Test with admin
admin_user = authenticate(username='admin@smartcare.com', password='admin123')
if admin_user:
    print('Admin authentication SUCCESS')
    print(f'Admin: {admin_user.email}, Role: {admin_user.role}')
else:
    print('Admin authentication FAILED')
