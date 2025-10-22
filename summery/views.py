# summary/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, Avg, Count, Q, F
from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from .models import (
    DailySummary, PerformanceMetric, GrowthMetric, 
    GeographicPerformance, Alert, AlertRule, 
    AnomalyDetection, TrendAnalysis, BenchmarkComparison
)


# ==============================================================================
#  DASHBOARD VIEWS
# ==============================================================================

def dashboard(request):
    """Main dashboard with LIVE real-time metrics"""
    from order.models import Order, OrderPayment
    from inventory.models import ProductSKU
    from tasks.models import FarmerTaskStatus
    from cropcycle.models import FarmerCropCycle
    from schedule.models import Farmer
    from flow.models import WhatsAppCall
    
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    # ============================================
    # LIVE ORDER METRICS (Real-time from database)
    # ============================================
    today_orders = Order.objects.filter(created_at__date=today)
    yesterday_orders = Order.objects.filter(created_at__date=yesterday)
    
    live_orders = {
        'total': today_orders.count(),
        'pending': today_orders.filter(status__in=['PENDING', 'CONFIRMED', 'PROCESSING']).count(),
        'completed': today_orders.filter(status__in=['COMPLETED', 'DELIVERED']).count(),
        'cancelled': today_orders.filter(status='CANCELLED').count(),
        'yesterday_total': yesterday_orders.count(),
    }
    
    if live_orders['total'] > 0:
        live_orders['completion_rate'] = round((live_orders['completed'] / live_orders['total']) * 100, 2)
    else:
        live_orders['completion_rate'] = 0
    
    # ============================================
    # LIVE REVENUE METRICS (Real-time)
    # ============================================
    today_revenue = today_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
    yesterday_revenue = yesterday_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
    
    today_payments = OrderPayment.objects.filter(payment_date__date=today)
    payments_collected = today_payments.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    
    all_orders = Order.objects.all()
    pending_payments = all_orders.aggregate(
        pending=Sum(F('total_amount') - F('paid_amount'))
    )['pending'] or Decimal('0.00')
    
    avg_order_value = (today_revenue / live_orders['total']) if live_orders['total'] > 0 else Decimal('0.00')
    
    live_revenue = {
        'total': float(today_revenue),
        'yesterday': float(yesterday_revenue),
        'payments_collected': float(payments_collected),
        'pending_payments': float(pending_payments),
        'average_order_value': float(avg_order_value),
    }
    
    # ============================================
    # LIVE INVENTORY METRICS (Real-time)
    # ============================================
    all_skus = ProductSKU.objects.all()
    
    low_stock = sum(1 for sku in all_skus if sku.is_low_stock() and sku.stock_quantity > 0)
    out_of_stock = all_skus.filter(stock_quantity=0).count()
    total_products = all_skus.count()
    in_stock = total_products - low_stock - out_of_stock
    
    inventory_value = sum(
        (sku.stock_quantity or 0) * (sku.price or 0)
        for sku in all_skus
    )
    
    live_inventory = {
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'in_stock': in_stock,
        'total_products': total_products,
        'inventory_value': float(inventory_value),
    }
    
    # ============================================
    # LIVE TASK METRICS (Real-time)
    # ============================================
    all_tasks = FarmerTaskStatus.objects.all()
    tasks_due = all_tasks.filter(planned_end_date__lte=today)
    
    tasks_completed = tasks_due.filter(status='COMPLETED').count()
    tasks_overdue = all_tasks.filter(status='OVERDUE').count()
    tasks_pending = all_tasks.filter(status='PENDING').count()
    tasks_in_progress = all_tasks.filter(status='IN_PROGRESS').count()
    
    total_due = tasks_due.count()
    task_completion_rate = round((tasks_completed / total_due * 100) if total_due > 0 else 0, 2)
    
    live_tasks = {
        'completed': tasks_completed,
        'overdue': tasks_overdue,
        'pending': tasks_pending,
        'in_progress': tasks_in_progress,
        'completion_rate': task_completion_rate,
    }
    
    # ============================================
    # LIVE FARMER METRICS (Real-time)
    # ============================================
    active_cycles = FarmerCropCycle.objects.filter(is_active=True)
    active_farmers_count = active_cycles.values('farmer').distinct().count()
    
    new_farmers_today = Farmer.objects.filter(created_at__date=today).count()
    total_farmers = Farmer.objects.count()
    
    live_farmers = {
        'active': active_farmers_count,
        'active_cycles': active_cycles.count(),
        'new_today': new_farmers_today,
        'total': total_farmers,
    }
    
    # ============================================
    # LIVE WHATSAPP METRICS (Real-time)
    # ============================================
    today_calls = WhatsAppCall.objects.filter(created_at__date=today)
    
    live_whatsapp = {
        'call_volume': today_calls.count(),
        'messages_sent': 0,  # Add when you implement message tracking
        'messages_received': 0,  # Add when you implement message tracking
    }
    
    # ============================================
    # ACTIVE ALERTS (Real-time)
    # ============================================
    all_active_alerts = Alert.objects.filter(status='ACTIVE')
    critical_alerts_count = all_active_alerts.filter(severity='CRITICAL').count()
    active_alerts_display = all_active_alerts.order_by('-severity', '-created_at')[:10]
    
    # ============================================
    # RECENT ANOMALIES
    # ============================================
    recent_anomalies = AnomalyDetection.objects.all()[:5]
    
    # ============================================
    # HISTORICAL DATA FOR CHARTS (Last 7 days)
    # ============================================
    last_7_days = DailySummary.objects.filter(
        date__gte=today - timedelta(days=7)
    ).order_by('-date')
    
    # Calculate trends from historical data
    revenue_trend = calculate_trend(last_7_days, 'total_revenue')
    order_trend = calculate_trend(last_7_days, 'total_orders')
    
    # Chart data
    chart_data = {
        'dates': [s.date.strftime('%b %d') for s in reversed(last_7_days)],
        'orders': [s.total_orders for s in reversed(last_7_days)],
        'revenue': [float(s.total_revenue) for s in reversed(last_7_days)],
    }
    
    context = {
        # Live data
        'live_orders': live_orders,
        'live_revenue': live_revenue,
        'live_inventory': live_inventory,
        'live_tasks': live_tasks,
        'live_farmers': live_farmers,
        'live_whatsapp': live_whatsapp,
        
        # Alerts
        'active_alerts': active_alerts_display,
        'critical_alerts_count': critical_alerts_count,
        
        # Anomalies
        'recent_anomalies': recent_anomalies,
        
        # Trends
        'revenue_trend': revenue_trend,
        'order_trend': order_trend,
        
        # Chart data
        'chart_data': chart_data,
        
        # Timestamp for "Last Updated"
        'last_updated': timezone.now(),
    }
    
    return render(request, 'dashboard.html', context)


# ==============================================================================
#  DAILY SUMMARY VIEWS
# ==============================================================================

@login_required
def daily_summary_list(request):
    """List all daily summaries"""
    summaries = DailySummary.objects.all()[:30]  # Last 30 days
    
    context = {
        'summaries': summaries,
    }
    
    return render(request, 'summary/daily_summary_list.html', context)


@login_required
def daily_summary_detail(request, date):
    """Detail view for a specific daily summary"""
    summary = get_object_or_404(DailySummary, date=date)
    
    # Get previous day for comparison
    prev_date = datetime.strptime(date, '%Y-%m-%d').date() - timedelta(days=1)
    prev_summary = DailySummary.objects.filter(date=prev_date).first()
    
    # Get performance metrics for this date
    metrics = PerformanceMetric.objects.filter(date=date)
    
    # Get alerts for this date
    alerts = Alert.objects.filter(created_at__date=date)
    
    # Calculate in-stock items
    in_stock_count = summary.total_products - summary.low_stock_items - summary.out_of_stock_items
    
    context = {
        'summary': summary,
        'prev_summary': prev_summary,
        'metrics': metrics,
        'alerts': alerts,
        'in_stock_count': in_stock_count,
    }
    
    return render(request, 'summary/daily_summary_detail.html', context)


# ==============================================================================
#  PERFORMANCE METRICS VIEWS
# ==============================================================================

@login_required
def performance_metrics(request):
    """Performance metrics dashboard"""
    metric_type = request.GET.get('type', 'ORDER_FULFILLMENT')
    days = int(request.GET.get('days', 30))
    
    start_date = timezone.now().date() - timedelta(days=days)
    
    metrics = PerformanceMetric.objects.filter(
        metric_type=metric_type,
        date__gte=start_date
    ).order_by('-date')
    
    # Calculate statistics
    if metrics.exists():
        avg_value = metrics.aggregate(Avg('value'))['value__avg']
        max_value = metrics.aggregate(models.Max('value'))['value__max']
        min_value = metrics.aggregate(models.Min('value'))['value__min']
    else:
        avg_value = max_value = min_value = None
    
    context = {
        'metrics': metrics,
        'metric_type': metric_type,
        'days': days,
        'avg_value': avg_value,
        'max_value': max_value,
        'min_value': min_value,
        'metric_types': PerformanceMetric.METRIC_TYPES,
    }
    
    return render(request, 'performence_metrix.html', context)


# ==============================================================================
#  GROWTH METRICS VIEWS
# ==============================================================================

@login_required
def growth_metrics(request):
    """Growth metrics dashboard"""
    period_type = request.GET.get('period', 'MONTHLY')
    
    metrics = GrowthMetric.objects.filter(
        period_type=period_type
    ).order_by('-period_end')[:12]
    
    context = {
        'metrics': metrics,
        'period_type': period_type,
        'period_types': GrowthMetric.PERIOD_TYPES,
    }
    
    return render(request, 'growth_metrix.html', context)


# ==============================================================================
#  GEOGRAPHIC PERFORMANCE VIEWS
# ==============================================================================

@login_required
def geographic_performance(request):
    """Geographic performance dashboard"""
    district = request.GET.get('district')
    
    # Get latest period
    latest_period = GeographicPerformance.objects.order_by('-period_end').first()
    
    if latest_period:
        performances = GeographicPerformance.objects.filter(
            period_end=latest_period.period_end
        ).order_by('-total_revenue')
    else:
        performances = GeographicPerformance.objects.none()
    
    # Filter by district if specified
    if district:
        performances = performances.filter(district=district)
    
    # Get list of districts
    districts = GeographicPerformance.objects.values_list('district', flat=True).distinct()
    
    context = {
        'performances': performances,
        'districts': districts,
        'selected_district': district,
    }
    
    return render(request, 'summary/geographic_metrix.html', context)


@login_required
def geographic_detail(request, pk):
    """Detail view for geographic performance"""
    performance = get_object_or_404(GeographicPerformance, pk=pk)
    
    # Get historical data for this location
    historical = GeographicPerformance.objects.filter(
        district=performance.district,
        taluka=performance.taluka,
        village=performance.village
    ).order_by('-period_end')[:6]
    
    context = {
        'performance': performance,
        'historical': historical,
    }
    
    return render(request, 'summary/geographic_detail.html', context)


# ==============================================================================
#  ALERT VIEWS
# ==============================================================================

@login_required
def alert_list(request):
    """List all alerts with filtering"""
    status = request.GET.get('status', 'ACTIVE')
    severity = request.GET.get('severity')
    category = request.GET.get('category')
    
    alerts = Alert.objects.all()
    
    if status:
        alerts = alerts.filter(status=status)
    if severity:
        alerts = alerts.filter(severity=severity)
    if category:
        alerts = alerts.filter(category=category)
    
    alerts = alerts.order_by('-created_at')
    
    # Get counts by status
    status_counts = {
        'ACTIVE': Alert.objects.filter(status='ACTIVE').count(),
        'ACKNOWLEDGED': Alert.objects.filter(status='ACKNOWLEDGED').count(),
        'RESOLVED': Alert.objects.filter(status='RESOLVED').count(),
        'DISMISSED': Alert.objects.filter(status='DISMISSED').count(),
    }
    
    context = {
        'alerts': alerts,
        'selected_status': status,
        'selected_severity': severity,
        'selected_category': category,
        'status_counts': status_counts,
        'severities': Alert.SEVERITY_LEVELS,
        'categories': Alert.ALERT_CATEGORIES,
    }
    
    return render(request, 'alert_list.html', context)


@login_required
def alert_detail(request, pk):
    """Detail view for an alert"""
    alert = get_object_or_404(Alert, pk=pk)
    
    # Get related anomaly if exists
    anomaly = AnomalyDetection.objects.filter(alert=alert).first()
    
    context = {
        'alert': alert,
        'anomaly': anomaly,
    }
    
    return render(request, 'alert_detail.html', context)


@login_required
def alert_acknowledge(request, pk):
    """Acknowledge an alert"""
    alert = get_object_or_404(Alert, pk=pk)
    alert.acknowledge(request.user)
    return redirect('alert_detail', pk=pk)


@login_required
def alert_resolve(request, pk):
    """Resolve an alert"""
    alert = get_object_or_404(Alert, pk=pk)
    
    if request.method == 'POST':
        notes = request.POST.get('resolution_notes', '')
        alert.resolve(request.user, notes)
        return redirect('alert_list')
    
    return render(request, 'alert_resolve.html', {'alert': alert})


@login_required
def alert_dismiss(request, pk):
    """Dismiss an alert"""
    alert = get_object_or_404(Alert, pk=pk)
    alert.dismiss()
    return redirect('alert_list')


# ==============================================================================
#  ANOMALY DETECTION VIEWS
# ==============================================================================

@login_required
def anomaly_list(request):
    """List all detected anomalies"""
    anomaly_type = request.GET.get('type')
    
    anomalies = AnomalyDetection.objects.all()
    
    if anomaly_type:
        anomalies = anomalies.filter(anomaly_type=anomaly_type)
    
    anomalies = anomalies.order_by('-detected_at')
    
    context = {
        'anomalies': anomalies,
        'selected_type': anomaly_type,
        'anomaly_types': AnomalyDetection.ANOMALY_TYPES,
    }
    
    return render(request, 'anomaly_list.html', context)


@login_required
def anomaly_detail(request, pk):
    """Detail view for an anomaly"""
    anomaly = get_object_or_404(AnomalyDetection, pk=pk)
    
    context = {
        'anomaly': anomaly,
    }
    
    return render(request, 'anomaly_detail.html', context)


# ==============================================================================
#  TREND ANALYSIS VIEWS
# ==============================================================================

@login_required
def trend_analysis(request):
    """Trend analysis dashboard"""
    metric_name = request.GET.get('metric')
    
    trends = TrendAnalysis.objects.all()
    
    if metric_name:
        trends = trends.filter(metric_name=metric_name)
    
    trends = trends.order_by('-period_end')[:10]
    
    # Get unique metric names
    metric_names = TrendAnalysis.objects.values_list('metric_name', flat=True).distinct()
    
    context = {
        'trends': trends,
        'selected_metric': metric_name,
        'metric_names': metric_names,
    }
    
    return render(request, 'trend_analysis.html', context)


@login_required
def trend_detail(request, pk):
    """Detail view for trend analysis"""
    trend = get_object_or_404(TrendAnalysis, pk=pk)
    
    # Get historical trends for the same metric
    historical = TrendAnalysis.objects.filter(
        metric_name=trend.metric_name
    ).order_by('-period_end')[:6]
    
    context = {
        'trend': trend,
        'historical': historical,
    }
    
    return render(request, 'trend_detail.html', context)


# ==============================================================================
#  BENCHMARK COMPARISON VIEWS
# ==============================================================================

@login_required
def benchmark_comparison(request):
    """Benchmark comparison dashboard"""
    entity_type = request.GET.get('entity_type')
    metric_name = request.GET.get('metric')
    
    comparisons = BenchmarkComparison.objects.all()
    
    if entity_type:
        comparisons = comparisons.filter(entity_type=entity_type)
    if metric_name:
        comparisons = comparisons.filter(metric_name=metric_name)
    
    comparisons = comparisons.order_by('-period_end', 'rank')
    
    # Get unique entity types and metrics
    entity_types = BenchmarkComparison.objects.values_list('entity_type', flat=True).distinct()
    metric_names = BenchmarkComparison.objects.values_list('metric_name', flat=True).distinct()
    
    context = {
        'comparisons': comparisons,
        'selected_entity_type': entity_type,
        'selected_metric': metric_name,
        'entity_types': entity_types,
        'metric_names': metric_names,
    }
    
    return render(request, 'summary/benchmark_comparison.html', context)


@login_required
def benchmark_detail(request, pk):
    """Detail view for benchmark comparison"""
    comparison = get_object_or_404(BenchmarkComparison, pk=pk)
    
    # Get similar entities for comparison
    similar = BenchmarkComparison.objects.filter(
        metric_name=comparison.metric_name,
        entity_type=comparison.entity_type,
        period_end=comparison.period_end
    ).order_by('rank')[:10]
    
    context = {
        'comparison': comparison,
        'similar': similar,
    }
    
    return render(request, 'summary/benchmark_detail.html', context)


# ==============================================================================
#  API VIEWS (JSON)
# ==============================================================================

@login_required
def api_daily_summary(request):
    """API endpoint for daily summary data"""
    days = int(request.GET.get('days', 7))
    start_date = timezone.now().date() - timedelta(days=days)
    
    summaries = DailySummary.objects.filter(date__gte=start_date).order_by('date')
    
    data = [{
        'date': s.date.isoformat(),
        'total_orders': s.total_orders,
        'total_revenue': float(s.total_revenue),
        'active_farmers': s.active_farmers,
        'task_completion_rate': float(s.task_completion_rate),
    } for s in summaries]
    
    return JsonResponse({'data': data})


@login_required
def api_alerts_summary(request):
    """API endpoint for alerts summary"""
    data = {
        'critical': Alert.objects.filter(status='ACTIVE', severity='CRITICAL').count(),
        'high': Alert.objects.filter(status='ACTIVE', severity='HIGH').count(),
        'medium': Alert.objects.filter(status='ACTIVE', severity='MEDIUM').count(),
        'low': Alert.objects.filter(status='ACTIVE', severity='LOW').count(),
    }
    
    return JsonResponse(data)


# ==============================================================================
#  UTILITY FUNCTIONS
# ==============================================================================

def calculate_trend(queryset, field_name):
    """Calculate trend direction for a field"""
    if not queryset.exists() or queryset.count() < 2:
        return 'stable'
    
    values = list(queryset.values_list(field_name, flat=True))
    
    if len(values) < 2:
        return 'stable'
    
    first_half = sum(values[:len(values)//2]) / (len(values)//2)
    second_half = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
    
    if second_half > first_half * 1.1:
        return 'up'
    elif second_half < first_half * 0.9:
        return 'down'
    else:
        return 'stable'
    
# summary/views.py - Add this to your existing views

from django.http import JsonResponse
from django.db.models import Sum, F

def api_live_dashboard(request):
    """
    API endpoint for live dashboard data refresh without page reload.
    Returns JSON with current metrics.
    """
    from order.models import Order, OrderPayment
    from inventory.models import ProductSKU
    from tasks.models import FarmerTaskStatus
    from cropcycle.models import FarmerCropCycle
    from schedule.models import Farmer
    from flow.models import WhatsAppCall
    
    today = timezone.now().date()
    
    # LIVE ORDER METRICS
    today_orders = Order.objects.filter(created_at__date=today)
    
    orders_data = {
        'total': today_orders.count(),
        'pending': today_orders.filter(status__in=['PENDING', 'CONFIRMED', 'PROCESSING']).count(),
        'completed': today_orders.filter(status__in=['COMPLETED', 'DELIVERED']).count(),
        'cancelled': today_orders.filter(status='CANCELLED').count(),
    }
    
    if orders_data['total'] > 0:
        orders_data['completion_rate'] = round((orders_data['completed'] / orders_data['total']) * 100, 2)
    else:
        orders_data['completion_rate'] = 0
    
    # LIVE REVENUE METRICS
    today_revenue = today_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    payments_collected = OrderPayment.objects.filter(
        payment_date__date=today
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    pending_payments = Order.objects.all().aggregate(
        pending=Sum(F('total_amount') - F('paid_amount'))
    )['pending'] or 0
    
    avg_order = (today_revenue / orders_data['total']) if orders_data['total'] > 0 else 0
    
    revenue_data = {
        'total': float(today_revenue),
        'payments_collected': float(payments_collected),
        'pending_payments': float(pending_payments),
        'average_order_value': float(avg_order),
    }
    
    # LIVE INVENTORY METRICS
    all_skus = ProductSKU.objects.all()
    
    low_stock = sum(1 for sku in all_skus if sku.is_low_stock() and sku.stock_quantity > 0)
    out_of_stock = all_skus.filter(stock_quantity=0).count()
    total_products = all_skus.count()
    
    inventory_data = {
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'in_stock': total_products - low_stock - out_of_stock,
        'total_products': total_products,
    }
    
    # LIVE TASK METRICS
    all_tasks = FarmerTaskStatus.objects.all()
    tasks_due = all_tasks.filter(planned_end_date__lte=today)
    
    tasks_completed = tasks_due.filter(status='COMPLETED').count()
    total_due = tasks_due.count()
    
    tasks_data = {
        'completed': tasks_completed,
        'overdue': all_tasks.filter(status='OVERDUE').count(),
        'pending': all_tasks.filter(status='PENDING').count(),
        'in_progress': all_tasks.filter(status='IN_PROGRESS').count(),
        'completion_rate': round((tasks_completed / total_due * 100) if total_due > 0 else 0, 2),
    }
    
    # LIVE FARMER METRICS
    active_cycles = FarmerCropCycle.objects.filter(is_active=True)
    
    farmers_data = {
        'active': active_cycles.values('farmer').distinct().count(),
        'active_cycles': active_cycles.count(),
        'new_today': Farmer.objects.filter(created_at__date=today).count(),
        'total': Farmer.objects.count(),
    }
    
    # LIVE ALERTS
    alerts_data = {
        'critical': Alert.objects.filter(status='ACTIVE', severity='CRITICAL').count(),
        'high': Alert.objects.filter(status='ACTIVE', severity='HIGH').count(),
        'medium': Alert.objects.filter(status='ACTIVE', severity='MEDIUM').count(),
        'low': Alert.objects.filter(status='ACTIVE', severity='LOW').count(),
        'total_active': Alert.objects.filter(status='ACTIVE').count(),
    }
    
    return JsonResponse({
        'success': True,
        'timestamp': timezone.now().isoformat(),
        'orders': orders_data,
        'revenue': revenue_data,
        'inventory': inventory_data,
        'tasks': tasks_data,
        'farmers': farmers_data,
        'alerts': alerts_data,
    })
from order.models import Order
from inventory.models import ProductSKU
from tasks.models import FarmerTaskStatus

def api_quick_stats(request):
    """
    Super fast API for just the critical numbers.
    Used for frequent polling without heavy queries.
    """
    today = timezone.now().date()
    
    # Quick counts only
    orders_today = Order.objects.filter(created_at__date=today).count()
    active_alerts = Alert.objects.filter(status='ACTIVE', severity='CRITICAL').count()
    tasks_overdue = FarmerTaskStatus.objects.filter(status='OVERDUE').count()
    out_of_stock = ProductSKU.objects.filter(stock_quantity=0).count()
    
    return JsonResponse({
        'orders_today': orders_today,
        'critical_alerts': active_alerts,
        'tasks_overdue': tasks_overdue,
        'out_of_stock': out_of_stock,
        'timestamp': timezone.now().isoformat(),
    })

def force_refresh_summary(request):
    """
    Force refresh today's summary data.
    Triggers immediate recalculation from live database.
    """
    from django.core.management import call_command
    
    try:
        # Run the populate command for today only
        call_command('populate_daily_summary', '--force')
        
        return JsonResponse({
            'success': True,
            'message': 'Summary data refreshed successfully',
            'timestamp': timezone.now().isoformat(),
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=500)