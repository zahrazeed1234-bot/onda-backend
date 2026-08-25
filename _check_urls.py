import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.test import Client
from django.urls import reverse, resolve

client = Client()

print('=== API ENDPOINTS RESOLUTION CHECK ===')

urls_to_check = [
    ('api:dashboard-stats', '/api/dashboard/stats/', 'GET'),
    ('schema-swagger-ui', '/swagger/', 'GET'),
]

# check URL patterns resolve correctly
from django.urls import get_resolver
resolver = get_resolver()

# Test known URL patterns
patterns = [
    ('/api/auth/token/', True),
    ('/api/auth/users/', True),
    ('/api/auth/users/me/', True),
    ('/api/auth/users/technicians/', True),
    ('/api/equipment/all/', True),
    ('/api/equipment/stats/', True),
    ('/api/equipment/choices/', True),
    ('/api/equipment/vor/', True),
    ('/api/equipment/ils/', True),
    ('/api/equipment/dme/', True),
    ('/api/equipment/radar/', True),
    ('/api/equipment/vcs/', True),
    ('/api/tickets/', True),
    ('/api/tickets/stats/summary/', True),
    ('/api/tickets/metadata/choices/', True),
    ('/api/tickets/assign/', True),
    ('/api/audit/logs/', True),
    ('/api/audit/logs/summary/', True),
    ('/api/audit/logs/latest/', True),
    ('/api/dashboard/stats/', True),
    ('/swagger/', True),
    ('/redoc/', True),
    ('/admin/', True),
]

all_ok = True
for url, should_resolve in patterns:
    try:
        match = resolve(url)
        if should_resolve:
            print(f'  OK   {url} -> {match.view_name}')
        else:
            print(f'  FAIL {url} - should NOT resolve but did')
            all_ok = False
    except Exception as e:
        if should_resolve:
            print(f'  FAIL {url} - NOT FOUND: {e}')
            all_ok = False
        else:
            print(f'  OK   {url} - correctly not resolved')

if all_ok:
    print('\n=== ALL ENDPOINTS OK ===')
else:
    print('\n=== SOME ENDPOINTS FAILED ===')
