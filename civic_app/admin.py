from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, Department

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'

class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'get_department', 'is_active')

    def get_role(self, instance):
        return instance.profile.get_role_display() if hasattr(instance, 'profile') else 'N/A'
    get_role.short_description = 'Role'

    def get_department(self, instance):
        return instance.profile.department.name if hasattr(instance, 'profile') and instance.profile.department else '-'
    get_department.short_description = 'Department'

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'admin_user', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
