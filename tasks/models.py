# from django.db import models
# from django.utils import timezone
# from datetime import timedelta
# from schedule.models import BaseModel

# class FarmerTaskStatus(BaseModel):
#     class StatusChoices(models.TextChoices):
#         PENDING = 'PENDING', 'Pending'
#         COMPLETED = 'COMPLETED', 'Completed'
#         OVERDUE = 'OVERDUE', 'Overdue'

#     farmer_crop_cycle = models.ForeignKey("cropcycle.FarmerCropCycle", on_delete=models.CASCADE, related_name='task_statuses')
#     schedule_task = models.ForeignKey("cropcycle.ScheduleTask", on_delete=models.CASCADE, related_name='farmer_tasks')
#     planned_start_date = models.DateField()
#     planned_end_date = models.DateField()
#     actual_completion_date = models.DateField(blank=True, null=True)
#     status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)
#     delay_days = models.IntegerField(default=0, help_text="Number of days delayed")
#     delay_reason = models.TextField(blank=True, null=True, help_text="Reason for delay")
#     delay_date = models.DateField(blank=True, null=True, help_text="Date when delay was recorded")

#     def mark_complete(self, completion_date=None):
#         if completion_date is None:
#             completion_date = timezone.now().date()
#         self.status = 'COMPLETED'
#         self.actual_completion_date = completion_date
#         if completion_date > self.planned_end_date:
#             self.delay_days = (completion_date - self.planned_end_date).days
#         self.save()
#         self.check_cycle_completion()

#     def add_delay(self, delay_days, reason=None):
#         self.delay_days = delay_days
#         self.delay_reason = reason
#         self.delay_date = timezone.now().date()
#         self.planned_start_date += timedelta(days=delay_days)
#         self.planned_end_date += timedelta(days=delay_days)
#         self.save()

#     def check_cycle_completion(self):
#         cycle = self.farmer_crop_cycle
#         all_tasks = cycle.task_statuses.all()
#         if all_tasks.filter(status='COMPLETED').count() == all_tasks.count():
#             self.activate_next_schedule()

#     def activate_next_schedule(self):
#         from cropcycle.models import Schedule, FarmerCropCycle
#         cycle = self.farmer_crop_cycle
#         current_schedule = cycle.schedule
#         crop_variety = cycle.crop_variety

#         next_schedule = Schedule.objects.filter(
#             crop_variety=crop_variety,
#             season=current_schedule.season,
#             id__gt=current_schedule.id
#         ).order_by('id').first()

#         if not next_schedule:
#             next_schedule = Schedule.objects.filter(
#                 crop_variety=crop_variety,
#                 season=current_schedule.season
#             ).exclude(id=current_schedule.id).first()

#         if next_schedule:
#             new_cycle = FarmerCropCycle.objects.create(
#                 farmer=cycle.farmer,
#                 crop_variety=crop_variety,
#                 schedule=next_schedule,
#                 sowing_date=timezone.now().date(),
#                 is_active=True
#             )
#             cycle.is_active = False
#             cycle.save()
#             self.generate_tasks_for_cycle(new_cycle)
#             return new_cycle

#         return None

#     def generate_tasks_for_cycle(self, cycle):
#         schedule_tasks = cycle.schedule.tasks.all().order_by('start_day')
#         for schedule_task in schedule_tasks:
#             self.__class__.objects.create(
#                 farmer_crop_cycle=cycle,
#                 schedule_task=schedule_task,
#                 planned_start_date=cycle.sowing_date + timedelta(days=schedule_task.start_day),
#                 planned_end_date=cycle.sowing_date + timedelta(days=schedule_task.end_day),
#                 status='PENDING'
#             )


from django.db import models
from django.utils import timezone
from datetime import timedelta
from schedule.models import BaseModel

class FarmerTaskStatus(BaseModel):
    class StatusChoices(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        OVERDUE = 'OVERDUE', 'Overdue'

    farmer_crop_cycle = models.ForeignKey(
        "cropcycle.FarmerCropCycle", 
        on_delete=models.CASCADE, 
        related_name='task_statuses'
    )
    schedule_task = models.ForeignKey(
        "cropcycle.ScheduleTask", 
        on_delete=models.CASCADE, 
        related_name='farmer_tasks'
    )
    planned_start_date = models.DateField()
    planned_end_date = models.DateField()
    actual_completion_date = models.DateField(blank=True, null=True)
    status = models.CharField(
        max_length=20, 
        choices=StatusChoices.choices, 
        default=StatusChoices.PENDING
    )
    delay_days = models.IntegerField(default=0, help_text="Number of days delayed")
    delay_reason = models.TextField(blank=True, null=True, help_text="Reason for delay")
    delay_date = models.DateField(blank=True, null=True, help_text="Date when delay was recorded")

    class Meta:
        ordering = ['farmer_crop_cycle', 'schedule_task__start_day']
        verbose_name = 'Farmer Task Status'
        verbose_name_plural = 'Farmer Task Statuses'

    def __str__(self):
        return f"{self.farmer_crop_cycle.farmer.name} - {self.schedule_task.stage_name}"

    def mark_complete(self, completion_date=None):
        """Mark task as complete and cascade updates to subsequent tasks"""
        if completion_date is None:
            completion_date = timezone.now().date()
        
        self.status = 'COMPLETED'
        self.actual_completion_date = completion_date
        
        # Calculate delay
        if completion_date > self.planned_end_date:
            delay_days = (completion_date - self.planned_end_date).days
            self.delay_days = delay_days
            self.delay_date = completion_date
            
            # Cascade the delay to subsequent tasks
            self._cascade_delay_to_subsequent_tasks(delay_days)
        
        self.save()
        self.check_cycle_completion()

    def add_delay(self, delay_days, reason=None):
        """Add delay to this task and cascade to subsequent tasks"""
        if delay_days <= 0:
            return
        
        self.delay_days = delay_days
        self.delay_reason = reason
        self.delay_date = timezone.now().date()
        
        # Update this task's dates
        self.planned_start_date += timedelta(days=delay_days)
        self.planned_end_date += timedelta(days=delay_days)
        
        # Update status based on new dates
        self._update_status()
        self.save()
        
        # Cascade to subsequent tasks
        self._cascade_delay_to_subsequent_tasks(delay_days)

    def _cascade_delay_to_subsequent_tasks(self, delay_days):
        """Update all subsequent tasks in this crop cycle"""
        # Get all tasks in this cycle that come after this one
        subsequent_tasks = FarmerTaskStatus.objects.filter(
            farmer_crop_cycle=self.farmer_crop_cycle,
            schedule_task__start_day__gt=self.schedule_task.start_day
        ).order_by('schedule_task__start_day')
        
        for task in subsequent_tasks:
            # Only update if not already completed
            if task.status != 'COMPLETED':
                task.planned_start_date += timedelta(days=delay_days)
                task.planned_end_date += timedelta(days=delay_days)
                task._update_status()
                task.save()

    def _update_status(self):
        """Update status based on current date and completion"""
        today = timezone.now().date()
        
        if self.actual_completion_date:
            self.status = 'COMPLETED'
        elif today > self.planned_end_date:
            self.status = 'OVERDUE'
        elif self.planned_start_date <= today <= self.planned_end_date:
            self.status = 'IN_PROGRESS'
        else:
            self.status = 'PENDING'

    def get_previous_task(self):
        """Get the previous task in sequence"""
        return FarmerTaskStatus.objects.filter(
            farmer_crop_cycle=self.farmer_crop_cycle,
            schedule_task__start_day__lt=self.schedule_task.start_day
        ).order_by('-schedule_task__start_day').first()

    def get_next_task(self):
        """Get the next task in sequence"""
        return FarmerTaskStatus.objects.filter(
            farmer_crop_cycle=self.farmer_crop_cycle,
            schedule_task__start_day__gt=self.schedule_task.start_day
        ).order_by('schedule_task__start_day').first()

    def recalculate_from_previous(self):
        """Recalculate this task's dates based on previous task completion"""
        previous_task = self.get_previous_task()
        
        if previous_task and previous_task.actual_completion_date:
            # Calculate based on when previous task actually completed
            days_between = self.schedule_task.start_day - previous_task.schedule_task.end_day
            new_start = previous_task.actual_completion_date + timedelta(days=days_between)
            
            # Calculate duration
            duration = (self.planned_end_date - self.planned_start_date).days
            
            # Update dates
            self.planned_start_date = new_start
            self.planned_end_date = new_start + timedelta(days=duration)
            
            self._update_status()
            self.save()
            
            return True
        
        return False

    def check_cycle_completion(self):
        """Check if all tasks in cycle are completed"""
        cycle = self.farmer_crop_cycle
        all_tasks = cycle.task_statuses.all()
        
        if all_tasks.filter(status='COMPLETED').count() == all_tasks.count():
            self.activate_next_schedule()

    def activate_next_schedule(self):
        """Activate next schedule when current cycle is complete"""
        from cropcycle.models import Schedule, FarmerCropCycle
        
        cycle = self.farmer_crop_cycle
        current_schedule = cycle.schedule
        crop_variety = cycle.crop_variety

        # Find next schedule
        next_schedule = Schedule.objects.filter(
            crop_variety=crop_variety,
            season=current_schedule.season,
            id__gt=current_schedule.id
        ).order_by('id').first()

        if not next_schedule:
            next_schedule = Schedule.objects.filter(
                crop_variety=crop_variety,
                season=current_schedule.season
            ).exclude(id=current_schedule.id).first()

        if next_schedule:
            # Create new cycle
            new_cycle = FarmerCropCycle.objects.create(
                farmer=cycle.farmer,
                crop_variety=crop_variety,
                schedule=next_schedule,
                sowing_date=timezone.now().date(),
                is_active=True
            )
            
            # Deactivate current cycle
            cycle.is_active = False
            cycle.save()
            
            # Generate tasks for new cycle
            self.generate_tasks_for_cycle(new_cycle)
            
            return new_cycle

        return None

    @classmethod
    def generate_tasks_for_cycle(cls, cycle):
        """Generate task statuses for a crop cycle with cascading logic"""
        schedule_tasks = cycle.schedule.tasks.all().order_by('start_day')
        previous_task_status = None
        
        for schedule_task in schedule_tasks:
            if previous_task_status is None:
                # First task: calculate from sowing date
                planned_start = cycle.sowing_date + timedelta(days=schedule_task.start_day)
            else:
                # Subsequent tasks: calculate from previous task's planned end
                # This ensures proper spacing even if tasks are generated fresh
                days_between = schedule_task.start_day - previous_task_status.schedule_task.end_day
                planned_start = previous_task_status.planned_end_date + timedelta(days=days_between)
            
            # Calculate end date
            task_duration = schedule_task.end_day - schedule_task.start_day
            planned_end = planned_start + timedelta(days=task_duration)
            
            # Create task status
            task_status = cls.objects.create(
                farmer_crop_cycle=cycle,
                schedule_task=schedule_task,
                planned_start_date=planned_start,
                planned_end_date=planned_end,
                status='PENDING'
            )
            
            # Update status based on dates
            task_status._update_status()
            task_status.save()
            
            previous_task_status = task_status

    def get_delay_impact(self):
        """Get information about how this task's delay affects others"""
        if self.delay_days <= 0:
            return None
        
        subsequent_count = FarmerTaskStatus.objects.filter(
            farmer_crop_cycle=self.farmer_crop_cycle,
            schedule_task__start_day__gt=self.schedule_task.start_day,
            status__in=['PENDING', 'IN_PROGRESS']
        ).count()
        
        return {
            'delay_days': self.delay_days,
            'affected_tasks': subsequent_count,
            'delay_reason': self.delay_reason,
            'delay_date': self.delay_date
        }

    @property
    def is_delayed(self):
        """Check if this task has any delay"""
        return self.delay_days > 0

    @property
    def days_until_due(self):
        """Calculate days until task is due"""
        if self.status == 'COMPLETED':
            return None
        
        today = timezone.now().date()
        return (self.planned_end_date - today).days

    @property
    def is_urgent(self):
        """Check if task is due within 3 days"""
        days_until = self.days_until_due
        return days_until is not None and 0 <= days_until <= 3