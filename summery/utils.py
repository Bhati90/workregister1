# summary/utils.py
# Utility functions for real-time summary data

from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from orders.models import Order, OrderPayment
from inventory.models import ProductSKU, StockAlert
from tasks.models import FarmerTaskStatus
from cropcycle.models import FarmerCropCycle
from schedule.models import Farmer
from whatsapp.models import WhatsAppCall


def get_realtime_summary():
    """
    Get real-time summary data without saving to database.
    Useful for dashboard displays.
    """
    today = timezone.now().date()
    
    return {
        'orders': get_realtime_order_metrics(today),
        'revenue': get_realtime_revenue_metrics(today),
        'inventory': get_realtime_inventory_metrics(),
        'tasks': get_realtime_task_metrics(today),
        'farmers': get_realtime_farmer_metrics(today),
        'alerts': get_realtime_alert_summary(),
    }


def get_realtime_order_metrics(date=None):
    """Get real-time order metrics"""
    if date is None:
        date = timezone.now().date()
    
    orders = Order.objects.filter(created_at__date=date)
    
    total = orders.count()
    pending = orders.filter(status__in=['PENDING', 'CONFIRMED', 'PROCESSING']).count()
    completed = orders.filter(status__in=['COMPLETED', 'DELIVERED']).count()
    cancelled = orders.filter(status='CANCELLED').count()
    
    completion_rate = (completed / total * 100) if total > 0 else 0
    
    return {
        'total_orders': total,
        'pending': pending,
        'completed': completed,
        'cancelled': cancelled,
        'completion_rate': round(completion_rate, 2),
    }


def get_realtime_revenue_metrics(date=None):
    """Get real-time revenue metrics"""
    if date is None:
        date = timezone.now().date()
    
    orders = Order.objects.filter(created_at__date=date)
    payments = OrderPayment.objects.filter(payment_date__date=date)
    
    total_revenue = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
    payments_collected = payments.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    
    # Pending payments across all orders
    all_orders = Order.objects.filter(created_at__date__lte=date)
    pending_payments = all_orders.aggregate(
        pending=Sum(F('total_amount') - F('paid_amount'))
    )['pending'] or Decimal('0.00')
    
    avg_order_value = (total_revenue / orders.count()) if orders.count() > 0 else Decimal('0.00')
    
    return {
        'total_revenue': float(total_revenue),
        'payments_collected': float(payments_collected),
        'pending_payments': float(pending_payments),
        'average_order_value': float(avg_order_value),
    }


def get_realtime_inventory_metrics():
    """Get real-time inventory metrics"""
    skus = ProductSKU.objects.all()
    
    low_stock = sum(1 for sku in skus if sku.is_low_stock())
    out_of_stock = skus.filter(stock_quantity=0).count()
    total_products = skus.count()
    
    # Calculate inventory value
    inventory_value = sum(
        (sku.stock_quantity or 0) * (sku.price or 0)
        for sku in skus
    )
    
    # Active stock alerts
    active_alerts = StockAlert.objects.filter(status='ACTIVE').count()
    
    return {
        'low_stock_items': low_stock,
        'out_of_stock_items': out_of_stock,
        'total_products': total_products,
        'inventory_value': float(inventory_value),
        'active_stock_alerts': active_alerts,
    }


def get_realtime_task_metrics(date=None):
    """Get real-time task metrics"""
    if date is None:
        date = timezone.now().date()
    
    # Tasks that should be completed by today
    tasks_due = FarmerTaskStatus.objects.filter(planned_end_date__lte=date)
    
    completed = tasks_due.filter(status='COMPLETED').count()
    overdue = tasks_due.filter(status='OVERDUE').count()
    pending = FarmerTaskStatus.objects.filter(
        status='PENDING',
        planned_start_date__lte=date
    ).count()
    in_progress = FarmerTaskStatus.objects.filter(status='IN_PROGRESS').count()
    
    total = tasks_due.count()
    completion_rate = (completed / total * 100) if total > 0 else 0
    
    return {
        'tasks_completed': completed,
        'tasks_overdue': overdue,
        'tasks_pending': pending,
        'tasks_in_progress': in_progress,
        'completion_rate': round(completion_rate, 2),
    }


def get_realtime_farmer_metrics(date=None):
    """Get real-time farmer metrics"""
    if date is None:
        date = timezone.now().date()
    
    # Active farmers with crop cycles
    active_crop_cycles = FarmerCropCycle.objects.filter(
        is_active=True,
        sowing_date__lte=date
    )
    
    active_farmers_from_cycles = active_crop_cycles.values('farmer').distinct().count()
    
    # Farmers with recent orders
    recent_orders = Order.objects.filter(
        created_at__date__gte=date - timedelta(days=30),
        created_at__date__lte=date
    )
    active_farmers_from_orders = recent_orders.values('farmer').distinct().count()
    
    # Combine unique farmers
    active_farmers = max(active_farmers_from_cycles, active_farmers_from_orders)
    
    # New farmers today
    new_farmers = Farmer.objects.filter(created_at__date=date).count()
    
    # Total farmers
    total_farmers = Farmer.objects.count()
    
    return {
        'active_farmers': active_farmers,
        'active_crop_cycles': active_crop_cycles.count(),
        'new_farmers': new_farmers,
        'total_farmers': total_farmers,
        'engagement_rate': round((active_farmers / total_farmers * 100) if total_farmers > 0 else 0, 2),
    }


def get_realtime_alert_summary():
    """Get summary of active alerts by severity"""
    from summary.models import Alert
    
    return {
        'critical': Alert.objects.filter(status='ACTIVE', severity='CRITICAL').count(),
        'high': Alert.objects.filter(status='ACTIVE', severity='HIGH').count(),
        'medium': Alert.objects.filter(status='ACTIVE', severity='MEDIUM').count(),
        'low': Alert.objects.filter(status='ACTIVE', severity='LOW').count(),
        'total_active': Alert.objects.filter(status='ACTIVE').count(),
    }


def get_comparison_data(days=7):
    """
    Get comparison data for the last N days.
    Returns data suitable for charts.
    """
    from summary.models import DailySummary
    
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    summaries = DailySummary.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date')
    
    return {
        'dates': [s.date.isoformat() for s in summaries],
        'orders': [s.total_orders for s in summaries],
        'revenue': [float(s.total_revenue) for s in summaries],
        'active_farmers': [s.active_farmers for s in summaries],
        'task_completion_rate': [float(s.task_completion_rate) for s in summaries],
        'order_completion_rate': [float(s.order_completion_rate) for s in summaries],
    }


def get_top_performers(metric='revenue', limit=10, period_days=30):
    """
    Get top performing farmers based on specified metric.
    """
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=period_days)
    
    if metric == 'revenue':
        # Top farmers by revenue
        farmer_revenues = Order.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).values('farmer', 'farmer__name').annotate(
            total_revenue=Sum('total_amount'),
            order_count=Count('id')
        ).order_by('-total_revenue')[:limit]
        
        return [{
            'farmer_id': str(item['farmer']),
            'farmer_name': item['farmer__name'],
            'total_revenue': float(item['total_revenue']),
            'order_count': item['order_count'],
        } for item in farmer_revenues]
    
    elif metric == 'orders':
        # Top farmers by order count
        farmer_orders = Order.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).values('farmer', 'farmer__name').annotate(
            order_count=Count('id'),
            total_revenue=Sum('total_amount')
        ).order_by('-order_count')[:limit]
        
        return [{
            'farmer_id': str(item['farmer']),
            'farmer_name': item['farmer__name'],
            'order_count': item['order_count'],
            'total_revenue': float(item['total_revenue']),
        } for item in farmer_orders]
    
    elif metric == 'task_completion':
        # Top farmers by task completion
        farmer_tasks = FarmerTaskStatus.objects.filter(
            planned_end_date__gte=start_date,
            planned_end_date__lte=end_date
        ).values('farmer_crop_cycle__farmer', 'farmer_crop_cycle__farmer__name').annotate(
            total_tasks=Count('id'),
            completed_tasks=Count('id', filter=Q(status='COMPLETED'))
        ).order_by('-completed_tasks')[:limit]
        
        return [{
            'farmer_id': str(item['farmer_crop_cycle__farmer']),
            'farmer_name': item['farmer_crop_cycle__farmer__name'],
            'total_tasks': item['total_tasks'],
            'completed_tasks': item['completed_tasks'],
            'completion_rate': round((item['completed_tasks'] / item['total_tasks'] * 100) if item['total_tasks'] > 0 else 0, 2),
        } for item in farmer_tasks]
    
    return []


def get_product_performance(period_days=30):
    """Get top selling products"""
    from orders.models import OrderItem
    
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=period_days)
    
    product_sales = OrderItem.objects.filter(
        order__created_at__date__gte=start_date,
        order__created_at__date__lte=end_date,
        order__status__in=['COMPLETED', 'DELIVERED']
    ).values(
        'sku__product__name',
        'sku__size'
    ).annotate(
        quantity_sold=Sum('quantity'),
        revenue=Sum('total_price')
    ).order_by('-quantity_sold')[:10]
    
    return [{
        'product_name': item['sku__product__name'],
        'size': item['sku__size'],
        'quantity_sold': item['quantity_sold'],
        'revenue': float(item['revenue']),
    } for item in product_sales]


def calculate_kpis():
    """Calculate key performance indicators"""
    today = timezone.now().date()
    last_30_days = today - timedelta(days=30)
    
    # Revenue KPIs
    revenue_30d = Order.objects.filter(
        created_at__date__gte=last_30_days
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Order KPIs
    total_orders = Order.objects.filter(created_at__date__gte=last_30_days).count()
    completed_orders = Order.objects.filter(
        created_at__date__gte=last_30_days,
        status__in=['COMPLETED', 'DELIVERED']
    ).count()
    
    # Farmer KPIs
    active_farmers = FarmerCropCycle.objects.filter(
        is_active=True
    ).values('farmer').distinct().count()
    
    total_farmers = Farmer.objects.count()
    
    # Task KPIs
    tasks_due = FarmerTaskStatus.objects.filter(
        planned_end_date__lte=today
    )
    task_completion_rate = (
        tasks_due.filter(status='COMPLETED').count() / tasks_due.count() * 100
    ) if tasks_due.count() > 0 else 0
    
    return {
        'monthly_revenue': float(revenue_30d),
        'monthly_orders': total_orders,
        'order_fulfillment_rate': round((completed_orders / total_orders * 100) if total_orders > 0 else 0, 2),
        'farmer_engagement_rate': round((active_farmers / total_farmers * 100) if total_farmers > 0 else 0, 2),
        'task_completion_rate': round(task_completion_rate, 2),
        'active_farmers': active_farmers,
        'total_farmers': total_farmers,
    }