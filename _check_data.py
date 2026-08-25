import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from accounts.models import User
from equipment.models import EquipmentVOR, EquipmentILS, EquipmentDME, EquipmentRadar, EquipmentVCS, MeasurementLog
from tickets.models import MaintenanceTicket, ChecklistItem
from audit.models import AuditLog

print('=== DEMO DATA CHECK ===')
n_users = User.objects.count()
admin_ok = User.objects.filter(username='admin_cns').exists()
print('Users:', n_users, '(admin_cns exists:', admin_ok, ')')
print('VOR:', EquipmentVOR.objects.count())
print('ILS:', EquipmentILS.objects.count())
print('DME:', EquipmentDME.objects.count())
print('Radar:', EquipmentRadar.objects.count())
print('VCS:', EquipmentVCS.objects.count())
print('Measurements:', MeasurementLog.objects.count())
print('Tickets:', MaintenanceTicket.objects.count())
print('Checklist items:', ChecklistItem.objects.count())
print('Audit logs:', AuditLog.objects.count())
if admin_ok:
    u = User.objects.get(username='admin_cns')
    print('Admin role:', u.role, '| is_superuser:', u.is_superuser)
print('=== DONE ===')
