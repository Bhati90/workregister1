import random
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.geos import Point

# Import all your models
from registration.models import (
    Job, JobLeaderResponse, JobAssignment, Notification, WorkerStatus,
    IndividualLabor, Mukkadam, Transport, Others
)

class Command(BaseCommand):
    help = 'Populates the database with sample data using the 4 registration types.'

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write("Deleting old data...")
        # Clean up in reverse order of dependency
        JobAssignment.objects.all().delete()
        WorkerStatus.objects.all().delete()
        JobLeaderResponse.objects.all().delete()
        Notification.objects.all().delete()
        Job.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        IndividualLabor.objects.all().delete()
        Mukkadam.objects.all().delete()
        Transport.objects.all().delete()
        Others.objects.all().delete()

        self.stdout.write("Creating new data...")
        
        # A list to hold all created worker/provider objects, regardless of type
        all_workers_and_providers = []

        # 1. Create Individual Laborers
        for i in range(10):
            laborer = IndividualLabor.objects.create(
                full_name=f'Individual Worker {i+1}',
                mobile_number=f'+9198765432{i:02d}',
                taluka='Bengaluru South', village='Koramangala',
                category='individual_labor',
                location=Point(77.61, 12.93), # Lng, Lat for Bengaluru
                gender=random.choice(['male', 'female']),
                age=random.randint(20, 50),
                primary_source_income='Agriculture',
                skill_harvesting=True,
                employment_type='seasonal',
                willing_to_migrate='travel_day_close_home',
                expected_wage=Decimal(random.uniform(700.0, 950.0)),
                availability='Available from next week',
                data_sharing_agreement=True,
            )
            all_workers_and_providers.append(laborer)
        self.stdout.write(self.style.SUCCESS(f"{IndividualLabor.objects.count()} Individual Laborers created."))

        # 2. Create Mukkadams (Labor contractors)
        for i in range(3):
            mukkadam = Mukkadam.objects.create(
                full_name=f'Mukkadam {i+1}',
                mobile_number=f'+9198765433{i:02d}',
                taluka='Bengaluru North', village='Hebbal',
                category='mukkadam',
                location=Point(77.59, 13.03), # Lng, Lat for Bengaluru
                providing_labour_count=random.randint(10, 50),
                total_workers_peak=random.randint(50, 100),
                expected_charges=Decimal(random.uniform(100.0, 200.0)),
                labour_supply_availability='All year round',
                arrange_transport='owned',
                data_sharing_agreement=True,
            )
            all_workers_and_providers.append(mukkadam)
        self.stdout.write(self.style.SUCCESS(f"{Mukkadam.objects.count()} Mukkadams created."))
        
        # 3. Create Transport Providers
        for i in range(5):
            transport = Transport.objects.create(
                full_name=f'Transport Provider {i+1}',
                mobile_number=f'+9198765434{i:02d}',
                taluka='Anekal', village='Electronic City',
                category='transport',
                location=Point(77.67, 12.84), # Lng, Lat for Bengaluru
                vehicle_type=random.choice(['Tata Ace', 'Minibus', 'Jeep']),
                people_capacity=random.randint(8, 20),
                expected_fair=Decimal(random.uniform(1500.0, 3000.0)),
                availability='With 1 day notice',
                data_sharing_agreement=True,
            )
            all_workers_and_providers.append(transport)
        self.stdout.write(self.style.SUCCESS(f"{Transport.objects.count()} Transport providers created."))
        
        # 4. Create Users (for finalized_leader, assigned_by)
        admin_user = User.objects.create_superuser(username='admin', password='password123', email='admin@example.com')
        self.stdout.write(self.style.SUCCESS("Admin user created."))

        # 5. Create Jobs
        jobs = []
        for i in range(5):
            job = Job.objects.create(
                title=f'Grape Harvesting Project #{i+1}',
                location=random.choice(['Devanahalli', 'Nandi Hills', 'Chikkaballapur']),
                workers_needed=random.randint(10, 20),
                duration_days=random.randint(15, 30),
                rate_per_day=Decimal(random.uniform(800.0, 1200.0)),
                required_by_date=date.today() + timedelta(days=random.randint(10, 40)),
                status='open_for_bidding'
            )
            jobs.append(job)
        self.stdout.write(self.style.SUCCESS(f"{len(jobs)} jobs created."))

        # 6. Assign workers/providers to a Job
        # Take the first job and assign a mix of workers/providers to it
        job_to_assign = jobs[0]
        job_to_assign.status = 'ongoing'
        # Let's say one of the Mukkadams is the leader for this job
        final_leader_mukkadam = Mukkadam.objects.first()
        # The 'finalized_leader' field needs a User object. Let's create one for the Mukkadam.
        leader_user, _ = User.objects.get_or_create(username=final_leader_mukkadam.mobile_number, defaults={'first_name': final_leader_mukkadam.full_name})
        job_to_assign.finalized_leader = leader_user
        job_to_assign.save()

        # Get a random sample from our list containing all types of workers/providers
        workers_for_job = random.sample(all_workers_and_providers, k=min(len(all_workers_and_providers), 5))

        for worker_or_provider in workers_for_job:
            JobAssignment.objects.create(
                job=job_to_assign,
                laborer=worker_or_provider,  # <-- The GFK handles any object type here!
                assigned_by=admin_user,
            )
            # Update the status of this worker/provider
            WorkerStatus.objects.update_or_create(
                # Get the ContentType for the specific object's class
                content_type=ContentType.objects.get_for_model(worker_or_provider),
                object_id=worker_or_provider.id,
                defaults={
                    'availability_status': 'booked',
                    'current_job': job_to_assign
                }
            )

        self.stdout.write(self.style.SUCCESS(f"Assigned {len(workers_for_job)} mixed workers/providers to '{job_to_assign.title}'."))
        self.stdout.write(self.style.SUCCESS("Database population complete!"))