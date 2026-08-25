import json
import logging
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save, post_delete
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.contrib.auth import get_user_model
from .models import AuditLog, log_audit_event

logger = logging.getLogger('audit')
User = get_user_model()

FREQUENCY_FIELDS = {'frequence', 'frequence_porteuse', 'frequence_interrogation', 'frequence_reponse'}


def _model_changed_fields(instance, previous):
    changed = {}
    model_fields = {f.name for f in instance._meta.get_fields() if f.concrete}
    for field in model_fields:
        old = getattr(previous, field, None)
        new = getattr(instance, field, None)
        if old != new:
            try:
                changed[field] = {'old': _serializable(old), 'new': _serializable(new)}
            except Exception:
                pass
    return changed


def _serializable(v):
    if hasattr(v, 'isoformat'):
        return v.isoformat()
    if isinstance(v, (dict, list, str, int, float, bool)) or v is None:
        return v
    return str(v)


@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    ip = request.META.get('REMOTE_ADDR') if request else None
    ua = request.META.get('HTTP_USER_AGENT') if request else None
    AuditLog.log(
        action=AuditLog.ACTION_LOGIN,
        utilisateur=user,
        ip=ip,
        user_agent=ua,
        description=f'Connexion réussie de {user}',
    )


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    ip = request.META.get('REMOTE_ADDR') if request else None
    ua = request.META.get('HTTP_USER_AGENT') if request else None
    AuditLog.log(
        action=AuditLog.ACTION_LOGOUT,
        utilisateur=user,
        ip=ip,
        user_agent=ua,
        description=f'Déconnexion de {user}',
    )


@receiver(user_login_failed)
def on_login_failed(sender, credentials, request=None, **kwargs):
    ip = request.META.get('REMOTE_ADDR') if request else None
    ua = request.META.get('HTTP_USER_AGENT') if request else None
    AuditLog.log(
        action=AuditLog.ACTION_LOGIN_FAILED,
        utilisateur=None,
        ip=ip,
        user_agent=ua,
        description=f'Échec connexion pour {credentials.get("username", "inconnu")}',
    )


@receiver(post_save, sender=User)
def on_user_saved(sender, instance, created, raw, **kwargs):
    if raw:
        return
    action = AuditLog.ACTION_USER_CREATED if created else AuditLog.ACTION_UPDATE
    ct = ContentType.objects.get_for_model(sender)
    AuditLog.log(
        action=action,
        utilisateur=instance,
        description=f'Utilisateur {"créé" if created else "modifié"}: {instance.username}',
        content_type=ct,
        object_id=instance.pk,
        nouvelle_valeur={'username': instance.username, 'role': instance.role},
    )


_equipment_cache = {}


def _get_previous_equipment(sender, instance):
    key = (sender, instance.pk)
    if instance.pk and key in _equipment_cache:
        return _equipment_cache.pop(key)
    return None


@receiver(pre_save)
def cache_equipment_previous(sender, instance, raw, **kwargs):
    if raw or not instance.pk:
        return
    name = sender.__name__
    if name.startswith('Equipment') or name == 'MaintenanceTicket':
        try:
            _equipment_cache[(sender, instance.pk)] = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            pass


@receiver(post_save)
def audit_equipment_and_ticket(sender, instance, created, raw, **kwargs):
    if raw:
        return
    name = sender.__name__
    if not (name.startswith('Equipment') or name == 'MaintenanceTicket'):
        return
    previous = _get_previous_equipment(sender, instance)
    ct = ContentType.objects.get_for_model(sender)
    if created:
        AuditLog.log(
            action=AuditLog.ACTION_CREATE,
            description=f'Création: {instance}',
            content_type=ct,
            object_id=instance.pk,
            nouvelle_valeur=str(instance),
        )
        return
    if previous is None:
        return
    changed = _model_changed_fields(instance, previous)
    if not changed:
        return
    changed_fields = set(changed.keys())
    action = AuditLog.ACTION_UPDATE
    if FREQUENCY_FIELDS & changed_fields:
        action = AuditLog.ACTION_FREQUENCY_CHANGE
    if name == 'MaintenanceTicket' and 'statut' in changed:
        old_s = changed['statut']['old']
        new_s = changed['statut']['new']
        if new_s == 'RESOLU':
            action = AuditLog.ACTION_TICKET_RESOLU
        elif new_s == 'CLOTURE':
            action = AuditLog.ACTION_TICKET_CLOTURE
    AuditLog.log(
        action=action,
        description=f'Modification {name}: {instance}',
        content_type=ct,
        object_id=instance.pk,
        ancienne_valeur={k: v['old'] for k, v in changed.items()},
        nouvelle_valeur={k: v['new'] for k, v in changed.items()},
    )


@receiver(post_delete)
def audit_delete(sender, instance, **kwargs):
    name = sender.__name__
    if not (name.startswith('Equipment') or name == 'MaintenanceTicket'):
        return
    ct = ContentType.objects.get_for_model(sender)
    AuditLog.log(
        action=AuditLog.ACTION_DELETE,
        description=f'Suppression: {instance}',
        content_type=ct,
        object_id=instance.pk,
        ancienne_valeur=str(instance),
    )


@receiver(log_audit_event)
def on_custom_audit_event(sender, action, user=None, instance=None,
                          ancienne_valeur=None, nouvelle_valeur=None,
                          description=None, **kwargs):
    ct = None
    oid = None
    if instance is not None:
        try:
            ct = ContentType.objects.get_for_model(instance.__class__)
            oid = instance.pk
        except Exception:
            pass
    AuditLog.log(
        action=action,
        utilisateur=user,
        description=description,
        content_type=ct,
        object_id=oid,
        ancienne_valeur=ancienne_valeur,
        nouvelle_valeur=nouvelle_valeur,
    )
