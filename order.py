"""
Standalone Django Script to Create Sample Orders
Run with: python import_orders_script.py

This script will:
1. Use your existing Farmers from schedule app
2. Use your existing Products from inventory app
3. Create realistic orders with various statuses
4. Create order items, payments, and status history
5. Optionally complete some orders to update inventory
"""

import os
import django
import random
from datetime import datetime, timedelta
from decimal import Decimal
from django.db import models

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'labour_crm.settings')
django.setup()

from django.db import transaction
from django.contrib.auth.models import User
from django.utils import timezone

# Import your existing models
from schedule.models import Farmer
from inventory.models import ProductSKU, StockHistory

# Import order models
from order.models import (
    Order, OrderItem, OrderPayment, OrderStatusHistory,
    NotificationTemplate, OrderNotification, FarmerProfile
)


def create_farmer_profiles():
    """Create FarmerProfile for existing farmers with address details"""
    print("\n" + "="*60)
    print("STEP 1: Creating Farmer Profiles")
    print("="*60)
    
    # Sample addresses in Maharashtra
    addresses = [
        {
            'address_line1': 'Survey No. 123, Near Temple',
            'village': 'Khandala',
            'taluka': 'Maval',
            'district': 'Pune',
            'pincode': '410301'
        },
        {
            'address_line1': 'Plot No. 45, Main Road',
            'village': 'Nashik Road',
            'taluka': 'Nashik',
            'district': 'Nashik',
            'pincode': '422101'
        },
        {
            'address_line1': 'Farm House, Bhigwan Road',
            'village': 'Baramati',
            'taluka': 'Baramati',
            'district': 'Pune',
            'pincode': '413102'
        },
        {
            'address_line1': 'Survey No. 78, Village Road',
            'village': 'Sangamner',
            'taluka': 'Sangamner',
            'district': 'Ahmednagar',
            'pincode': '422605'
        },
        {
            'address_line1': 'Gat No. 234, Near School',
            'village': 'Indapur',
            'taluka': 'Indapur',
            'district': 'Pune',
            'pincode': '413106'
        },
    ]
    
    farmers = Farmer.objects.all()
    profiles_created = 0
    
    for idx, farmer in enumerate(farmers):
        # Check if profile already exists
        if hasattr(farmer, 'order_profile'):
            continue
        
        # Get random address
        address = addresses[idx % len(addresses)]
        
        # Create profile
        FarmerProfile.objects.create(
            farmer=farmer,
            alternate_phone=f"98765432{20+idx:02d}",
            email=f"{farmer.name.lower().replace(' ', '.')}@example.com",
            address_line1=address['address_line1'],
            village=address['village'],
            taluka=address['taluka'],
            district=address['district'],
            state='Maharashtra',
            pincode=address['pincode'],
            preferred_payment_method=random.choice(['CASH', 'UPI', 'CREDIT']),
            credit_limit=Decimal(str(random.choice([10000, 20000, 50000]))),
            is_active=True
        )
        profiles_created += 1
    
    print(f"✓ Created {profiles_created} farmer profiles")
    return farmers


def create_notification_templates():
    """Create notification templates if they don't exist"""
    print("\n" + "="*60)
    print("STEP 2: Creating Notification Templates")
    print("="*60)
    
    templates = [
        {
            'name': 'Order Confirmed',
            'notification_type': 'ORDER_CONFIRMED',
            'subject_template': 'Order {order_number} Confirmed',
            'message_template_en': '''Dear {farmer_name},

Your order {order_number} has been confirmed!

Order Details:
- Order Number: {order_number}
- Total Amount: ₹{total_amount}
- Expected Delivery: {delivery_date}

Thank you for your order!''',
            'message_template_mr': '''प्रिय {farmer_name},

तुमचा ऑर्डर {order_number} पुष्टी झाला आहे!

ऑर्डर तपशील:
- ऑर्डर क्रमांक: {order_number}
- एकूण रक्कम: ₹{total_amount}
- अपेक्षित वितरण: {delivery_date}

तुमच्या ऑर्डरबद्दल धन्यवाद!'''
        },
        {
            'name': 'Order Shipped',
            'notification_type': 'ORDER_SHIPPED',
            'subject_template': 'Order {order_number} Shipped',
            'message_template_en': '''Dear {farmer_name},

Your order {order_number} has been shipped!

Tracking Number: {tracking_number}
Expected Delivery: {delivery_date}

You will receive your order soon!''',
            'message_template_mr': '''प्रिय {farmer_name},

तुमचा ऑर्डर {order_number} पाठवला गेला आहे!

ट्रॅकिंग नंबर: {tracking_number}
अपेक्षित वितरण: {delivery_date}

तुम्हाला लवकरच तुमचा ऑर्डर मिळेल!'''
        },
        {
            'name': 'Order Delivered',
            'notification_type': 'ORDER_DELIVERED',
            'subject_template': 'Order {order_number} Delivered',
            'message_template_en': '''Dear {farmer_name},

Your order {order_number} has been delivered!

Thank you for choosing us.''',
            'message_template_mr': '''प्रिय {farmer_name},

तुमचा ऑर्डर {order_number} वितरित केला गेला आहे!

आम्हाला निवडल्याबद्दल धन्यवाद.'''
        },
    ]
    
    created = 0
    for template_data in templates:
        _, was_created = NotificationTemplate.objects.get_or_create(
            notification_type=template_data['notification_type'],
            defaults=template_data
        )
        if was_created:
            created += 1
    
    print(f"✓ Created {created} notification templates")


def create_sample_orders(farmers, num_orders=50):
    """Create sample orders with various statuses"""
    print("\n" + "="*60)
    print(f"STEP 3: Creating {num_orders} Sample Orders")
    print("="*60)
    
    # Get products with stock
    products = list(ProductSKU.objects.select_related('product').filter(stock_quantity__gt=0)[:100])
    
    if not products:
        print("⚠ No products with stock found! Please add stock to products first.")
        return []
    
    # Get or create a user for orders
    user, _ = User.objects.get_or_create(
        username='admin',
        defaults={'is_staff': True, 'is_superuser': True}
    )
    
    statuses = [
        ('PENDING', 0.15),
        ('CONFIRMED', 0.15),
        ('PROCESSING', 0.10),
        ('SHIPPED', 0.15),
        ('IN_TRANSIT', 0.10),
        ('OUT_FOR_DELIVERY', 0.05),
        ('DELIVERED', 0.20),
        ('COMPLETED', 0.10),
    ]
    
    payment_methods = ['CASH', 'UPI', 'BANK_TRANSFER', 'CREDIT']
    
    orders_created = []
    
    with transaction.atomic():
        for i in range(num_orders):
            # Select random farmer
            farmer = random.choice(farmers)
            
            # Get farmer address
            try:
                profile = farmer.order_profile
                delivery_address = profile.get_full_address()
                delivery_contact = farmer.phone_number
            except:
                delivery_address = f"Farm address for {farmer.name}"
                delivery_contact = farmer.phone_number
            
            # Select order status based on weights
            status = random.choices(
                [s[0] for s in statuses],
                weights=[s[1] for s in statuses]
            )[0]
            
            # Create order date (last 30 days)
            days_ago = random.randint(0, 30)
            order_date = timezone.now() - timedelta(days=days_ago)
            
            # Create order
            order = Order.objects.create(
                farmer=farmer,
                status=status,
                payment_method=random.choice(payment_methods),
                payment_status='UNPAID' if status in ['PENDING', 'CONFIRMED'] else 'PARTIALLY_PAID' if random.random() > 0.5 else 'PAID',
                delivery_address=delivery_address,
                delivery_contact=delivery_contact,
                expected_delivery_date=(order_date + timedelta(days=random.randint(3, 7))).date(),
                discount=Decimal(str(random.choice([0, 50, 100, 200]))),
                delivery_charges=Decimal(str(random.choice([0, 50, 100]))),
                notes=f"Sample order {i+1}",
                created_by=user,
                created_at=order_date,
                inventory_updated=False
            )
            
            # Add tracking number for shipped orders
            if status in ['SHIPPED', 'IN_TRANSIT', 'OUT_FOR_DELIVERY', 'DELIVERED', 'COMPLETED']:
                order.tracking_number = f"TRK{order_date.strftime('%Y%m%d')}{i:04d}"
                order.save()
            
            # Add order items (2-5 items per order)
            num_items = random.randint(2, 5)
            selected_products = random.sample(products, min(num_items, len(products)))
            
            for product_sku in selected_products:
                # Only add if we have stock
                max_quantity = min(product_sku.stock_quantity, 10)
                if max_quantity > 0:
                    quantity = random.randint(1, max_quantity)
                    
                    OrderItem.objects.create(
                        order=order,
                        sku=product_sku,
                        quantity=quantity,
                        unit_price=product_sku.price,
                        discount=Decimal(str(random.choice([0, 10, 20, 50])))
                    )
            
            # Calculate totals
            order.calculate_totals()
            
            # Create status history
            OrderStatusHistory.objects.create(
                order=order,
                new_status=status,
                notes=f'Order created with status {status}',
                changed_by=user,
                created_at=order_date
            )
            
            # Add payment if order is paid
            if order.payment_status in ['PAID', 'PARTIALLY_PAID']:
                payment_amount = order.total_amount if order.payment_status == 'PAID' else order.total_amount * Decimal('0.5')
                OrderPayment.objects.create(
                    order=order,
                    amount=payment_amount,
                    payment_method=order.payment_method,
                    payment_date=order_date + timedelta(days=1),
                    transaction_id=f"TXN{order_date.strftime('%Y%m%d')}{i:04d}",
                    recorded_by=user
                )
            
            orders_created.append(order)
            
            if (i + 1) % 10 == 0:
                print(f"  Created {i + 1}/{num_orders} orders...")
    
    print(f"✓ Successfully created {len(orders_created)} orders")
    return orders_created


def complete_some_orders(orders, percentage=20):
    """Complete a percentage of delivered orders and update inventory"""
    print("\n" + "="*60)
    print(f"STEP 4: Completing {percentage}% of Orders & Updating Inventory")
    print("="*60)
    
    # Get or create user
    user = User.objects.first()
    
    # Get delivered orders that haven't been completed
    delivered_orders = [o for o in orders if o.status in ['DELIVERED'] and not o.inventory_updated]
    
    if not delivered_orders:
        print("⚠ No delivered orders to complete")
        return
    
    # Calculate how many to complete
    num_to_complete = max(1, int(len(delivered_orders) * (percentage / 100)))
    orders_to_complete = random.sample(delivered_orders, num_to_complete)
    
    completed = 0
    insufficient_stock = 0
    
    with transaction.atomic():
        for order in orders_to_complete:
            can_complete = True
            
            # Check if we have enough stock for all items
            for item in order.items.all():
                if item.sku.stock_quantity < item.quantity:
                    can_complete = False
                    insufficient_stock += 1
                    break
            
            if not can_complete:
                continue
            
            # Update stock for each item
            for item in order.items.all():
                sku = item.sku
                old_stock = sku.stock_quantity
                new_stock = old_stock - item.quantity
                
                # Update SKU stock
                sku.stock_quantity = new_stock
                sku.save()
                
                # Create stock history
                StockHistory.objects.create(
                    sku=sku,
                    transaction_type='SALE',
                    quantity_before=old_stock,
                    quantity_changed=-item.quantity,
                    quantity_after=new_stock,
                    notes=f'Stock deducted for order {order.order_number}',
                    reference_number=order.order_number,
                    performed_by=user,
                    unit_price=item.unit_price,
                    total_value=item.total_price
                )
            
            # Mark order as completed and inventory updated
            order.status = 'COMPLETED'
            order.inventory_updated = True
            order.actual_delivery_date = order.expected_delivery_date
            order.save()
            
            # Create status history
            OrderStatusHistory.objects.create(
                order=order,
                old_status='DELIVERED',
                new_status='COMPLETED',
                notes='Order completed and inventory updated',
                changed_by=user
            )
            
            completed += 1
    
    print(f"✓ Completed {completed} orders")
    print(f"✓ Updated inventory for {completed} orders")
    if insufficient_stock > 0:
        print(f"⚠ Skipped {insufficient_stock} orders due to insufficient stock")


def print_summary():
    """Print summary statistics"""
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    total_orders = Order.objects.count()
    total_items = OrderItem.objects.count()
    total_revenue = Order.objects.filter(status='COMPLETED').aggregate(
        total=models.Sum('total_amount')
    )['total'] or 0
    
    print(f"Total Orders:          {total_orders}")
    print(f"Total Order Items:     {total_items}")
    print(f"Completed Orders:      {Order.objects.filter(status='COMPLETED').count()}")
    print(f"Pending Orders:        {Order.objects.filter(status='PENDING').count()}")
    print(f"In Transit:            {Order.objects.filter(status__in=['SHIPPED', 'IN_TRANSIT']).count()}")
    print(f"Total Revenue:         ₹{total_revenue:,.2f}")
    print(f"Inventory Updated:     {Order.objects.filter(inventory_updated=True).count()}")
    print(f"Payments Recorded:     {OrderPayment.objects.count()}")
    print(f"Status Changes:        {OrderStatusHistory.objects.count()}")
    
    print("\nOrder Status Distribution:")
    from django.db.models import Count
    statuses = Order.objects.values('status').annotate(count=Count('id')).order_by('-count')
    for status in statuses:
        print(f"  {status['status']:20s}: {status['count']:3d} orders")


def main():
    """Main execution function"""
    print("\n" + "="*60)
    print("ORDER DATA IMPORT SCRIPT")
    print("="*60)
    
    try:
        # Import models at runtime to avoid errors
        from django.db import models
        
        # Step 1: Get farmers
        farmers = list(Farmer.objects.all())
        if not farmers:
            print("⚠ No farmers found! Please run farmer import script first.")
            return
        print(f"✓ Found {len(farmers)} farmers")
        
        # Step 2: Create farmer profiles
        create_farmer_profiles()
        
        # Step 3: Create notification templates
        create_notification_templates()
        
        # Step 4: Create sample orders
        orders = create_sample_orders(farmers, num_orders=50)
        
        # Step 5: Complete some orders and update inventory
        complete_some_orders(orders, percentage=20)
        
        # Step 6: Print summary
        print_summary()
        
        print("\n" + "="*60)
        print("✓ IMPORT COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\nYou can now:")
        print("  1. Visit /orders/ to see the dashboard")
        print("  2. Visit /orders/list/ to see all orders")
        print("  3. Click on any order to see details")
        print("  4. Try completing more orders to update inventory")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()