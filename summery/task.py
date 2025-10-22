# summary/tasks.py
# Celery tasks for automated summary generation

from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(name='generate_daily_summary')
def generate_daily_summary():
    """
    Generate daily summary for today.
    Run this task daily at midnight.
    """
    try:
        logger.info("Starting daily summary generation")
        call_command('populate_daily_summary')
        logger.info("Daily summary generation completed")
        return "Success"
    except Exception as e:
        logger.error(f"Error generating daily summary: {str(e)}")
        return f"Error: {str(e)}"


@shared_task(name='generate_weekly_analytics')
def generate_weekly_analytics():
    """
    Generate weekly analytics including geographic performance and growth metrics.
    Run this task weekly on Monday.
    """
    try:
        logger.info("Starting weekly analytics generation")
        call_command('populate_analytics', '--type=all', '--period=week')
        logger.info("Weekly analytics generation completed")
        return "Success"
    except Exception as e:
        logger.error(f"Error generating weekly analytics: {str(e)}")
        return f"Error: {str(e)}"


@shared_task(name='generate_monthly_analytics')
def generate_monthly_analytics():
    """
    Generate monthly analytics.
    Run this task on the 1st of each month.
    """
    try:
        logger.info("Starting monthly analytics generation")
        call_command('populate_analytics', '--type=all', '--period=month')
        logger.info("Monthly analytics generation completed")
        return "Success"
    except Exception as e:
        logger.error(f"Error generating monthly analytics: {str(e)}")
        return f"Error: {str(e)}"


@shared_task(name='detect_anomalies_task')
def detect_anomalies_task():
    """
    Run anomaly detection.
    Run this task every 6 hours.
    """
    try:
        logger.info("Starting anomaly detection")
        call_command('populate_analytics', '--type=anomalies')
        logger.info("Anomaly detection completed")
        return "Success"
    except Exception as e:
        logger.error(f"Error in anomaly detection: {str(e)}")
        return f"Error: {str(e)}"


@shared_task(name='cleanup_old_alerts')
def cleanup_old_alerts():
    """
    Auto-resolve old alerts and cleanup.
    Run this task daily.
    """
    try:
        from summary.models import Alert
        
        # Auto-resolve alerts older than 7 days that are still active
        seven_days_ago = timezone.now() - timedelta(days=7)
        old_alerts = Alert.objects.filter(
            status='ACTIVE',
            created_at__lt=seven_days_ago,
            auto_resolve=True
        )
        
        count = old_alerts.count()
        old_alerts.update(
            status='RESOLVED',
            resolved_at=timezone.now(),
            resolution_notes='Auto-resolved after 7 days'
        )
        
        logger.info(f"Auto-resolved {count} old alerts")
        return f"Resolved {count} alerts"
    except Exception as e:
        logger.error(f"Error cleaning up alerts: {str(e)}")
        return f"Error: {str(e)}"


@shared_task(name='backfill_summaries')
def backfill_summaries(days_back=30):
    """
    Backfill summary data for historical dates.
    Use this for initial setup or data recovery.
    """
    try:
        logger.info(f"Starting backfill for last {days_back} days")
        call_command('populate_daily_summary', f'--days-back={days_back}', '--force')
        logger.info("Backfill completed")
        return "Success"
    except Exception as e:
        logger.error(f"Error during backfill: {str(e)}")
        return f"Error: {str(e)}"


# Celery Beat Schedule Configuration
# Add this to your celery.py or settings.py

"""
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'generate-daily-summary': {
        'task': 'generate_daily_summary',
        'schedule': crontab(hour=0, minute=5),  # Run at 00:05 every day
    },
    'generate-weekly-analytics': {
        'task': 'generate_weekly_analytics',
        'schedule': crontab(day_of_week=1, hour=1, minute=0),  # Monday at 1 AM
    },
    'generate-monthly-analytics': {
        'task': 'generate_monthly_analytics',
        'schedule': crontab(day_of_month=1, hour=2, minute=0),  # 1st of month at 2 AM
    },
    'detect-anomalies': {
        'task': 'detect_anomalies_task',
        'schedule': crontab(hour='*/6'),  # Every 6 hours
    },
    'cleanup-old-alerts': {
        'task': 'cleanup_old_alerts',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM
    },
}
"""