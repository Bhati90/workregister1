
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings # Good practice to import settings

from django.contrib.gis.db import models as gis_models
from django.db import models
from django.core.validators import RegexValidator
import uuid
import os

def photo_upload_path(instance, filename):
    """Generate upload path for captured photos"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4().hex}.{ext}"
    return f'captured_photos/{filename}'

class BaseRegistration(models.Model):
    # First page - Basic Information
    full_name = models.CharField(max_length=200)

    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    mobile_number = models.CharField(validators=[phone_regex], max_length=17)

    taluka = models.CharField(max_length=100)
    village = models.CharField(max_length=100)

    # Updated photo field for camera capture
    photo = models.ImageField(upload_to=photo_upload_path, null=True, blank=True)

    # Location field using PostGIS
    location = gis_models.PointField(
        null=True,
        blank=True,
        help_text="GPS coordinates (longitude, latitude)",
        srid=4326  # WGS84 coordinate system
    )

    # Additional location metadata
    location_accuracy = models.FloatField(
        null=True,
        blank=True,
        help_text="GPS accuracy in meters"
    )
    location_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When location was captured"
    )

    CATEGORY_CHOICES = [
        ('individual_labor', 'Individual Labor'),
        ('transport', 'Transport'),
        ('mukkadam', 'Mukkadam'),
        ('others', 'Others'),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)

    # Data sharing agreement
    data_sharing_agreement = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def get_location_display(self):
        """Get human-readable location coordinates"""
        if self.location:
            return f"Lat: {self.location.y:.6f}, Lng: {self.location.x:.6f}"
        return "Location not available"

    def get_location_accuracy_display(self):
        """Get human-readable accuracy"""
        if self.location_accuracy:
            return f"{self.location_accuracy:.2f} meters"
        return "Accuracy not available"

class IndividualLabor(BaseRegistration):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    age = models.PositiveIntegerField()
    primary_source_income = models.CharField(max_length=200)

    # Skills - multiple choice
    skill_pruning = models.BooleanField(default=False)
    skill_harvesting = models.BooleanField(default=False)
    skill_dipping = models.BooleanField(default=False)
    skill_thinning = models.BooleanField(default=False)
    skill_none = models.BooleanField(default=False)
    skill_other = models.CharField(max_length=200, blank=True)

    EMPLOYMENT_CHOICES = [
        ('daily', 'Daily'),
        ('seasonal', 'Seasonal'),
        ('year_around', 'Year Around'),
        ('other', 'Other'),
    ]
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_CHOICES)

    MIGRATION_CHOICES = [
        ('migrate_to_company', 'Migrate to Company'),
        ('migrate_anywhere', 'Migrate Anywhere'),
        ('travel_day_close_home', 'Travel for the Day Close to Home'),
        ('other', 'Other'),
    ]
    willing_to_migrate = models.CharField(max_length=30, choices=MIGRATION_CHOICES)

    expected_wage = models.DecimalField(max_digits=10, decimal_places=2)
    availability = models.TextField()
    want_training = models.BooleanField(default=False)

    # Communication preferences - multiple choice
    comm_mobile_app = models.BooleanField(default=False)
    comm_whatsapp = models.BooleanField(default=False)
    comm_calling = models.BooleanField(default=False)
    comm_sms = models.BooleanField(default=False)
    comm_other = models.CharField(max_length=200, blank=True)

    adult_men_seeking_employment = models.IntegerField(default=0)
    adult_women_seeking_employment = models.IntegerField(default=0)

    can_refer_others = models.BooleanField(default=False)
    referral_name = models.CharField(max_length=200, blank=True)
    referral_contact = models.CharField(max_length=17, blank=True)

class Mukkadam(BaseRegistration):
    providing_labour_count = models.PositiveIntegerField()
    total_workers_peak = models.PositiveIntegerField()

    # Skills - multiple choice
    skill_pruning = models.BooleanField(default=False)
    skill_harvesting = models.BooleanField(default=False)
    skill_dipping = models.BooleanField(default=False)
    skill_thinning = models.BooleanField(default=False)
    skill_none = models.BooleanField(default=False)
    skill_other = models.CharField(max_length=200, blank=True)

    expected_charges = models.DecimalField(max_digits=10, decimal_places=2)
    labour_supply_availability = models.TextField()

    TRANSPORT_CHOICES = [
        ('rented', 'Rented'),
        ('owned', 'Owned'),
        ('no', 'No'),
        ('other', 'Other'),
    ]
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, # Or models.CASCADE
        null=True, 
        blank=True,
        related_name='mukadam_profile'
    )
    arrange_transport = models.CharField(max_length=20, choices=TRANSPORT_CHOICES)
    transport_other = models.CharField(max_length=200, blank=True)

    provide_tools = models.BooleanField(default=False)
    supply_areas = models.TextField()

class Transport(BaseRegistration):
    vehicle_type = models.CharField(max_length=200)
    people_capacity = models.PositiveIntegerField()
    expected_fair = models.DecimalField(max_digits=10, decimal_places=2)
    availability = models.TextField()
    service_areas = models.TextField()
    home_address = models.CharField(max_length=255, blank=True, null=True)
    whatsapp_number = models.CharField(max_length=15, blank=True, null=True)
    

class Others(BaseRegistration):
    business_name = models.CharField(max_length=200)
    interested_referrals = models.BooleanField(default=False)
    help_description = models.TextField()
    know_mukadams_labourers = models.BooleanField(default=False)
from datetime import date, timedelta, datetime, time # Make sure datetime and time are imported


from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from datetime import date, timedelta
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Job(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('waiting_for_response', 'Waiting for Response'), 
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('awaiting_leader_confirmation', 'Awaiting Leader Confirmation'), #
        ('open_for_bidding', 'Open for Bidding'),
    ]
    
    COMPETITION_CHOICES = [
        ('good_chance', 'Good Chance'),
        ('moderate', 'Moderate'),
        ('high_competition', 'High Competition'),
    ]
    
    title = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    workers_needed = models.PositiveIntegerField()
    duration_days = models.PositiveIntegerField()
    rate_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    required_by_date = models.DateField()
    bidding_deadline = models.DateTimeField(null=True, blank=True)
    # Status and metadata
    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default='pending')
    competition_level = models.CharField(max_length=20, choices=COMPETITION_CHOICES, default='moderate')
    is_urgent = models.BooleanField(default=False)
    
    # Relationships
    sent_to_leaders = models.ManyToManyField(User, through='JobLeaderResponse', related_name='received_jobs')
    finalized_leader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='finalized_jobs')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completion_date = models.DateTimeField(null=True, blank=True)
    

    leader_response_message = models.TextField(
        blank=True, null=True, help_text="Notes or response from the team leader."
    )
    leader_quoted_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, help_text="The final price quoted by the leader."
    )
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.location}"
    
    @property
    def status_class(self):
        status_mapping = {
            'pending': 'pending',
            'waiting_for_response': 'allocated', 
            'ongoing': 'ongoing',
            'completed': 'completed',
            'open_for_bidding': 'pending',
        }
        return status_mapping.get(self.status, 'pending')
    
    @property
    def competition_class(self):
        competition_mapping = {
            'good_chance': 'good-chance',
            'moderate': 'moderate',
            'high_competition': 'high-competition',
        }
        return competition_mapping.get(self.competition_level, 'moderate')
    
    @property 
    def dates_display(self):
        return 'Urgent' if self.is_urgent else 'Fixed Dates'
    
    def save(self, *args, **kwargs):
        """
        Automatically sets the bidding deadline to be 10 days before the job starts.
        This version correctly handles the date-to-datetime conversion.
        """
        if self.required_by_date and not self.bidding_deadline:
            # Calculate the date of the deadline
            deadline_date = self.required_by_date - timedelta(days=10)
            
            # Combine the date with the latest possible time (23:59:59) to create a datetime object.
            # This ensures the entire day of the deadline is included.
            self.bidding_deadline = datetime.combine(deadline_date, time.max)

        super().save(*args, **kwargs)

    @property
    def is_latest(self):
        """Check if job was created within last 2 days"""
        return self.created_at.date() >= (date.today() - timedelta(days=2))


class JobLeaderResponse(models.Model):
    RESPONSE_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'), 
        ('rejected', 'Rejected'),
    ]
    
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    leader = models.ForeignKey(User, on_delete=models.CASCADE)
    response = models.CharField(max_length=10, choices=RESPONSE_CHOICES, default='pending')
    quoted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    available_workers_count = models.PositiveIntegerField(null=True, blank=True)
    response_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('job', 'leader')
    
    def __str__(self):
        return f"{self.job.title} - {self.leader.get_full_name()} - {self.response}"


class JobAssignment(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='assignments')
    
    # These three fields work together to point to ANY model object
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    worker = GenericForeignKey('content_type', 'object_id') # This is the magic!
    
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('job', 'content_type', 'object_id')
    
    def __str__(self):
        worker_name = getattr(self.worker, 'full_name', f"Worker ID: {self.object_id}")
        return f"{worker_name} assigned to {self.job.title}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.title}"


# registration/models.py

class StatusUpdate(models.Model):
    """Stores a historical log of status updates for a specific worker on a specific job."""
    
    STATUS_CHOICES = [
        ('assigned', 'Assigned to Job'),
        ('mobilizing', 'Mobilizing'),
        ('transport_arranged', 'Transport Arranged'),
        ('en_route', 'En Route to Site'),
        ('on_site', 'Arrived at Site'),
        ('work_started', 'Work Started'),
        ('work_in_progress', 'Work in Progress'),
        ('work_completed', 'Work Completed'),
        ('payment_processed', 'Payment Processed'),
    ]

    # Link to the specific assignment, which links to the job, worker, and leader
    assignment = models.ForeignKey(JobAssignment, on_delete=models.CASCADE, related_name='status_updates')
    
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    notes = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # Optional: Store the location where the update was made
    location = gis_models.PointField(srid=4326, null=True, blank=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.assignment.worker} on {self.assignment.job.title} - {self.get_status_display()}"

# Add availability status to existing models
class WorkerStatus(models.Model):
    """Track availability status of workers"""
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    worker = GenericForeignKey('content_type', 'object_id')
    
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('booked', 'Booked'),
        ('proposed', 'Proposed for a Job'), 
        ('not_available', 'Not Available'),
    ]
    proposed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='proposed_workers')

    availability_status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='available')
    current_job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('content_type', 'object_id')
    
    def __str__(self):
        return f"{self.worker.full_name} - {self.availability_status}"
    

# registration/models.py
# registration/models.py
from django.conf import settings # Make sure this is imported

class JobBid(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='bids')
    mukadam = models.ForeignKey('Mukkadam', on_delete=models.CASCADE, related_name='bids_made')

    bid_price = models.DecimalField(max_digits=10, decimal_places=2)
    workers_provided = models.PositiveIntegerField(default=0)
    notes_on_skills = models.TextField(blank=True, help_text="Details on the skills of the workers provided.")

    # Checklist of included services
    includes_transport = models.BooleanField(default=False)
    includes_accommodation = models.BooleanField(default=False)
    no_advance_required = models.BooleanField(default=False)
    
    registered_labourers = models.ManyToManyField(
        'IndividualLabor', 
        blank=True, # A bid doesn't have to include registered labourers
        related_name='bids_included_in'
    )
    timestamp = models.DateTimeField(auto_now=True)
    
    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        WON = 'won', 'Won'
        LOST = 'lost', 'Lost'

    # ... all your existing fields ...
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    
    class Meta:
        unique_together = ('job', 'mukadam') # A mukadam can only have one bid per job
        ordering = ['bid_price'] # Default order is lowest price first

    def __str__(self):
        return f"Bid by {self.mukadam.full_name} for {self.job.title} at {self.bid_price}"
    # ... all your other Mukkadam fields ...

class BidReview(JobBid):
    class Meta:
        proxy = True
        verbose_name = 'Bid Review'
        verbose_name_plural = 'Bid Reviews'


class JobFeedback(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='feedback')
    
    # This allows feedback to be linked to a Leader, Mukadam, or Labourer
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    feedback_for = GenericForeignKey('content_type', 'object_id')

    rating = models.PositiveIntegerField(default=5) # e.g., 1 to 5 stars
    comment = models.TextField(blank=True)
    
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for {self.feedback_for} on job {self.job.title}"

# registration/models.py

# ... (all your existing models) ...

# ADD THIS NEW MODEL
class JobLeaderAllocation(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='leader_allocations')
    leader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='job_allocations')
    allocated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('job', 'leader') # A leader can only be allocated to a job once

    def __str__(self):
        return f"{self.leader.username} allocated to {self.job.title}"
         
class LaboursAdvancedProfiles(models.Model):
    """
    Stores advanced search data for a labourer, now with date ranges.
    """
    labour = models.OneToOneField(
        'IndividualLabor', 
        on_delete=models.CASCADE, 
        primary_key=True,
        related_name='advanced_profile'
    )
    
    # NEW: Start and end dates for availability
    available_from = models.DateField(
        null=True, blank=True, help_text="The start date of their availability period."
    )
    available_to = models.DateField(
        null=True, blank=True, help_text="The end date of their availability period."
    )

    advanced_rate_per_day = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="The per-day rate this labourer has agreed to for advanced bookings."
    )

    requires_transport = models.BooleanField(
        default=True,
        help_text="Does this labourer require transport to be arranged and paid for?"
    )

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Advanced Profile for {self.labour.full_name}"
    """
    Stores advanced search data for a labourer, linked to their main profile.
    This keeps the original IndividualLabor model untouched.
    """
    labour = models.OneToOneField(
        'IndividualLabor', 
        on_delete=models.CASCADE, 
        primary_key=True,
        related_name='advanced_profile'
    )
    
    available_dates = models.JSONField(
        default=list, 
        blank=True,
        help_text="A list of dates in YYYY-MM-DD format."
    )

    advanced_rate_per_day = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="The per-day rate this labourer has agreed to for advanced bookings."
    )

    requires_transport = models.BooleanField(
        default=True,
        help_text="Does this labourer require transport to be arranged and paid for?"
    )

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Advanced Profile for {self.labour.full_name}"