
import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SmartCareSystem.settings')
django.setup()

from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.adapter import get_adapter
from django.test import RequestFactory

def check_apps():
    print("--- Database Apps ---")
    apps = SocialApp.objects.all()
    for app in apps:
        print(f"ID: {app.id}, Provider: {app.provider}, Client ID: {app.client_id}, Sites: {[site.id for site in app.sites.all()]}")
    
    if not apps:
        print("No SocialApp records found in database.")

    print("\n--- Adapter Check ---")
    factory = RequestFactory()
    request = factory.get('/')
    adapter = get_adapter(request)
    
    try:
        app = adapter.get_app(request, provider='google')
        print(f"Adapter found app: {app}")
        print(f"App provider: {app.provider}")
        print(f"App client_id: {app.client_id}")
    except Exception as e:
        print(f"Adapter failed to find app: {type(e).__name__}: {e}")

if __name__ == "__main__":
    check_apps()
