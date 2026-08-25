from rest_framework import permissions


class IsAdminCNS(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_admin_cns()


class IsAdminOrTechnician(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_admin_cns() or request.user.is_technician()


class IsAdminOrTechnicianReadOnlyForConsultant(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_admin_cns() or request.user.is_technician()


class FrequencyFieldProtected(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        frequency_fields = ['frequence', 'frequence_porteuse', 'frequence_interrogation', 'frequence_reponse']
        if hasattr(view, 'action') and view.action in ['update', 'partial_update']:
            data = request.data or {}
            has_freq_change = any(field in data for field in frequency_fields)
            if has_freq_change:
                return request.user.is_admin_cns()
        return True


class CanModifyEquipment(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_admin_cns()
