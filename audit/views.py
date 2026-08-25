from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count
from accounts.permissions import IsAdminCNS
from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related('utilisateur', 'content_type').all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminCNS]
    filterset_fields = ['action', 'utilisateur', 'content_type']
    search_fields = ['description', 'utilisateur__username', 'adresse_ip', 'endpoint']
    ordering_fields = ['timestamp', 'action']
    ordering = ['-timestamp']

    @action(detail=False, methods=['get'])
    def summary(self, request):
        qs = self.get_queryset()
        limit = request.query_params.get('days', 7)
        try:
            from datetime import timedelta
            from django.utils import timezone
            debut = timezone.now() - timedelta(days=int(limit))
            qs = qs.filter(timestamp__gte=debut)
        except (ValueError, TypeError):
            pass
        data = {
            'total': qs.count(),
            'par_action': dict(qs.values_list('action').annotate(c=Count('id')).values_list('action', 'c')),
            'connexions_reussies': qs.filter(action=AuditLog.ACTION_LOGIN).count(),
            'connexions_echouees': qs.filter(action=AuditLog.ACTION_LOGIN_FAILED).count(),
            'modifications_freq': qs.filter(action=AuditLog.ACTION_FREQUENCY_CHANGE).count(),
            'suppressions': qs.filter(action=AuditLog.ACTION_DELETE).count(),
        }
        return Response(data)

    @action(detail=False, methods=['get'])
    def latest(self, request):
        limit = int(request.query_params.get('limit', 20))
        qs = self.get_queryset()[:limit]
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
