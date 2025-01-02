# decorators.py

from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def client_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'CLIENT':
            messages.error(request, 'Access denied. Client privileges required.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# decorators.py

def translator_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'TRANSLATOR':
            messages.error(request, 'Access denied. Translator privileges required.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# decorators.py

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'ADMIN':
            messages.error(request, 'Access denied. Administrator privileges required.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view