import json
import logging
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.dispatch import Signal

logger = logging.getLogger('audit')

User = get_user_model()

log_audit_event = Signal()


class AuditLog(models.Model):
    ACTION_LOGIN = 'LOGIN'
    ACTION_LOGOUT = 'LOGOUT'
    ACTION_LOGIN_FAILED = 'LOGIN_FAILED'

    ACTION_CREATE = 'CREATE'
    ACTION_UPDATE = 'UPDATE'
    ACTION_DELETE = 'DELETE'

    ACTION_FREQUENCY_CHANGE = 'FREQUENCY_CHANGE'
    ACTION_ASSIGNATION_TICKET = 'ASSIGNATION_TICKET'
    ACTION_TICKET_RESOLU = 'TICKET_RESOLU'
    ACTION_TICKET_CLOTURE = 'TICKET_CLOTURE'

    ACTION_USER_CREATED = 'USER_CREATED'
    ACTION_PERMISSION_CHANGED = 'PERMISSION_CHANGED'

    ACTION_CHOICES = [
        (ACTION_LOGIN, 'Connexion'),
        (ACTION_LOGOUT, 'Déconnexion'),
        (ACTION_LOGIN_FAILED, 'Échec connexion'),
        (ACTION_CREATE, 'Création'),
        (ACTION_UPDATE, 'Modification'),
        (ACTION_DELETE, 'Suppression'),
        (ACTION_FREQUENCY_CHANGE, 'Changement fréquence'),
        (ACTION_ASSIGNATION_TICKET, 'Assignation ticket'),
        (ACTION_TICKET_RESOLU, 'Ticket résolu'),
        (ACTION_TICKET_CLOTURE, 'Ticket clôturé'),
        (ACTION_USER_CREATED, 'Utilisateur créé'),
        (ACTION_PERMISSION_CHANGED, 'Changement de permission'),
    ]

    utilisateur = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='logs_audit', verbose_name=_('Utilisateur'),
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, verbose_name=_('Action'))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_('Horodatage'))
    adresse_ip = models.GenericIPAddressField(blank=True, null=True, verbose_name=_('Adresse IP'))
    user_agent = models.TextField(blank=True, null=True, verbose_name=_('User-Agent'))

    content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Type d\'objet'),
    )
    object_id = models.PositiveIntegerField(null=True, blank=True, verbose_name=_('ID objet'))
    objet = GenericForeignKey('content_type', 'object_id')
    description = models.CharField(max_length=500, blank=True, null=True, verbose_name=_('Description'))

    ancienne_valeur = models.JSONField(blank=True, null=True, verbose_name=_('Ancienne valeur'))
    nouvelle_valeur = models.JSONField(blank=True, null=True, verbose_name=_('Nouvelle valeur'))

    endpoint = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Endpoint API'))
    methode_http = models.CharField(max_length=10, blank=True, null=True, verbose_name=_('Méthode HTTP'))

    class Meta:
        verbose_name = _('Journal d\'Audit')
        verbose_name_plural = _('Journaux d\'Audit')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['action', 'utilisateur']),
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f'[{self.timestamp:%Y-%m-%d %H:%M}] {self.get_action_display()} par {self.utilisateur}'

    @classmethod
    def log(cls, action, utilisateur=None, ip=None, user_agent=None,
            description=None, content_type=None, object_id=None,
            ancienne_valeur=None, nouvelle_valeur=None,
            endpoint=None, methode_http=None):
        try:
            with transaction.atomic():
                return cls.objects.create(
                    utilisateur=utilisateur,
                    action=action,
                    adresse_ip=ip,
                    user_agent=user_agent,
                    description=description,
                    content_type=content_type,
                    object_id=object_id,
                    ancienne_valeur=cls._to_json_safe(ancienne_valeur),
                    nouvelle_valeur=cls._to_json_safe(nouvelle_valeur),
                    endpoint=endpoint,
                    methode_http=methode_http,
                )
        except Exception as exc:
            logger.error(f'Erreur enregistrement audit: {exc}')
            return None

    @staticmethod
    def _to_json_safe(value):
        if value is None:
            return None
        if isinstance(value, (dict, list, str, int, float, bool)):
            return value
        try:
            return json.loads(json.dumps(value, default=str, ensure_ascii=False))
        except Exception:
            return str(value)
