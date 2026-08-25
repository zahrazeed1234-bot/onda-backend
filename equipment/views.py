from itertools import chain
from django.utils import timezone
from datetime import timedelta
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, Count, Avg
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import (
    IsAdminCNS, IsAdminOrTechnicianReadOnlyForConsultant,
    CanModifyEquipment, FrequencyFieldProtected, IsAdminOrTechnician,
)
from .models import (
    EquipmentVOR, EquipmentILS, EquipmentDME, EquipmentRadar, EquipmentVCS, MeasurementLog,
    STATUS_OK, STATUS_DEGRADE, STATUS_HS, STATUS_CHOICES,
)
from .serializers import (
    EquipmentVORSerializer, EquipmentILSSerializer, EquipmentDMESerializer,
    EquipmentRadarSerializer, EquipmentVCSSerializer, MeasurementLogSerializer,
    GenericEquipmentSerializer,
)


EQUIPMENT_CLASSES = {
    'EquipmentVOR': (EquipmentVOR, EquipmentVORSerializer),
    'EquipmentILS': (EquipmentILS, EquipmentILSSerializer),
    'EquipmentDME': (EquipmentDME, EquipmentDMESerializer),
    'EquipmentRadar': (EquipmentRadar, EquipmentRadarSerializer),
    'EquipmentVCS': (EquipmentVCS, EquipmentVCSSerializer),
}


def _get_stats():
    stats = {'par_type': {}, 'par_statut': {}, 'alerte_seuils': [], 'disponibilite': 0.0}
    all_items = []
    for cls_name, (cls, _) in EQUIPMENT_CLASSES.items():
        qs = cls.objects.all()
        total = qs.count()
        par_statut = {
            STATUS_OK: qs.filter(statut_operationnel=STATUS_OK).count(),
            STATUS_DEGRADE: qs.filter(statut_operationnel=STATUS_DEGRADE).count(),
            STATUS_HS: qs.filter(statut_operationnel=STATUS_HS).count(),
        }
        label = cls_name.replace('Equipment', '').upper()
        stats['par_type'][label] = {
            'total': total,
            **par_statut,
            'disponibilite': round(100 * par_statut[STATUS_OK] / total, 2) if total else 100.0,
        }
        all_items.append(qs)
        if cls_name == 'EquipmentILS':
            seuil_ddm = 0.160
            pour_loc = qs.filter(type_ils='LOC')
            for equip in pour_loc.filter(ddm_nominale__gt=seuil_ddm):
                stats['alerte_seuils'].append({
                    'code': equip.code_unique, 'nom': equip.nom,
                    'type': 'ILS DDM', 'valeur': equip.ddm_nominale,
                    'seuil': seuil_ddm, 'niveau': 'WARNING',
                })
        if cls_name == 'EquipmentDME':
            seuil = 70
            for equip in qs.filter(rendement_recent__lt=seuil):
                stats['alerte_seuils'].append({
                    'code': equip.code_unique, 'nom': equip.nom,
                    'type': 'DME Rendement', 'valeur': equip.rendement_recent,
                    'seuil': seuil, 'niveau': 'ALARME',
                })
        if cls_name == 'EquipmentVOR':
            for equip in qs.exclude(taux_modulation_AM__range=(25, 35)):
                stats['alerte_seuils'].append({
                    'code': equip.code_unique, 'nom': equip.nom,
                    'type': 'VOR Mod AM', 'valeur': equip.taux_modulation_AM,
                    'seuil': '25-35%', 'niveau': 'WARNING',
                })
    all_qs = chain.from_iterable(q.values_list('statut_operationnel', flat=True) for q in all_items)
    items = list(all_qs)
    total_all = len(items)
    ok = items.count(STATUS_OK)
    degrade = items.count(STATUS_DEGRADE)
    hs = items.count(STATUS_HS)
    stats['par_statut'] = {STATUS_OK: ok, STATUS_DEGRADE: degrade, STATUS_HS: hs}
    stats['total_equipements'] = total_all
    stats['critique_count'] = sum(
        v.get('total', 0) for k, v in stats['par_type'].items() if k in ('VOR', 'ILS', 'DME')
    )
    stats['disponibilite'] = round(100 * ok / total_all, 2) if total_all else 100.0

    date_debut = timezone.now() - timedelta(days=7)
    mesures_ddm = MeasurementLog.objects.filter(
        equipment_type='EquipmentILS', parametre='DDM', date_mesure__gte=date_debut
    ).order_by('date_mesure')
    stats['courbe_ddm_7j'] = [
        {
            'date': m.date_mesure.strftime('%Y-%m-%d %H:%M'),
            'equipment_id': m.equipment_id,
            'valeur': m.valeur,
        }
        for m in mesures_ddm
    ]
    mesures_rendement = MeasurementLog.objects.filter(
        equipment_type='EquipmentDME', parametre='RENDREMENT', date_mesure__gte=date_debut
    ).order_by('date_mesure')
    if not mesures_rendement.exists():
        dmes = EquipmentDME.objects.all()
        from datetime import datetime as dt
        for i, d in enumerate(dmes):
            offset = i % 7
            stats['courbe_rendement_7j'] = [
                {
                    'date': (timezone.now() - timedelta(days=x)).strftime('%Y-%m-%d'),
                    'equipment_id': d.id,
                    'code': d.code_unique,
                    'valeur': max(68.0, min(95.0, d.rendement_recent + (x - 3) * 0.8)),
                }
                for x in range(7)
            ]
            break
    else:
        stats['courbe_rendement_7j'] = [
            {
                'date': m.date_mesure.strftime('%Y-%m-%d %H:%M'),
                'equipment_id': m.equipment_id,
                'valeur': m.valeur,
            }
            for m in mesures_rendement
        ]
    return stats


class _BaseEquipmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminOrTechnicianReadOnlyForConsultant]
    filterset_fields = ['statut_operationnel']
    search_fields = ['nom', 'code_unique', 'description']
    ordering_fields = ['code_unique', 'date_mise_en_service', 'date_modification']

    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            self.permission_classes = [CanModifyEquipment]
        elif self.action in ['update', 'partial_update']:
            self.permission_classes = [IsAdminOrTechnician, FrequencyFieldProtected]
        return super().get_permissions()

    @action(detail=True, methods=['get'])
    def mesures(self, request, pk=None):
        obj = self.get_object()
        ct = ContentType.objects.get_for_model(obj.__class__)
        logs = MeasurementLog.objects.filter(
            equipment_type=obj.__class__.__name__, equipment_id=obj.pk
        ).order_by('-date_mesure')[:100]
        serializer = MeasurementLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrTechnicianReadOnlyForConsultant])
    def ajouter_mesure(self, request, pk=None):
        obj = self.get_object()
        serializer = MeasurementLogSerializer(data={
            **request.data,
            'equipment_type': obj.__class__.__name__,
            'equipment_id': obj.pk,
        })
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EquipmentVORViewSet(_BaseEquipmentViewSet):
    queryset = EquipmentVOR.objects.all()
    serializer_class = EquipmentVORSerializer


class EquipmentILSViewSet(_BaseEquipmentViewSet):
    queryset = EquipmentILS.objects.all()
    serializer_class = EquipmentILSSerializer
    filterset_fields = ['statut_operationnel', 'type_ils']


class EquipmentDMEViewSet(_BaseEquipmentViewSet):
    queryset = EquipmentDME.objects.all()
    serializer_class = EquipmentDMESerializer
    filterset_fields = ['statut_operationnel', 'canal', 'mode_fonctionnement']


class EquipmentRadarViewSet(_BaseEquipmentViewSet):
    queryset = EquipmentRadar.objects.all()
    serializer_class = EquipmentRadarSerializer
    filterset_fields = ['statut_operationnel', 'type_radar']


class EquipmentVCSViewSet(_BaseEquipmentViewSet):
    queryset = EquipmentVCS.objects.all()
    serializer_class = EquipmentVCSSerializer
    filterset_fields = ['statut_operationnel', 'codec', 'protocole']


class AllEquipmentListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        type_filter = request.query_params.get('type')
        statut_filter = request.query_params.get('statut')
        search = request.query_params.get('search')
        result = []
        for cls_name, (cls, serializer_cls) in EQUIPMENT_CLASSES.items():
            type_short = cls_name.replace('Equipment', '').upper()
            if type_filter and type_filter.upper() != type_short:
                continue
            qs = cls.objects.all()
            if statut_filter:
                qs = qs.filter(statut_operationnel=statut_filter)
            if search:
                qs = qs.filter(Q(nom__icontains=search) | Q(code_unique__icontains=search))
            for obj in qs:
                data = serializer_cls(obj).data
                result.append({
                    'id': obj.pk,
                    'code_unique': obj.code_unique,
                    'nom': obj.nom,
                    'type': cls_name,
                    'type_label': type_short,
                    'statut_operationnel': obj.statut_operationnel,
                    'statut_label': obj.get_statut_operationnel_display(),
                    'is_critique': type_short in ('VOR', 'ILS', 'DME'),
                    'localisation_lat': obj.localisation_lat,
                    'localisation_lng': obj.localisation_lng,
                    'date_mise_en_service': obj.date_mise_en_service,
                    'description': obj.description,
                    'details': data,
                })
        result.sort(key=lambda x: x['code_unique'])
        return Response(result)


class StatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        stats = _get_stats()
        return Response(stats)


class EquipmentChoicesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        choices = []
        for cls_name, (cls, _) in EQUIPMENT_CLASSES.items():
            ct = ContentType.objects.get_for_model(cls)
            for obj in cls.objects.all().order_by('code_unique'):
                choices.append({
                    'id': obj.pk,
                    'code_unique': obj.code_unique,
                    'nom': obj.nom,
                    'type': cls_name,
                    'type_label': cls_name.replace('Equipment', '').upper(),
                    'content_type_id': ct.pk,
                })
        return Response({
            'types': [
                {'value': 'EquipmentVOR', 'label': 'VOR'},
                {'value': 'EquipmentILS', 'label': 'ILS'},
                {'value': 'EquipmentDME', 'label': 'DME'},
                {'value': 'EquipmentRadar', 'label': 'Radar'},
                {'value': 'EquipmentVCS', 'label': 'VCS'},
            ],
            'statuts': [{'value': v, 'label': l} for v, l in STATUS_CHOICES],
            'equipements': choices,
        })
