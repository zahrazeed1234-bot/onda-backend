from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EquipmentVORViewSet, EquipmentILSViewSet, EquipmentDMEViewSet,
    EquipmentRadarViewSet, EquipmentVCSViewSet,
    AllEquipmentListView, StatsView, EquipmentChoicesView,
)

router = DefaultRouter()
router.register(r'vor', EquipmentVORViewSet, basename='equipment-vor')
router.register(r'ils', EquipmentILSViewSet, basename='equipment-ils')
router.register(r'dme', EquipmentDMEViewSet, basename='equipment-dme')
router.register(r'radar', EquipmentRadarViewSet, basename='equipment-radar')
router.register(r'vcs', EquipmentVCSViewSet, basename='equipment-vcs')

urlpatterns = [
    path('', include(router.urls)),
    path('all/', AllEquipmentListView.as_view(), name='equipment-all'),
    path('stats/', StatsView.as_view(), name='equipment-stats'),
    path('choices/', EquipmentChoicesView.as_view(), name='equipment-choices'),
]
