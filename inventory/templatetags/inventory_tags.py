
# inventory/templatetags/inventory_tags.py
from django import template

register = template.Library()

@register.filter
def get_translated_name(obj, lang):
    """Get translated name based on language"""
    if lang == 'mr':
        return getattr(obj, 'name_mr', obj.name) or obj.name
    return obj.name

@register.filter
def get_translated_description(obj, lang):
    """Get translated description based on language"""
    if lang == 'mr':
        return getattr(obj, 'description_mr', obj.description) or obj.description
    return obj.description