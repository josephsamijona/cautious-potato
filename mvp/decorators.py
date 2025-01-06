from django.http import JsonResponse
from django.shortcuts import redirect
from functools import wraps

def translator_required(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        # Check if user has a profile and is a translator
        if hasattr(request.user, 'profile') and request.user.profile.role == 'TRANSLATOR':
            return function(request, *args, **kwargs)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Translator privileges required.'
                }, status=403)
            return redirect('home')
    return wrap