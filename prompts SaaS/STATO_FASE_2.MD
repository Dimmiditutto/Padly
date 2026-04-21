# STATO_FASE_2

## Data

21-04-2026

## Esito reale

- PASS: FASE 2 completata e verificata.
- PASS: suite backend completa verde con 84 passed in 63.09s.
- PASS: migrazione tenant foundation verificata con upgrade, downgrade e re-upgrade tramite [backend/tests/test_tenant_foundation_migration.py](backend/tests/test_tenant_foundation_migration.py).
- PASS: harness test stabilizzato su SQLite con database per-test in [backend/tests/conftest.py](backend/tests/conftest.py).

## Decisioni di dominio confermate

- Il tenant root reale introdotto in questa fase e Club in [backend/app/models/__init__.py](backend/app/models/__init__.py).
- Il modello dominio tenant-aware introdotto in questa fase e ClubDomain in [backend/app/models/__init__.py](backend/app/models/__init__.py).
- La strategia confermata resta shared database con isolamento logico per club_id.
- La retrocompatibilita single-tenant e garantita tramite default club bootstrap e backfill deterministico.
- BookingPayment non riceve club_id diretto in FASE 2: il suo scoping passa ancora dalla relazione obbligatoria verso Booking.
- PaymentWebhookEvent non riceve club_id diretto in FASE 2: resta un log tecnico globale provider-centric, da rivalutare in FASE 3 o fase di hardening se si richiede audit tenant-first anche sul raw webhook trail.

## File reali toccati

- [backend/app/models/__init__.py](backend/app/models/__init__.py)
- [backend/app/services/tenant_service.py](backend/app/services/tenant_service.py)
- [backend/app/services/settings_service.py](backend/app/services/settings_service.py)
- [backend/app/main.py](backend/app/main.py)
- [backend/app/services/email_service.py](backend/app/services/email_service.py)
- [backend/app/services/booking_service.py](backend/app/services/booking_service.py)
- [backend/app/services/report_service.py](backend/app/services/report_service.py)
- [backend/app/api/routers/admin_bookings.py](backend/app/api/routers/admin_bookings.py)
- [backend/app/api/routers/admin_ops.py](backend/app/api/routers/admin_ops.py)
- [backend/alembic/versions/20260421_0003_tenant_foundation.py](backend/alembic/versions/20260421_0003_tenant_foundation.py)
- [backend/tests/test_tenant_foundation_migration.py](backend/tests/test_tenant_foundation_migration.py)
- [backend/tests/conftest.py](backend/tests/conftest.py)

## Schema finale reale

### Tenant root: Club

Entita introdotta in [backend/app/models/__init__.py](backend/app/models/__init__.py) con i seguenti campi reali:

- id
- slug unique
- public_name
- legal_name nullable
- notification_email
- billing_email nullable
- support_email nullable
- support_phone nullable
- timezone
- currency
- is_active
- created_at
- updated_at

Relazioni reali esposte dal modello:

- domains
- admins
- customers
- recurring_series
- bookings
- events
- blackouts
- settings
- email_notifications

### Tenant domain: ClubDomain

Entita introdotta in [backend/app/models/__init__.py](backend/app/models/__init__.py) con i seguenti campi reali:

- id
- club_id
- host unique
- is_primary
- is_active
- created_at

### Colonne di scoping aggiunte

Scoping diretto con club_id aggiunto in:

- admins
- customers
- recurring_booking_series
- bookings
- booking_events_log
- blackout_periods
- app_settings
- email_notifications_log

Vincoli e scelte reali conseguenti:

- Admin passa da unicita globale su email a unicita per club con uq_admin_club_email in [backend/app/models/__init__.py](backend/app/models/__init__.py).
- AppSetting diventa scoped per club tramite chiave primaria composta club_id + key in [backend/app/models/__init__.py](backend/app/models/__init__.py).
- Su PostgreSQL, la migrazione aggiorna il vincolo di non sovrapposizione booking includendo club_id in [backend/alembic/versions/20260421_0003_tenant_foundation.py](backend/alembic/versions/20260421_0003_tenant_foundation.py).

### Tabelle non propagate direttamente in FASE 2

- booking_payments: nessun club_id diretto, scoping derivato da booking_id.
- payment_webhook_events: nessun club_id diretto, log tecnico lasciato globale in questa fase.

## Migrazione reale

- Nome migrazione: 20260421_0003_tenant_foundation
- File: [backend/alembic/versions/20260421_0003_tenant_foundation.py](backend/alembic/versions/20260421_0003_tenant_foundation.py)
- Revises: 20260417_0002

Contenuto reale della migrazione:

- crea le tabelle clubs e club_domains
- crea indici univoci su clubs.slug e club_domains.host
- inserisce default club e default host
- aggiunge club_id alle tabelle legacy prioritarie con server default e backfill
- ricostruisce admins con vincolo tenant-aware su email
- trasforma app_settings da tabella globale a tabella scoped per club
- mantiene downgrade reale e re-upgrade senza errori

## Strategia di bootstrap e retrocompatibilita

- Il bootstrap default tenant e centralizzato in [backend/app/services/tenant_service.py](backend/app/services/tenant_service.py).
- Le costanti di retrocompatibilita introdotte sono DEFAULT_CLUB_ID, DEFAULT_CLUB_SLUG e DEFAULT_CLUB_HOST in [backend/app/models/__init__.py](backend/app/models/__init__.py).
- [backend/app/main.py](backend/app/main.py) ora crea l'admin bootstrap sul default club.
- Il backfill migrazione assegna il default club a tutte le righe legacy rese tenant-scoped.
- I modelli tenant-scoped usano default coerenti su club_id per mantenere operativi insert legacy-like durante la transizione.
- [backend/app/services/settings_service.py](backend/app/services/settings_service.py) legge e scrive booking rules in forma club-scoped.
- [backend/app/services/booking_service.py](backend/app/services/booking_service.py) applica scoping minimo su customer lookup, availability, booking list, blackout, recurring e log eventi.
- [backend/app/services/email_service.py](backend/app/services/email_service.py) registra email log con club_id coerente.
- [backend/app/services/report_service.py](backend/app/services/report_service.py) rende tenant-aware il report summary.
- [backend/app/api/routers/admin_bookings.py](backend/app/api/routers/admin_bookings.py) e [backend/app/api/routers/admin_ops.py](backend/app/api/routers/admin_ops.py) usano admin.club_id per le operazioni gia adattate.

## Test aggiunti e verifiche reali

### Test aggiunti

- [backend/tests/test_tenant_foundation_migration.py](backend/tests/test_tenant_foundation_migration.py)

Copertura reale del nuovo test:

- upgrade da legacy head a tenant foundation
- seed dati legacy
- verifica default club e default domain
- verifica admin legacy ancora autenticabile dopo la migrazione
- verifica backfill club_id sulle tabelle prioritarie
- verifica app_settings scoped per club
- downgrade e re-upgrade senza errori

### Verifiche eseguite realmente

- PASS: test mirato bootstrap admin e compatibilita tenant.
- PASS: [backend/tests/test_booking_api.py](backend/tests/test_booking_api.py).
- PASS: [backend/tests/test_admin_and_recurring.py](backend/tests/test_admin_and_recurring.py).
- PASS: [backend/tests/test_payment_flows.py](backend/tests/test_payment_flows.py).
- PASS: [backend/tests/test_security.py](backend/tests/test_security.py).
- PASS: [backend/tests/test_tenant_foundation_migration.py](backend/tests/test_tenant_foundation_migration.py).
- PASS: suite backend completa da [backend/tests](backend/tests) con 84 passed.

### Nota tecnica sui test

- Durante la validazione e emersa instabilita del file SQLite condiviso su Windows.
- La soluzione finale adottata in [backend/tests/conftest.py](backend/tests/conftest.py) isola ogni test su un database SQLite dedicato, ri-configurando SessionLocal sul nuovo engine per-test.
- Questa correzione elimina i falsi negativi legati a database is locked e no such table senza alterare il runtime applicativo.

## Limiti residui intenzionali dopo FASE 2

- La tenant resolution per host o slug non e ancora applicata alle request pubbliche e admin.
- [backend/app/api/deps.py](backend/app/api/deps.py) continua a risolvere l'admin per email, quindi non e ancora tenant-safe in un vero scenario multi-club con email duplicate tra tenant.
- Il frontend resta sostanzialmente single-tenant e default-club oriented.
- Il mutex single_court globale in [backend/app/services/booking_service.py](backend/app/services/booking_service.py) non e ancora tenant-aware.
- PaymentWebhookEvent resta fuori dal tenant scoping diretto.
- Branding, settings pubblici e tenant resolution HTTP restano lavoro della FASE 3.

## PASS/FAIL finale

- PASS reale.

## CONTEXT BLOCK PER FASE_3

- Tenant root reale: Club.
- Tenant key reale usata in FASE 2: club_id.
- Default tenant retrocompatibile gia introdotto.
- Tabelle gia scoped direttamente: admins, customers, recurring_booking_series, bookings, booking_events_log, blackout_periods, app_settings, email_notifications_log.
- Tabelle non ancora scoped direttamente: booking_payments, payment_webhook_events.
- Admin club-aware disponibile nel modello, ma dependency auth non ancora tenant-safe.
- I router admin gia toccati usano admin.club_id nelle operazioni migrate.
- La request tenant resolution non va inventata da zero in FASE 3: deve appoggiarsi a ClubDomain o a un fallback esplicito default club, senza rompere il deploy attuale.
- La FASE 3 deve partire da dependency condivisa di tenant context e da filtro sistematico delle query, non da patch sparse endpoint per endpoint.
- La baseline verificata da preservare e: shared database, default club compatibile, migrazione 20260421_0003 gia valida, suite backend verde.