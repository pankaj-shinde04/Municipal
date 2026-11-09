from django.shortcuts import redirect
from django.urls import reverse

class AuthSecurityMiddleware:
    """
    Custom Middleware for authentication checks and session security:
    - Protects authenticated/guest routes (e.g. redirects already logged-in users away from /login and /register).
    - Attaches helper attributes to request for quick template/view access.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Guest-only routes: already logged-in users visiting login or register get redirected to home
        guest_only_paths = [
            reverse('login'),
            reverse('register'),
        ]

        if request.user.is_authenticated and request.path in guest_only_paths:
            return redirect('home')

        # Attach role helper to request
        if request.user.is_authenticated:
            request.user_role = getattr(getattr(request.user, 'profile', None), 'role', 'citizen')
        else:
            request.user_role = 'anonymous'

        response = self.get_response(request)
        return response

