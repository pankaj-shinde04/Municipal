from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.user_dashboard_redirect, name='dashboard_redirect'),
    path('login/', views.user_login, name='login'),
    path('register/', views.user_register, name='register'),
    path('logout/', views.user_logout, name='logout'),
    path('super-admin/dashboard/', views.super_admin_dashboard, name='super_admin_dashboard'),
    path('super-admin/export/csv/', views.super_admin_export_csv, name='super_admin_export_csv'),
    path('super-admin/export/pdf/', views.super_admin_export_pdf, name='super_admin_export_pdf'),
    path('dept-admin/dashboard/', views.dept_admin_dashboard, name='dept_admin_dashboard'),
    path('worker/dashboard/', views.worker_dashboard, name='worker_dashboard'),
    path('citizen/dashboard/', views.citizen_dashboard, name='citizen_dashboard'),
    path('citizen/report-issue/', views.report_issue, name='report_issue'),
    path('citizen/notifications/<int:notif_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/<int:notif_id>/read/', views.mark_notification_read, name='universal_mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
]
