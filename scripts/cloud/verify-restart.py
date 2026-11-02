#!/usr/bin/env python3
"""Exercise an owned runtime restart without printing credentials or row contents."""
import hashlib
import dev

def fingerprint():
    state = dev.load()
    sql = '''SELECT jsonb_build_object(
      'users', (SELECT jsonb_agg(to_jsonb(t) ORDER BY "Id") FROM public."Usuarios" t),
      'operators', (SELECT jsonb_agg(to_jsonb(t) ORDER BY "Id") FROM public."Operadores" t),
      'commerce', (SELECT jsonb_agg(to_jsonb(t) ORDER BY "Id") FROM public."Comercios" t),
      'shipments', (SELECT jsonb_agg(to_jsonb(t) ORDER BY "Id") FROM public."Envios" t),
      'migrations', (SELECT count(*) FROM public."__EFMigrationsHistory"));'''
    return (hashlib.sha256((dev.STATE/'private.json').read_bytes()).digest(),
            hashlib.sha256(dev.psql(state,sql).encode()).digest())

dev.verify()
before = fingerprint()
dev.stop()
dev.start()
dev.verify()
assert fingerprint() == before, 'Persisted rows or private state changed during restart'
print('Restart preserved users, organizations, shipments, migrations and private state')
