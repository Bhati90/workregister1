from django.core.management.base import BaseCommand
from django.db import transaction
from tasks.models import FarmerTaskStatus
from cropcycle.models import FarmerCropCycle

class Command(BaseCommand):
    help = 'Recalculate all task dates with cascading logic'

    @transaction.atomic
    def handle(self, *args, **options):
        cycles = FarmerCropCycle.objects.filter(is_active=True)
        total_updated = 0
        
        self.stdout.write(self.style.WARNING('Starting recalculation...'))
        
        for cycle in cycles:
            self.stdout.write(f'\nProcessing: {cycle.farmer.name} - {cycle.crop_variety.name}')
            
            tasks = FarmerTaskStatus.objects.filter(
                farmer_crop_cycle=cycle
            ).order_by('schedule_task__start_day')
            
            previous_task = None
            
            for task in tasks:
                if previous_task and task.status != 'COMPLETED':
                    if task.recalculate_from_previous():
                        total_updated += 1
                        self.stdout.write(
                            f'  ✓ Updated: {task.schedule_task.stage_name}'
                        )
                
                previous_task = task
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Recalculated {total_updated} tasks across {cycles.count()} cycles')
        )