# summary/management/commands/populate_analytics.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q, F
from datetime import datetime, timedelta
from decimal import Decimal

from summery.models import (
    GeographicPerformance, GrowthMetric, TrendAnalysis,
    BenchmarkComparison, AnomalyDetection, DailySummary
)
from order.models import Order
from tasks.models import FarmerTaskStatus
from cropcycle.models import FarmerCropCycle
from schedule.models import Farmer


class Command(BaseCommand):
    help = 'Populate geographic performance, growth metrics, and analytics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['geographic', 'growth', 'trends', 'benchmarks', 'anomalies', 'all'],
            default='all',
            help='Type of analytics to populate',
        )
        parser.add_argument(
            '--period',
            type=str,
            default='month',
            help='Period for analysis (week, month, quarter)',
        )

    def handle(self, *args, **options):
        analytics_type = options['type']
        period = options['period']

        if analytics_type in ['geographic', 'all']:
            self.populate_geographic_performance(period)

        if analytics_type in ['growth', 'all']:
            self.populate_growth_metrics(period)

        if analytics_type in ['trends', 'all']:
            self.populate_trend_analysis(period)

        if analytics_type in ['benchmarks', 'all']:
            self.populate_benchmarks(period)

        if analytics_type in ['anomalies', 'all']:
            self.detect_anomalies()

        self.stdout.write(self.style.SUCCESS('Successfully populated analytics'))

    def populate_geographic_performance(self, period='month'):
        """Populate geographic performance metrics"""
        self.stdout.write('Populating geographic performance...')

        end_date = timezone.now().date()
        
        if period == 'week':
            start_date = end_date - timedelta(days=7)
        elif period == 'quarter':
            start_date = end_date - timedelta(days=90)
        else:  # month
            start_date = end_date - timedelta(days=30)

        # Get all farmers with their locations
        farmers = Farmer.objects.all()

        # Group by district (you may need to add district field to Farmer model)
        # For now, we'll create a simple aggregation
        
        # Get unique locations from orders (if you have address data)
        # or from farmer profiles
        
        # Example: Aggregate by district
        districts = set()
        
        # You might need to extract district from farmer profiles
        # For this example, we'll assume you have district data
        
        # Create performance records for each district
        for district in ['District A', 'District B', 'District C']:  # Replace with actual districts
            farmers_in_district = farmers.filter(
                # Add your district filter here
                # example: order_profile__district=district
            )

            if not farmers_in_district.exists():
                continue

            # Calculate metrics
            orders = Order.objects.filter(
                farmer__in=farmers_in_district,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date
            )

            tasks = FarmerTaskStatus.objects.filter(
                farmer_crop_cycle__farmer__in=farmers_in_district,
                planned_end_date__gte=start_date,
                planned_end_date__lte=end_date
            )

            revenue = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
            order_count = orders.count()
            avg_order = revenue / order_count if order_count > 0 else Decimal('0.00')

            completed_tasks = tasks.filter(status='COMPLETED').count()
            total_tasks = tasks.count()
            task_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else Decimal('0.00')

            GeographicPerformance.objects.update_or_create(
                district=district,
                period_start=start_date,
                period_end=end_date,
                defaults={
                    'total_farmers': farmers_in_district.count(),
                    'total_orders': order_count,
                    'total_revenue': revenue,
                    'average_order_value': avg_order.quantize(Decimal('0.01')),
                    'active_farmers_count': farmers_in_district.filter(
                        crop_cycles__is_active=True
                    ).distinct().count(),
                    'task_completion_rate': Decimal(str(task_rate)).quantize(Decimal('0.01')),
                    'cancelled_orders': orders.filter(status='CANCELLED').count(),
                    'overdue_tasks': tasks.filter(status='OVERDUE').count(),
                }
            )

        self.stdout.write(self.style.SUCCESS('✓ Geographic performance populated'))

    def populate_growth_metrics(self, period='month'):
        """Calculate growth metrics"""
        self.stdout.write('Calculating growth metrics...')

        end_date = timezone.now().date()

        metrics_to_track = [
            'total_revenue',
            'total_orders',
            'active_farmers',
            'active_crop_cycles',
        ]

        for metric_name in metrics_to_track:
            if period == 'week':
                period_type = 'WEEKLY'
                start_date = end_date - timedelta(days=7)
                prev_start = start_date - timedelta(days=7)
                prev_end = start_date - timedelta(days=1)
            elif period == 'quarter':
                period_type = 'QUARTERLY'
                start_date = end_date - timedelta(days=90)
                prev_start = start_date - timedelta(days=90)
                prev_end = start_date - timedelta(days=1)
            else:  # month
                period_type = 'MONTHLY'
                start_date = end_date - timedelta(days=30)
                prev_start = start_date - timedelta(days=30)
                prev_end = start_date - timedelta(days=1)

            # Get current period value
            current_summaries = DailySummary.objects.filter(
                date__gte=start_date,
                date__lte=end_date
            )

            if not current_summaries.exists():
                continue

            # Calculate start and end values
            start_value = getattr(current_summaries.order_by('date').first(), metric_name, 0)
            end_value = getattr(current_summaries.order_by('-date').first(), metric_name, 0)

            # Calculate growth
            growth_absolute = Decimal(str(end_value)) - Decimal(str(start_value))
            
            if Decimal(str(start_value)) > 0:
                growth_rate = (growth_absolute / Decimal(str(start_value))) * 100
            else:
                growth_rate = Decimal('0.00')

            # Get previous period growth for comparison
            prev_summaries = DailySummary.objects.filter(
                date__gte=prev_start,
                date__lte=prev_end
            )

            prev_growth = None
            if prev_summaries.exists():
                prev_start_val = getattr(prev_summaries.order_by('date').first(), metric_name, 0)
                prev_end_val = getattr(prev_summaries.order_by('-date').first(), metric_name, 0)
                prev_abs = Decimal(str(prev_end_val)) - Decimal(str(prev_start_val))
                
                if Decimal(str(prev_start_val)) > 0:
                    prev_growth = (prev_abs / Decimal(str(prev_start_val))) * 100

            GrowthMetric.objects.update_or_create(
                metric_name=metric_name,
                period_type=period_type,
                period_start=start_date,
                period_end=end_date,
                defaults={
                    'start_value': Decimal(str(start_value)).quantize(Decimal('0.01')),
                    'end_value': Decimal(str(end_value)).quantize(Decimal('0.01')),
                    'growth_rate': growth_rate.quantize(Decimal('0.01')),
                    'growth_absolute': growth_absolute.quantize(Decimal('0.01')),
                    'previous_period_growth': prev_growth.quantize(Decimal('0.01')) if prev_growth else None,
                    'is_positive_growth': growth_rate > 0,
                }
            )

        self.stdout.write(self.style.SUCCESS('✓ Growth metrics calculated'))

    def populate_trend_analysis(self, period='month'):
        """Analyze trends in metrics"""
        self.stdout.write('Analyzing trends...')

        end_date = timezone.now().date()
        
        if period == 'week':
            start_date = end_date - timedelta(days=7)
        elif period == 'quarter':
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=30)

        metrics_to_analyze = [
            'total_revenue',
            'total_orders',
            'order_completion_rate',
            'task_completion_rate',
        ]

        summaries = DailySummary.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date')

        for metric_name in metrics_to_analyze:
            values = [float(getattr(s, metric_name, 0)) for s in summaries]
            
            if len(values) < 2:
                continue

            # Calculate trend direction
            avg_value = sum(values) / len(values)
            first_half = sum(values[:len(values)//2]) / (len(values)//2)
            second_half = sum(values[len(values)//2:]) / (len(values) - len(values)//2)

            if second_half > first_half * 1.1:
                trend_direction = 'UP'
                trend_strength = ((second_half - first_half) / first_half * 100)
            elif second_half < first_half * 0.9:
                trend_direction = 'DOWN'
                trend_strength = ((first_half - second_half) / first_half * 100)
            else:
                trend_direction = 'STABLE'
                trend_strength = Decimal('0.00')

            # Calculate volatility (standard deviation)
            variance = sum((x - avg_value) ** 2 for x in values) / len(values)
            volatility = variance ** 0.5

            # Simple forecast (linear projection)
            if len(values) >= 2:
                # Calculate slope
                x_values = list(range(len(values)))
                x_mean = sum(x_values) / len(x_values)
                y_mean = avg_value
                
                numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values))
                denominator = sum((x - x_mean) ** 2 for x in x_values)
                
                if denominator != 0:
                    slope = numerator / denominator
                    intercept = y_mean - slope * x_mean
                    forecasted = slope * len(values) + intercept
                else:
                    forecasted = avg_value
            else:
                forecasted = avg_value

            TrendAnalysis.objects.update_or_create(
                metric_name=metric_name,
                period_start=start_date,
                period_end=end_date,
                defaults={
                    'trend_direction': trend_direction,
                    'trend_strength': Decimal(str(trend_strength)).quantize(Decimal('0.01')),
                    'average_value': Decimal(str(avg_value)).quantize(Decimal('0.01')),
                    'volatility': Decimal(str(volatility)).quantize(Decimal('0.01')),
                    'forecasted_next_value': Decimal(str(forecasted)).quantize(Decimal('0.01')),
                    'forecast_confidence': Decimal('75.00'),  # Simple confidence score
                }
            )

        self.stdout.write(self.style.SUCCESS('✓ Trend analysis completed'))

    def populate_benchmarks(self, period='month'):
        """Create benchmark comparisons for farmers"""
        self.stdout.write('Creating benchmark comparisons...')

        end_date = timezone.now().date()
        
        if period == 'week':
            start_date = end_date - timedelta(days=7)
        else:
            start_date = end_date - timedelta(days=30)

        # Revenue benchmark by farmer
        farmers = Farmer.objects.all()
        
        # Calculate average revenue across all farmers
        all_farmer_revenues = []
        
        for farmer in farmers:
            farmer_orders = Order.objects.filter(
                farmer=farmer,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date
            )
            
            revenue = farmer_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
            all_farmer_revenues.append(float(revenue))

        if not all_farmer_revenues:
            return

        benchmark_value = sum(all_farmer_revenues) / len(all_farmer_revenues)
        sorted_revenues = sorted(all_farmer_revenues, reverse=True)

        for farmer in farmers:
            farmer_orders = Order.objects.filter(
                farmer=farmer,
                created_at__date__gte=start_date,
                created_at__date__lte=end_date
            )
            
            actual_value = farmer_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
            actual_float = float(actual_value)
            
            difference = Decimal(str(actual_float - benchmark_value))
            diff_percentage = (difference / Decimal(str(benchmark_value)) * 100) if benchmark_value > 0 else Decimal('0.00')
            
            # Calculate rank
            rank = sorted_revenues.index(actual_float) + 1 if actual_float in sorted_revenues else len(farmers)
            percentile = ((len(farmers) - rank) / len(farmers) * 100)
            
            # Determine performance tier
            if percentile >= 80:
                tier = 'TOP'
            elif percentile >= 60:
                tier = 'ABOVE_AVG'
            elif percentile >= 40:
                tier = 'AVERAGE'
            elif percentile >= 20:
                tier = 'BELOW_AVG'
            else:
                tier = 'POOR'

            BenchmarkComparison.objects.update_or_create(
                metric_name='revenue',
                entity_type='farmer',
                entity_id=str(farmer.id),
                entity_name=farmer.name,
                period_start=start_date,
                period_end=end_date,
                defaults={
                    'actual_value': actual_value,
                    'benchmark_value': Decimal(str(benchmark_value)).quantize(Decimal('0.01')),
                    'difference': difference.quantize(Decimal('0.01')),
                    'difference_percentage': diff_percentage.quantize(Decimal('0.01')),
                    'rank': rank,
                    'total_entities': len(farmers),
                    'percentile': Decimal(str(percentile)).quantize(Decimal('0.01')),
                    'is_above_benchmark': actual_float > benchmark_value,
                    'performance_tier': tier,
                }
            )

        self.stdout.write(self.style.SUCCESS('✓ Benchmark comparisons created'))

    def detect_anomalies(self):
        """Detect anomalies in recent data"""
        self.stdout.write('Detecting anomalies...')

        today = timezone.now().date()
        
        # Get last 30 days for baseline
        last_30_days = DailySummary.objects.filter(
            date__gte=today - timedelta(days=30),
            date__lt=today
        ).order_by('date')

        if last_30_days.count() < 7:
            self.stdout.write(self.style.WARNING('Not enough historical data for anomaly detection'))
            return

        # Get today's summary
        today_summary = DailySummary.objects.filter(date=today).first()
        
        if not today_summary:
            return

        metrics_to_check = [
            'total_orders',
            'total_revenue',
            'order_completion_rate',
            'tasks_overdue',
            'low_stock_items',
        ]

        for metric_name in metrics_to_check:
            # Calculate expected value (mean of last 30 days)
            values = [float(getattr(s, metric_name, 0)) for s in last_30_days]
            expected_value = sum(values) / len(values)
            
            # Calculate standard deviation
            variance = sum((x - expected_value) ** 2 for x in values) / len(values)
            std_dev = variance ** 0.5
            
            # Get actual value
            actual_value = float(getattr(today_summary, metric_name, 0))
            
            # Detect anomaly (2 standard deviations)
            threshold = 2 * std_dev
            deviation = actual_value - expected_value
            deviation_pct = (abs(deviation) / expected_value * 100) if expected_value > 0 else 0
            
            anomaly_type = None
            confidence = 0
            
            if deviation > threshold:
                anomaly_type = 'SUDDEN_SPIKE'
                confidence = min(95, 50 + (abs(deviation) / threshold * 20))
            elif deviation < -threshold:
                anomaly_type = 'SUDDEN_DROP'
                confidence = min(95, 50 + (abs(deviation) / threshold * 20))
            
            if anomaly_type and confidence > 70:
                # Determine possible causes
                possible_causes = self.analyze_anomaly_causes(
                    metric_name, 
                    anomaly_type, 
                    today_summary
                )
                
                anomaly = AnomalyDetection.objects.create(
                    anomaly_type=anomaly_type,
                    metric_name=metric_name,
                    expected_value=Decimal(str(expected_value)).quantize(Decimal('0.01')),
                    actual_value=Decimal(str(actual_value)).quantize(Decimal('0.01')),
                    deviation_percentage=Decimal(str(deviation_pct)).quantize(Decimal('0.01')),
                    confidence_score=Decimal(str(confidence)).quantize(Decimal('0.01')),
                    possible_causes=possible_causes,
                )
                
                # Create alert for significant anomalies
                if confidence > 80:
                    from summary.models import Alert
                    
                    severity = 'HIGH' if confidence > 90 else 'MEDIUM'
                    
                    alert = Alert.objects.create(
                        title=f"Anomaly Detected: {metric_name}",
                        description=f"Detected {anomaly_type.replace('_', ' ').lower()} in {metric_name}. "
                                  f"Expected: {expected_value:.2f}, Actual: {actual_value:.2f}",
                        severity=severity,
                        category='ANOMALY',
                        status='ACTIVE',
                        current_value=Decimal(str(actual_value)).quantize(Decimal('0.01')),
                        threshold_value=Decimal(str(expected_value)).quantize(Decimal('0.01')),
                    )
                    
                    anomaly.alert = alert
                    anomaly.save()

        self.stdout.write(self.style.SUCCESS('✓ Anomaly detection completed'))

    def analyze_anomaly_causes(self, metric_name, anomaly_type, summary):
        """Analyze possible causes for an anomaly"""
        causes = []
        
        if metric_name == 'total_orders':
            if anomaly_type == 'SUDDEN_DROP':
                if summary.out_of_stock_items > 5:
                    causes.append("Multiple products out of stock")
                if summary.active_farmers < 10:
                    causes.append("Low farmer engagement")
            elif anomaly_type == 'SUDDEN_SPIKE':
                causes.append("Possible seasonal demand or promotion")
                
        elif metric_name == 'total_revenue':
            if anomaly_type == 'SUDDEN_DROP':
                if summary.orders_cancelled > summary.orders_completed:
                    causes.append("High cancellation rate")
                if summary.average_order_value < 1000:
                    causes.append("Lower average order values")
                    
        elif metric_name == 'tasks_overdue':
            if anomaly_type == 'SUDDEN_SPIKE':
                causes.append("Possible resource shortage or weather delays")
                causes.append("Check farmer engagement and support needs")
                
        elif metric_name == 'low_stock_items':
            if anomaly_type == 'SUDDEN_SPIKE':
                causes.append("Inventory replenishment may be delayed")
                causes.append("Check with suppliers")
        
        if not causes:
            causes.append("Investigate further to determine root cause")
        
        return "\n".join(f"• {cause}" for cause in causes)