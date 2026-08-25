from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from accounts.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from audit.signals import log_audit_event


TICKET_TYPE_PREVENTIVE = 'PREVENTIVE'
TICKET_TYPE_CORRECTIVE = 'CORRECTIVE'
TICKET_TYPE_URGENCE = 'URGENCE'

TICKET_TYPE_CHOICES = [
    (TICKET_TYPE_PREVENTIVE, 'Maintenance Préventive'),
    (TICKET_TYPE_CORRECTIVE, 'Maintenance Corrective'),
    (TICKET_TYPE_URGENCE, 'Intervention Urgence'),
]

PRIORITY_BASSE = 'BASSE'
PRIORITY_MOYENNE = 'MOYENNE'
PRIORITY_HAUTE = 'HAUTE'
PRIORITY_CRITIQUE = 'CRITIQUE'

PRIORITY_CHOICES = [
    (PRIORITY_BASSE, 'Basse'),
    (PRIORITY_MOYENNE, 'Moyenne'),
    (PRIORITY_HAUTE, 'Haute'),
    (PRIORITY_CRITIQUE, 'Critique'),
]

STATUS_CREE = 'CREE'
STATUS_ASSIGNE = 'ASSIGNE'
STATUS_EN_COURS = 'EN_COURS'
STATUS_RESOLU = 'RESOLU'
STATUS_CLOTURE = 'CLOTURE'

STATUS_CHOICES = [
    (STATUS_CREE, 'Créé'),
    (STATUS_ASSIGNE, 'Assigné'),
    (STATUS_EN_COURS, 'En cours'),
    (STATUS_RESOLU, 'Résolu'),
    (STATUS_CLOTURE, 'Clôturé'),
]

TRANSITIONS = {
    STATUS_CREE: [STATUS_ASSIGNE, STATUS_CLOTURE],
    STATUS_ASSIGNE: [STATUS_EN_COURS, STATUS_CREE],
    STATUS_EN_COURS: [STATUS_RESOLU, STATUS_ASSIGNE],
    STATUS_RESOLU: [STATUS_CLOTURE, STATUS_EN_COURS],
    STATUS_CLOTURE: [],
}


class MaintenanceTicket(models.Model):
    titre = models.CharField(max_length=250, verbose_name=_('Titre'))
    description = models.TextField(verbose_name=_('Description'))
    type_ticket = models.CharField(max_length=20, choices=TICKET_TYPE_CHOICES, verbose_name=_('Type'))
    priorite = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_MOYENNE, verbose_name=_('Priorité'))
    statut = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CREE, verbose_name=_('Statut'))

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Type équipement'))
    object_id = models.PositiveIntegerField(null=True, blank=True, verbose_name=_('ID équipement'))
    equipement = GenericForeignKey('content_type', 'object_id')

    cree_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets_crees', verbose_name=_('Créé par'))
    assigne_a = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets_assignes', verbose_name=_('Assigné à'))
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name=_('Date de création'))
    date_modification = models.DateTimeField(auto_now=True, verbose_name=_('Date de modification'))
    date_cloture = models.DateTimeField(null=True, blank=True, verbose_name=_('Date de clôture'))
    rapport_intervention = models.TextField(blank=True, null=True, verbose_name=_('Rapport d\'intervention'))

    class Meta:
        verbose_name = _('Ticket de Maintenance')
        verbose_name_plural = _('Tickets de Maintenance')
        ordering = ['-priorite', '-date_creation']
        indexes = [
            models.Index(fields=['statut', 'priorite']),
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f'Ticket #{self.id} - {self.titre}'

    def get_possible_transitions(self):
        return TRANSITIONS.get(self.statut, [])

    def changer_statut(self, nouveau_statut, utilisateur=None, commentaire=''):
        if nouveau_statut not in self.get_possible_transitions():
            raise ValueError(f'Transition {self.statut} -> {nouveau_statut} non autorisée')
        ancien_statut = self.statut
        self.statut = nouveau_statut
        if nouveau_statut == STATUS_CLOTURE:
            from django.utils import timezone
            self.date_cloture = timezone.now()
        self.save()
        TicketHistorique.objects.create(
            ticket=self,
            action='CHANGEMENT_STATUT',
            utilisateur=utilisateur,
            commentaire=commentaire,
            ancienne_valeur=ancien_statut,
            nouvelle_valeur=nouveau_statut,
        )
        return self

    def assigner(self, technicien, utilisateur=None):
        self.assigne_a = technicien
        if self.statut == STATUS_CREE:
            self.statut = STATUS_ASSIGNE
        self.save()
        TicketHistorique.objects.create(
            ticket=self,
            action='ASSIGNATION',
            utilisateur=utilisateur,
            commentaire=f'Ticket assigné à {technicien}',
            nouvelle_valeur=str(technicien),
        )
        log_audit_event.send(
            sender=self.__class__,
            action='ASSIGNATION_TICKET',
            user=utilisateur or self.cree_par,
            instance=self,
            nouvelle_valeur=str(technicien),
        )
        return self


class ChecklistItem(models.Model):
    ticket = models.ForeignKey(MaintenanceTicket, on_delete=models.CASCADE, related_name='checklist', verbose_name=_('Ticket'))
    libelle = models.CharField(max_length=300, verbose_name=_('Libellé'))
    est_effectue = models.BooleanField(default=False, verbose_name=_('Effectué'))
    ordre = models.PositiveIntegerField(default=0, verbose_name=_('Ordre'))
    commentaire = models.TextField(blank=True, null=True, verbose_name=_('Commentaire'))

    class Meta:
        verbose_name = _('Item Checklist')
        verbose_name_plural = _('Items Checklist')
        ordering = ['ordre', 'id']

    def __str__(self):
        return f'[{self.ticket.id}] {self.libelle}'


class TicketHistorique(models.Model):
    ACTION_CREATION = 'CREATION'
    ACTION_MODIFICATION = 'MODIFICATION'
    ACTION_ASSIGNATION = 'ASSIGNATION'
    ACTION_CHANGEMENT_STATUT = 'CHANGEMENT_STATUT'
    ACTION_COMMENTAIRE = 'COMMENTAIRE'

    ACTION_CHOICES = [
        (ACTION_CREATION, 'Création'),
        (ACTION_MODIFICATION, 'Modification'),
        (ACTION_ASSIGNATION, 'Assignation'),
        (ACTION_CHANGEMENT_STATUT, 'Changement de statut'),
        (ACTION_COMMENTAIRE, 'Commentaire'),
    ]

    ticket = models.ForeignKey(MaintenanceTicket, on_delete=models.CASCADE, related_name='historique', verbose_name=_('Ticket'))
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, verbose_name=_('Action'))
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Utilisateur'))
    commentaire = models.TextField(blank=True, null=True, verbose_name=_('Commentaire'))
    ancienne_valeur = models.TextField(blank=True, null=True, verbose_name=_('Ancienne valeur'))
    nouvelle_valeur = models.TextField(blank=True, null=True, verbose_name=_('Nouvelle valeur'))
    date = models.DateTimeField(auto_now_add=True, verbose_name=_('Date'))

    class Meta:
        verbose_name = _('Historique Ticket')
        verbose_name_plural = _('Historiques Ticket')
        ordering = ['-date']

    def __str__(self):
        return f'{self.get_action_display()} - Ticket #{self.ticket.id} ({self.date:%Y-%m-%d %H:%M})'


DEFAULT_CHECKLISTS = {
    'EquipmentILS': [
        ('Vérifier l\'alimentation électrique et les protections',),
        ('Contrôler la phase VHF entre signaux CSB et SBO',),
        ('Mesurer la DDM dans l\'axe de référence (seuil OACI ±DDM)',),
        ('Vérifier le niveau du signal CSB (portée)',),
        ('Mesurer les taux de modulation 90Hz / 150Hz',),
        ('Vérifier l\'absence d\'obstacle en zone critique et sensible',),
        ('Contrôler l\'intégrité du code Morse / identifiant',),
        ('Vérifier la synchronisation avec le DME associé',),
        ('Mesurer la SDM (profondeur de modulation somme)',),
        ('Vérifier les alarmes moniteur (BITE)',),
    ],
    'EquipmentVOR': [
        ('Contrôler l\'état de l\'antenne et du feeder',),
        ('Mesurer la fréquence porteuse (108-118MHz)',),
        ('Vérifier le taux de modulation AM 30%',),
        ('Contrôler les signaux 30Hz REF et VAR (indice FM=16)',),
        ('Mesurer la puissance ERP',),
        ('Vérifier l\'identifiant Morse',),
        ('Tester la commande de changement de fréquence (Standby)',),
        ('Vérifier les tests BITE internes',),
    ],
    'EquipmentDME': [
        ('Contrôler la fréquence interrogation / réponse',),
        ('Mesurer le retard systématique (50µs ou 56µs)',),
        ('Vérifier le rendement des réponses (>70% OACI)',),
        ('Mesurer le jitter de la réponse (< spécification)',),
        ('Contrôler la puissance de sortie',),
        ('Vérifier la commutation canal X/Y',),
        ('Tester les modes Search / Track',),
        ('Vérifier l\'interface avec LOC/GP (ILS)',),
    ],
    'EquipmentRadar': [
        ('Vérifier le système de refroidissement (climatisation armoire)',),
        ('Contrôler la rotation de l\'antenne et son moteur',),
        ('Mesurer la puissance RF émise',),
        ('Vérifier les niveaux de bruit et la sensibilité',),
        ('Contrôler la portée nominale (PSR/SSR)',),
        ('Tester la chaîne de traitement (OLDI si concerné)',),
        ('Vérifier le Mode S et ADS-B (le cas échéant)',),
    ],
    'EquipmentVCS': [
        ('Contrôler la connectivité IP / VoIP',),
        ('Vérifier l\'état des cartes codec (G.711)',),
        ('Tester les canaux VHF (réception/émission)',),
        ('Contrôler le protocole ED-137 (SIP/RTP)',),
        ('Vérifier les alarmes SNMP',),
        ('Tester la commutation vers le site radio secours',),
    ],
}


@receiver(post_save, sender=MaintenanceTicket)
def generer_checklist_par_defaut(sender, instance, created, **kwargs):
    if created and instance.content_type:
        class_name = instance.content_type.model_class().__name__
        items = DEFAULT_CHECKLISTS.get(class_name)
        if items:
            checklist_items = []
            for ordre, item_data in enumerate(items):
                libelle = item_data[0] if isinstance(item_data, tuple) else item_data
                checklist_items.append(ChecklistItem(
                    ticket=instance,
                    libelle=libelle,
                    ordre=ordre,
                    est_effectue=False,
                ))
            if checklist_items:
                ChecklistItem.objects.bulk_create(checklist_items)
