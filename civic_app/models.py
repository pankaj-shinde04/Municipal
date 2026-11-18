from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Department(models.Model):
    """
    Municipal Department created and managed by Super Admin.
    Examples: Road Infrastructure, Sanitation & Waste, Water & Sewage, Street Lighting.
    """
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, null=True)
    admin_user = models.OneToOneField(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='managed_department'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        admin_name = self.admin_user.get_full_name() or self.admin_user.username if self.admin_user else "Unassigned"
        return f"{self.name} (Admin: {admin_name})"


class UserProfile(models.Model):
    """
    User Profile extending Django's built-in User authentication model.
    Stores roles, department affiliation, and worker-specific geo/operational attributes.
    """
    ROLE_CHOICES = (
        ('citizen', 'Citizen'),
        ('dept_admin', 'Department Admin'),
        ('worker', 'Worker'),
        ('super_admin', 'Super Admin'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='citizen')
    department = models.ForeignKey(
        Department, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='staff_members'
    )
    # Operative / Worker geospatial attributes
    base_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    base_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    service_radius_km = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)
    is_available = models.BooleanField(default=True)

    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"


class Issue(models.Model):
    """
    Civic Issue / Complaint record routed to departments and assigned to workers.
    """
    STATUS_CHOICES = (
        ('Submitted', 'Submitted'),
        ('Assigned', 'Assigned'),
        ('In Progress', 'In Progress'),
        ('Resolved', 'Resolved'),
        ('Closed', 'Closed'),
    )

    PRIORITY_CHOICES = (
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='issues'
    )
    citizen = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reported_issues'
    )
    assigned_worker = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks'
    )

    description = models.TextField()
    category = models.CharField(max_length=100, default='General')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Submitted')

    # Location
    location_address = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Photographic evidence
    image = models.ImageField(upload_to='issues/', blank=True, null=True)
    completion_image = models.ImageField(upload_to='completions/', blank=True, null=True)

    # Verification & Admin Audit
    admin_notes = models.TextField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    verified_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='verified_issues'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def image_url(self):
        """Safe URL accessor for initial image."""
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        return ''

    @property
    def completion_image_url(self):
        """Safe URL accessor for worker completion proof."""
        if self.completion_image and hasattr(self.completion_image, 'url'):
            return self.completion_image.url
        return ''

    @property
    def complaint_id(self):
        """Standardized unique complaint ID (e.g. C100, C102)."""
        return f"C{100 + self.id}"

    @property
    def citizen_name(self):
        """Safe accessor for citizen display name."""
        if self.citizen:
            return self.citizen.get_full_name() or self.citizen.username
        return "Citizen"

    @property
    def worker_name(self):
        """Safe accessor for assigned worker display name."""
        if self.assigned_worker:
            return self.assigned_worker.get_full_name() or self.assigned_worker.username
        return "Unassigned"

    @property
    def sla_hours_threshold(self):
        """SLA threshold based on priority: High=24h, Medium=48h, Low=72h."""
        if self.priority == 'High':
            return 24
        elif self.priority == 'Medium':
            return 48
        return 72

    @property
    def is_sla_breached(self):
        """Returns True if issue is unresolved and elapsed time exceeds SLA threshold."""
        from django.utils import timezone
        if self.status in ['Resolved', 'Closed']:
            return False
        elapsed_hours = (timezone.now() - self.created_at).total_seconds() / 3600.0
        return elapsed_hours > self.sla_hours_threshold

    @property
    def sla_status_label(self):
        """Returns readable SLA status description."""
        if self.status in ['Resolved', 'Closed']:
            hours = self.resolution_duration_hours
            if hours and hours <= self.sla_hours_threshold:
                return "Met SLA"
            return "Resolved (Overdue)"
        if self.is_sla_breached:
            return "SLA Breached"
        return "On Track"

    @property
    def resolution_duration_hours(self):
        """Hours taken to reach Resolved/Closed state, or None if pending."""
        if self.status in ['Resolved', 'Closed']:
            diff = (self.updated_at - self.created_at).total_seconds() / 3600.0
            return max(round(diff, 1), 0.1)
        return None

    def __str__(self):
        return f"{self.complaint_id} - {self.description[:30]} ({self.status})"


class Notification(models.Model):
    """
    Notifications for citizens, workers, and administrators.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:30]}"


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Signal receiver: Automatically creates/updates UserProfile.
    """
    if created:
        UserProfile.objects.create(user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()
