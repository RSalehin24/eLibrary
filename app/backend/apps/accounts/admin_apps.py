from django.contrib.admin.apps import AdminConfig


class MaintenanceAdminConfig(AdminConfig):
    default_site = "apps.accounts.maintenance.MaintenanceAdminSite"
