# registration/decorators.py
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

def mukadam_required(function):
    def check(user):
        if user.is_authenticated and user.groups.filter(name='Mukadams').exists():
            return True
        raise PermissionDenied
    return user_passes_test(check)(function)