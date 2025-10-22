"""
Standalone Django Script to Populate Summary App Models
Run with: python populate_summary_data.py

This script will:
1.  Aggregate data from your order, inventory, and schedule apps.
2.  Populate the DailySummary model for the last 60 days.
3.  Generate GeographicPerformance metrics.
4.  Create sample AlertRules.
5.  Check rules against daily summaries and create Alerts.
6.  (Optional) Can be extended to populate other analysis models.
"""

import os
import django
import random
from datetime import timedelta
from decimal import Decimal

# --- DJANGO SETUP ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'labour_crm.settings')
django.setup()
# --- END DJANGO SETUP ---

from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Count, Avg, F, Case, When, Value, IntegerField, DecimalField

# Import models from other apps
from order.models import Order, FarmerProfile
from inventory.models import ProductSKU
from schedule.models import Farmer
 # Assuming you have a Task model in schedule
from django.contrib.auth.models import User
from tasks.models import Task
# Import models to populate
from summery.models import (
    DailySummary,
    GeographicPerformance,
    AlertRule,
    Alert
)

# --- CONFIGURATION ---
DAYS_TO_PROCESS = 60 # How many past days of data to generate

def populate_daily_summaries(start_date, end_date):
    """
    Calculates and saves daily summary metrics for a given date range.
    This is the core function that aggregates data from other apps.
    """
    print("\n" + "="*60)
    print(f"STEP 1: Populating Daily Summaries from {start_date} to {end_date}")
    print("="*60)

    current_date = start_date
    days_processed = 0

    while current_date <= end_date:
        print(f"  Processing summary for: {current_date.strftime('%Y-%m-%d')}...")

        with transaction.atomic():
            # --- ORDER METRICS ---
            orders_today = Order.objects.filter(created_at__date=current_date)
            order_metrics = orders_today.aggregate(
                total_orders=Count('id'),
                orders_pending=Count(Case(When(status='PENDING', then=1), output_field=IntegerField())),
                orders_completed=Count(Case(When(status='COMPLETED', then=1), output_field=IntegerField())),
                orders_cancelled=Count(Case(When(status='CANCELLED', then=1), output_field=IntegerField())),
                total_revenue=Sum(
                    Case(When(status='COMPLETED', then=F('total_amount')), default=Value(0), output_field=DecimalField())
                ),
                total_payments_collected=Sum('payments__amount', default=Decimal('0.00'))
            )
            total_orders = order_metrics['total_orders']
            orders_completed = order_metrics['orders_completed']
            order_completion_rate = (orders_completed / total_orders * 100) if total_orders > 0 else 0

            # --- INVENTORY METRICS ---
            inventory_metrics = ProductSKU.objects.aggregate(
                low_stock_items=Count(Case(When(stock_quantity__lte=F('reorder_level'), stock_quantity__gt=0, then=1))),
                out_of_stock_items=Count(Case(When(stock_quantity=0, then=1))),
                total_products=Count('id'),
                inventory_value=Sum(F('stock_quantity') * F('price'), output_field=DecimalField())
            )

            # --- TASK METRICS (assuming a Task model) ---
            tasks_today = Task.objects.filter(created_at__date=current_date)
            task_metrics = tasks_today.aggregate(
                tasks_completed=Count(Case(When(status='COMPLETED', then=1))),
                tasks_overdue=Count(Case(When(due_date__lt=current_date, status__in=['PENDING', 'IN_PROGRESS'], then=1))),
                tasks_pending=Count(Case(When(status='PENDING', then=1))),
            )
            total_tasks = tasks_today.count()
            tasks_completed = task_metrics.get('tasks_completed', 0)
            task_completion_rate = (tasks_completed / total_tasks * 100) if total_tasks > 0 else 0

            # --- FARMER ENGAGEMENT ---
            active_farmers_count = orders_today.values('farmer_id').distinct().count()
            new_farmers_count = Farmer.objects.filter(created_at__date=current_date).count()

            # --- CREATE OR UPDATE SUMMARY OBJECT ---
            summary, created = DailySummary.objects.update_or_create(
                date=current_date,
                defaults={
                    # Order Metrics
                    'total_orders': total_orders,
                    'orders_pending': order_metrics.get('orders_pending', 0),
                    'orders_completed': orders_completed,
                    'orders_cancelled': order_metrics.get('orders_cancelled', 0),
                    'order_completion_rate': round(Decimal(order_completion_rate), 2),
                    # Revenue Metrics
                    'total_revenue': order_metrics.get('total_revenue', Decimal('0.00')),
                    'total_payments_collected': order_metrics.get('total_payments_collected', Decimal('0.00')),
                    'pending_payments': F('total_revenue') - F('total_payments_collected'), # Calculated in DB
                    'average_order_value': (order_metrics['total_revenue'] / total_orders) if total_orders > 0 else 0,
                    # Inventory Metrics
                    'low_stock_items': inventory_metrics.get('low_stock_items', 0),
                    'out_of_stock_items': inventory_metrics.get('out_of_stock_items', 0),
                    'total_products': inventory_metrics.get('total_products', 0),
                    'inventory_value': inventory_metrics.get('inventory_value', Decimal('0.00')),
                    # Task Metrics
                    'tasks_completed': tasks_completed,
                    'tasks_overdue': task_metrics.get('tasks_overdue', 0),
                    'tasks_pending': task_metrics.get('tasks_pending', 0),
                    'task_completion_rate': round(Decimal(task_completion_rate), 2),
                    # Farmer Engagement
                    'active_farmers': active_farmers_count,
                    'new_farmers': new_farmers_count,
                    # (Dummy WhatsApp Metrics)
                    'total_messages_sent': random.randint(50, 200),
                    'total_messages_received': random.randint(40, 150),
                }
            )
        
        days_processed += 1
        current_date += timedelta(days=1)
    
    print(f"✓ Processed and saved {days_processed} daily summaries.")


def populate_geographic_performance(start_date, end_date):
    """Aggregates performance metrics by district."""
    print("\n" + "="*60)
    print("STEP 2: Populating Geographic Performance")
    print("="*60)
    
    districts = FarmerProfile.objects.values_list('district', flat=True).distinct()
    
    with transaction.atomic():
        for district in districts:
            if not district:
                continue
            
            print(f"  Processing performance for: {district}...")
            
            # Find farmers in this district
            farmer_ids_in_district = FarmerProfile.objects.filter(district=district).values_list('farmer_id', flat=True)
            
            # Aggregate orders for these farmers in the date range
            geo_metrics = Order.objects.filter(
                farmer_id__in=farmer_ids_in_district,
                created_at__date__range=[start_date, end_date]
            ).aggregate(
                total_orders=Count('id'),
                total_revenue=Sum('total_amount', default=Decimal('0.00')),
                cancelled_orders=Count(Case(When(status='CANCELLED', then=1)))
            )

            GeographicPerformance.objects.update_or_create(
                district=district,
                period_start=start_date,
                period_end=end_date,
                defaults={
                    'total_farmers': len(farmer_ids_in_district),
                    'total_orders': geo_metrics['total_orders'],
                    'total_revenue': geo_metrics['total_revenue'],
                    'average_order_value': (geo_metrics['total_revenue'] / geo_metrics['total_orders']) if geo_metrics['total_orders'] > 0 else 0,
                    'cancelled_orders': geo_metrics['cancelled_orders'],
                    # Dummy values for other metrics
                    'active_farmers_count': int(len(farmer_ids_in_district) * random.uniform(0.6, 0.9)),
                    'task_completion_rate': round(Decimal(random.uniform(70, 98)), 2),
                    'overdue_tasks': random.randint(0, 5)
                }
            )
            
    print(f"✓ Saved performance data for {len(districts)} districts.")


def create_alert_rules():
    """Create a set of predefined alert rules if they don't exist."""
    print("\n" + "="*60)
    print("STEP 3: Creating Alert Rules")
    print("="*60)
    
    rules = [
        {
            'name': 'High Number of Cancelled Orders',
            'category': 'ORDERS',
            'severity': 'HIGH',
            'metric_type': 'orders_cancelled',
            'condition_operator': 'GTE',
            'threshold_value': 5,
            'title_template': 'High Order Cancellations: {current_value} cancelled today',
            'description_template': 'The number of cancelled orders ({current_value}) has exceeded the threshold of {threshold_value}. Please investigate.'
        },
        {
            'name': 'Low Stock Alert for Multiple Items',
            'category': 'INVENTORY',
            'severity': 'MEDIUM',
            'metric_type': 'low_stock_items',
            'condition_operator': 'GTE',
            'threshold_value': 10,
            'title_template': 'Low Stock Alert: {current_value} items are running low',
            'description_template': 'There are {current_value} items with stock below their reorder level. Threshold is {threshold_value}. Please restock.'
        },
        {
            'name': 'Zero Revenue Day',
            'category': 'FINANCIAL',
            'severity': 'CRITICAL',
            'metric_type': 'total_revenue',
            'condition_operator': 'EQ',
            'threshold_value': 0,
            'title_template': 'Critical: Zero revenue recorded today',
            'description_template': 'No completed orders with revenue were recorded today. Please check for system issues or data processing errors.'
        },
        {
            'name': 'High Number of Overdue Tasks',
            'category': 'TASKS',
            'severity': 'HIGH',
            'metric_type': 'tasks_overdue',
            'condition_operator': 'GTE',
            'threshold_value': 10,
            'title_template': 'Task Alert: {current_value} tasks are overdue',
            'description_template': 'There are {current_value} overdue tasks, exceeding the threshold of {threshold_value}. Follow up is required.'
        }
    ]
    
    created_count = 0
    for rule_data in rules:
        _, created = AlertRule.objects.get_or_create(name=rule_data['name'], defaults=rule_data)
        if created:
            created_count += 1
            
    print(f"✓ Created {created_count} new alert rules. Total rules: {AlertRule.objects.count()}")


def check_rules_and_create_alerts(start_date, end_date):
    """Check daily summaries against alert rules and create alerts."""
    print("\n" + "="*60)
    print("STEP 4: Checking Rules and Creating Alerts")
    print("="*60)
    
    active_rules = AlertRule.objects.filter(is_active=True)
    summaries = DailySummary.objects.filter(date__range=[start_date, end_date])
    alerts_created = 0
    
    with transaction.atomic():
        for summary in summaries:
            for rule in active_rules:
                current_value = getattr(summary, rule.metric_type, None)
                if current_value is None:
                    continue

                # Check if the condition is met
                condition_met = False
                op = rule.condition_operator
                if op == 'GTE' and current_value >= rule.threshold_value: condition_met = True
                elif op == 'GT' and current_value > rule.threshold_value: condition_met = True
                elif op == 'LTE' and current_value <= rule.threshold_value: condition_met = True
                elif op == 'LT' and current_value < rule.threshold_value: condition_met = True
                elif op == 'EQ' and current_value == rule.threshold_value: condition_met = True
                
                if condition_met:
                    # Create the alert if it doesn't already exist for this rule and day
                    title = rule.title_template.format(current_value=current_value, threshold_value=rule.threshold_value)
                    
                    _, created = Alert.objects.get_or_create(
                        title=title,
                        created_at__date=summary.date,
                        defaults={
                            'description': rule.description_template.format(current_value=current_value, threshold_value=rule.threshold_value),
                            'severity': rule.severity,
                            'category': rule.category,
                            'status': 'ACTIVE',
                            'current_value': current_value,
                            'threshold_value': rule.threshold_value,
                            'created_at': timezone.make_aware(datetime.combine(summary.date, datetime.min.time()))
                        }
                    )
                    if created:
                        alerts_created += 1

    print(f"✓ Checked {summaries.count()} summaries against {active_rules.count()} rules. Created {alerts_created} new alerts.")


def main():
    """Main execution function"""
    print("\n" + "="*60)
    print("SUMMARY DATA POPULATION SCRIPT")
    print("="*60)

    try:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=DAYS_TO_PROCESS)

        # Step 1: Populate daily summaries
        populate_daily_summaries(start_date, end_date)

        # Step 2: Populate geographic performance
        populate_geographic_performance(start_date, end_date)
        
        # Step 3: Create alert rules
        create_alert_rules()
        
        # Step 4: Check rules and create alerts
        check_rules_and_create_alerts(start_date, end_date)
        
        # (You can add calls to populate other models like TrendAnalysis here)

        print("\n" + "="*60)
        print("✓ SUMMARY POPULATION COMPLETED SUCCESSFULLY!")
        print("="*60)

    except Exception as e:
        print(f"\n❌ ERROR: An unexpected error occurred: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # Ensure a user exists to be assigned as creator/resolver if needed
    if not User.objects.filter(is_superuser=True).exists():
        print("Creating a default superuser 'admin' with password 'admin'...")
        User.objects.create_superuser('admin', 'admin@example.com', 'admin')

    main()