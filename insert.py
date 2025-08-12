import json
import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yourproject.settings')  # replace with your project name
django.setup()

from .registration.models import LabourNeed  # replace with your app name

# Load the JSON file
with open('labour_data.json', 'r') as f:
    data = json.load(f)

# Insert into DB
for item in data:
    LabourNeed.objects.create(
        job_id=item['job_id'],
        farmer=item['farmer'],
        created_at=item['created_at'],
        labour_count=item['labour_count'],
        activities=item['activities'],
        date_needed=item['date_needed'],
        is_completed=item['is_completed'],
        notes=item['notes'],
        location=item['location'],
        price=item['price']
    )

print("✅ Data inserted successfully!")
