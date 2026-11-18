import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count
from django.utils import timezone
from .models import Department, UserProfile, Issue, Notification

def get_issue_area_name(issue):
    """Returns readable location/area description for notifications."""
    if issue.location_address and issue.location_address.strip():
        addr = issue.location_address.strip()
        return addr[:65]
    elif issue.latitude and issue.longitude:
        return f"Lat: {float(issue.latitude):.4f}, Lng: {float(issue.longitude):.4f}"
    return "Local Zone"

def send_notification(user, message, issue=None):
    """Safely dispatches a single notification record."""
    if not user:
        return None
    return Notification.objects.create(user=user, issue=issue, message=message)

def notify_super_admins(message, issue=None):
    """Dispatches notifications to all Super Administrators."""
    super_admins = User.objects.filter(Q(is_superuser=True) | Q(profile__role='super_admin')).distinct()
    for sa in super_admins:
        send_notification(sa, message, issue=issue)

def notify_dept_admins(department, message, issue=None):
    """Dispatches notifications to all relevant Department Administrators."""
    if not department:
        return
    admins = set()
    if department.admin_user:
        admins.add(department.admin_user)
    dept_admins = User.objects.filter(profile__department=department, profile__role='dept_admin')
    for da in dept_admins:
        admins.add(da)
    for a in admins:
        send_notification(a, message, issue=issue)

def user_dashboard_redirect(request):
    """
    Role-based dynamic redirector:
    Directs any logged-in user to their respective dashboard:
    - super_admin / superuser -> super_admin_dashboard
    - dept_admin -> dept_admin_dashboard
    - worker -> worker_dashboard
    - citizen -> citizen_dashboard
    """
    if not request.user.is_authenticated:
        return redirect('login')

    role = getattr(getattr(request.user, 'profile', None), 'role', '')
    if request.user.is_superuser or role == 'super_admin':
        return redirect('super_admin_dashboard')
    elif role == 'dept_admin':
        return redirect('dept_admin_dashboard')
    elif role == 'worker':
        return redirect('worker_dashboard')
    return redirect('citizen_dashboard')

def home(request):
    """Landing page view."""
    return render(request, 'landing.html')

def user_register(request):
    """
    User registration view:
    - Fields: name (Full Name), email, password
    - Redirects to login on success
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

        if User.objects.filter(email=email).exists():
            messages.error(request, 'A user with this email already exists.')
            return render(request, 'auth/register.html')

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
        return redirect('login')

    return render(request, 'auth/register.html')

def user_login(request):
    """
    User login view:
    - Fields: email, password
    - Directs superadmin directly to Global Command dashboard
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
            role = getattr(getattr(user, 'profile', None), 'role', '')
            if user.is_superuser or role == 'super_admin':
                return redirect('super_admin_dashboard')
            elif role == 'dept_admin':
                return redirect('dept_admin_dashboard')
            elif role == 'worker':
                return redirect('worker_dashboard')
            elif role == 'citizen':
                return redirect('citizen_dashboard')
            return redirect('home')
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'auth/login.html')

def user_logout(request):
    """User logout view."""
    logout(request)
    return redirect('home')

def super_admin_dashboard(request):
    """
    Super Admin Unified Dashboard:
    - Tab 1: System Health & Heatmap
    - Tab 2: Infrastructure Depts (Create, Edit, Terminate)
    - Tab 3: Department Admins (Deploy, Update credentials, Revoke)
    - Tab 4: Global Logs
    """
    if not request.user.is_authenticated:
        return redirect('login')

    role = getattr(getattr(request.user, 'profile', None), 'role', '')
    if not (request.user.is_superuser or role == 'super_admin'):
        return redirect('home')

    active_tab = request.GET.get('tab', 'overview')

    # Handle Actions (Create / Edit / Delete Department & Admin)
    if request.method == 'POST':
        action = request.POST.get('action')

        # 1. Create Department
        if action == 'create_department':
            dept_name = request.POST.get('name', '').strip()
            if not dept_name:
                messages.error(request, 'Department name is required.', extra_tags='dept_error')
            elif Department.objects.filter(name__iexact=dept_name).exists():
                messages.error(request, f"Department '{dept_name}' already exists.", extra_tags='dept_error')
            else:
                Department.objects.create(name=dept_name, is_active=True)
                messages.success(request, f"Department '{dept_name}' created successfully!", extra_tags='dept_success')
            return redirect('/super-admin/dashboard/?tab=departments')

        # 2. Edit Department
        elif action == 'edit_department':
            dept_id = request.POST.get('department_id')
            new_name = request.POST.get('name', '').strip()
            dept = get_object_or_404(Department, id=dept_id)
            if new_name:
                dept.name = new_name
                dept.save()
                messages.success(request, f"Department updated to '{new_name}'.", extra_tags='dept_success')
            return redirect('/super-admin/dashboard/?tab=departments')

        # 3. Terminate / Delete Department
        elif action == 'delete_department':
            dept_id = request.POST.get('department_id')
            dept = get_object_or_404(Department, id=dept_id)
            dept_name = dept.name
            dept.delete()
            messages.success(request, f"Department '{dept_name}' terminated.", extra_tags='dept_success')
            return redirect('/super-admin/dashboard/?tab=departments')

        # 4. Deploy / Create Department Admin
        elif action == 'create_admin':
            admin_name = request.POST.get('admin_name', '').strip()
            admin_email = request.POST.get('admin_email', '').strip().lower()
            admin_password = request.POST.get('admin_password', '')
            dept_id = request.POST.get('department_id')

            if not admin_name or not admin_email or not admin_password or not dept_id:
                messages.error(request, 'All admin fields are required.', extra_tags='admin_error')
            elif User.objects.filter(email=admin_email).exists():
                messages.error(request, f"A user with email '{admin_email}' already exists.", extra_tags='admin_error')
            else:
                dept = get_object_or_404(Department, id=dept_id)

                username = admin_email.split('@')[0]
                base_username = username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1

                first_name = admin_name.split()[0] if admin_name else ""
                last_name = " ".join(admin_name.split()[1:]) if len(admin_name.split()) > 1 else ""

                new_admin = User.objects.create_user(
                    username=username,
                    email=admin_email,
                    password=admin_password,
                    first_name=first_name,
                    last_name=last_name,
                    is_staff=True
                )

                # Set profile
                profile = new_admin.profile
                profile.role = 'dept_admin'
                profile.department = dept
                profile.save()

                # Link department's admin_user
                dept.admin_user = new_admin
                dept.save()

                messages.success(request, f"Admin credentials for '{admin_email}' provisioned successfully!", extra_tags='admin_success')
            return redirect('/super-admin/dashboard/?tab=admins')

        # 5. Edit Department Admin
        elif action == 'edit_admin':
            user_id = request.POST.get('user_id')
            admin_name = request.POST.get('admin_name', '').strip()
            admin_email = request.POST.get('admin_email', '').strip().lower()
            admin_password = request.POST.get('admin_password', '')
            dept_id = request.POST.get('department_id')

            target_user = get_object_or_404(User, id=user_id)
            if admin_name:
                target_user.first_name = admin_name.split()[0]
                target_user.last_name = " ".join(admin_name.split()[1:]) if len(admin_name.split()) > 1 else ""
            if admin_email:
                target_user.email = admin_email
            if admin_password:
                target_user.set_password(admin_password)
            target_user.save()

            if dept_id:
                new_dept = get_object_or_404(Department, id=dept_id)
                profile = target_user.profile
                profile.department = new_dept
                profile.save()
                new_dept.admin_user = target_user
                new_dept.save()

            messages.success(request, f"Admin credentials for '{target_user.email}' updated successfully!", extra_tags='admin_success')
            return redirect('/super-admin/dashboard/?tab=admins')

        # 6. Revoke / Delete Department Admin
        elif action == 'delete_admin':
            user_id = request.POST.get('user_id')
            target_user = get_object_or_404(User, id=user_id)
            admin_email = target_user.email
            target_user.delete()
            messages.success(request, f"Admin '{admin_email}' access revoked successfully.", extra_tags='admin_success')
            return redirect('/super-admin/dashboard/?tab=admins')

    # Query Real Civic Data
    departments = Department.objects.all().select_related('admin_user')
    dept_admins = User.objects.filter(profile__role='dept_admin').select_related('profile__department')
    all_issues = Issue.objects.all().select_related('department', 'citizen', 'assigned_worker').order_by('-created_at')

    # Status counts
    total_issues = all_issues.count()
    sub_cnt = all_issues.filter(status='Submitted').count()
    asg_cnt = all_issues.filter(status='Assigned').count()
    inp_cnt = all_issues.filter(status__in=['InProgress', 'In Progress']).count()
    res_cnt = all_issues.filter(status='Resolved').count()
    cls_cnt = all_issues.filter(status='Closed').count()
    resolved_count = res_cnt + cls_cnt
    active_field_ops = inp_cnt
    resolution_rate = int(round((resolved_count / total_issues * 100))) if total_issues > 0 else 0

    # Average Resolution Time calculation
    resolved_issues = [i for i in all_issues if i.status in ['Resolved', 'Closed'] and i.resolution_duration_hours is not None]
    if resolved_issues:
        avg_res_hours = round(sum(i.resolution_duration_hours for i in resolved_issues) / len(resolved_issues), 1)
        if avg_res_hours >= 24:
            avg_res_time_display = f"{round(avg_res_hours / 24, 1)} days"
        else:
            avg_res_time_display = f"{avg_res_hours} hrs"
    else:
        avg_res_hours = 0.0
        avg_res_time_display = "Under Target"

    # SLA Breaches
    sla_breached_issues = [i for i in all_issues if i.is_sla_breached]
    sla_breach_count = len(sla_breached_issues)

    # Department Metrics & Efficiency Rating
    dept_metrics = []
    for d in departments:
        d_issues = all_issues.filter(department=d)
        d_total = d_issues.count()
        d_sub = d_issues.filter(status='Submitted').count()
        d_asg = d_issues.filter(status='Assigned').count()
        d_inp = d_issues.filter(status__in=['InProgress', 'In Progress']).count()
        d_res = d_issues.filter(status='Resolved').count()
        d_cls = d_issues.filter(status='Closed').count()
        d_done = d_res + d_cls
        d_eff = int(round(d_done / d_total * 100)) if d_total > 0 else 100
        d_breaches = sum(1 for i in d_issues if i.is_sla_breached)

        d_resolved = [i for i in d_issues if i.status in ['Resolved', 'Closed'] and i.resolution_duration_hours]
        d_avg_time = round(sum(i.resolution_duration_hours for i in d_resolved) / len(d_resolved), 1) if d_resolved else 0.0

        if d_eff >= 90:
            rating = 5.0
            rating_label = "Exceptional"
            rating_badge = "bg-emerald-100 text-emerald-800 border-emerald-200"
        elif d_eff >= 75:
            rating = 4.2
            rating_label = "Optimal"
            rating_badge = "bg-blue-100 text-blue-800 border-blue-200"
        elif d_eff >= 50:
            rating = 3.5
            rating_label = "Moderate"
            rating_badge = "bg-amber-100 text-amber-800 border-amber-200"
        else:
            rating = 2.4
            rating_label = "Attention Needed"
            rating_badge = "bg-rose-100 text-rose-800 border-rose-200"

        admin_display = (d.admin_user.get_full_name() or d.admin_user.username) if d.admin_user else "Unassigned"
        dept_metrics.append({
            'id': d.id,
            'name': d.name,
            'admin_name': admin_display,
            'total': d_total,
            'active': d_sub + d_asg + d_inp,
            'completed': d_done,
            'efficiency': d_eff,
            'sla_breaches': d_breaches,
            'avg_resolution_hours': d_avg_time,
            'rating': rating,
            'rating_label': rating_label,
            'rating_badge': rating_badge,
            'statuses': {
                'Submitted': d_sub,
                'Assigned': d_asg,
                'InProgress': d_inp,
                'Resolved': d_res,
                'Closed': d_cls
            }
        })

    # Category Volume Breakdown
    category_qs = all_issues.values('category').annotate(total=Count('id')).order_by('-total')
    category_data = list(category_qs)
    category_labels = [c['category'] for c in category_data]
    category_values = [c['total'] for c in category_data]

    # Worker Performance Rating Indicators
    workers = User.objects.filter(profile__role='worker').select_related('profile__department')
    worker_performance = []
    for w in workers:
        w_issues = all_issues.filter(assigned_worker=w)
        w_total = w_issues.count()
        w_done = w_issues.filter(status__in=['Resolved', 'Closed']).count()
        w_active = w_issues.filter(status__in=['Assigned', 'In Progress', 'InProgress']).count()
        w_rate = int(round(w_done / w_total * 100)) if w_total > 0 else 0
        w_breaches = sum(1 for i in w_issues if i.is_sla_breached)

        if w_total > 0 and w_rate >= 90:
            w_rating = 5.0
            w_status = "Elite Operative"
            w_badge = "bg-emerald-100 text-emerald-800 border-emerald-200"
        elif w_total > 0 and w_rate >= 60:
            w_rating = 4.2
            w_status = "High Yield"
            w_badge = "bg-blue-100 text-blue-800 border-blue-200"
        elif w_total > 0:
            w_rating = 3.6
            w_status = "Active Field"
            w_badge = "bg-amber-100 text-amber-800 border-amber-200"
        else:
            w_rating = 5.0
            w_status = "Standby"
            w_badge = "bg-slate-100 text-slate-700 border-slate-200"

        worker_performance.append({
            'worker': w,
            'name': w.get_full_name() or w.username,
            'email': w.email,
            'department_name': w.profile.department.name if w.profile.department else "General Field",
            'total_tasks': w_total,
            'completed_tasks': w_done,
            'active_tasks': w_active,
            'efficiency_rate': w_rate,
            'sla_breaches': w_breaches,
            'rating': w_rating,
            'status_label': w_status,
            'badge_class': w_badge,
        })

    # Geospatial Array Data
    issues_json = []
    for iss in all_issues:
        issues_json.append({
            'id': iss.id,
            'complaint_id': iss.complaint_id,
            'description': iss.description[:60],
            'category': iss.category,
            'priority': iss.priority,
            'status': iss.status,
            'department': iss.department.name if iss.department else "General",
            'worker': iss.worker_name,
            'lat': float(iss.latitude) if iss.latitude else None,
            'lng': float(iss.longitude) if iss.longitude else None,
            'is_sla_breached': iss.is_sla_breached,
            'created_at': iss.created_at.strftime('%b %d, %Y'),
            'image_url': iss.image_url,
            'completion_image_url': iss.completion_image_url,
        })

    metrics = {
        'totalIssues': total_issues,
        'activeFieldOps': active_field_ops,
        'resolved_count': resolved_count,
        'resolution_rate': resolution_rate,
        'avg_resolution_time': avg_res_time_display,
        'avg_resolution_hours': avg_res_hours,
        'sla_breach_count': sla_breach_count,
        'byStatus': {
            'Submitted': sub_cnt,
            'Assigned': asg_cnt,
            'InProgress': inp_cnt,
            'Resolved': res_cnt,
            'Closed': cls_cnt,
        },
        'byDepartment': dept_metrics,
        'byCategory': category_data,
        'category_labels': category_labels,
        'category_values': category_values,
    }

    return render(request, 'dashboard/super_admin.html', {
        'metrics': metrics,
        'issues': all_issues,
        'issues_json': issues_json,
        'departments': departments,
        'dept_admins': dept_admins,
        'worker_performance': worker_performance,
        'sla_breached_issues': sla_breached_issues,
        'active_tab': active_tab,
    })

def super_admin_export_csv(request):
    """
    Module 8: System-Wide CSV Dataset Export for Municipal Council Audits.
    """
    if not request.user.is_authenticated:
        return redirect('login')
    role = getattr(getattr(request.user, 'profile', None), 'role', '')
    if not (request.user.is_superuser or role == 'super_admin'):
        return redirect('home')

    response = HttpResponse(content_type='text/csv')
    timestamp = timezone.now().strftime('%Y%m%d_%H%M')
    response['Content-Disposition'] = f'attachment; filename="smartcivic_audit_report_{timestamp}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Complaint ID',
        'Department',
        'Category',
        'Priority',
        'Status',
        'SLA Status',
        'SLA Threshold (Hours)',
        'Resolution Time (Hours)',
        'Citizen Name',
        'Assigned Worker',
        'Location Address',
        'Latitude',
        'Longitude',
        'Created At',
        'Last Updated At',
        'Description',
    ])

    issues = Issue.objects.all().select_related('department', 'citizen', 'assigned_worker').order_by('-created_at')
    for iss in issues:
        writer.writerow([
            iss.complaint_id,
            iss.department.name if iss.department else 'General',
            iss.category,
            iss.priority,
            iss.status,
            iss.sla_status_label,
            iss.sla_hours_threshold,
            iss.resolution_duration_hours if iss.resolution_duration_hours is not None else 'Pending',
            iss.citizen_name,
            iss.worker_name,
            iss.location_address or '',
            iss.latitude or '',
            iss.longitude or '',
            iss.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            iss.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            iss.description.replace('\n', ' ').strip(),
        ])

    return response

def super_admin_export_pdf(request):
    """
    Module 8: Printable Executive Municipal Audit Report for Council Presentations.
    """
    if not request.user.is_authenticated:
        return redirect('login')
    role = getattr(getattr(request.user, 'profile', None), 'role', '')
    if not (request.user.is_superuser or role == 'super_admin'):
        return redirect('home')

    all_issues = Issue.objects.all().select_related('department', 'citizen', 'assigned_worker').order_by('-created_at')
    departments = Department.objects.all().select_related('admin_user')

    total_issues = all_issues.count()
    res_cnt = all_issues.filter(status='Resolved').count()
    cls_cnt = all_issues.filter(status='Closed').count()
    resolved_count = res_cnt + cls_cnt
    active_count = total_issues - resolved_count
    resolution_rate = int(round((resolved_count / total_issues * 100))) if total_issues > 0 else 0
    sla_breaches = [i for i in all_issues if i.is_sla_breached]

    resolved_issues = [i for i in all_issues if i.status in ['Resolved', 'Closed'] and i.resolution_duration_hours]
    avg_res_hours = round(sum(i.resolution_duration_hours for i in resolved_issues) / len(resolved_issues), 1) if resolved_issues else 0.0

    dept_summaries = []
    for d in departments:
        d_issues = all_issues.filter(department=d)
        d_total = d_issues.count()
        d_done = d_issues.filter(status__in=['Resolved', 'Closed']).count()
        d_rate = int(round(d_done / d_total * 100)) if d_total > 0 else 100
        dept_summaries.append({
            'name': d.name,
            'admin': d.admin_user.get_full_name() or d.admin_user.username if d.admin_user else "Unassigned",
            'total': d_total,
            'resolved': d_done,
            'active': d_total - d_done,
            'rate': d_rate,
            'breaches': sum(1 for i in d_issues if i.is_sla_breached),
        })

    return render(request, 'reports/municipal_audit_report.html', {
        'generated_at': timezone.now(),
        'total_issues': total_issues,
        'resolved_count': resolved_count,
        'active_count': active_count,
        'resolution_rate': resolution_rate,
        'avg_res_hours': avg_res_hours,
        'sla_breach_count': len(sla_breaches),
        'sla_breaches': sla_breaches,
        'dept_summaries': dept_summaries,
        'issues': all_issues[:150],
    })

def dept_admin_dashboard(request):
    """
    Department Admin Dashboard:
    - Oversees workers in their assigned department.
    - Registers/deploys workers and assigns them to the department.
    - Tracks and manages complaints routed to this department.
    """
    if not request.user.is_authenticated:
        return redirect('login')

    profile = getattr(request.user, 'profile', None)
    role = getattr(profile, 'role', '')
    department = getattr(profile, 'department', None)

    # Allow dept_admin or superuser to view
    if not (request.user.is_superuser or role == 'dept_admin'):
        return redirect('home')

    if not department and not request.user.is_superuser:
        messages.error(request, 'No municipal department is assigned to your account.')
        return redirect('home')

    # If superuser is inspecting, fallback to first active department
    if not department and request.user.is_superuser:
        department = Department.objects.filter(is_active=True).first()

    # Handle Department Admin Actions
    if request.method == 'POST':
        action = request.POST.get('action')
        redirect_tab = request.POST.get('redirect_tab', 'workers')

        # 1. Register Worker
        if action == 'register_worker':
            worker_name = request.POST.get('name', '').strip()
            worker_email = request.POST.get('email', '').strip().lower()
            worker_password = request.POST.get('password', '')
            lat = request.POST.get('lat')
            lng = request.POST.get('lng')
            radius = request.POST.get('radius', 5.0)

            if not worker_name or not worker_email or not worker_password:
                messages.error(request, 'Worker name, email, and password are required.')
            elif User.objects.filter(email=worker_email).exists():
                messages.error(request, f"A user with email '{worker_email}' already exists.")
            else:
                username = worker_email.split('@')[0]
                base_username = username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1

                first_name = worker_name.split()[0] if worker_name else ""
                last_name = " ".join(worker_name.split()[1:]) if len(worker_name.split()) > 1 else ""

                worker_user = User.objects.create_user(
                    username=username,
                    email=worker_email,
                    password=worker_password,
                    first_name=first_name,
                    last_name=last_name
                )

                w_profile = worker_user.profile
                w_profile.role = 'worker'
                w_profile.department = department
                if lat:
                    w_profile.base_latitude = lat
                if lng:
                    w_profile.base_longitude = lng
                if radius:
                    w_profile.service_radius_km = radius
                w_profile.save()

                messages.success(request, f"Operative '{worker_name}' successfully deployed to {department.name}!")
            return redirect(f"/dept-admin/dashboard/?tab={redirect_tab}")

        # 2. Edit Worker
        elif action == 'edit_worker':
            worker_id = request.POST.get('worker_id')
            worker_user = get_object_or_404(User, id=worker_id, profile__department=department)
            name = request.POST.get('name', '').strip()
            email = request.POST.get('email', '').strip().lower()
            password = request.POST.get('password', '').strip()
            lat = request.POST.get('lat')
            lng = request.POST.get('lng')
            radius = request.POST.get('radius')
            is_available = request.POST.get('is_available') == 'true'

            if name:
                worker_user.first_name = name.split()[0]
                worker_user.last_name = " ".join(name.split()[1:]) if len(name.split()) > 1 else ""
            if email and email != worker_user.email:
                if User.objects.filter(email=email).exclude(id=worker_user.id).exists():
                    messages.error(request, f"Email '{email}' is already in use by another account.")
                    return redirect(f"/dept-admin/dashboard/?tab={redirect_tab}")
                worker_user.email = email
            if password:
                worker_user.set_password(password)
            worker_user.save()

            profile = worker_user.profile
            if lat:
                profile.base_latitude = lat
            if lng:
                profile.base_longitude = lng
            if radius:
                profile.service_radius_km = radius
            profile.is_available = is_available
            profile.save()

            messages.success(request, f"Operative '{worker_user.get_full_name() or worker_user.username}' updated successfully.")
            return redirect(f"/dept-admin/dashboard/?tab={redirect_tab}")

        # 3. Delete Worker
        elif action == 'delete_worker':
            worker_id = request.POST.get('worker_id')
            worker_user = get_object_or_404(User, id=worker_id, profile__department=department)
            w_name = worker_user.get_full_name() or worker_user.username

            # Revert any uncompleted issues back to Submitted and Unassigned
            Issue.objects.filter(
                assigned_worker=worker_user, 
                status__in=['Assigned', 'In Progress']
            ).update(assigned_worker=None, status='Submitted')

            worker_user.delete()
            messages.success(request, f"Operative '{w_name}' terminated and active tasks unassigned.")
            return redirect(f"/dept-admin/dashboard/?tab={redirect_tab}")

        # 4. Verify & Approve Issue (Module 6 & 7)
        elif action == 'verify_approve_issue':
            issue_id = request.POST.get('issue_id')
            admin_notes = request.POST.get('admin_notes', '').strip()
            issue = get_object_or_404(Issue, id=issue_id, department=department)

            issue.status = 'Closed'
            issue.verified_by = request.user
            if admin_notes:
                issue.admin_notes = admin_notes
            issue.rejection_reason = None  # Clear any previous rejection
            issue.save()

            area_name = get_issue_area_name(issue)

            # Dispatches audit notifications
            if issue.citizen:
                send_notification(
                    issue.citizen,
                    f"Your complaint #{issue.complaint_id} at {area_name} was verified and officially Closed by {department.name}. You can view the completed work photo in your dashboard.",
                    issue=issue
                )
            if issue.assigned_worker:
                send_notification(
                    issue.assigned_worker,
                    f"Great job! Proof of fix for #{issue.complaint_id} was verified and approved by Department Admin. Issue is officially Closed.",
                    issue=issue
                )
            notify_super_admins(
                f"Complaint #{issue.complaint_id} ({department.name}) at {area_name} was verified and officially closed.",
                issue=issue
            )

            messages.success(request, f"Complaint #{issue.complaint_id} verified and officially Closed.")
            return redirect('/dept-admin/dashboard/?tab=issues')

        # 5. Reject Issue Proof (Module 6 & 7)
        elif action == 'reject_issue':
            issue_id = request.POST.get('issue_id')
            reason = request.POST.get('rejection_reason', '').strip()
            if not reason:
                messages.error(request, "A mandatory rejection reason is required to reject proof.")
                return redirect('/dept-admin/dashboard/?tab=issues')

            issue = get_object_or_404(Issue, id=issue_id, department=department)
            issue.status = 'In Progress'
            issue.rejection_reason = reason
            issue.save()

            area_name = get_issue_area_name(issue)

            # Notify worker of rejection with mandatory reason
            if issue.assigned_worker:
                send_notification(
                    issue.assigned_worker,
                    f"⚠️ Fix Rejected for #{issue.complaint_id}: {reason}. Please re-examine the site at {area_name} and submit new proof.",
                    issue=issue
                )
            if issue.citizen:
                send_notification(
                    issue.citizen,
                    f"Quality check update for #{issue.complaint_id}: Admin requested additional rework from the operative ({reason}).",
                    issue=issue
                )
            notify_super_admins(
                f"Proof rejected for #{issue.complaint_id} ({department.name}): '{reason}'. Returned to operative for rework.",
                issue=issue
            )

            messages.warning(request, f"Complaint #{issue.complaint_id} proof rejected. Returned to worker with instructions.")
            return redirect('/dept-admin/dashboard/?tab=issues')

        # 6. Reassign Worker to Issue
        elif action == 'reassign_issue':
            from .assignment import assign_nearest_worker_for_issue

            issue_id = request.POST.get('issue_id')
            worker_select = request.POST.get('assigned_worker_id')
            issue = get_object_or_404(Issue, id=issue_id, department=department)

            if worker_select == 'auto':
                assigned = assign_nearest_worker_for_issue(issue)
                if assigned:
                    messages.success(request, f"Complaint #{issue.complaint_id} automatically assigned to nearest operative: {assigned.get_full_name() or assigned.username}")
                else:
                    messages.warning(request, f"No available workers found within service radius for #{issue.complaint_id}.")
            elif worker_select:
                target_worker = get_object_or_404(User, id=worker_select, profile__department=department)
                issue.assigned_worker = target_worker
                if issue.status == 'Submitted':
                    issue.status = 'Assigned'
                issue.save()

                Notification.objects.create(
                    user=target_worker,
                    issue=issue,
                    message=f"You have been manually dispatched to task #{issue.complaint_id} by Department Admin."
                )
                messages.success(request, f"Complaint #{issue.complaint_id} dispatched to {target_worker.get_full_name() or target_worker.username}.")
            else:
                issue.assigned_worker = None
                issue.status = 'Submitted'
                issue.save()
                messages.info(request, f"Complaint #{issue.complaint_id} is now unassigned.")

            return redirect('/dept-admin/dashboard/?tab=issues')

    # Fetch workers affiliated strictly with this department
    workers = User.objects.filter(
        profile__role='worker',
        profile__department=department
    ).select_related('profile')

    # Fetch issues routed strictly to this department
    issues = Issue.objects.filter(department=department).select_related('citizen', 'assigned_worker').order_by('-created_at')

    # Calculate Worker Analytics & Efficiency Metrics for Tab 4
    worker_analytics = []
    for w in workers:
        w_tasks = issues.filter(assigned_worker=w)
        total = w_tasks.count()
        active = w_tasks.filter(status__in=['Assigned', 'In Progress']).count()
        resolved = w_tasks.filter(status__in=['Resolved', 'Closed']).count()
        rate = int((resolved / total * 100)) if total > 0 else 0
        worker_analytics.append({
            'worker': w,
            'total_tasks': total,
            'active_tasks': active,
            'resolved_tasks': resolved,
            'efficiency_rate': rate,
        })

    awaiting_verification = issues.filter(status='Resolved')

    return render(request, 'dashboard/dept_admin.html', {
        'department': department,
        'workers': workers,
        'issues': issues,
        'worker_analytics': worker_analytics,
        'awaiting_verification': awaiting_verification,
        'current_tab': request.GET.get('tab', 'workers'),
    })

def worker_dashboard(request):
    """
    Field Operative / Worker Dashboard:
    - Lists active tasks assigned to the worker.
    - Allows worker to mark tasks 'In Progress' and submit completion proof photos to mark 'Resolved'.
    """
    if not request.user.is_authenticated:
        return redirect('login')

    role = getattr(getattr(request.user, 'profile', None), 'role', '')
    if not (request.user.is_superuser or role == 'worker'):
        return redirect('home')

    if request.method == 'POST':
        action = request.POST.get('action')

        # Allow worker to update their operational base location
        if action == 'update_base_location':
            new_lat = request.POST.get('base_latitude')
            new_lng = request.POST.get('base_longitude')
            if new_lat and new_lng and hasattr(request.user, 'profile'):
                try:
                    request.user.profile.base_latitude = float(new_lat)
                    request.user.profile.base_longitude = float(new_lng)
                    request.user.profile.save()
                    messages.success(request, f"Worker base location updated to ({float(new_lat):.4f}, {float(new_lng):.4f}).")
                except ValueError:
                    messages.error(request, "Invalid coordinates provided.")
            return redirect('worker_dashboard')

        issue_id = request.POST.get('issue_id')
        new_status = request.POST.get('new_status')
        issue = get_object_or_404(Issue, id=issue_id)

        # Security check: ensure this issue is assigned to this worker (or superuser)
        if not request.user.is_superuser and issue.assigned_worker != request.user:
            messages.error(request, 'Permission denied: This issue is not assigned to you.')
            return redirect('worker_dashboard')

        if new_status == 'In Progress':
            issue.status = 'In Progress'
            issue.save()
            area_name = get_issue_area_name(issue)
            w_name = request.user.get_full_name() or request.user.username
            if issue.citizen:
                send_notification(
                    issue.citizen,
                    f"Operative {w_name} has started work on your complaint #{issue.complaint_id} at {area_name} (Status: In Progress).",
                    issue=issue
                )
            notify_dept_admins(
                issue.department,
                f"Operative {w_name} started work on #{issue.complaint_id} at {area_name}.",
                issue=issue
            )
            messages.success(request, f"Task #{issue.complaint_id} marked as In Progress.")

        elif new_status == 'Resolved':
            completion_file = request.FILES.get('completion_image')
            if not completion_file:
                messages.error(request, 'A completion proof image is required to resolve this task.')
            else:
                issue.status = 'Resolved'
                issue.completion_image = completion_file
                issue.save()
                area_name = get_issue_area_name(issue)
                w_name = request.user.get_full_name() or request.user.username

                # Notify Department Admin
                notify_dept_admins(
                    issue.department,
                    f"Work completed for #{issue.complaint_id} at {area_name} by operative {w_name}. Proof of fix uploaded and awaiting your verification.",
                    issue=issue
                )
                # Notify Super Admin
                notify_super_admins(
                    f"Operative {w_name} submitted resolution proof for #{issue.complaint_id} ({issue.department.name if issue.department else 'General'}) at {area_name}. Awaiting department verification.",
                    issue=issue
                )
                # Notify Citizen
                if issue.citizen:
                    send_notification(
                        issue.citizen,
                        f"Work completed on your complaint #{issue.complaint_id} at {area_name}! Operational proof has been submitted for department verification.",
                        issue=issue
                    )
                messages.success(request, f"Proof uploaded! Task #{issue.complaint_id} marked as Resolved and sent for verification.")

        return redirect('worker_dashboard')

    # Fetch tasks assigned to the logged-in worker
    active_issues = Issue.objects.filter(
        assigned_worker=request.user
    ).exclude(status='Resolved').exclude(status='Closed').select_related('department')

    completed_issues = Issue.objects.filter(
        assigned_worker=request.user,
        status__in=['Resolved', 'Closed']
    ).select_related('department')

    profile = getattr(request.user, 'profile', None)
    worker_lat = float(profile.base_latitude) if profile and profile.base_latitude is not None else None
    worker_lng = float(profile.base_longitude) if profile and profile.base_longitude is not None else None

    return render(request, 'dashboard/worker.html', {
        'active_issues': active_issues,
        'completed_issues': completed_issues,
        'worker_lat': worker_lat,
        'worker_lng': worker_lng,
        'worker_name': request.user.get_full_name() or request.user.username,
    })

def citizen_dashboard(request):
    """
    Citizen Command Hub:
    - Lists issues reported by the logged-in citizen.
    - Displays status timeline, photo proof of completion, and geospatial coordinates.
    - Allows citizen to acknowledge proof of work and formally transition issue to 'Closed'.
    - Integrated with notifications.
    """
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'close_issue':
            issue_id = request.POST.get('issue_id')
            issue = get_object_or_404(Issue, id=issue_id, citizen=request.user)
            if issue.status in ['Resolved', 'In Progress', 'Assigned']:
                issue.status = 'Closed'
                issue.save()

                area_name = get_issue_area_name(issue)
                send_notification(
                    request.user,
                    f"Complaint #{issue.complaint_id} has been formally acknowledged and closed.",
                    issue=issue
                )
                if issue.assigned_worker:
                    send_notification(
                        issue.assigned_worker,
                        f"Citizen confirmed resolution for Complaint #{issue.complaint_id} at {area_name}. Task is officially Closed.",
                        issue=issue
                    )
                notify_dept_admins(
                    issue.department,
                    f"Citizen confirmed resolution for complaint #{issue.complaint_id} at {area_name}.",
                    issue=issue
                )
                notify_super_admins(
                    f"Complaint #{issue.complaint_id} ({issue.department.name if issue.department else 'General'}) at {area_name} closed with citizen confirmation.",
                    issue=issue
                )
                messages.success(request, f"Complaint #{issue.complaint_id} confirmed and closed successfully!")
            return redirect('citizen_dashboard')

    issues = Issue.objects.filter(citizen=request.user).select_related('department')
    notifications = Notification.objects.filter(user=request.user)
    unread_count = notifications.filter(is_read=False).count()

    return render(request, 'dashboard/citizen.html', {
        'issues': issues,
        'notifications': notifications,
        'unread_count': unread_count,
    })

def report_issue(request):
    """
    Module 2: Citizen Issue Reporting
    - Submit complaint form with Department, category, priority, description, location, and photo.
    """
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == 'POST':
        dept_id = request.POST.get('department_id')
        category = request.POST.get('category', 'General').strip() or 'General'
        priority = request.POST.get('priority', 'Medium')
        description = request.POST.get('description', '').strip()
        location_address = request.POST.get('location_address', '').strip()
        lat = request.POST.get('latitude')
        lng = request.POST.get('longitude')
        image = request.FILES.get('image')

        if not dept_id or not description:
            messages.error(request, 'Department and description are required.')
            return redirect('report_issue')

        department = get_object_or_404(Department, id=dept_id)

        # 1. Create the complaint record
        issue = Issue.objects.create(
            department=department,
            citizen=request.user,
            category=category,
            priority=priority,
            description=description,
            location_address=location_address if location_address else None,
            latitude=lat if lat else None,
            longitude=lng if lng else None,
            image=image if image else None,
            status='Submitted'
        )

        area_name = get_issue_area_name(issue)

        # Module 7: Dispatches alerts to Super Admin & Department Admin
        notify_super_admins(
            f"New civic issue #{issue.complaint_id} ({issue.category}) reported at {area_name} routed to {department.name}.",
            issue=issue
        )
        notify_dept_admins(
            department,
            f"New issue reported in {department.name} at {area_name}: #{issue.complaint_id} - '{issue.description[:50]}'",
            issue=issue
        )

        # 2. Module 4: Department-Scoped Automated Worker Assignment
        from .assignment import find_nearest_department_worker
        nearest_worker, distance_km = find_nearest_department_worker(department, lat, lng)

        if nearest_worker:
            issue.assigned_worker = nearest_worker
            issue.status = 'Assigned'
            issue.save()

            # Notification for assigned worker
            send_notification(
                nearest_worker,
                f"New task assigned! Complaint #{issue.complaint_id} ({category}) at {area_name} (~{distance_km} km from your base).",
                issue=issue
            )

            # Notification for citizen informing about automatic worker assignment
            send_notification(
                request.user,
                f"Your complaint #{issue.complaint_id} at {area_name} has been automatically assigned to {department.name} operative ({nearest_worker.get_full_name() or nearest_worker.username}).",
                issue=issue
            )
            messages.success(request, f"Complaint #{issue.complaint_id} submitted and automatically assigned to nearby worker ({nearest_worker.get_full_name() or nearest_worker.username})!")
        else:
            # Fallback when no worker is registered with coordinates in this department
            send_notification(
                request.user,
                f"Your complaint #{issue.complaint_id} ({category}) at {area_name} was submitted to {department.name} and is awaiting dispatch.",
                issue=issue
            )
            messages.success(request, f"Complaint #{issue.complaint_id} submitted successfully to {department.name}!")

        return redirect('citizen_dashboard')

    departments = Department.objects.filter(is_active=True)
    return render(request, 'issues/report_issue.html', {'departments': departments})

def mark_notification_read(request, notif_id):
    """Marks a notification as read (supports JSON AJAX and redirect fallback)."""
    if not request.user.is_authenticated:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        return redirect('login')

    notif = get_object_or_404(Notification, id=notif_id, user=request.user)
    notif.is_read = True
    notif.save()

    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json' or request.GET.get('format') == 'json':
        return JsonResponse({'status': 'ok', 'unread_count': unread_count})

    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('dashboard_redirect')

def mark_all_notifications_read(request):
    """Marks all unread notifications as read for current user."""
    if not request.user.is_authenticated:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        return redirect('login')

    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json' or request.GET.get('format') == 'json':
        return JsonResponse({'status': 'ok', 'unread_count': 0})

    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('dashboard_redirect')

