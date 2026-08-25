from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MaintenanceTicketViewSet, TicketDashboardStatsView, TicketChoicesView,
)

router = DefaultRouter()
router.register(r'', MaintenanceTicketViewSet, basename='ticket')

urlpatterns = [
    path('', include(router.urls)),
    path('stats/summary/', TicketDashboardStatsView.as_view(), name='ticket-stats-summary'),
    path('metadata/choices/', TicketChoicesView.as_view(), name='ticket-choices'),
]
