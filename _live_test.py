import urllib.request
import urllib.error
import json

BASE = 'http://localhost:8000'

def post(path, data, token=None):
    body = json.dumps(data).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status, json.loads(r.read().decode('utf-8'))

def get(path, token=None):
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(BASE + path, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status, json.loads(r.read().decode('utf-8'))

print('=== BACKEND API LIVE TEST ===')
print()

# Login test
print('1. Login admin_cns...')
s, data = post('/api/auth/token/', {'username': 'admin_cns', 'password': 'Admin@2026!'})
assert s == 200, f'Login failed: {s}'
token = data['access']
print(f'   OK (status 200, token length: {len(token)})')

# Me endpoint
print('2. GET /api/auth/users/me/...')
s, me = get('/api/auth/users/me/', token)
print(f'   OK - {me["username"]} ({me["role_label"]})')

# Equipment all
print('3. GET /api/equipment/all/...')
s, eqs = get('/api/equipment/all/', token)
print(f'   OK - {len(eqs)} équipements CNS')

# Equipment stats
print('4. GET /api/equipment/stats/...')
s, stats = get('/api/equipment/stats/', token)
print(f'   OK - Dispo: {stats["disponibilite"]}%, Critiques: {stats["critique_count"]}')

# Tickets
print('5. GET /api/tickets/...')
s, tks = get('/api/tickets/', token)
if isinstance(tks, dict):
    tlist = tks.get('results', [])
else:
    tlist = tks
print(f'   OK - {len(tlist)} tickets de maintenance')

# Tickets stats
print('6. GET /api/tickets/stats/summary/...')
s, tstats = get('/api/tickets/stats/summary/', token)
print(f'   OK - Ouverts: {tstats["ouverts"]}, Critiques: {tstats["critics"]}, Urgents: {tstats["urgents"]}')

# Dashboard combined
print('7. GET /api/dashboard/stats/...')
s, dash = get('/api/dashboard/stats/', token)
print(f'   OK - equipment+tickets combinés')

# Audit latest (admin only)
print('8. GET /api/audit/logs/latest/...')
s, audit = get('/api/audit/logs/latest/', token)
print(f'   OK - {len(audit)} derniers logs audit')

# Swagger UI check
print('9. GET /swagger/ (Swagger UI)...')
try:
    req = urllib.request.Request(BASE + '/swagger/')
    with urllib.request.urlopen(req, timeout=10) as r:
        html = r.read().decode('utf-8', errors='ignore')
        print(f'   OK (Swagger UI chargé, {len(html)} octets)')
except Exception as e:
    print(f'   WARN: {e}')

print()
print('=== TOUS LES ENDPOINTS SONT OPÉRATIONNELS ===')
print()
print('BACKEND URLS:')
print(f'  • API Root:       {BASE}/api/')
print(f'  • Swagger UI:     {BASE}/swagger/')
print(f'  • ReDoc Docs:     {BASE}/redoc/')
print(f'  • Admin Django:   {BASE}/admin/')
print()
print('COMPTES DÉMO:')
print('  • admin_cns / Admin@2026!        (Super Admin)')
print('  • tech_maint_1 / Tech@2026!     (Technicien)')
print('  • consultant_safety / Cons@2026! (Consultant lecture seule)')
