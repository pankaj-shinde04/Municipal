from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages

def home(request):
    """Landing page view."""
    return render(request, 'landing.html')

def user_register(request):
    """
    Converted from React RegisterPage:
    - Fields: name (Full Name), email, password
    - Redirects to login on success as per PRD step 4
    """
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        if not name or not email or not password:
            messages.error(request, 'All fields are required.')
            return render(request, 'auth/register.html')

        if len(password) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
            return render(request, 'auth/register.html')

        # Check if user with this email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, 'A user with this email already exists.')
            return render(request, 'auth/register.html')

        # Use email as username (or fallback to username from email)
        username = email.split('@')[0]
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        first_name = name.split()[0] if name else ""
        last_name = " ".join(name.split()[1:]) if len(name.split()) > 1 else ""

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        messages.success(request, 'Account created successfully! Please sign in.')
        # Navigate to login after successful registration as per the PRD step 4
        return redirect('login')

    return render(request, 'auth/register.html')

def user_login(request):
    """
    Converted from React LoginPage:
    - Fields: email, password
    - Authenticates user by email & password
    """
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        try:
            user_obj = User.objects.get(email=email)
            username = user_obj.username
        except User.DoesNotExist:
            username = None

        user = None
        if username:
            user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'auth/login.html')

def user_logout(request):
    """User logout view."""
    logout(request)
    return redirect('home')
