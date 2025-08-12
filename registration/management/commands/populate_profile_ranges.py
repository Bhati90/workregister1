# registration/management/commands/populate_profile_ranges.py

import csv
import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from registration.models import IndividualLabor, LaboursAdvancedProfiles

class Command(BaseCommand):
    help = 'Populates LabourAdvancedProfile model with availability date RANGES.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file_path', type=str, help='The path to the registration_individuallabor.csv file.')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file_path']
        self.stdout.write(f"Starting to populate advanced profiles with date ranges from {csv_file_path}...")

        created_count = 0
        updated_count = 0

        try:
            with open(csv_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for row in reader:
                    try:
                        labour_id = int(row['id'])
                        labourer = IndividualLabor.objects.get(id=labour_id)
                        
                        # --- Generate Random Data for the new structure ---
                        
                        # 1. Generate a random availability period
                        # Availability starts sometime in the next 90 days
                        start_day_offset = random.randint(1, 90)
                        available_from_date = date.today() + timedelta(days=start_day_offset)
                        
                        # The labourer is available for a random duration between 20 and 75 days
                        availability_duration = random.randint(20, 75)
                        available_to_date = available_from_date + timedelta(days=availability_duration)
                        
                        # 2. Set the advanced rate based on existing wage
                        base_wage = Decimal(row.get('expected_wage', '500'))
                        adjustment_factor = Decimal(random.uniform(0.95, 1.05))
                        advanced_rate = round(base_wage * adjustment_factor, 2)

                        # --- Create or Update the Profile ---
                        profile, created = LaboursAdvancedProfiles.objects.update_or_create(
                            labour=labourer,
                            defaults={
                                'available_from': available_from_date,
                                'available_to': available_to_date,
                                'advanced_rate_per_day': advanced_rate,
                                'requires_transport': True # Defaulting to True
                            }
                        )

                        if created:
                            created_count += 1
                        else:
                            updated_count += 1

                    except IndividualLabor.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f"Skipping: Labourer with ID {row['id']} not found."))
                    except (ValueError, KeyError) as e:
                        self.stdout.write(self.style.WARNING(f"Skipping row due to data error: {e}"))

            self.stdout.write(self.style.SUCCESS("Population with date ranges complete!"))
            self.stdout.write(f"Created: {created_count} new profiles.")
            self.stdout.write(f"Updated: {updated_count} existing profiles.")

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"Error: File '{csv_file_path}' not found."))