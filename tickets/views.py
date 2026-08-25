from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, Count
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsAdminOrTechnicianReadOnlyForConsultant, IsAdminOrTechnician
from .models import (
    MaintenanceTicket, ChecklistItem, TicketHistorique,
    TICKET_TYPE_CHOICES, PRIORITY_CHOICES, STATUS_CHOICES,
    TICKET_TYPE_PREVENTIVE, TICKET_TYPE_CORRECTIVE, TICKET_TYPE_URGENCE,
    PRIORITY_BASSE, PRIORITY_MOYENNE, PRIORITY_HAUTE, PRIORITY_CRITIQUE,
    STATUS_CREE, STATUS_ASSIGNE, STATUS_EN_COURS, STATUS_RESOLU, STATUS_CLOTURE,
)
from .serializers import (
    MaintenanceTicketSerializer, TicketTransitionSerializer,
    TicketAssignSerializer, ChecklistItemSerializer,
    ChecklistUpdateSerializer, TicketHistoriqueSerializer,
)


class MaintenanceTicketViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceTicket.objects.select_related(
        'cree_par', 'assigne_a', 'content_type'
    ).prefetch_related('checklist', 'historique').all()
    serializer_class = MaintenanceTicketSerializer
    permission_classes = [IsAdminOrTechnicianReadOnlyForConsultant]
    filterset_fields = ['type_ticket', 'priorite', 'statut', 'content_type']
    search_fields = ['titre', 'description', 'rapport_intervention']
    ordering_fields = ['date_creation', 'priorite', 'date_modification', 'date_cloture']
    ordering = ['-date_creation']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_admin_cns():
            if user.is_technician():
                qs = qs.filter(Q(assigne_a=user) | Q(cree_par=user) | Q(statut=STATUS_CREE))
            else:
                qs = qs.filter(statut__in=[STATUS_ASSIGNE, STATUS_EN_COURS, STATUS_RESOLU])
        assigne = self.request.query_params.get('assigne_a')
        if assigne:
            qs = qs.filter(assigne_a__id=assigne)
        cree_par = self.request.query_params.get('cree_par')
        if cree_par:
            qs = qs.filter(cree_par__id=cree_par)
        return qs

    def get_permissions(self):
        if self.action in ['destroy']:
            self.permission_classes = [IsAdminOrTechnician]
        return super().get_permissions()

    def perform_create(self, serializer):
        instance = serializer.save(cree_par=self.request.user)
        TicketHistorique.objects.create(
            ticket=instance,
            action=TicketHistorique.ACTION_CREATION,
            utilisateur=self.request.user,
            commentaire='Ticket créé via API',
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrTechnician])
    def transition(self, request, pk=None):
        ticket = self.get_object()
        serializer = TicketTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            ticket.changer_statut(
                serializer.validated_data['nouveau_statut'],
                utilisateur=request.user,
                commentaire=serializer.validated_data.get('commentaire', ''),
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(MaintenanceTicketSerializer(ticket, context={'request': request}).data)

    @action(detail=False, methods=['post'], permission_classes=[IsAdminOrTechnician], url_path='assign')
    def assign_ticket(self, request):
        ticket_id = request.data.get('ticket_id')
        technicien_id = request.data.get('technicien_id')
        commentaire = request.data.get('commentaire', '')
        if not ticket_id or not technicien_id:
            return Response(
                {'detail': 'ticket_id et technicien_id requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            ticket = MaintenanceTicket.objects.get(pk=ticket_id)
        except MaintenanceTicket.DoesNotExist:
            return Response({'detail': 'Ticket introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            technicien = User.objects.get(pk=technicien_id)
        except User.DoesNotExist:
            return Response({'detail': 'Technicien introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        ticket.assigner(technicien, utilisateur=request.user)
        return Response(MaintenanceTicketSerializer(ticket, context={'request': request}).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrTechnician])
    def update_checklist(self, request, pk=None):
        ticket = self.get_object()
        items = request.data.get('items', [])
        updated = 0
        for item_data in items:
            item_id = item_data.get('id')
            try:
                item = ticket.checklist.get(pk=item_id)
                if 'est_effectue' in item_data:
                    item.est_effectue = item_data['est_effectue']
                if 'commentaire' in item_data:
                    item.commentaire = item_data.get('commentaire') or ''
                item.save()
                updated += 1
            except ChecklistItem.DoesNotExist:
                continue
        TicketHistorique.objects.create(
            ticket=ticket,
            action=TicketHistorique.ACTION_MODIFICATION,
            utilisateur=request.user,
            commentaire=f'Mise à jour de la checklist: {updated} items modifiés.',
        )
        return Response({'detail': f'{updated} items mis à jour.'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrTechnician])
    def commenter(self, request, pk=None):
        ticket = self.get_object()
        texte = request.data.get('commentaire', '').strip()
        if not texte:
            return Response({'detail': 'Commentaire vide.'}, status=status.HTTP_400_BAD_REQUEST)
        hist = TicketHistorique.objects.create(
            ticket=ticket,
            action=TicketHistorique.ACTION_COMMENTAIRE,
            utilisateur=request.user,
            commentaire=texte,
        )
        return Response(TicketHistoriqueSerializer(hist).data, status=status.HTTP_201_CREATED)


class TicketDashboardStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = MaintenanceTicket.objects.all()
        if not request.user.is_admin_cns():
            if request.user.is_technician():
                qs = qs.filter(Q(assigne_a=request.user) | Q(cree_par=request.user))
        ouverts = qs.exclude(statut__in=[STATUS_RESOLU, STATUS_CLOTURE])
        critics_count = ouverts.filter(priorite=PRIORITY_CRITIQUE).count()
        urgents_count = ouverts.filter(type_ticket=TICKET_TYPE_URGENCE).count()
        data = {
            'total': qs.count(),
            'ouverts': ouverts.count(),
            'en_cours': qs.filter(statut=STATUS_EN_COURS).count(),
            'assignes': qs.filter(statut=STATUS_ASSIGNE).count(),
            'resolus': qs.filter(statut__in=[STATUS_RESOLU, STATUS_CLOTURE]).count(),
            'critics': critics_count,
            'urgents': urgents_count,
            'par_priorite': {
                p: qs.filter(priorite=p).count() for p, _ in PRIORITY_CHOICES
            },
            'par_type': {
                t: qs.filter(type_ticket=t).count() for t, _ in TICKET_TYPE_CHOICES
            },
            'par_statut': {
                s: qs.filter(statut=s).count() for s, _ in STATUS_CHOICES
            },
        }
        return Response(data)


class TicketChoicesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            'types': [{'value': v, 'label': l} for v, l in TICKET_TYPE_CHOICES],
            'priorites': [{'value': v, 'label': l} for v, l in PRIORITY_CHOICES],
            'statuts': [{'value': v, 'label': l} for v, l in STATUS_CHOICES],
        })
