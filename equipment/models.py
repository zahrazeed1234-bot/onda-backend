from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


STATUS_OK = 'OK'
STATUS_DEGRADE = 'DEGRADE'
STATUS_HS = 'HS'

STATUS_CHOICES = [
    (STATUS_OK, 'Opérationnel'),
    (STATUS_DEGRADE, 'Dégradé'),
    (STATUS_HS, 'Hors Service'),
]

EQUIPMENT_TYPES = [
    ('VOR', 'VOR - VHF Omnidirectional Range'),
    ('ILS', 'ILS - Instrument Landing System'),
    ('DME', 'DME - Distance Measuring Equipment'),
    ('RADAR', 'Radar (PSR/SSR/ADS-B)'),
    ('VCS', 'VCS - Voice Communication System'),
]


class BaseEquipment(models.Model):
    nom = models.CharField(max_length=200, verbose_name=_('Nom'))
    code_unique = models.CharField(max_length=50, unique=True, verbose_name=_('Code Unique'))
    localisation_lat = models.FloatField(blank=True, null=True, verbose_name=_('Latitude'))
    localisation_lng = models.FloatField(blank=True, null=True, verbose_name=_('Longitude'))
    statut_operationnel = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_OK,
        verbose_name=_('Statut Opérationnel'),
    )
    date_mise_en_service = models.DateField(blank=True, null=True, verbose_name=_('Date de mise en service'))
    description = models.TextField(blank=True, null=True, verbose_name=_('Description'))
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name=_('Date de création'))
    date_modification = models.DateTimeField(auto_now=True, verbose_name=_('Date de modification'))

    class Meta:
        abstract = True
        ordering = ['code_unique']

    def __str__(self):
        return f'{self.code_unique} - {self.nom}'

    @property
    def type_equipement(self):
        return self.__class__.__name__.replace('Equipment', '').upper()

    @property
    def is_critique(self):
        return self.type_equipement in ('ILS', 'DME', 'VOR')


class EquipmentVOR(BaseEquipment):
    frequence = models.FloatField(
        validators=[MinValueValidator(108.0), MaxValueValidator(117.95)],
        verbose_name=_('Fréquence (MHz)'),
        help_text=_('Plage: 108.0 - 117.95 MHz'),
    )
    taux_modulation_AM = models.FloatField(
        default=30.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_('Taux de modulation AM (%)'),
        help_text=_('Valeur nominale: 30%'),
    )
    indice_FM = models.FloatField(
        default=16.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_('Indice de modulation FM'),
        help_text=_('Valeur nominale: 16 (signaux 30Hz REF/VAR)'),
    )
    puissance_erp = models.FloatField(blank=True, null=True, verbose_name=_('Puissance ERP (W)'))
    identifiant_morse = models.CharField(max_length=10, blank=True, null=True, verbose_name=_('Identifiant Morse'))

    class Meta(BaseEquipment.Meta):
        verbose_name = _('Équipement VOR')
        verbose_name_plural = _('Équipements VOR')


class EquipmentILS(BaseEquipment):
    TYPE_LOC = 'LOC'
    TYPE_GP = 'GP'

    TYPE_ILS_CHOICES = [
        (TYPE_LOC, 'Localizer (LOC)'),
        (TYPE_GP, 'Glide Path (GP)'),
    ]

    type_ils = models.CharField(max_length=10, choices=TYPE_ILS_CHOICES, verbose_name=_('Type ILS'))
    frequence_porteuse = models.FloatField(verbose_name=_('Fréquence porteuse (MHz)'))
    taux_modulation_90Hz = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_('Taux de modulation 90Hz (%)'),
    )
    taux_modulation_150Hz = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_('Taux de modulation 150Hz (%)'),
    )
    ddm_nominale = models.FloatField(
        default=0.155,
        validators=[MinValueValidator(0), MaxValueValidator(0.5)],
        verbose_name=_('DDM nominale'),
        help_text=_('Ex: 0.155 pour LOC, ~0.12 pour GP'),
    )
    sdm_nominale = models.FloatField(
        default=0.40,
        validators=[MinValueValidator(0), MaxValueValidator(1.0)],
        verbose_name=_('SDM nominale'),
        help_text=_('Profondeur de modulation de somme'),
    )
    course = models.FloatField(blank=True, null=True, verbose_name=_('Course magnétique (°)'))
    identifiant = models.CharField(max_length=10, blank=True, null=True, verbose_name=_('Identifiant'))

    class Meta(BaseEquipment.Meta):
        verbose_name = _('Équipement ILS')
        verbose_name_plural = _('Équipements ILS')


class EquipmentDME(BaseEquipment):
    CANAL_X = 'X'
    CANAL_Y = 'Y'
    CANAL_CHOICES = [(CANAL_X, 'Canal X'), (CANAL_Y, 'Canal Y')]

    MODE_SEARCH = 'SEARCH'
    MODE_TRACK = 'TRACK'
    MODE_CHOICES = [(MODE_SEARCH, 'Search'), (MODE_TRACK, 'Track')]

    canal = models.CharField(max_length=5, choices=CANAL_CHOICES, verbose_name=_('Canal'))
    numero_canal = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(126)],
        verbose_name=_('Numéro de canal (1-126)'),
    )
    frequence_interrogation = models.FloatField(
        validators=[MinValueValidator(962), MaxValueValidator(1213)],
        verbose_name=_('Fréquence interrogation (MHz)'),
        help_text=_('Bande: 962-1213 MHz'),
    )
    frequence_reponse = models.FloatField(
        validators=[MinValueValidator(962), MaxValueValidator(1213)],
        verbose_name=_('Fréquence réponse (MHz)'),
    )
    retard_systematique = models.FloatField(
        choices=[(50, '50 µs'), (56, '56 µs')],
        default=50,
        verbose_name=_('Retard systématique (µs)'),
    )
    puissance_sortie = models.FloatField(blank=True, null=True, verbose_name=_('Puissance de sortie (W)'))
    mode_fonctionnement = models.CharField(
        max_length=10, choices=MODE_CHOICES, default=MODE_TRACK, verbose_name=_('Mode de fonctionnement')
    )
    jitter_spec = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        verbose_name=_('Jitter maximal (µs)'),
    )
    rendement_recent = models.FloatField(
        default=85.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_('Rendement récent (%)'),
        help_text=_('Seuil OACI: > 70%'),
    )

    class Meta(BaseEquipment.Meta):
        verbose_name = _('Équipement DME')
        verbose_name_plural = _('Équipements DME')


class EquipmentRadar(BaseEquipment):
    TYPE_PSR = 'PSR'
    TYPE_SSR = 'SSR'
    TYPE_ADSB = 'ADS-B'
    TYPE_CHOICES = [
        (TYPE_PSR, 'PSR - Primary Surveillance Radar'),
        (TYPE_SSR, 'SSR - Secondary Surveillance Radar'),
        (TYPE_ADSB, 'ADS-B - Automatic Dependent Surveillance-Broadcast'),
    ]

    type_radar = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name=_('Type de Radar'))
    frequence_bande = models.CharField(max_length=20, verbose_name=_('Bande de fréquence'))
    portee_max = models.FloatField(
        validators=[MinValueValidator(0)],
        verbose_name=_('Portée maximale (NM)'),
    )
    mode_s_actif = models.BooleanField(default=False, verbose_name=_('Mode S actif'))
    traitement_oldi = models.BooleanField(default=False, verbose_name=_('Traitement OLDI'))
    puissance_emetteur = models.FloatField(blank=True, null=True, verbose_name=_('Puissance émetteur (kW)'))

    class Meta(BaseEquipment.Meta):
        verbose_name = _('Équipement Radar')
        verbose_name_plural = _('Équipements Radar')


class EquipmentVCS(BaseEquipment):
    PROTO_ED137 = 'ED-137'
    PROTO_SIP = 'SIP'
    PROTO_CHOICES = [(PROTO_ED137, 'ED-137 (EUROCAE)'), (PROTO_SIP, 'SIP (RFC 3261)')]

    CODEC_G711A = 'G.711A'
    CODEC_G711U = 'G.711U'
    CODEC_G729 = 'G.729'
    CODEC_CHOICES = [
        (CODEC_G711A, 'G.711 A-law'),
        (CODEC_G711U, 'G.711 µ-law'),
        (CODEC_G729, 'G.729'),
    ]

    site_radio = models.CharField(max_length=200, verbose_name=_('Site radio associé'))
    codec = models.CharField(max_length=20, choices=CODEC_CHOICES, default=CODEC_G711A, verbose_name=_('Codec audio'))
    protocole = models.CharField(max_length=20, choices=PROTO_CHOICES, default=PROTO_ED137, verbose_name=_('Protocole'))
    canaux_vhf = models.IntegerField(default=0, verbose_name=_('Nombre canaux VHF'))
    voip_active = models.BooleanField(default=True, verbose_name=_('VoIP activé'))
    adresse_ip = models.GenericIPAddressField(blank=True, null=True, verbose_name=_('Adresse IP du contrôleur'))

    class Meta(BaseEquipment.Meta):
        verbose_name = _('Équipement VCS')
        verbose_name_plural = _('Équipements VCS')


class MeasurementLog(models.Model):
    EQUIPMENT_CLASS_CHOICES = [
        ('EquipmentVOR', 'VOR'),
        ('EquipmentILS', 'ILS'),
        ('EquipmentDME', 'DME'),
        ('EquipmentRadar', 'Radar'),
        ('EquipmentVCS', 'VCS'),
    ]

    equipment_type = models.CharField(max_length=50, choices=EQUIPMENT_CLASS_CHOICES)
    equipment_id = models.IntegerField()
    date_mesure = models.DateTimeField(auto_now_add=True, verbose_name=_('Date de mesure'))
    parametre = models.CharField(max_length=100, verbose_name=_('Paramètre mesuré'))
    valeur = models.FloatField(verbose_name=_('Valeur'))
    unite = models.CharField(max_length=20, blank=True, null=True, verbose_name=_('Unité'))
    commentaire = models.TextField(blank=True, null=True, verbose_name=_('Commentaire'))

    class Meta:
        verbose_name = _('Journal de mesure')
        verbose_name_plural = _('Journaux de mesure')
        ordering = ['-date_mesure']
        indexes = [
            models.Index(fields=['equipment_type', 'equipment_id', 'parametre']),
            models.Index(fields=['-date_mesure']),
        ]

    def __str__(self):
        return f'{self.equipment_type} #{self.equipment_id} - {self.parametre} = {self.valeur} ({self.date_mesure:%Y-%m-%d})'
