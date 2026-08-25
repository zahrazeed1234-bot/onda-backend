from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    ROLE_ADMIN = 'ADMIN_CNS'
    ROLE_TECHNICIAN = 'TECHNICIAN_MAINTENANCE'
    ROLE_CONSULTANT = 'CONSULTANT'

    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Administrateur CNS'),
        (ROLE_TECHNICIAN, 'Technicien Maintenance'),
        (ROLE_CONSULTANT, 'Consultant'),
    ]

    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        default=ROLE_TECHNICIAN,
        verbose_name=_('Rôle'),
        help_text=_('Rôle principal de l\'utilisateur (synchronisé avec Groups)'),
    )
    telephone = models.CharField(max_length=20, blank=True, null=True, verbose_name=_('Téléphone'))
    service = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('Service'))
    matricule = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name=_('Matricule'))

    class Meta:
        verbose_name = _('Utilisateur')
        verbose_name_plural = _('Utilisateurs')
        ordering = ['username']

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.get_role_display()})'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._sync_role_to_group()

    def _sync_role_to_group(self):
        group_map = {
            self.ROLE_ADMIN: 'Admin_CNS',
            self.ROLE_TECHNICIAN: 'Technicien_Maintenance',
            self.ROLE_CONSULTANT: 'Consultant',
        }
        group_name = group_map.get(self.role)
        if group_name:
            group, _ = Group.objects.get_or_create(name=group_name)
            if not self.groups.filter(pk=group.pk).exists():
                self.groups.clear()
                self.groups.add(group)

    def is_admin_cns(self):
        return self.role == self.ROLE_ADMIN or self.is_superuser

    def is_technician(self):
        return self.role == self.ROLE_TECHNICIAN

    def is_consultant(self):
        return self.role == self.ROLE_CONSULTANT
