import logging
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone

logger = logging.getLogger('audit')


class AuditMiddleware(MiddlewareMixin):
    SENSITIVE_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}
    AUDIT_ENDPOINTS_PREFIX = '/api/'

    def process_request(self, request):
        request._audit_start_time = timezone.now()

    def process_response(self, request, response):
        try:
            path = getattr(request, 'path', '')
            if not path.startswith(self.AUDIT_ENDPOINTS_PREFIX):
                return response
            method = request.method
            if method not in self.SENSITIVE_METHODS:
                return response
            status = getattr(response, 'status_code', 0)
            if status >= 500:
                return response
            user = getattr(request, 'user', None)
            if user is None or not getattr(user, 'is_authenticated', False):
                return response
            from .models import AuditLog
            ip = request.META.get('REMOTE_ADDR')
            ua = request.META.get('HTTP_USER_AGENT')
            if method == 'DELETE':
                action = AuditLog.ACTION_DELETE
            elif method == 'POST':
                action = AuditLog.ACTION_CREATE
            else:
                action = AuditLog.ACTION_UPDATE
            AuditLog.log(
                action=action,
                utilisateur=user,
                ip=ip,
                user_agent=ua,
                description=f'{method} {path} ({status})',
                endpoint=path,
                methode_http=method,
            )
        except Exception as exc:
            logger.warning(f'AuditMiddleware erreur: {exc}')
        return response
