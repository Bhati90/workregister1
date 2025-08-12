# registration/management/commands/populate_profiles.py

import csv
import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from registration.models import IndividualLabor, LabourAdvancedProfile

class Command(BaseCommand):
    help = 'Populates LabourAdvancedProfile model from an existing IndividualLabor CSV file.'

    def add_arguments(self, parser):
        # The first argument is the path to your CSV file
        parser.add_argument('csv_file_path', type=str, help='The path to the registration_individuallabor.csv file.')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file_path']
        self.stdout.write(f"Starting to populate advanced profiles from {csv_file_path}...")

        # Helper function to generate random dates
        def generate_random_dates(num_dates):
            """Generates a list of random dates within the next 6 months."""
            start_date = date.today()
            end_date = start_date + timedelta(days=180)
            date_list = []
            for _ in range(num_dates):
                random_days = random.randint(0, (end_date - start_date).days)
                random_date = start_date + timedelta(days=random_days)
                # Ensure no duplicate dates are added
                if random_date not in date_list:
                    date_list.append(random_date.strftime('%Y-%m-%d'))
            return sorted(date_list)

        try:
            with open(csv_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                created_count = 0
                updated_count = 0

                for row in reader:
                    try:
                        labour_id = int(row['id'])
                        labourer = IndividualLabor.objects.get(id=labour_id)
                        
                        # --- Generate Random Data ---
                        # 1. Generate between 10 to 30 random available dates
                        random_available_dates = generate_random_dates(random.randint(10, 30))
                        
                        # 2. Set the advanced rate based on existing wage, with a slight random adjustment (-5% to +5%)
                        base_wage = Decimal(row.get('expected_wage', '500')) # Default to 500 if not present
                        adjustment_factor = Decimal(random.uniform(0.95, 1.05))
                        advanced_rate = round(base_wage * adjustment_factor, 2)

                        # 3. Assume transport is required by default
                        transport_required = True

                        # --- Create or Update the Profile ---
                        # This safely creates a new profile or updates an existing one
                        profile, created = LabourAdvancedProfile.objects.update_or_create(
                            labour=labourer,
                            defaults={
                                'available_dates': random_available_dates,
                                'advanced_rate_per_day': advanced_rate,
                                'requires_transport': transport_required
                            }
                        )

                        if created:
                            created_count += 1
                        else:
                            updated_count += 1

                    except IndividualLabor.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f"Skipping row: Labourer with ID {row['id']} not found in the database."))
                    except (ValueError, KeyError) as e:
                        self.stdout.write(self.style.WARNING(f"Skipping row due to data error: {e} in row {row}"))

            self.stdout.write(self.style.SUCCESS(f"Population complete!"))
            self.stdout.write(f"Created: {created_count} new profiles.")
            self.stdout.write(f"Updated: {updated_count} existing profiles.")

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"Error: The file '{csv_file_path}' was not found."))