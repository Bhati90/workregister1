# summary/management/commands/populate_daily_summary.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q, F
from datetime import datetime, timedelta
from decimal import Decimal

from summery.models import DailySummary, PerformanceMetric, Alert
from order.models import Order, OrderPayment
from inventory.models import ProductSKU, StockHistory, StockAlert
from tasks.models import FarmerTaskStatus
from cropcycle.models import FarmerCropCycle
from schedule.models import Farmer
from flow.models import WhatsAppCall, UserFlowSessions, Flows


class Command(BaseCommand):
    help = 'Populate daily summary data from existing models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Date to populate (YYYY-MM-DD). Default is today.',
        )
        parser.add_argument(
            '--days-back',
            type=int,
            default=0,
            help='Number of days back to populate. Default is 0 (today only).',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update existing summaries',
        )

    def handle(self, *args, **options):
        if options['date']:
            target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            self.populate_for_date(target_date, options['force'])
        else:
            days_back = options['days_back']
            today = timezone.now().date()
            
            for i in range(days_back + 1):
                target_date = today - timedelta(days=i)
                self.populate_for_date(target_date, options['force'])

        self.stdout.write(self.style.SUCCESS('Successfully populated daily summaries'))

    def populate_for_date(self, target_date, force=False):
        """Populate or update summary for a specific date"""
        self.stdout.write(f'Processing date: {target_date}')

        # Check if summary exists
        summary, created = DailySummary.objects.get_or_create(
            date=target_date,
            defaults=self.get_default_summary_data(target_date)
        )

        if not created and not force:
            self.stdout.write(
                self.style.WARNING(f'Summary for {target_date} already exists. Use --force to update.')
            )
            return

        # Update summary with actual data
        self.update_order_metrics(summary, target_date)
        self.update_revenue_metrics(summary, target_date)
        self.update_inventory_metrics(summary, target_date)
        self.update_task_metrics(summary, target_date)
        self.update_farmer_metrics(summary, target_date)
        self.update_whatsapp_metrics(summary, target_date)

        summary.save()

        # Generate alerts if needed
        self.generate_alerts(summary, target_date)

        # Create performance metrics
        self.create_performance_metrics(target_date)

        self.stdout.write(
            self.style.SUCCESS(f'✓ Completed summary for {target_date}')
        )

    def get_default_summary_data(self, date):
        """Get default data structure for summary"""
        return {
            'total_orders': 0,
            'orders_pending': 0,
            'orders_completed': 0,
            'orders_cancelled': 0,
            'order_completion_rate': Decimal('0.00'),
            'total_revenue': Decimal('0.00'),
            'total_payments_collected': Decimal('0.00'),
            'pending_payments': Decimal('0.00'),
            'average_order_value': Decimal('0.00'),
            'low_stock_items': 0,
            'out_of_stock_items': 0,
            'total_products': 0,
            'inventory_value': Decimal('0.00'),
            'tasks_completed': 0,
            'tasks_overdue': 0,
            'tasks_pending': 0,
            'task_completion_rate': Decimal('0.00'),
            'active_farmers': 0,
            'active_crop_cycles': 0,
            'new_farmers': 0,
            'total_messages_sent': 0,
            'total_messages_received': 0,
            'flow_completions': 0,
            'flow_dropoffs': 0,
            'call_volume': 0,
        }

    def update_order_metrics(self, summary, date):
        """Update order-related metrics"""
        # Filter orders created on this date
        orders_on_date = Order.objects.filter(created_at__date=date)

        summary.total_orders = orders_on_date.count()
        summary.orders_pending = orders_on_date.filter(
            status__in=['PENDING', 'CONFIRMED', 'PROCESSING']
        ).count()
        summary.orders_completed = orders_on_date.filter(
            status__in=['COMPLETED', 'DELIVERED']
        ).count()
        summary.orders_cancelled = orders_on_date.filter(
            status='CANCELLED'
        ).count()

        # Calculate completion rate
        if summary.total_orders > 0:
            summary.order_completion_rate = Decimal(
                (summary.orders_completed / summary.total_orders) * 100
            ).quantize(Decimal('0.01'))

    def update_revenue_metrics(self, summary, date):
        """Update revenue and payment metrics"""
        # Total revenue from orders created on this date
        orders_on_date = Order.objects.filter(created_at__date=date)
        
        revenue_data = orders_on_date.aggregate(
            total=Sum('total_amount'),
            paid=Sum('paid_amount')
        )

        summary.total_revenue = revenue_data['total'] or Decimal('0.00')
        
        # Payments collected on this date (regardless of order date)
        payments_on_date = OrderPayment.objects.filter(payment_date__date=date)
        summary.total_payments_collected = payments_on_date.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        # Pending payments (all unpaid orders up to this date)
        all_orders = Order.objects.filter(created_at__date__lte=date)
        summary.pending_payments = all_orders.aggregate(
            pending=Sum(F('total_amount') - F('paid_amount'))
        )['pending'] or Decimal('0.00')

        # Average order value
        if summary.total_orders > 0:
            summary.average_order_value = (
                summary.total_revenue / summary.total_orders
            ).quantize(Decimal('0.01'))

    def update_inventory_metrics(self, summary, date):
        """Update inventory metrics"""
        # Get SKU status as of this date
        skus = ProductSKU.objects.all()

        summary.low_stock_items = sum(1 for sku in skus if sku.is_low_stock())
        summary.out_of_stock_items = skus.filter(stock_quantity=0).count()
        summary.total_products = skus.count()

        # Calculate inventory value
        inventory_value = sum(
            (sku.stock_quantity or 0) * (sku.price or 0)
            for sku in skus
        )
        summary.inventory_value = Decimal(str(inventory_value)).quantize(Decimal('0.01'))

    def update_task_metrics(self, summary, date):
        """Update task completion metrics"""
        # Tasks that should have been completed by this date
        tasks_due = FarmerTaskStatus.objects.filter(
            planned_end_date__lte=date
        )

        summary.tasks_completed = tasks_due.filter(
            status='COMPLETED',
            actual_completion_date__lte=date
        ).count()

        summary.tasks_overdue = tasks_due.filter(
            status='OVERDUE'
        ).count()

        # Pending tasks as of this date
        summary.tasks_pending = FarmerTaskStatus.objects.filter(
            status='PENDING',
            planned_start_date__lte=date
        ).count()

        # Task completion rate
        total_tasks = tasks_due.count()
        if total_tasks > 0:
            summary.task_completion_rate = Decimal(
                (summary.tasks_completed / total_tasks) * 100
            ).quantize(Decimal('0.01'))

    def update_farmer_metrics(self, summary, date):
        """Update farmer engagement metrics"""
        # Active farmers (those with active crop cycles or recent orders)
        active_farmers_ids = set()

        # Farmers with active crop cycles
        active_cycles = FarmerCropCycle.objects.filter(
            is_active=True,
            sowing_date__lte=date
        )
        active_farmers_ids.update(
            active_cycles.values_list('farmer_id', flat=True)
        )

        # Farmers with orders in last 30 days
        recent_orders = Order.objects.filter(
            created_at__date__lte=date,
            created_at__date__gte=date - timedelta(days=30)
        )
        active_farmers_ids.update(
            recent_orders.values_list('farmer_id', flat=True)
        )

        summary.active_farmers = len(active_farmers_ids)

        # Active crop cycles
        summary.active_crop_cycles = active_cycles.count()

        # New farmers registered on this date
        summary.new_farmers = Farmer.objects.filter(
            created_at__date=date
        ).count()

    def update_whatsapp_metrics(self, summary, date):
        """Update WhatsApp engagement metrics"""
        # Note: You'll need to implement message tracking in your WhatsApp models
        # For now, we'll use available data

        # Call volume
        summary.call_volume = WhatsAppCall.objects.filter(
            created_at__date=date
        ).count()

        # Flow completions (sessions that completed on this date)
        # This is approximate - you may need to add completion tracking
        active_sessions = UserFlowSessions.objects.filter(
            updated_at__date=date
        )
        summary.flow_completions = active_sessions.count()

        # You may want to add fields to UserFlowSessions to track:
        # - is_completed
        # - completed_at
        # - dropped_at
        # For now, we'll estimate based on session updates

    def generate_alerts(self, summary, date):
        """Generate alerts based on summary metrics"""
        # Critical: Out of stock items
        if summary.out_of_stock_items > 0:
            Alert.objects.get_or_create(
                title=f"{summary.out_of_stock_items} Products Out of Stock",
                category='INVENTORY',
                severity='CRITICAL',
                status='ACTIVE',
                defaults={
                    'description': f"There are {summary.out_of_stock_items} products completely out of stock as of {date}.",
                    'current_value': Decimal(str(summary.out_of_stock_items)),
                    'threshold_value': Decimal('0'),
                }
            )

        # High: Low completion rate
        if summary.order_completion_rate < 70:
            Alert.objects.get_or_create(
                title=f"Low Order Completion Rate: {summary.order_completion_rate}%",
                category='ORDERS',
                severity='HIGH',
                status='ACTIVE',
                defaults={
                    'description': f"Order completion rate is below 70% on {date}.",
                    'current_value': summary.order_completion_rate,
                    'threshold_value': Decimal('70.00'),
                }
            )

        # Medium: Low stock items
        if summary.low_stock_items > 5:
            Alert.objects.get_or_create(
                title=f"{summary.low_stock_items} Products Running Low",
                category='INVENTORY',
                severity='MEDIUM',
                status='ACTIVE',
                defaults={
                    'description': f"{summary.low_stock_items} products are below reorder level as of {date}.",
                    'current_value': Decimal(str(summary.low_stock_items)),
                    'threshold_value': Decimal('5'),
                }
            )

        # High: Many overdue tasks
        if summary.tasks_overdue > 10:
            Alert.objects.get_or_create(
                title=f"{summary.tasks_overdue} Tasks Overdue",
                category='TASKS',
                severity='HIGH',
                status='ACTIVE',
                defaults={
                    'description': f"There are {summary.tasks_overdue} overdue tasks as of {date}.",
                    'current_value': Decimal(str(summary.tasks_overdue)),
                    'threshold_value': Decimal('10'),
                }
            )

    def create_performance_metrics(self, date):
        """Create performance metric entries for the date"""
        # Order Fulfillment Rate
        orders = Order.objects.filter(created_at__date__lte=date)
        if orders.exists():
            completed = orders.filter(status__in=['COMPLETED', 'DELIVERED']).count()
            rate = (completed / orders.count()) * 100
            
            PerformanceMetric.objects.update_or_create(
                metric_type='ORDER_FULFILLMENT',
                date=date,
                defaults={
                    'value': Decimal(str(rate)).quantize(Decimal('0.01')),
                    'target_value': Decimal('90.00'),
                }
            )

        # Task Completion Rate
        tasks = FarmerTaskStatus.objects.filter(planned_end_date__lte=date)
        if tasks.exists():
            completed_tasks = tasks.filter(status='COMPLETED').count()
            task_rate = (completed_tasks / tasks.count()) * 100
            
            PerformanceMetric.objects.update_or_create(
                metric_type='TASK_COMPLETION',
                date=date,
                defaults={
                    'value': Decimal(str(task_rate)).quantize(Decimal('0.01')),
                    'target_value': Decimal('85.00'),
                }
            )

        # Payment Collection Rate
        all_orders = Order.objects.filter(created_at__date__lte=date)
        if all_orders.exists():
            total_amount = all_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            paid_amount = all_orders.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0
            
            if total_amount > 0:
                payment_rate = (paid_amount / total_amount) * 100
                
                PerformanceMetric.objects.update_or_create(
                    metric_type='PAYMENT_COLLECTION',
                    date=date,
                    defaults={
                        'value': Decimal(str(payment_rate)).quantize(Decimal('0.01')),
                        'target_value': Decimal('95.00'),
                    }
                )

        # Farmer Engagement (active farmers ratio)
        total_farmers = Farmer.objects.filter(created_at__date__lte=date).count()
        if total_farmers > 0:
            active_farmers = FarmerCropCycle.objects.filter(
                is_active=True,
                sowing_date__lte=date
            ).values('farmer').distinct().count()
            
            engagement_rate = (active_farmers / total_farmers) * 100
            
            PerformanceMetric.objects.update_or_create(
                metric_type='FARMER_ENGAGEMENT',
                date=date,
                defaults={
                    'value': Decimal(str(engagement_rate)).quantize(Decimal('0.01')),
                    'target_value': Decimal('75.00'),
                }
            )