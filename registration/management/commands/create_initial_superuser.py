import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    """
    A Django management command to create a superuser from environment variables.
    
    This command is idempotent, meaning it can be run multiple times without
    creating duplicate users or causing errors. It checks if a user with the
    specified username already exists before attempting to create one.
    """
    help = 'Creates a superuser from environment variables if one does not exist'

    def handle(self, *args, **options):
        # Read credentials from environment variables
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        # Check if all required environment variables are set
        if not all([username, email, password]):
            self.stdout.write(self.style.ERROR(
                'Missing superuser environment variables. Please set DJANGO_SUPERUSER_USERNAME, '
                'DJANGO_SUPERUSER_EMAIL, and DJANGO_SUPERUSER_PASSWORD.'
            ))
            return

        # Check if a superuser with that username already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'Superuser "{username}" already exists. Skipping.'))
        else:
            # Create the superuser
            self.stdout.write(self.style.SUCCESS(f'Creating superuser account for {username}'))
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(self.style.SUCCESS('Superuser created successfully!'))