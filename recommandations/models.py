from django.db import models
from schedule.models import BaseModel
from inventory.models import Product

class Crop(BaseModel):
    """Crop model."""
    name = models.CharField(max_length=100, unique=True)
    name_mr = models.CharField(max_length=100, blank=True, null=True, verbose_name='Name (Marathi)')
    description = models.TextField(blank=True, null=True)
    

    def __str__(self):
        return self.name
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Crop'
        verbose_name_plural = 'Crops'


class Advisory(BaseModel):
    """General agricultural advisory information."""
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=100)
    crops = models.ManyToManyField("recommandations.Crop", related_name='advisories', blank=True)

    def __str__(self):
        return self.title

    class Meta(BaseModel.Meta):
        verbose_name_plural = "Advisories"



# ==============================================================================
#  Knowledge Base & Advisory Models
# ==============================================================================

# +++ UPDATED MODEL - ADD ONLY THIS ONE LINE +++
class CropSpecificBenefit(BaseModel):
    """Links a Product to a Crop with a specific benefit description."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='crop_benefits')
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='product_benefits')
    # Benefit Details
    description = models.TextField(verbose_name='Benefit Description')
    description_mr = models.TextField(blank=True, null=True, verbose_name='Description (Marathi)')
    
    dosage_recommendation = models.CharField(max_length=255, blank=True, null=True, 
                                            help_text='Recommended dosage per acre')
    dosage_recommendation_mr = models.CharField(max_length=255, blank=True, null=True,
                                               verbose_name='Dosage (Marathi)')
    
    application_timing = models.CharField(max_length=255, blank=True, null=True,
                                         help_text='When to apply (e.g., "30 days after planting")')
    application_timing_mr = models.CharField(max_length=255, blank=True, null=True,
                                            verbose_name='Timing (Marathi)')
    
    expected_results = models.TextField(blank=True, null=True, verbose_name='Expected Results')
    expected_results_mr = models.TextField(blank=True, null=True, verbose_name='Results (Marathi)')
    
    # Priority for display
    priority = models.IntegerField(default=0, help_text='Higher priority appears first')
    
    class Meta(BaseModel.Meta):
        unique_together = ('product', 'crop')
        ordering = ['-priority', 'crop__name']
        verbose_name = 'Crop-Specific Benefit'
        verbose_name_plural = 'Crop-Specific Benefits'
    
    def __str__(self):
        return f"{self.product.name} - {self.crop.name}"

    
