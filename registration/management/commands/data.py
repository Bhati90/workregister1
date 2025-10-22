"""
Django management command to populate complete system with sample data
Location: advisory/management/commands/populate_all_data.py (or inventory/management/commands/)
Run: python manage.py populate_all_data
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import random

from inventory.models import Company, ProductCategory, Product, ProductSKU
from schedule.models import (
    Farmer)

from cropcycle.models import (
     CropVariety, Schedule, ScheduleTask, 
    TaskProduct, FarmerCropCycle
)
from recommandations.models import CropSpecificBenefit ,Crop
from tasks.models import FarmerTaskStatus

class Command(BaseCommand):
    help = 'Populate complete system with bilingual data'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS('Starting Complete Data Population...'))
        self.stdout.write(self.style.SUCCESS('='*70))
        
        # # Create all data
        # sahyadri = self.create_company()
        # self.stdout.write(self.style.SUCCESS('✓ Company created'))
        
        # categories = self.create_categories()
        # self.stdout.write(self.style.SUCCESS(f'✓ {len(categories)} categories created'))
        
        # products = self.create_products(sahyadri, categories)
        # self.stdout.write(self.style.SUCCESS(f'✓ {len(products)} products created'))
        
        # grape_crop, varieties = self.create_grape_varieties()
        # self.stdout.write(self.style.SUCCESS(f'✓ Crop and {len(varieties)} varieties created'))
        
        # schedules = self.create_schedules(varieties, products)
        # self.stdout.write(self.style.SUCCESS(f'✓ {len(schedules)} schedules created'))
        
        # self.create_crop_benefits(products, grape_crop)
        # self.stdout.write(self.style.SUCCESS('✓ Crop benefits created'))
        
        # farmers = self.create_sample_farmers()
        # self.stdout.write(self.style.SUCCESS(f'✓ {len(farmers)} farmers created'))
        
        # cycles = self.create_farmer_cycles(farmers, varieties, schedules)
        # self.stdout.write(self.style.SUCCESS(f'✓ {len(cycles)} crop cycles created'))
        
        # tasks_created = self.create_task_statuses(cycles)
        # self.stdout.write(self.style.SUCCESS(f'✓ {tasks_created} task statuses created'))
        
        # self.stdout.write(self.style.SUCCESS('='*70))
        # self.stdout.write(self.style.SUCCESS('✅ DATA POPULATION COMPLETED!'))
        # self.stdout.write(self.style.SUCCESS('='*70))
        # self.print_summary(farmers, cycles, tasks_created)

    def create_sample_farmers(self):
        farmers_data = [
            ('Rajesh Patil', '9876543210', 5.0, 'ACRE'),
            ('Suresh Kumar', '9876543211', 3.5, 'ACRE'),
            ('Ramesh Deshmukh', '9876543212', 7.0, 'ACRE'),
            ('Prakash Jadhav', '9876543213', 2.5, 'ACRE'),
            ('Santosh More', '9876543214', 10.0, 'ACRE'),
            ('Vijay Shinde', '9876543215', 4.0, 'ACRE'),
            ('Ganesh Pawar', '9876543216', 6.5, 'ACRE'),
            ('Mahesh Kulkarni', '9876543217', 8.0, 'ACRE'),
            ('Dinesh Bhosale', '9876543218', 3.0, 'ACRE'),
            ('Anil Gaikwad', '9876543219', 5.5, 'ACRE'),
        ]
        
        farmers = []
        for name, phone, farm_size, unit in farmers_data:
            farmer, _ = Farmer.objects.get_or_create(
                phone_number=phone,
                defaults={
                    'name': name,
                    'farm_size': Decimal(str(farm_size)),
                    'farm_size_unit': unit
                }
            )
            farmers.append(farmer)
        
        return farmers

    def create_schedules(self, varieties, products):
        schedules = {}
        
        for variety_key, variety in varieties.items():
            schedule, _ = Schedule.objects.get_or_create(
                crop_variety=variety,
                name=f'{variety_key} - October Schedule 2025-26',
                defaults={'season': 'October 2025-26'}
            )
            
            # Create tasks
            tasks_data = [
                {'stage': 'Leaf Fall', 'start': -15, 'end': -15, 'type': 'Spray', 'purpose': 'Defoliation', 'products': []},
                {'stage': 'Pasting', 'start': 0, 'end': 0, 'type': 'Paste', 'purpose': 'Dormancy breaking', 'products': [('13:00:45', 50, 'gm', 1, 'ACRE')]},
                {'stage': 'Green Point', 'start': 9, 'end': 10, 'type': 'Spray', 'purpose': 'Early growth', 'products': [('00:49:32', 2, 'gm', 1, 'ACRE'), ('Jeshtha', 0.5, 'gm', 1, 'ACRE')]},
                {'stage': '50% Flowering', 'start': 30, 'end': 35, 'type': 'Spray', 'purpose': 'Fruit set', 'products': [('Ardra', 0.5, 'gm', 1, 'ACRE')]},
                {'stage': 'Fruit Set', 'start': 40, 'end': 45, 'type': 'Spray', 'purpose': 'Berry development', 'products': [('Vitaflora', 5, 'ml', 1, 'ACRE'), ('Ek-Lon Max', 2.5, 'ml', 1, 'ACRE')]},
                {'stage': 'Berry 6-8mm', 'start': 53, 'end': 56, 'type': 'Spray', 'purpose': 'Berry sizing', 'products': [('Vitaflora', 5, 'ml', 1, 'ACRE'), ('Kamab 26', 2.5, 'ml', 1, 'ACRE')]},
                {'stage': 'Berry 10-12mm', 'start': 65, 'end': 67, 'type': 'Spray', 'purpose': 'Size enhancement', 'products': [('Kamab 26', 2.5, 'ml', 1, 'ACRE'), ('Hasta', 0.5, 'gm', 1, 'ACRE')]},
                {'stage': 'Color Development', 'start': 85, 'end': 87, 'type': 'Spray', 'purpose': 'Color enhancement', 'products': [('Pharmamin-M', 2.5, 'ml', 1, 'ACRE'), ('Silicio', 1.5, 'ml', 1, 'ACRE')]},
            ]
            
            for task_data in tasks_data:
                task = ScheduleTask.objects.create(
                    schedule=schedule,
                    stage_name=task_data['stage'],
                    start_day=task_data['start'],
                    end_day=task_data['end'],
                    application_type=task_data['type'],
                    purpose_and_benefits=task_data['purpose']
                )
                
                for prod_data in task_data['products']:
                    prod_name, dosage, unit, per_area, area_unit = prod_data
                    if prod_name in products:
                        TaskProduct.objects.create(
                            task=task,
                            product=products[prod_name],
                            dosage_amount=Decimal(str(dosage)),
                            dosage_unit=unit,
                            dosage_per_area=Decimal(str(per_area)),
                            dosage_area_unit=area_unit
                        )
            
            schedules[variety_key] = schedule
        
        return schedules
    def create_products(self, company, categories):
        products = {}
        product_data = [
            ('13:00:45', 'fertilizers', 'NPK 13:00:45', '25kg', 2900.00, 100),
            ('00:52:34', 'fertilizers', 'MKP 00:52:34', '25kg', 3670.00, 50),
            ('00:00:50', 'fertilizers', 'SOP 00:00:50', '25kg', 2150.00, 75),
            ('00:49:32', 'fertilizers', 'MKP 00:49:32', '5kg', 700.00, 200),  # Smaller pack
            ('Ardra', 'bio_products', 'Trichoderma Viride', '100gm', 150.00, 500),
            ('Jeshtha', 'bio_products', 'Bacillus Subtilis', '100gm', 150.00, 300),
            ('Hasta', 'bio_products', 'Multi Beneficial Virus', '100gm', 370.00, 200),
            ('Vitaflora', 'micronutrients', 'Multi Micronutrients', '1ltr', 490.00, 400),
            ('Vitaflora', 'micronutrients', 'Multi Micronutrients', '500ml', 270.00, 600),  # Multiple SKUs
            ('Kamab 26', 'micronutrients', 'K Adriatica', '1ltr', 970.00, 250),
            ('Pharmamin-M', 'micronutrients', 'Amino Acids', '1ltr', 1350.00, 150),
            ('Zincmor', 'micronutrients', 'Zinc Sulphate', '1ltr', 1233.00, 180),
            ('Silicio', 'micronutrients', 'Ortho Silicic Acid', '1ltr', 1110.00, 220),
            ('Ek-Lon Max', 'pgr', 'Seaweed Extract', '1ltr', 1060.00, 300),
            ('Bombardier', 'pgr', 'Potassium Nitrate', '1ltr', 700.00, 350),
        ]
        
        for name, cat_key, tech, size, price, stock in product_data:
            product, _ = Product.objects.get_or_create(
                company=company,
                name=name,
                defaults={
                    'category': categories[cat_key],
                    'technical_composition': tech
                }
            )
            
            ProductSKU.objects.get_or_create(
                product=product,
                size=size,
                defaults={
                    'price': Decimal(str(price)),
                    'stock_quantity': stock,
                    'reorder_level': 10,
                    'max_stock_level': 1000
                }
            )
            
            products[name] = product
        
        return products
    # def print_summary(self, farmers, cycles, tasks_created):
    #     self.stdout.write('')
    #     self.stdout.write(self.style.SUCCESS('📊 SUMMARY:'))
    #     self.stdout.write(f'   • Farmers: {len(farmers)}')
    #     self.stdout.write(f'   • Crop Cycles: {len(cycles)}')
    #     self.stdout.write(f'   • Task Statuses: {tasks_created}')
    #     self.stdout.write(f'   • Products: {Product.objects.count()}')
    #     self.stdout.write(f'   • Schedules: {Schedule.objects.count()}')
    #     self.stdout.write('')
    #     self.stdout.write(self.style.WARNING('🌐 ACCESS YOUR SYSTEM:'))
    #     self.stdout.write('   • Farmers: /advisory/farmers/')
    #     self.stdout.write('   • Crop Cycles: /advisory/crop-cycles/')
    #     self.stdout.write('   • Tasks: /advisory/tasks/')
    #     self.stdout.write('   • Products: /inventory/')
    #     self.stdout.write('')