from django import template

register = template.Library()

@register.filter
def count_by_status(tasks, status):
    return sum(1 for task in tasks if task.status == status)