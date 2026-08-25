from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from .models import (
    EquipmentVOR, EquipmentILS, EquipmentDME, EquipmentRadar, EquipmentVCS, MeasurementLog,
    STATUS_CHOICES,
)


class _BaseEquipmentSerializer(serializers.ModelSerializer):
    statut_label = serializers.CharField(source='get_statut_operationnel_display', read_only=True)
    type_label = serializers.SerializerMethodField()
    is_critique = serializers.SerializerMethodField()

    def get_type_label(self, obj):
        name = obj.__class__.__name__.replace('Equipment', '')
        return name.upper()

    def get_is_critique(self, obj):
        name = obj.__class__.__name__
        return name in ('EquipmentILS', 'EquipmentDME', 'EquipmentVOR')


class EquipmentVORSerializer(_BaseEquipmentSerializer):
    class Meta:
        model = EquipmentVOR
        fields = '__all__'

    def validate_frequence(self, value):
        if not (108.0 <= value <= 117.95):
            raise serializers.ValidationError('Fréquence VOR hors bande OACI (108.0-117.95 MHz).')
        step = round((value - 108.0) * 100, 3)
        if not (step == int(step) or abs(step - int(step) - 0.05) < 0.01):
            raise serializers.ValidationError('Fréquence VOR doit respecter les canaux de 50kHz.')
        return value

    def validate_taux_modulation_AM(self, value):
        if not (20 <= value <= 40):
            raise serializers.ValidationError('Taux modulation AM hors tolérance OACI (20-40%).')
        return value


class EquipmentILSSerializer(_BaseEquipmentSerializer):
    type_ils_label = serializers.CharField(source='get_type_ils_display', read_only=True)

    class Meta:
        model = EquipmentILS
        fields = '__all__'

    def validate_frequence_porteuse(self, value):
        type_ils = self.initial_data.get('type_ils') or (getattr(self.instance, 'type_ils', None) if self.instance else None)
        if type_ils == 'LOC' and not (108.0 <= value <= 111.95):
            raise serializers.ValidationError('Fréquence LOC hors bande (108.0-111.95 MHz).')
        if type_ils == 'GP' and not (329.3 <= value <= 335.0):
            raise serializers.ValidationError('Fréquence GP hors bande UHF (329.3-335.0 MHz).')
        return value

    def validate(self, attrs):
        ddm = attrs.get('ddm_nominale', getattr(self.instance, 'ddm_nominale', None))
        type_ils = attrs.get('type_ils', getattr(self.instance, 'type_ils', None))
        if ddm is not None and type_ils == 'LOC' and ddm > 0.20:
            raise serializers.ValidationError({'ddm_nominale': 'DDM LOC excessive (OACI ≤ 0.20 en alerte).'})
        return attrs


class EquipmentDMESerializer(_BaseEquipmentSerializer):
    canal_label = serializers.CharField(source='get_canal_display', read_only=True)
    mode_label = serializers.CharField(source='get_mode_fonctionnement_display', read_only=True)

    class Meta:
        model = EquipmentDME
        fields = '__all__'

    def validate(self, attrs):
        f_int = attrs.get('frequence_interrogation') or getattr(self.instance, 'frequence_interrogation', None)
        f_rep = attrs.get('frequence_reponse') or getattr(self.instance, 'frequence_reponse', None)
        canal = attrs.get('canal') or getattr(self.instance, 'canal', None)
        if f_int and f_rep and canal:
            delta = 63 if canal == 'X' else 60
            if abs(abs(f_rep - f_int) - delta) > 0.1:
                raise serializers.ValidationError(
                    'Décalage fréquence interrogation/réponse incorrect ({delta} MHz pour canal {canal}).'.format(delta=delta, canal=canal)
                )
        rendement = attrs.get('rendement_recent', getattr(self.instance, 'rendement_recent', None))
        if rendement is not None and rendement < 70:
            raise serializers.ValidationError({'rendement_recent': 'Rendement DME < 70% (seuil OACI).'})
        return attrs


class EquipmentRadarSerializer(_BaseEquipmentSerializer):
    type_radar_label = serializers.CharField(source='get_type_radar_display', read_only=True)

    class Meta:
        model = EquipmentRadar
        fields = '__all__'


class EquipmentVCSSerializer(_BaseEquipmentSerializer):
    codec_label = serializers.CharField(source='get_codec_display', read_only=True)
    protocole_label = serializers.CharField(source='get_protocole_display', read_only=True)

    class Meta:
        model = EquipmentVCS
        fields = '__all__'


class MeasurementLogSerializer(serializers.ModelSerializer):
    equipment_type_label = serializers.CharField(source='get_equipment_type_display', read_only=True)

    class Meta:
        model = MeasurementLog
        fields = '__all__'


class GenericEquipmentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    code_unique = serializers.CharField()
    nom = serializers.CharField()
    type = serializers.CharField()
    type_label = serializers.CharField()
    statut_operationnel = serializers.CharField()
    statut_label = serializers.CharField()
    is_critique = serializers.BooleanField()
    localisation_lat = serializers.FloatField(allow_null=True)
    localisation_lng = serializers.FloatField(allow_null=True)
    date_mise_en_service = serializers.DateField(allow_null=True)
    description = serializers.CharField(allow_null=True)
    details = serializers.DictField()


class EquipmentTypeChoicesSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()


class StatusChoicesSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()
