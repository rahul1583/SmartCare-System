from django.test import TestCase
from django.contrib.auth import authenticate
from accounts.models import User

class LoginTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            'test@gmail.com',
            'test@gmail.com', 
            'test123',
            first_name='Test',
            last_name='User',
            role='patient'
        )
    
    def test_email_authentication(self):
        # Test that email authentication works
        user = authenticate(username='test@gmail.com', password='test123')
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'test@gmail.com')
        
    def test_wrong_password(self):
        # Test that wrong password fails
        user = authenticate(username='test@gmail.com', password='wrong')
        self.assertIsNone(user)
        
    def test_nonexistent_user(self):
        # Test that nonexistent user fails
        user = authenticate(username='nonexistent@gmail.com', password='test123')
        self.assertIsNone(user)
