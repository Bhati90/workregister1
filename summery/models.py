# summary/models.py

import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta
from decimal import Decimal


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True
        ordering = ['-created_at']


# ==============================================================================
#  SUMMARY METRICS MODELS
# ==============================================================================

class DailySummary(BaseModel):
    """Daily aggregated metrics across all systems"""
    
    date = models.DateField(unique=True, db_index=True)
    
    # Order Metrics
    total_orders = models.IntegerField(default=0)
    orders_pending = models.IntegerField(default=0)
    orders_completed = models.IntegerField(default=0)
    orders_cancelled = models.IntegerField(default=0)
    order_completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Revenue Metrics
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_payments_collected = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    pending_payments = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Inventory Metrics
    low_stock_items = models.IntegerField(default=0)
    out_of_stock_items = models.IntegerField(default=0)
    total_products = models.IntegerField(default=0)
    inventory_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Task Metrics
    tasks_completed = models.IntegerField(default=0)
    tasks_overdue = models.IntegerField(default=0)
    tasks_pending = models.IntegerField(default=0)
    task_completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Farmer Engagement
    active_farmers = models.IntegerField(default=0)
    active_crop_cycles = models.IntegerField(default=0)
    new_farmers = models.IntegerField(default=0)
    
    # WhatsApp Metrics
    total_messages_sent = models.IntegerField(default=0)
    total_messages_received = models.IntegerField(default=0)
    flow_completions = models.IntegerField(default=0)
    flow_dropoffs = models.IntegerField(default=0)
    call_volume = models.IntegerField(default=0)
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Daily Summary'
        verbose_name_plural = 'Daily Summaries'
        ordering = ['-date']
    
    def __str__(self):
        return f"Summary for {self.date}"


class PerformanceMetric(BaseModel):
    """Track specific performance metrics over time"""
    
    METRIC_TYPES = [
        ('ORDER_FULFILLMENT', 'Order Fulfillment Time'),
        ('PAYMENT_COLLECTION', 'Payment Collection Rate'),
        ('TASK_COMPLETION', 'Task Completion Rate'),
        ('FARMER_ENGAGEMENT', 'Farmer Engagement'),
        ('INVENTORY_TURNOVER', 'Inventory Turnover'),
        ('RESPONSE_TIME', 'Response Time'),
        ('FLOW_COMPLETION', 'Flow Completion Rate'),
    ]
    
    metric_type = models.CharField(max_length=50, choices=METRIC_TYPES)
    date = models.DateField(db_index=True)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    target_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Metadata
    entity_type = models.CharField(max_length=50, null=True, blank=True)  # e.g., 'farmer', 'product', 'area'
    entity_id = models.CharField(max_length=100, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Performance Metric'
        verbose_name_plural = 'Performance Metrics'
        ordering = ['-date', 'metric_type']
        indexes = [
            models.Index(fields=['metric_type', 'date']),
            models.Index(fields=['entity_type', 'date']),
        ]
    
    def __str__(self):
        return f"{self.get_metric_type_display()} - {self.date}: {self.value}"
    
    def is_meeting_target(self):
        """Check if metric meets target"""
        if self.target_value:
            return self.value >= self.target_value
        return None


class GrowthMetric(BaseModel):
    """Track growth rates for key metrics"""
    
    PERIOD_TYPES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
    ]
    
    metric_name = models.CharField(max_length=100)
    period_type = models.CharField(max_length=20, choices=PERIOD_TYPES)
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Growth Data
    start_value = models.DecimalField(max_digits=15, decimal_places=2)
    end_value = models.DecimalField(max_digits=15, decimal_places=2)
    growth_rate = models.DecimalField(max_digits=7, decimal_places=2)  # Percentage
    growth_absolute = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Comparison
    previous_period_growth = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    is_positive_growth = models.BooleanField(default=True)
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Growth Metric'
        verbose_name_plural = 'Growth Metrics'
        ordering = ['-period_end']
    
    def __str__(self):
        return f"{self.metric_name} ({self.period_type}): {self.growth_rate}%"


class GeographicPerformance(BaseModel):
    """Track performance metrics by geographic location"""
    
    district = models.CharField(max_length=100)
    taluka = models.CharField(max_length=100, null=True, blank=True)
    village = models.CharField(max_length=100, null=True, blank=True)
    
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Metrics
    total_farmers = models.IntegerField(default=0)
    total_orders = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Engagement
    active_farmers_count = models.IntegerField(default=0)
    task_completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Issues
    cancelled_orders = models.IntegerField(default=0)
    overdue_tasks = models.IntegerField(default=0)
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Geographic Performance'
        verbose_name_plural = 'Geographic Performance'
        ordering = ['-period_end', 'district']
        indexes = [
            models.Index(fields=['district', 'period_end']),
        ]
    
    def __str__(self):
        return f"{self.district} - {self.period_start} to {self.period_end}"


# ==============================================================================
#  ALERT MODELS
# ==============================================================================
# summary/models.py
# Only showing the Alert model - replace your existing Alert model with this

class Alert(BaseModel):
    """System alerts for issues requiring attention"""
    
    SEVERITY_LEVELS = [
        ('CRITICAL', 'Critical'),
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
        ('INFO', 'Info'),
    ]
    
    ALERT_CATEGORIES = [
        ('INVENTORY', 'Inventory'),
        ('ORDERS', 'Orders'),
        ('TASKS', 'Tasks'),
        ('FINANCIAL', 'Financial'),
        ('ENGAGEMENT', 'Engagement'),
        ('PERFORMANCE', 'Performance'),
        ('SYSTEM', 'System'),
        ('ANOMALY', 'Anomaly'),
    ]
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('ACKNOWLEDGED', 'Acknowledged'),
        ('RESOLVED', 'Resolved'),
        ('DISMISSED', 'Dismissed'),
    ]
    
    # Alert Details
    title = models.CharField(max_length=255)
    description = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, db_index=True)
    category = models.CharField(max_length=50, choices=ALERT_CATEGORIES, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE', db_index=True)
    
    # Context
    entity_type = models.CharField(max_length=50, null=True, blank=True)
    entity_id = models.CharField(max_length=100, null=True, blank=True)
    entity_name = models.CharField(max_length=255, null=True, blank=True)
    
    # Geographic
    location = models.CharField(max_length=255, null=True, blank=True)
    
    # Metric Data
    current_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    threshold_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    previous_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Resolution - FIXED: Changed related_name to avoid conflicts
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='summary_resolved_alerts'  # CHANGED
    )
    resolution_notes = models.TextField(blank=True, null=True)
    
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='summary_acknowledged_alerts'  # CHANGED
    )
    
    # Auto-resolution
    auto_resolve = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Alert'
        verbose_name_plural = 'Alerts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['severity', 'status']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['entity_type', 'entity_id']),
        ]
    
    def __str__(self):
        return f"[{self.severity}] {self.title}"
    
    def acknowledge(self, user):
        """Mark alert as acknowledged"""
        self.status = 'ACKNOWLEDGED'
        self.acknowledged_at = timezone.now()
        self.acknowledged_by = user
        self.save()
    
    def resolve(self, user, notes=None):
        """Mark alert as resolved"""
        self.status = 'RESOLVED'
        self.resolved_at = timezone.now()
        self.resolved_by = user
        if notes:
            self.resolution_notes = notes
        self.save()
    
    def dismiss(self):
        """Dismiss alert"""
        self.status = 'DISMISSED'
        self.save()
        
class AlertRule(BaseModel):
    """Define rules for generating alerts automatically"""
    
    name = models.CharField(max_length=255)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    
    # Rule Configuration
    category = models.CharField(max_length=50, choices=Alert.ALERT_CATEGORIES)
    severity = models.CharField(max_length=20, choices=Alert.SEVERITY_LEVELS)
    
    # Condition
    metric_type = models.CharField(max_length=100)
    condition_operator = models.CharField(
        max_length=20,
        choices=[
            ('GT', 'Greater Than'),
            ('LT', 'Less Than'),
            ('EQ', 'Equal To'),
            ('GTE', 'Greater Than or Equal'),
            ('LTE', 'Less Than or Equal'),
            ('CHANGE_GT', 'Change Greater Than'),
            ('CHANGE_LT', 'Change Less Than'),
        ]
    )
    threshold_value = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Check Frequency
    check_interval_hours = models.IntegerField(default=24)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    
    # Alert Template
    title_template = models.CharField(max_length=255)
    description_template = models.TextField()
    
    # Auto-resolution
    auto_resolve_after_hours = models.IntegerField(null=True, blank=True)
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Alert Rule'
        verbose_name_plural = 'Alert Rules'
    
    def __str__(self):
        return self.name


class AnomalyDetection(BaseModel):
    """Detect unusual patterns or anomalies in data"""
    
    ANOMALY_TYPES = [
        ('SUDDEN_SPIKE', 'Sudden Spike'),
        ('SUDDEN_DROP', 'Sudden Drop'),
        ('UNUSUAL_PATTERN', 'Unusual Pattern'),
        ('TREND_BREAK', 'Trend Break'),
        ('OUTLIER', 'Outlier'),
    ]
    
    anomaly_type = models.CharField(max_length=50, choices=ANOMALY_TYPES)
    metric_name = models.CharField(max_length=100)
    detected_at = models.DateTimeField(auto_now_add=True)
    
    # Anomaly Data
    expected_value = models.DecimalField(max_digits=15, decimal_places=2)
    actual_value = models.DecimalField(max_digits=15, decimal_places=2)
    deviation_percentage = models.DecimalField(max_digits=7, decimal_places=2)
    
    # Context
    entity_type = models.CharField(max_length=50, null=True, blank=True)
    entity_id = models.CharField(max_length=100, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    
    # Analysis
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2)  # 0-100
    possible_causes = models.TextField(blank=True, null=True)
    
    # Alert Generated
    alert = models.ForeignKey(Alert, on_delete=models.SET_NULL, null=True, blank=True, related_name='anomaly')
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Anomaly Detection'
        verbose_name_plural = 'Anomaly Detections'
        ordering = ['-detected_at']
    
    def __str__(self):
        return f"{self.get_anomaly_type_display()} in {self.metric_name}"


class TrendAnalysis(BaseModel):
    """Analyze trends in key metrics"""
    
    TREND_DIRECTIONS = [
        ('UP', 'Upward'),
        ('DOWN', 'Downward'),
        ('STABLE', 'Stable'),
        ('VOLATILE', 'Volatile'),
    ]
    
    metric_name = models.CharField(max_length=100)
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Trend Data
    trend_direction = models.CharField(max_length=20, choices=TREND_DIRECTIONS)
    trend_strength = models.DecimalField(max_digits=5, decimal_places=2)  # 0-100
    average_value = models.DecimalField(max_digits=15, decimal_places=2)
    volatility = models.DecimalField(max_digits=7, decimal_places=2)
    
    # Forecast
    forecasted_next_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    forecast_confidence = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Insights
    insights = models.TextField(blank=True, null=True)
    recommendations = models.TextField(blank=True, null=True)
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Trend Analysis'
        verbose_name_plural = 'Trend Analyses'
        ordering = ['-period_end']
    
    def __str__(self):
        return f"{self.metric_name} - {self.get_trend_direction_display()} ({self.period_start} to {self.period_end})"


# ==============================================================================
#  COMPARISON & BENCHMARKING
# ==============================================================================

class BenchmarkComparison(BaseModel):
    """Compare performance against benchmarks"""
    
    metric_name = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=50)  # 'farmer', 'area', 'product', etc.
    entity_id = models.CharField(max_length=100)
    entity_name = models.CharField(max_length=255)
    
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Performance
    actual_value = models.DecimalField(max_digits=15, decimal_places=2)
    benchmark_value = models.DecimalField(max_digits=15, decimal_places=2)
    difference = models.DecimalField(max_digits=15, decimal_places=2)
    difference_percentage = models.DecimalField(max_digits=7, decimal_places=2)
    
    # Ranking
    rank = models.IntegerField(null=True, blank=True)
    total_entities = models.IntegerField(null=True, blank=True)
    percentile = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Status
    is_above_benchmark = models.BooleanField(default=False)
    performance_tier = models.CharField(
        max_length=20,
        choices=[
            ('TOP', 'Top Performer'),
            ('ABOVE_AVG', 'Above Average'),
            ('AVERAGE', 'Average'),
            ('BELOW_AVG', 'Below Average'),
            ('POOR', 'Needs Improvement'),
        ],
        null=True,
        blank=True
    )
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Benchmark Comparison'
        verbose_name_plural = 'Benchmark Comparisons'
        ordering = ['-period_end', 'metric_name']
    
    def __str__(self):
        return f"{self.entity_name} - {self.metric_name}: {self.actual_value} vs {self.benchmark_value}"