# from django.contrib.gis.db import models as gis_models
# from django.db import models
# from django.core.validators import RegexValidator
# import uuid
# import os
# from django.contrib.auth.models import User # Import Django's built-in User model

# def photo_upload_path(instance, filename):
#     """Generate upload path for captured photos"""
#     ext = filename.split('.')[-1]
#     filename = f"{uuid.uuid4().hex}.{ext}"
#     return f'captured_photos/{filename}'

# class BaseRegistration(models.Model):
#     # First page - Basic Information
#     full_name = models.CharField(max_length=200)

#     phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
#     mobile_number = models.CharField(validators=[phone_regex], max_length=17, unique=True) # Added unique=True

#     taluka = models.CharField(max_length=100)
#     village = models.CharField(max_length=100)

#     # Updated photo field for camera capture
#     photo = models.ImageField(upload_to=photo_upload_path, null=True, blank=True)

#     # Location field using PostGIS
#     location = gis_models.PointField(
#         null=True,
#         blank=True,
#         help_text="GPS coordinates (longitude, latitude)",
#         srid=4326  # WGS84 coordinate system
#     )

#     # Additional location metadata
#     location_accuracy = models.FloatField(
#         null=True,
#         blank=True,
#         help_text="GPS accuracy in meters"
#     )
#     location_timestamp = models.DateTimeField(
#         null=True,
#         blank=True,
#         help_text="When location was captured"
#     )

#     CATEGORY_CHOICES = [
#         ('individual_labor', 'Individual Labor'),
#         ('transport', 'Transport'),
#         ('mukkadam', 'Mukkadam'),
#         ('others', 'Others'),
#     ]
#     category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)

#     # Data sharing agreement
#     data_sharing_agreement = models.BooleanField(default=False)

#     # Timestamps
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         abstract = True

#     def get_location_display(self):
#         """Get human-readable location coordinates"""
#         if self.location:
#             return f"Lat: {self.location.y:.6f}, Lng: {self.location.x:.6f}"
#         return "Location not available"

#     def get_location_accuracy_display(self):
#         """Get human-readable accuracy"""
#         if self.location_accuracy:
#             return f"{self.location_accuracy:.2f} meters"
#         return "Accuracy not available"


# class IndividualLabor(BaseRegistration):
#     # Link to Django's built-in User model
#     user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True,
#                                 help_text="Associated user account for login") # Made null=True, blank=True for now, but ideally it should be created on registration

#     GENDER_CHOICES = [
#         ('male', 'Male'),
#         ('female', 'Female'),
#         ('other', 'Other'),
#     ]
#     gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
#     age = models.PositiveIntegerField()
#     primary_source_income = models.CharField(max_length=200)

#     # Skills - multiple choice
#     skill_pruning = models.BooleanField(default=False)
#     skill_harvesting = models.BooleanField(default=False)
#     skill_dipping = models.BooleanField(default=False)
#     skill_thinning = models.BooleanField(default=False)
#     skill_none = models.BooleanField(default=False)
#     skill_other = models.CharField(max_length=200, blank=True)

#     EMPLOYMENT_CHOICES = [
#         ('daily', 'Daily'),
#         ('seasonal', 'Seasonal'),
#         ('year_around', 'Year Around'),
#         ('other', 'Other'),
#     ]
#     employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_CHOICES)

#     MIGRATION_CHOICES = [
#         ('migrate_to_company', 'Migrate to Company'),
#         ('migrate_anywhere', 'Migrate Anywhere'),
#         ('travel_day_close_home', 'Travel for the Day Close to Home'),
#         ('other', 'Other'),
#     ]
#     willing_to_migrate = models.CharField(max_length=30, choices=MIGRATION_CHOICES)

#     expected_wage = models.DecimalField(max_digits=10, decimal_places=2)
#     availability = models.TextField()
#     want_training = models.BooleanField(default=False)

#     # Communication preferences - multiple choice
#     comm_mobile_app = models.BooleanField(default=False)
#     comm_whatsapp = models.BooleanField(default=False)
#     comm_calling = models.BooleanField(default=False)
#     comm_sms = models.BooleanField(default=False)
#     comm_other = models.CharField(max_length=200, blank=True)

#     adult_men_seeking_employment = models.IntegerField(default=0)
#     adult_women_seeking_employment = models.IntegerField(default=0)

#     can_refer_others = models.BooleanField(default=False)
#     referral_name = models.CharField(max_length=200, blank=True)
#     referral_contact = models.CharField(
#         validators=[BaseRegistration.phone_regex], max_length=17, blank=True)


# class Mukkadam(BaseRegistration):
#     # Link to Django's built-in User model
#     user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True,
#                                 help_text="Associated user account for login") # Made null=True, blank=True for now

#     providing_labour_count = models.PositiveIntegerField()
#     total_workers_peak = models.PositiveIntegerField()

#     # Skills - multiple choice
#     skill_pruning = models.BooleanField(default=False)
#     skill_harvesting = models.BooleanField(default=False)
#     skill_dipping = models.BooleanField(default=False)
#     skill_thinning = models.BooleanField(default=False)
#     skill_none = models.BooleanField(default=False)
#     skill_other = models.CharField(max_length=200, blank=True)

#     expected_charges = models.DecimalField(max_digits=10, decimal_places=2)
#     labour_supply_availability = models.TextField()

#     TRANSPORT_CHOICES = [
#         ('rented', 'Rented'),
#         ('owned', 'Owned'),
#         ('no', 'No'),
#         ('other', 'Other'),
#     ]
#     arrange_transport = models.CharField(max_length=20, choices=TRANSPORT_CHOICES)
#     transport_other = models.CharField(max_length=200, blank=True)

#     provide_tools = models.BooleanField(default=False)
#     supply_areas = models.TextField()

# class Transport(BaseRegistration):
#     # Typically, Transport might not need a login unless it's a transport company representative
#     # user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
#     vehicle_type = models.CharField(max_length=200)
#     people_capacity = models.PositiveIntegerField()
#     expected_fair = models.DecimalField(max_digits=10, decimal_places=2)
#     availability = models.TextField()
#     service_areas = models.TextField()

# class Others(BaseRegistration):
#     # Similar to Transport, might not need a login unless it's a specific type of 'other' business
#     # user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
#     business_name = models.CharField(max_length=200)
#     interested_referrals = models.BooleanField(default=False)
#     help_description = models.TextField()
#     know_mukadams_labourers = models.BooleanField(default=False)



from django.contrib.gis.db import models as gis_models
from django.db import models
from django.core.validators import RegexValidator
import uuid
import os

def photo_upload_path(instance, filename):
      """Generate upload path for photos - this won't be used with Cloudinary URLs but good to keep"""
      return f'registrations/{instance.category}/{instance.mobile_number}/{filename}'


class BaseRegistration(models.Model):
    # First page - Basic Information
    full_name = models.CharField(max_length=200)

    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    mobile_number = models.CharField(validators=[phone_regex], max_length=17)

    taluka = models.CharField(max_length=100)
    village = models.CharField(max_length=100)

    # Updated photo field for camera capture
    photo = models.URLField(max_length=500, null=True, blank=True, help_text="Cloudinary image URL")
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

    def __str__(self):
        return f"{self.full_name} - {self.mobile_number} ({self.category})"
    
    class Meta:
        verbose_name = "Labor Registration"
        verbose_name_plural = "Labor Registrations"
        ordering = ['-created_at']
        
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

class Others(BaseRegistration):
    business_name = models.CharField(max_length=200)
    interested_referrals = models.BooleanField(default=False)
    help_description = models.TextField()
    know_mukadams_labourers = models.BooleanField(default=False)