import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker
from registration.models import Farmer, CropDetails, Intervention

# --- Pre-defined data for realistic generation ---
CROP_TYPES = [
    "Rice", "Wheat", "Maize", "Sugarcane", "Cotton", "Soybean",
    "Groundnut", "Mustard", "Potato", "Onion", "Tomato", "Mango",
    "Banana", "Lentils", "Chickpeas", "Millet", "Sorghum", "Barley"
]

# Detailed intervention templates
INTERVENTION_TEMPLATES = {
    "Fertilizer": [
        {
            "activity_name": "Urea Application",
            "main_input": "Urea - 5 kg",
            "secondary_input": "Compost, Neem Oil",
            "how_to": "Mix fertilizer evenly around the base and water lightly",
            "brands": ["IFFCO Urea 46% N", "Tata Urea", "Chambal Urea"],
            "purpose": "Improve nitrogen level for faster growth",
            "cost_range": (400, 600)
        },
        {
            "activity_name": "DAP Application",
            "main_input": "DAP - 10 kg",
            "secondary_input": "Potash, Micronutrients",
            "how_to": "Apply in rows between plants, mix with soil",
            "brands": ["IFFCO DAP", "Tata DAP", "Coromandel DAP"],
            "purpose": "Boost phosphorus for root development",
            "cost_range": (800, 1200)
        },
        {
            "activity_name": "NPK Complex Application",
            "main_input": "NPK 10:26:26 - 8 kg",
            "secondary_input": "Zinc Sulfate, Boron",
            "how_to": "Broadcast evenly and irrigate immediately",
            "brands": ["Tata NPK", "IFFCO Complex", "Rallis NPK"],
            "purpose": "Balanced nutrition for overall plant health",
            "cost_range": (600, 900)
        },
        {
            "activity_name": "Organic Compost",
            "main_input": "Vermicompost - 20 kg",
            "secondary_input": "Cow dung manure, Neem cake",
            "how_to": "Spread around plant base, mix with topsoil",
            "brands": ["Local Organic", "Bio-Compost", "Green Gold"],
            "purpose": "Improve soil structure and microbial activity",
            "cost_range": (200, 400)
        }
    ],
    "Pesticide": [
        {
            "activity_name": "Fungicide Spray",
            "main_input": "Mancozeb - 500 ml",
            "secondary_input": "Sticker solution, Surfactant",
            "how_to": "Dilute in 200L water, spray on leaves uniformly",
            "brands": ["Bayer Mancozeb", "PI Industries", "Dhanuka"],
            "purpose": "Prevent fungal diseases and leaf spots",
            "cost_range": (300, 500)
        },
        {
            "activity_name": "Insecticide Application",
            "main_input": "Chlorpyrifos - 300 ml",
            "secondary_input": "Emulsifier",
            "how_to": "Mix with water, spray during early morning",
            "brands": ["Dhanuka Insecticide", "Crystal", "Shaktiman"],
            "purpose": "Control sucking pests and borers",
            "cost_range": (250, 450)
        },
        {
            "activity_name": "Bio-Pesticide Spray",
            "main_input": "Neem Oil - 1 liter",
            "secondary_input": "Garlic extract, Soap solution",
            "how_to": "Spray on both sides of leaves in evening",
            "brands": ["Nimbecidine", "Econeem Plus", "Organic Neem"],
            "purpose": "Organic pest control without chemical residue",
            "cost_range": (150, 300)
        }
    ],
    "Pruning/Weeding": [
        {
            "activity_name": "Manual Weeding",
            "main_input": "Hand tools - weeder, khurpi",
            "secondary_input": "Gloves, collection bags",
            "how_to": "Remove weeds carefully without disturbing crop roots",
            "brands": ["Manual Labor"],
            "purpose": "Reduce weed competition for nutrients",
            "cost_range": (200, 400)
        },
        {
            "activity_name": "Pruning Lower Branches",
            "main_input": "Pruning shears",
            "secondary_input": "Disinfectant solution",
            "how_to": "Cut lower branches at 45-degree angle, disinfect tools",
            "brands": ["Manual"],
            "purpose": "Improve air circulation and light penetration",
            "cost_range": (150, 300)
        }
    ],
    "Irrigation": [
        {
            "activity_name": "Drip Irrigation",
            "main_input": "Water - as per crop need",
            "secondary_input": "Fertigation if needed",
            "how_to": "Run drip system for calculated duration",
            "brands": ["Drip System"],
            "purpose": "Maintain optimal soil moisture",
            "cost_range": (100, 200)
        }
    ]
}

class Command(BaseCommand):
    help = 'Populates database with 500 sample farmers with detailed interventions'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting database population...")
        fake = Faker('en_IN')
        
        with transaction.atomic():
            self.stdout.write("Clearing existing data...")
            Farmer.objects.all().delete()
            
            for i in range(500):
                # Create Farmer
                farmer_name = fake.name()
                phone_number = f"+91{random.randint(7000000000, 9999999999)}"
                farm_size = round(random.uniform(1.5, 25.0), 2)

                farmer = Farmer.objects.create(
                    farmer_name=farmer_name,
                    phone_number=phone_number,
                    farm_size_acres=farm_size
                )

                # Create Crop Details
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
                    next_crop_recommendation=random.choice(["Legumes", "Green Manure", "Marigold"]),
                    soil_improvement_tip=random.choice([
                        "Add organic matter like compost",
                        "Practice crop rotation",
                        "Test soil pH annually"
                    ])
                )

                harvest_date = crop_details.harvesting_date
                
                # Create detailed interventions
                intervention_days = [15, 20, 30, 35, 45, 50, 60, 65, 75, 80, 90]
                
                for day in intervention_days:
                    event_date = seeding_date + timedelta(days=day)
                    if event_date >= harvest_date:
                        break
                    
                    # Determine intervention type based on crop stage
                    if day < 30:
                        int_type = "Fertilizer"
                    elif day < 60:
                        int_type = random.choice(["Fertilizer", "Pesticide", "Pruning/Weeding"])
                    else:
                        int_type = random.choice(["Pesticide", "Irrigation"])
                    
                    template = random.choice(INTERVENTION_TEMPLATES.get(int_type, []))
                    if not template:
                        continue
                    
                    cost = round(random.uniform(*template["cost_range"]), 2)
                    
                    Intervention.objects.create(
                        crop_details=crop_details,
                        intervention_type=int_type,
                        date=event_date,
                        day_number_from_planting=day,
                        activity_name=template["activity_name"],
                        main_input_values=template["main_input"],
                        secondary_input_values=template["secondary_input"],
                        how_to_do_it=template["how_to"],
                        price_cost=cost,
                        product_catalog_brand=random.choice(template["brands"]),
                        purpose_goal=template["purpose"],
                        product_used=template["main_input"].split('-')[0].strip(),
                        notes=f"Applied on day {day} from planting"
                    )
                
                if (i + 1) % 50 == 0:
                    self.stdout.write(f"Created {i + 1} farmers...")

        self.stdout.write(self.style.SUCCESS(
            'Successfully populated database with 500 detailed farmer records!'
        ))