import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# ==============================================================================
#  Abstract Base Model
# ==============================================================================

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True
        ordering = ['-created_at']

# ==============================================================================
#  Core & General Models
# ==============================================================================

class Company(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    name_mr = models.CharField(max_length=255, blank=True, null=True, verbose_name='Name (Marathi)')
    company_type = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self): 
        return self.name
    
    class Meta(BaseModel.Meta): 
        verbose_name_plural = "Companies"

# ==============================================================================
#  Product & Inventory Models
# ==============================================================================

class ProductCategory(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    name_mr = models.CharField(max_length=255, blank=True, null=True, verbose_name='Name (Marathi)')
    description = models.TextField(blank=True, null=True)
    description_mr = models.TextField(blank=True, null=True, verbose_name='Description (Marathi)')
    
    def __str__(self): 
        return self.name
    
    class Meta(BaseModel.Meta): 
        verbose_name_plural = "Product Categories"

class Product(BaseModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT, related_name='products')
    name = models.CharField(max_length=255)
    name_mr = models.CharField(max_length=255, blank=True, null=True, verbose_name='Name (Marathi)')
    
    # Product Details
    description = models.TextField(blank=True, null=True, verbose_name='Product Description')
    description_mr = models.TextField(blank=True, null=True, verbose_name='Description (Marathi)')
    
    technical_composition = models.TextField(blank=True)
    technical_composition_mr = models.TextField(blank=True, null=True, verbose_name='Technical Composition (Marathi)')
    
    application_method = models.TextField(blank=True, null=True, verbose_name='Application Method')
    application_method_mr = models.TextField(blank=True, null=True, verbose_name='Application Method (Marathi)')
    
    precautions = models.TextField(blank=True, null=True, verbose_name='Precautions')
    precautions_mr = models.TextField(blank=True, null=True, verbose_name='Precautions (Marathi)')
    
    # NEW: Purpose and Benefits fields
    purpose = models.TextField(blank=True, null=True, verbose_name='Purpose/Use Cases', 
                              help_text='What is this product used for?')
    purpose_mr = models.TextField(blank=True, null=True, verbose_name='Purpose (Marathi)')
    
    benefits = models.TextField(blank=True, null=True, verbose_name='Benefits/Impact',
                               help_text='Key benefits and expected impact')
    benefits_mr = models.TextField(blank=True, null=True, verbose_name='Benefits (Marathi)')
    
    # Stock Alert Thresholds
    low_stock_threshold = models.IntegerField(default=10, help_text='Alert when stock falls below this quantity')
    
    def __str__(self): 
        return f"{self.name} by {self.company.name}"
    
    def get_total_stock(self):
        """Get total stock across all SKUs"""
        return sum(sku.stock_quantity or 0 for sku in self.skus.all())
    
    def is_low_stock(self):
        """Check if any SKU is low on stock"""
        return any(sku.is_low_stock() for sku in self.skus.all())

class ProductSKU(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='skus')
    size = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    mrp = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='MRP')
    stock_quantity = models.IntegerField(default=0, help_text='Current stock quantity')
    
    # NEW: Image field - using static path for now, will migrate to S3 later
    image = models.ImageField(upload_to='products/skus/', null=True, blank=True)
    
    # Stock Management
    reorder_level = models.IntegerField(default=10, help_text='Minimum stock level before reorder')
    max_stock_level = models.IntegerField(default=100, help_text='Maximum stock capacity')
    
    def __str__(self): 
        return f"{self.product.name} - {self.size}"
    
    class Meta(BaseModel.Meta): 
        unique_together = ('product', 'size')
        verbose_name = 'Product SKU'
        verbose_name_plural = 'Product SKUs'
    
    def is_low_stock(self):
        """Check if stock is below reorder level"""
        return self.stock_quantity <= self.reorder_level
    
    def stock_status(self):
        """Return stock status as string"""
        if self.stock_quantity == 0:
            return 'OUT_OF_STOCK'
        elif self.stock_quantity <= self.reorder_level:
            return 'LOW_STOCK'
        elif self.stock_quantity >= self.max_stock_level:
            return 'OVERSTOCKED'
        return 'IN_STOCK'
    
    def get_image_url(self):
        """Get the image URL for the SKU"""
        if self.image_path:
            # For now, return static file path
            # Later this will return S3 URL
            return f"/static/{self.image_path}"
        # Return a default placeholder image
        return "/static/images/product-placeholder.png"

class StockHistory(BaseModel):
    """Track all stock movements for complete audit trail"""
    
    TRANSACTION_TYPES = [
        ('PURCHASE', 'Purchase/Stock In'),
        ('SALE', 'Sale/Stock Out'),
        ('ADJUSTMENT', 'Manual Adjustment'),
        ('RETURN', 'Return'),
        ('DAMAGE', 'Damage/Loss'),
        ('TRANSFER', 'Transfer'),
        ('INITIAL', 'Initial Stock'),
    ]
    
    sku = models.ForeignKey(ProductSKU, on_delete=models.CASCADE, related_name='stock_history')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    
    # Stock Changes
    quantity_before = models.IntegerField(help_text='Stock quantity before transaction')
    quantity_changed = models.IntegerField(help_text='Quantity added (+) or removed (-)')
    quantity_after = models.IntegerField(help_text='Stock quantity after transaction')
    
    # Transaction Details
    reference_number = models.CharField(max_length=100, blank=True, null=True, help_text='Invoice/Order number')
    notes = models.TextField(blank=True, null=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_transactions')
    transaction_date = models.DateTimeField(default=timezone.now)
    
    # Additional Info
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    total_value = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Stock History'
        verbose_name_plural = 'Stock History'
        ordering = ['-transaction_date', '-created_at']
    
    def __str__(self):
        return f"{self.sku.product.name} - {self.transaction_type} - {self.quantity_changed:+d} units"
    
    def save(self, *args, **kwargs):
        # Calculate total value if unit price is provided
        if self.unit_price and self.quantity_changed:
            self.total_value = abs(self.quantity_changed) * self.unit_price
        super().save(*args, **kwargs)

# ==============================================================================
#  Stock Alert Model
# ==============================================================================

class StockAlert(BaseModel):
    """Track and manage stock alerts"""
    
    ALERT_TYPES = [
        ('LOW_STOCK', 'Low Stock'),
        ('OUT_OF_STOCK', 'Out of Stock'),
        ('OVERSTOCK', 'Overstock'),
    ]
    
    ALERT_STATUS = [
        ('ACTIVE', 'Active'),
        ('ACKNOWLEDGED', 'Acknowledged'),
        ('RESOLVED', 'Resolved'),
    ]
    
    sku = models.ForeignKey(ProductSKU, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    status = models.CharField(max_length=20, choices=ALERT_STATUS, default='ACTIVE')
    
    stock_level_at_alert = models.IntegerField()
    threshold_level = models.IntegerField()
    
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                       related_name='acknowledged_alerts')
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True, null=True)
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Stock Alert'
        verbose_name_plural = 'Stock Alerts'
    
    def __str__(self):
        return f"{self.alert_type} - {self.sku.product.name} ({self.sku.size})"