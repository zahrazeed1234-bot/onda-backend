from django.contrib import admin
from .models import (
    EquipmentVOR, EquipmentILS, EquipmentDME, EquipmentRadar, EquipmentVCS, MeasurementLog
)


class EquipmentBaseAdmin(admin.ModelAdmin):
    list_display = ('code_unique', 'nom', 'statut_operationnel', 'date_mise_en_service')
    list_filter = ('statut_operationnel',)
    search_fields = ('code_unique', 'nom', 'description')
    readonly_fields = ('date_creation', 'date_modification')


@admin.register(EquipmentVOR)
class EquipmentVORAdmin(EquipmentBaseAdmin):
    fieldsets = (
        (None, {'fields': ('nom', 'code_unique', 'statut_operationnel', 'date_mise_en_service', 'description')}),
        ('Localisation', {'fields': ('localisation_lat', 'localisation_lng')}),
        ('Paramètres VOR', {
            'fields': ('frequence', 'taux_modulation_AM', 'indice_FM', 'puissance_erp', 'identifiant_morse'),
        }),
        ('Métadonnées', {'fields': ('date_creation', 'date_modification')}),
    )


@admin.register(EquipmentILS)
class EquipmentILSAdmin(EquipmentBaseAdmin):
    fieldsets = (
        (None, {'fields': ('nom', 'code_unique', 'statut_operationnel', 'date_mise_en_service', 'description')}),
        ('Localisation', {'fields': ('localisation_lat', 'localisation_lng')}),
        ('Paramètres ILS', {
            'fields': (
                'type_ils', 'frequence_porteuse', 'taux_modulation_90Hz', 'taux_modulation_150Hz',
                'ddm_nominale', 'sdm_nominale', 'course', 'identifiant',
            ),
        }),
        ('Métadonnées', {'fields': ('date_creation', 'date_modification')}),
    )


@admin.register(EquipmentDME)
class EquipmentDMEAdmin(EquipmentBaseAdmin):
    fieldsets = (
        (None, {'fields': ('nom', 'code_unique', 'statut_operationnel', 'date_mise_en_service', 'description')}),
        ('Localisation', {'fields': ('localisation_lat', 'localisation_lng')}),
        ('Paramètres DME', {
            'fields': (
                'canal', 'numero_canal', 'frequence_interrogation', 'frequence_reponse',
                'retard_systematique', 'puissance_sortie', 'mode_fonctionnement', 'jitter_spec', 'rendement_recent',
            ),
        }),
        ('Métadonnées', {'fields': ('date_creation', 'date_modification')}),
    )


@admin.register(EquipmentRadar)
class EquipmentRadarAdmin(EquipmentBaseAdmin):
    fieldsets = (
        (None, {'fields': ('nom', 'code_unique', 'statut_operationnel', 'date_mise_en_service', 'description')}),
        ('Localisation', {'fields': ('localisation_lat', 'localisation_lng')}),
        ('Paramètres Radar', {
            'fields': ('type_radar', 'frequence_bande', 'portee_max', 'mode_s_actif', 'traitement_oldi', 'puissance_emetteur'),
        }),
        ('Métadonnées', {'fields': ('date_creation', 'date_modification')}),
    )


@admin.register(EquipmentVCS)
class EquipmentVCSAdmin(EquipmentBaseAdmin):
    fieldsets = (
        (None, {'fields': ('nom', 'code_unique', 'statut_operationnel', 'date_mise_en_service', 'description')}),
        ('Localisation', {'fields': ('localisation_lat', 'localisation_lng')}),
        ('Paramètres VCS', {
            'fields': ('site_radio', 'codec', 'protocole', 'canaux_vhf', 'voip_active', 'adresse_ip'),
        }),
        ('Métadonnées', {'fields': ('date_creation', 'date_modification')}),
    )


@admin.register(MeasurementLog)
class MeasurementLogAdmin(admin.ModelAdmin):
    list_display = ('equipment_type', 'equipment_id', 'parametre', 'valeur', 'unite', 'date_mesure')
    list_filter = ('equipment_type', 'parametre')
    search_fields = ('parametre', 'commentaire')
    readonly_fields = ('date_mesure',)
