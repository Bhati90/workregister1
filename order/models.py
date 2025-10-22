# orders/models.py

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Import existing models from other apps
from schedule.models import Farmer  # Your existing Farmer model
from inventory.models import ProductSKU, StockHistory, StockAlert  # Your existing models


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True
        ordering = ['-created_at']


# ==============================================================================
#  Extend Farmer Model with Additional Fields (if needed)
# ==============================================================================

class FarmerProfile(BaseModel):
    """
    Extended profile for farmers with order-specific information.
    Links to your existing Farmer model from schedule app.
    """
    farmer = models.OneToOneField(Farmer, on_delete=models.CASCADE, related_name='order_profile')
    
    # Additional contact info
    alternate_phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    
    # Address details (if not in your Farmer model)
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    village = models.CharField(max_length=100, blank=True, null=True)
    taluka = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, default='Maharashtra')
    pincode = models.CharField(max_length=6, blank=True, null=True)
    
    # Order preferences
    preferred_payment_method = models.CharField(
        max_length=20,
        choices=[
            ('CASH', 'Cash on Delivery'),
            ('UPI', 'UPI'),
            ('BANK_TRANSFER', 'Bank Transfer'),
            ('CREDIT', 'Credit'),
        ],
        default='CASH'
    )
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Profile for {self.farmer.name}"
    
    def get_full_address(self):
        """Get formatted full address"""
        parts = [
            self.address_line1,
            self.address_line2,
            self.village,
            self.taluka,
            self.district,
            self.state,
            self.pincode
        ]
        return ", ".join([p for p in parts if p])
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Farmer Profile'
        verbose_name_plural = 'Farmer Profiles'


# ==============================================================================
#  Order Models
# ==============================================================================

class Order(BaseModel):
    """Main Order model - Uses your existing Farmer and ProductSKU"""
    
    ORDER_STATUS = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('PROCESSING', 'Processing'),
        ('PACKED', 'Packed'),
        ('SHIPPED', 'Shipped'),
        ('IN_TRANSIT', 'In Transit'),
        ('OUT_FOR_DELIVERY', 'Out for Delivery'),
        ('DELIVERED', 'Delivered'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('RETURNED', 'Returned'),
    ]
    
    PAYMENT_STATUS = [
        ('UNPAID', 'Unpaid'),
        ('PARTIALLY_PAID', 'Partially Paid'),
        ('PAID', 'Paid'),
        ('REFUNDED', 'Refunded'),
    ]
    
    PAYMENT_METHOD = [
        ('CASH', 'Cash on Delivery'),
        ('UPI', 'UPI'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CARD', 'Card Payment'),
        ('CREDIT', 'Credit'),
    ]
    
    # Order identification
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    farmer = models.ForeignKey(Farmer, on_delete=models.PROTECT, related_name='orders')
    
    # Order details
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='PENDING')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='UNPAID')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD, default='CASH')
    
    # Financial
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    delivery_charges = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Delivery details
    delivery_address = models.TextField()
    delivery_contact = models.CharField(max_length=20)
    expected_delivery_date = models.DateField(blank=True, null=True)
    actual_delivery_date = models.DateField(blank=True, null=True)
    
    # Tracking
    courier_name = models.CharField(max_length=100, blank=True, null=True)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    
    # Additional info
    notes = models.TextField(blank=True, null=True)
    internal_notes = models.TextField(blank=True, null=True)
    
    # Staff handling
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='orders_created')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders_assigned')
    
    # Inventory impact
    inventory_updated = models.BooleanField(default=False, help_text='Whether stock has been deducted')
    
    def __str__(self):
        return f"{self.order_number} - {self.farmer.name}"
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate order number: ORD-YYYYMMDD-XXXX
            from django.db.models import Max
            today = timezone.now().strftime('%Y%m%d')
            last_order = Order.objects.filter(
                order_number__startswith=f'ORD-{today}'
            ).aggregate(Max('order_number'))
            
            if last_order['order_number__max']:
                last_number = int(last_order['order_number__max'].split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.order_number = f'ORD-{today}-{new_number:04d}'
        
        super().save(*args, **kwargs)
    
    def calculate_totals(self):
        """Calculate order totals from items"""
        items = self.items.all()
        self.subtotal = sum(item.total_price for item in items)
        self.total_amount = self.subtotal - self.discount + self.tax + self.delivery_charges
        self.save(update_fields=['subtotal', 'total_amount'])
    
    def get_pending_amount(self):
        """Get remaining amount to be paid"""
        return self.total_amount - self.paid_amount
    
    def can_update_inventory(self):
        """Check if order is in a state where inventory can be updated"""
        return self.status in ['COMPLETED', 'DELIVERED'] and not self.inventory_updated
    
    def get_projected_stock_impact(self):
        """Calculate how much stock will be affected when order is completed"""
        impact = []
        for item in self.items.all():
            impact.append({
                'sku': item.sku,
                'product_name': item.sku.product.name,
                'size': item.sku.size,
                'current_stock': item.sku.stock_quantity,
                'order_quantity': item.quantity,
                'projected_stock': item.sku.stock_quantity - item.quantity
            })
        return impact


class OrderItem(BaseModel):
    """Individual items in an order - Uses your existing ProductSKU"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    sku = models.ForeignKey(ProductSKU, on_delete=models.PROTECT, related_name='order_items')
    
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.order.order_number} - {self.sku.product.name} ({self.sku.size})"
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
    
    def save(self, *args, **kwargs):
        # Calculate total price
        self.total_price = (self.unit_price * self.quantity) - self.discount
        super().save(*args, **kwargs)
        
        # Update order totals
        self.order.calculate_totals()


class OrderStatusHistory(BaseModel):
    """Track all status changes of an order"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=20, blank=True, null=True)
    new_status = models.CharField(max_length=20)
    notes = models.TextField(blank=True, null=True)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notification_sent = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.order.order_number} - {self.old_status} → {self.new_status}"
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Order Status History'
        verbose_name_plural = 'Order Status History'


class OrderPayment(BaseModel):
    """Track payments for orders"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=Order.PAYMENT_METHOD)
    payment_date = models.DateTimeField(default=timezone.now)
    
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return f"{self.order.order_number} - ₹{self.amount}"
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Order Payment'
        verbose_name_plural = 'Order Payments'
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Update order paid amount and payment status
        order = self.order
        order.paid_amount = sum(p.amount for p in order.payments.all())
        
        if order.paid_amount >= order.total_amount:
            order.payment_status = 'PAID'
        elif order.paid_amount > 0:
            order.payment_status = 'PARTIALLY_PAID'
        else:
            order.payment_status = 'UNPAID'
        
        order.save(update_fields=['paid_amount', 'payment_status'])


class NotificationTemplate(BaseModel):
    """Templates for farmer notifications"""
    
    NOTIFICATION_TYPE = [
        ('ORDER_CONFIRMED', 'Order Confirmed'),
        ('ORDER_PACKED', 'Order Packed'),
        ('ORDER_SHIPPED', 'Order Shipped'),
        ('OUT_FOR_DELIVERY', 'Out for Delivery'),
        ('ORDER_DELIVERED', 'Order Delivered'),
        ('ORDER_CANCELLED', 'Order Cancelled'),
        ('PAYMENT_RECEIVED', 'Payment Received'),
    ]
    
    name = models.CharField(max_length=100)
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPE, unique=True)
    
    # Template content
    subject_template = models.CharField(max_length=200, help_text='Subject for SMS/Email')
    message_template_en = models.TextField(help_text='Message template in English')
    message_template_mr = models.TextField(blank=True, null=True, help_text='Message template in Marathi')
    
    # Available variables help text
    available_variables = models.TextField(
        help_text='Available variables: {farmer_name}, {order_number}, {total_amount}, {delivery_date}, {tracking_number}, {status}',
        editable=False,
        default='{farmer_name}, {order_number}, {total_amount}, {delivery_date}, {tracking_number}, {status}'
    )
    
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.notification_type})"
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Notification Template'
        verbose_name_plural = 'Notification Templates'
    
    def render(self, order, language='en'):
        """Render template with order data"""
        context = {
            'farmer_name': order.farmer.name,
            'order_number': order.order_number,
            'total_amount': order.total_amount,
            'delivery_date': order.expected_delivery_date,
            'tracking_number': order.tracking_number or 'Not available',
            'status': order.get_status_display(),
        }
        
        template = self.message_template_mr if language == 'mr' and self.message_template_mr else self.message_template_en
        subject = self.subject_template
        
        for key, value in context.items():
            template = template.replace('{' + key + '}', str(value))
            subject = subject.replace('{' + key + '}', str(value))
        
        return {
            'subject': subject,
            'message': template
        }


class OrderNotification(BaseModel):
    """Log of notifications sent to farmers"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='notifications')
    template = models.ForeignKey(NotificationTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    
    notification_type = models.CharField(max_length=30)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    language = models.CharField(max_length=2, choices=[('en', 'English'), ('mr', 'Marathi')], default='en')
    
    # Delivery details
    sent_at = models.DateTimeField(auto_now_add=True)
    is_sent = models.BooleanField(default=False)
    sent_via = models.CharField(max_length=20, choices=[('SMS', 'SMS'), ('EMAIL', 'Email'), ('WHATSAPP', 'WhatsApp')], default='SMS')
    
    # Status
    delivery_status = models.CharField(max_length=20, default='PENDING')
    error_message = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.order.order_number} - {self.notification_type}"
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Order Notification'
        verbose_name_plural = 'Order Notifications'