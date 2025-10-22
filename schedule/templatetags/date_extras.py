from django import template
from datetime import timedelta

register = template.Library()

@register.filter
def add_days(value, days):
    """Add a number of days to a date."""
    if not value:
        return value
    try:
        return value + timedelta(days=int(days))
    except Exception:
        return value
