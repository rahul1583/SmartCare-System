from django.contrib.auth import authenticate
from accounts.models import User

print("Testing authentication...")
print("Available users:")
for user in User.objects.all():
    print(f"  {user.email} - {user.role}")

# Test with existing user
print("\nTesting authentication with testpatient@gmail.com...")
user = authenticate(username='testpatient@gmail.com', password='test123')
if user:
    print(f"SUCCESS: Authenticated user {user.email}")
else:
    print("FAILED: Authentication failed")

# Test with admin
print("\nTesting authentication with admin@smartcare.com...")
admin = authenticate(username='admin@smartcare.com', password='admin123')
if admin:
    print(f"SUCCESS: Authenticated admin {admin.email}")
else:
    print("FAILED: Admin authentication failed")
