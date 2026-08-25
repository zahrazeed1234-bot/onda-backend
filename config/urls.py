from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.views.static import serve as static_serve
from pathlib import Path
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="GMAO CNS API",
        default_version='v1',
        description="API Gestion de Maintenance Assistée par Ordinateur - Systèmes CNS ONDA",
        terms_of_service="https://www.onda.ma/",
        contact=openapi.Contact(email="support@onda.ma"),
        license=openapi.License(name="Confidentiel ONDA"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


class DashboardStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from equipment.views import _get_stats
        from tickets.models import (
            MaintenanceTicket,
            TICKET_TYPE_URGENCE,
            PRIORITY_CRITIQUE,
            STATUS_RESOLU,
            STATUS_CLOTURE,
            STATUS_EN_COURS,
            STATUS_ASSIGNE,
            PRIORITY_CHOICES,
            TICKET_TYPE_CHOICES,
            STATUS_CHOICES,
        )
        from django.db.models import Q

        eq_stats = _get_stats()

        qs = MaintenanceTicket.objects.all()
        if not request.user.is_admin_cns():
            if request.user.is_technician():
                qs = qs.filter(Q(assigne_a=request.user) | Q(cree_par=request.user))
        ouverts = qs.exclude(statut__in=[STATUS_RESOLU, STATUS_CLOTURE])
        tk_stats = {
            'total': qs.count(),
            'ouverts': ouverts.count(),
            'en_cours': qs.filter(statut=STATUS_EN_COURS).count(),
            'assignes': qs.filter(statut=STATUS_ASSIGNE).count(),
            'resolus': qs.filter(statut__in=[STATUS_RESOLU, STATUS_CLOTURE]).count(),
            'critics': ouverts.filter(priorite=PRIORITY_CRITIQUE).count(),
            'urgents': ouverts.filter(type_ticket=TICKET_TYPE_URGENCE).count(),
            'par_priorite': {p: qs.filter(priorite=p).count() for p, _ in PRIORITY_CHOICES},
            'par_type': {t: qs.filter(type_ticket=t).count() for t, _ in TICKET_TYPE_CHOICES},
            'par_statut': {s: qs.filter(statut=s).count() for s, _ in STATUS_CHOICES},
        }
        return Response({'equipment': eq_stats, 'tickets': tk_stats})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/equipment/', include('equipment.urls')),
    path('api/tickets/', include('tickets.urls')),
    path('api/audit/', include('audit.urls')),
    path('api/dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

_STATIC_ROOT = Path(settings.STATIC_ROOT)
urlpatterns += [
    re_path(r'^onda\.svg$', lambda r: static_serve(r, 'onda.svg', document_root=_STATIC_ROOT)),
    re_path(r'^$', TemplateView.as_view(template_name='spa_index.html'), name='spa-root'),
    re_path(r'^(?!api|admin|swagger|redoc|static|media).*', TemplateView.as_view(template_name='spa_index.html'), name='spa-catchall'),
]
