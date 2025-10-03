import random
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker

# Import your models
from registration.models import Farmer, CropDetails, Intervention

# --- Pre-defined data for realistic generation ---
CROP_TYPES = [
    "Rice", "Wheat", "Maize", "Sugarcane", "Cotton", "Soybean",
    "Groundnut", "Mustard", "Potato", "Onion", "Tomato", "Mango",
    "Banana", "Lentils", "Chickpeas", "Millet", "Sorghum", "Barley"
]

PESTICIDES = {
    "Rice": ["Buprofezin", "Acephate", "Tricyclazole"],
    "Wheat": ["Clodinafop", "Sulfosulfuron", "Propiconazole"],
    "Maize": ["Atrazine", "Pendimethalin", "Carbofuran"],
    "Sugarcane": ["Chlorantraniliprole", "Imidacloprid", "Metribuzin"],
    "Cotton": ["Acetamiprid", "Spinosad", "Profenofos"],
    "Soybean": ["Imazethapyr", "Quizalofop-ethyl", "Chlorpyrifos"],
    "Tomato": ["Dimethoate", "Mancozeb", "Imidacloprid"],
    "Potato": ["Mancozeb", "Propamocarb", "Thiamethoxam"]
}

FERTILIZERS = {
    "All": ["Urea", "DAP (Di-Ammonium Phosphate)", "MOP (Muriate of Potash)", "NPK 10:26:26"],
    "Organic": ["Vermicompost", "Neem Cake", "Farm Yard Manure (FYM)", "Jeevamrut"]
}

RECOMMENDATIONS = {
    "next_crops": ["Legumes (for nitrogen fixation)", "Green Manure crops", "Marigold (for pest control)"],
    "soil_tips": [
        "Incorporate organic matter like compost to improve soil structure.",
        "Practice crop rotation to prevent nutrient depletion.",
        "Test your soil pH and nutrient levels annually.",
        "Use cover crops during the off-season to prevent erosion."
    ]
}

class Command(BaseCommand):
    help = 'Populates the database with 500 sample farmer records.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting to populate the database...")

        fake = Faker('en_IN')
        
        # Using a transaction ensures that all records are created successfully, or none are.
        # This is faster and safer.
        with transaction.atomic():
            # Clear existing data to avoid duplicates on re-runs
            self.stdout.write("Deleting existing data...")
            Farmer.objects.all().delete()
            
            for _ in range(500):
                # 1. Create Farmer
                farmer_name = fake.name()
                phone_number = fake.unique.phone_number() # Ensure uniqueness
                farm_size = round(random.uniform(1.5, 25.0), 2)

                farmer = Farmer.objects.create(
                    farmer_name=farmer_name,
                    phone_number=phone_number,
                    farm_size_acres=farm_size
                )

                # 2. Create Crop Details
                crop_name = random.choice(CROP_TYPES)
                seeding_date = datetime.now().date() - timedelta(days=random.randint(60, 365))
                
                crop_details = CropDetails.objects.create(
                    farmer=farmer,
                    crop_name=crop_name,
                    seeding_date=seeding_date,
                    germination_date=seeding_date + timedelta(days=random.randint(7, 15)),
                    vegetative_stage_start=seeding_date + timedelta(days=random.randint(16, 30)),
                    flowering_stage_start=seeding_date + timedelta(days=random.randint(45, 60)),
                    fruiting_stage_start=seeding_date + timedelta(days=random.randint(65, 85)),
                    harvesting_date=seeding_date + timedelta(days=random.randint(100, 140)),
                    next_crop_recommendation=random.choice(RECOMMENDATIONS["next_crops"]),
                    soil_improvement_tip=random.choice(RECOMMENDATIONS["soil_tips"])
                )

                # 3. Create Interventions
                harvest_date = crop_details.harvesting_date

                # Fertilizer applications
                for _ in range(random.randint(2, 4)):
                    event_date = seeding_date + timedelta(days=random.randint(20, 90))
                    if event_date < harvest_date:
                        Intervention.objects.create(
                            crop_details=crop_details,
                            intervention_type="Fertilizer",
                            date=event_date,
                            product_used=random.choice(FERTILIZERS["All"] + FERTILIZERS["Organic"]),
                            notes="Applied as per standard dosage for this stage."
                        )

                # Pesticide applications
                for _ in range(random.randint(1, 3)):
                    event_date = seeding_date + timedelta(days=random.randint(30, 80))
                    if event_date < harvest_date:
                        crop_pesticides = PESTICIDES.get(crop_name, ["Generic Pesticide A", "Generic Pesticide B"])
                        Intervention.objects.create(
                            crop_details=crop_details,
                            intervention_type="Pesticide",
                            date=event_date,
                            product_used=random.choice(crop_pesticides),
                            notes="Preventative spraying for common pests."
                        )

                # Other activities
                Intervention.objects.create(
                    crop_details=crop_details,
                    intervention_type="Pruning/Weeding",
                    date=seeding_date + timedelta(days=random.randint(35, 50)),
                    product_used="Manual",
                    notes="Removed weeds and trimmed lower leaves."
                )

        self.stdout.write(self.style.SUCCESS('Successfully populated the database with 500 farmer records.'))