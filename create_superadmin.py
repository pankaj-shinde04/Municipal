import os
import django

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartcivic.settings')
django.setup()

from django.contrib.auth.models import User
from civic_app.models import UserProfile

def create_superadmin():
    username = os.environ.get('SUPERADMIN_USERNAME', 'admin')
    email = os.environ.get('SUPERADMIN_EMAIL', 'admin@smartcivic.com')
    password = os.environ.get('SUPERADMIN_PASSWORD', 'admin123')
    first_name = os.environ.get('SUPERADMIN_FIRST_NAME', 'Super')
    last_name = os.environ.get('SUPERADMIN_LAST_NAME', 'Admin')

    if User.objects.filter(username=username).exists():
        print(f"User '{username}' already exists. Updating to superuser...")
        user = User.objects.get(username=username)
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()
    elif User.objects.filter(email=email).exists():
        print(f"User with email '{email}' already exists. Updating to superuser...")
        user = User.objects.get(email=email)
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()
    else:
        print(f"Creating new Superadmin: {username} ({email})...")
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

    # Ensure role in UserProfile is 'super_admin'
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.role = 'super_admin'
    profile.save()

    print("==========================================")
    print(" Superadmin created / updated successfully!")
    print(f" Username : {user.username}")
    print(f" Email    : {user.email}")
    print(f" Password : {password}")
    print(f" Role     : {profile.role}")
    print("==========================================")

if __name__ == '__main__':
    create_superadmin()

