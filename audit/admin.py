from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'action', 'utilisateur', 'adresse_ip', 'description', 'endpoint')
    list_filter = ('action', 'content_type')
    search_fields = ('description', 'utilisateur__username', 'adresse_ip')
    readonly_fields = (
        'utilisateur', 'action', 'timestamp', 'adresse_ip', 'user_agent',
        'content_type', 'object_id', 'description', 'ancienne_valeur',
        'nouvelle_valeur', 'endpoint', 'methode_http',
    )
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
