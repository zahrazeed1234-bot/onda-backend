from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from accounts.models import User
from accounts.serializers import UserSummarySerializer
from .models import (
    MaintenanceTicket, ChecklistItem, TicketHistorique,
    TICKET_TYPE_CHOICES, PRIORITY_CHOICES, STATUS_CHOICES,
    STATUS_CREE, STATUS_ASSIGNE,
)


class ChecklistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistItem
        fields = '__all__'
        read_only_fields = ['ticket']


class TicketHistoriqueSerializer(serializers.ModelSerializer):
    action_label = serializers.CharField(source='get_action_display', read_only=True)
    utilisateur_info = UserSummarySerializer(source='utilisateur', read_only=True)

    class Meta:
        model = TicketHistorique
        fields = '__all__'


class MaintenanceTicketSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source='get_type_ticket_display', read_only=True)
    priorite_label = serializers.CharField(source='get_priorite_display', read_only=True)
    statut_label = serializers.CharField(source='get_statut_display', read_only=True)
    cree_par_info = UserSummarySerializer(source='cree_par', read_only=True)
    assigne_a_info = UserSummarySerializer(source='assigne_a', read_only=True)
    checklist = ChecklistItemSerializer(many=True, read_only=True)
    historique = TicketHistoriqueSerializer(many=True, read_only=True)
    content_type_label = serializers.SerializerMethodField()
    equipement_info = serializers.SerializerMethodField()
    possible_transitions = serializers.SerializerMethodField()

    class Meta:
        model = MaintenanceTicket
        fields = '__all__'
        read_only_fields = ['cree_par', 'date_creation', 'date_modification', 'date_cloture']

    def get_content_type_label(self, obj):
        if obj.content_type:
            return obj.content_type.model_class().__name__.replace('Equipment', '').upper()
        return None

    def get_equipement_info(self, obj):
        if obj.content_type and obj.object_id:
            try:
                eq = obj.content_type.get_object_for_this_type(pk=obj.object_id)
                return {
                    'id': eq.pk,
                    'code_unique': getattr(eq, 'code_unique', None),
                    'nom': getattr(eq, 'nom', None),
                    'statut': getattr(eq, 'statut_operationnel', None),
                }
            except Exception:
                return None
        return None

    def get_possible_transitions(self, obj):
        return [
            {'value': s, 'label': next((l for v, l in STATUS_CHOICES if v == s), s)}
            for s in obj.get_possible_transitions()
        ]

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['cree_par'] = request.user
        assigne_a = validated_data.pop('assigne_a', None)
        instance = super().create(validated_data)
        if assigne_a is not None:
            utilisateur = request.user if (request and hasattr(request, 'user')) else None
            instance.assigner(assigne_a, utilisateur=utilisateur)
            instance.refresh_from_db()
        return instance

    def update(self, instance, validated_data):
        request = self.context.get('request')
        assigne_a = validated_data.pop('assigne_a', None)
        old_assigne = instance.assigne_a
        instance = super().update(instance, validated_data)
        if assigne_a is not None and (old_assigne is None or old_assigne.pk != assigne_a.pk):
            utilisateur = request.user if (request and hasattr(request, 'user')) else None
            instance.assigner(assigne_a, utilisateur=utilisateur)
            instance.refresh_from_db()
        return instance


class TicketTransitionSerializer(serializers.Serializer):
    nouveau_statut = serializers.ChoiceField(choices=STATUS_CHOICES)
    commentaire = serializers.CharField(required=False, allow_blank=True)


class TicketAssignSerializer(serializers.Serializer):
    technicien_id = serializers.IntegerField()
    commentaire = serializers.CharField(required=False, allow_blank=True)


class ChecklistUpdateSerializer(serializers.Serializer):
    items = serializers.ListField(child=serializers.DictField())


class TicketChoicesSerializer(serializers.Serializer):
    types = serializers.ListField()
    priorites = serializers.ListField()
    statuts = serializers.ListField()
