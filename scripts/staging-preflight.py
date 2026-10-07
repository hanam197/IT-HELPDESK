#!/usr/bin/env python3
"""Validate staging env without displaying secrets. No third-party dependencies."""
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

path = Path(sys.argv[1] if len(sys.argv) > 1 else '.env.staging')
values = {}
for line in path.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        key, value = line.split('=', 1)
        values[key] = value.strip().strip('\"\'')
errors = []
for key in ('POSTGRES_PASSWORD', 'SECRET_KEY'):
    value = values.get(key, '')
    if len(value) < 32 or any(word in value.lower() for word in ('change', 'example', 'placeholder')):
        errors.append(f'{key}: require a generated secret of at least 32 characters')
if not re.fullmatch(r'[A-Za-z0-9]+', values.get('POSTGRES_PASSWORD', '')):
    errors.append('POSTGRES_PASSWORD: use alphanumeric characters for the connection URL')
if values.get('POSTGRES_PASSWORD') == values.get('SECRET_KEY'):
    errors.append('Generate separate database and session secrets')
url = urlparse(values.get('FRONTEND_URL', ''))
if url.scheme != 'https' or not url.hostname or url.hostname.endswith('example.com') or url.path not in ('', '/') or url.query or url.fragment:
    errors.append('FRONTEND_URL: require the real HTTPS staging origin')
if values.get('SECURE_COOKIE', '').lower() != 'true':
    errors.append('SECURE_COOKIE must be true')
if values.get('SEED_PASSWORD'):
    errors.append('SEED_PASSWORD must be empty; use bootstrap instead of demo seed')
if values.get('HTTP_BIND') != '127.0.0.1':
    errors.append('HTTP_BIND must be 127.0.0.1 behind the host TLS proxy')
if not values.get('HTTP_PORT', '').isdigit() or not 1024 <= int(values['HTTP_PORT']) <= 65535:
    errors.append('HTTP_PORT: require a port between 1024 and 65535')
if errors:
    print('\n'.join(errors), file=sys.stderr)
    sys.exit(1)
print('Staging configuration passed; secrets were not displayed.')
