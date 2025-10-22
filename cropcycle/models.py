from django.db import models
from datetime import timedelta
from django.utils import timezone
from schedule.models import BaseModel, Farmer
from inventory.models import Product
from decimal import Decimal


class CropVariety(BaseModel):
    crop = models.ForeignKey("recommandations.Crop", on_delete=models.CASCADE, related_name='varieties')
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.crop.name})"

    class Meta(BaseModel.Meta):
        verbose_name_plural = "Crop Varieties"
        unique_together = ('crop', 'name')


class Schedule(BaseModel):
    crop_variety = models.ForeignKey(CropVariety, on_delete=models.CASCADE, related_name='schedules')
    name = models.CharField(max_length=255)
    season = models.CharField(max_length=100)
    def __str__(self): return self.name

class ScheduleTask(BaseModel):
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='tasks')
    stage_name = models.CharField(max_length=255)
    start_day = models.IntegerField()
    end_day = models.IntegerField()
    application_type = models.CharField(max_length=100)
    purpose_and_benefits = models.TextField()
    products = models.ManyToManyField(Product, through='TaskProduct', related_name='schedule_tasks')
    def __str__(self): return f"{self.stage_name} (Day {self.start_day}-{self.end_day}) for {self.schedule.name}"


class TaskProduct(BaseModel):
    task = models.ForeignKey("cropcycle.ScheduleTask", on_delete=models.CASCADE)
    product = models.ForeignKey("inventory.Product", on_delete=models.CASCADE)
    dosage_amount = models.DecimalField(max_digits=10, decimal_places=2)
    dosage_unit = models.CharField(max_length=50)
    dosage_per_area = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=1.0,
        help_text="Area unit this dosage is for (e.g., 1 acre, 1 hectare)"
    )
    dosage_area_unit = models.CharField(
        max_length=20,
        choices=[
            ('ACRE', 'Per Acre'),
            ('HECTARE', 'Per Hectare'),
        ],
        default='ACRE'
    )
    
    def calculate_total_for_farmer(self, farmer):
        """Calculate total product needed for a specific farmer's farm size"""
        farmer_acres = farmer.get_farm_size_in_acres()
        
        # Convert dosage area to acres
        if self.dosage_area_unit == 'HECTARE':
            dosage_acres = float(self.dosage_per_area) * 2.47105
        else:
            dosage_acres = float(self.dosage_per_area)
        
        # Calculate total = (dosage_amount / dosage_acres) * farmer_acres
        total_needed = (float(self.dosage_amount) / dosage_acres) * farmer_acres
        
        return Decimal(str(round(total_needed, 2)))
    
    def __str__(self):
        return f"{self.product.name} - {self.dosage_amount}{self.dosage_unit} per {self.dosage_per_area} {self.dosage_area_unit}"

    def __str__(self):
        return f"{self.product.name} for task: {self.task.stage_name}"

    class Meta(BaseModel.Meta):
        unique_together = ('task', 'product')


class FarmerCropCycle(BaseModel):
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='crop_cycles')
    crop_variety = models.ForeignKey(CropVariety, on_delete=models.CASCADE)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='farmer_cycles')
    sowing_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-sowing_date']

    def __str__(self):
        return f"{self.farmer.name} - {self.crop_variety.name} ({self.sowing_date})"

    def generate_tasks(self):
        """Generate all tasks for this crop cycle."""
        from tasks.models import FarmerTaskStatus  # Local import avoids circular ref
        schedule_tasks = self.schedule.tasks.all().order_by('start_day')
        for schedule_task in schedule_tasks:
            FarmerTaskStatus.objects.get_or_create(
                farmer_crop_cycle=self,
                schedule_task=schedule_task,
                defaults={
                    'planned_start_date': self.sowing_date + timedelta(days=schedule_task.start_day),
                    'planned_end_date': self.sowing_date + timedelta(days=schedule_task.end_day),
                    'status': 'PENDING',
                }
            )

    def get_progress_percentage(self):
        total = self.task_statuses.count()
        return 0 if total == 0 else int((self.task_statuses.filter(status='COMPLETED').count() / total) * 100)

    def get_completed_tasks_count(self):
        return self.task_statuses.filter(status='COMPLETED').count()

    def get_pending_tasks_count(self):
        return self.task_statuses.filter(status='PENDING').count()

    def get_overdue_tasks_count(self):
        return self.task_statuses.filter(status='OVERDUE').count()
