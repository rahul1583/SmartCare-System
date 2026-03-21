from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from notifications.models import NotificationPreference

User = get_user_model()


class Command(BaseCommand):
    help = 'Create notification preferences for all existing users'
    
    def handle(self, *args, **options):
        users_without_preferences = User.objects.filter(notification_preferences__isnull=True)
        
        created_count = 0
        for user in users_without_preferences:
            NotificationPreference.objects.create(user=user)
            created_count += 1
            self.stdout.write(f'Created preferences for {user.get_full_name() or user.email}')
        
        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created notification preferences for {created_count} users')
            )
        else:
            self.stdout.write(
                self.style.WARNING('All users already have notification preferences')
            )
