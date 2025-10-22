# advisory/models.py - ADD ONLY ONE LINE TO CropSpecificBenefit

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from inventory.models import Product
import datetime
from django.utils import timezone
# from datetime import timedelta


# ==============================================================================
#  Abstract Base Model
# ==============================================================================

class BaseModel(models.Model):
    """
    An abstract base class model that provides self-updating
    `created_at` and `updated_at` fields.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True
        ordering = ['-created_at']


class Farmer(BaseModel):
    """Represents a farmer in the system."""
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, unique=True)

    farm_size = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=1.0,
        help_text="Farm size in acres"
    )
    farm_size_unit = models.CharField(
        max_length=20,
        choices=[
            ('ACRE', 'Acre'),
            ('HECTARE', 'Hectare'),
        ],
        default='ACRE'
    )
    
    def get_farm_size_in_acres(self):
        """Convert farm size to acres for standardization"""
        if self.farm_size_unit == 'HECTARE':
            return float(self.farm_size) * 2.47105  # 1 hectare = 2.47105 acres
        return float(self.farm_size)
    
    def __str__(self):
        return f"{self.name} ({self.farm_size} {self.farm_size_unit})"

    

