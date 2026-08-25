import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
import json

User = get_user_model()
client = Client()

print('=== FUNCTIONAL API TESTS ===')

# 1. Test login endpoint with wrong credentials
print('\n1. Test login (bad credentials)...')
resp = client.post('/api/auth/token/', {'username': 'admin_cns', 'password': 'wrongpass'}, content_type='application/json')
print(f'   Status: {resp.status_code} (expected 401)')
assert resp.status_code == 401, f'Expected 401, got {resp.status_code}'
print('   OK')

# 2. Test login endpoint with correct credentials
print('\n2. Test login (correct credentials)...')
resp = client.post('/api/auth/token/', {'username': 'admin_cns', 'password': 'Admin@2026!'}, content_type='application/json')
print(f'   Status: {resp.status_code} (expected 200)')
assert resp.status_code == 200, f'Expected 200, got {resp.status_code}: {resp.content}'
data = json.loads(resp.content)
access = data.get('access')
refresh = data.get('refresh')
print(f'   Access token: {"OK" if access else "MISSING"}')
print(f'   Refresh token: {"OK" if refresh else "MISSING"}')
assert access and refresh, 'Tokens missing'
print('   OK')

auth_headers = {'HTTP_AUTHORIZATION': f'Bearer {access}'}

# 3. Test /api/auth/users/me/
print('\n3. Test /api/auth/users/me/...')
resp = client.get('/api/auth/users/me/', **auth_headers)
print(f'   Status: {resp.status_code}')
assert resp.status_code == 200
me = json.loads(resp.content)
print(f'   User: {me.get("username")} Role: {me.get("role")}')
assert me['username'] == 'admin_cns'
print('   OK')

# 4. Test /api/equipment/all/
print('\n4. Test /api/equipment/all/...')
resp = client.get('/api/equipment/all/', **auth_headers)
print(f'   Status: {resp.status_code}')
assert resp.status_code == 200
eqs = json.loads(resp.content)
print(f'   Equipments returned: {len(eqs)}')
assert len(eqs) >= 7
print('   OK')

# 5. Test /api/equipment/stats/
print('\n5. Test /api/equipment/stats/...')
resp = client.get('/api/equipment/stats/', **auth_headers)
print(f'   Status: {resp.status_code}')
assert resp.status_code == 200
stats = json.loads(resp.content)
print(f'   Total equipements: {stats.get("total_equipements")}')
print(f'   Critiques: {stats.get("critique_count")}')
print(f'   Disponibilité: {stats.get("disponibilite")}%')
assert 'par_type' in stats
assert 'alerte_seuils' in stats
print('   OK')

# 6. Test /api/tickets/
print('\n6. Test /api/tickets/...')
resp = client.get('/api/tickets/', **auth_headers)
print(f'   Status: {resp.status_code}')
assert resp.status_code == 200
data = json.loads(resp.content)
if isinstance(data, dict):
    tickets = data.get('results', [])
else:
    tickets = data
print(f'   Tickets returned: {len(tickets)}')
assert len(tickets) >= 4
print('   OK')

# 7. Test /api/tickets/stats/summary/
print('\n7. Test /api/tickets/stats/summary/...')
resp = client.get('/api/tickets/stats/summary/', **auth_headers)
print(f'   Status: {resp.status_code}')
assert resp.status_code == 200
tk_stats = json.loads(resp.content)
print(f'   Total: {tk_stats.get("total")}, Ouverts: {tk_stats.get("ouverts")}, Critics: {tk_stats.get("critics")}, Urgents: {tk_stats.get("urgents")}')
assert 'critics' in tk_stats
assert 'urgents' in tk_stats
print('   OK')

# 8. Test /api/dashboard/stats/ (combined endpoint)
print('\n8. Test /api/dashboard/stats/ (combined endpoint)...')
resp = client.get('/api/dashboard/stats/', **auth_headers)
print(f'   Status: {resp.status_code}')
assert resp.status_code == 200
dash = json.loads(resp.content)
print(f'   Keys: {list(dash.keys())}')
assert 'equipment' in dash
assert 'tickets' in dash
print('   OK')

# 9. Test /api/audit/logs/latest/
print('\n9. Test /api/audit/logs/latest/ (admin only)...')
resp = client.get('/api/audit/logs/latest/', **auth_headers)
print(f'   Status: {resp.status_code}')
assert resp.status_code == 200
latest = json.loads(resp.content)
print(f'   Latest audit logs returned: {len(latest) if isinstance(latest, list) else "N/A"}')
print('   OK')

# 10. Test equipment choices endpoint
print('\n10. Test /api/equipment/choices/...')
resp = client.get('/api/equipment/choices/', **auth_headers)
print(f'   Status: {resp.status_code}')
assert resp.status_code == 200
choices = json.loads(resp.content)
assert 'types' in choices
assert 'equipements' in choices
print(f'   Equipment choices: {len(choices["equipements"])}')
print('   OK')

print('\n=== ALL 10 API TESTS PASSED ===')
print('\nDemo accounts:')
print('  - Admin:      admin_cns / Admin@2026!')
print('  - Technician: tech_maint_1 / Tech@2026!')
print('  - Consultant: consultant_safety / Cons@2026!')
