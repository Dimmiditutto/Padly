# STATO_FASE_1

## Data

21-04-2026

## Decisioni prese

- La roadmap confermata resta single codebase -> SaaS multi-tenant con database unico condiviso.
- Il tenant root puo essere modellato come Club, ma la chiave architetturale resta il tenant boundary.
- Non sono emersi motivi tecnici reali per preferire database-per-tenant o schema-per-tenant.
- Chat, LLM e matchmaking non fanno parte della traiettoria corretta di trasformazione SaaS per questo repository.
- I contratti public/admin esistenti vanno estesi con patch minime; non vanno duplicati senza motivo.

## Prerequisiti verificati

- PASS: import backend da [backend/app/main.py](backend/app/main.py) con interprete locale [.venv/Scripts/python.exe](.venv/Scripts/python.exe).
- PASS: Alembic disponibile e migrazioni eseguibili in modalita offline SQL su SQLite locale tramite [backend/alembic.ini](backend/alembic.ini) e [backend/alembic/env.py](backend/alembic/env.py).
- PASS: suite backend esiste ed e lanciabile da [backend/tests](backend/tests); il sottoinsieme [backend/tests/test_security.py](backend/tests/test_security.py) passa. La suite completa e stata avviata ma non osservata fino a fine esecuzione nei limiti del tool.
- PASS: frontend buildabile; build Vite confermata verde da [frontend/package.json](frontend/package.json).
- PASS: routing frontend identificabile in [frontend/src/App.tsx](frontend/src/App.tsx).
- PASS: sistema email identificabile in [backend/app/services/email_service.py](backend/app/services/email_service.py).
- PASS: modello Booking e logica disponibilita rintracciabili in [backend/app/models/__init__.py](backend/app/models/__init__.py) e [backend/app/services/booking_service.py](backend/app/services/booking_service.py).
- PASS: auth admin, password reset e settings admin rintracciabili in [backend/app/api/routers/admin_auth.py](backend/app/api/routers/admin_auth.py) e [backend/app/api/routers/admin_settings.py](backend/app/api/routers/admin_settings.py).

## File reali individuati

### Backend core

- [backend/app/main.py](backend/app/main.py)
- [backend/app/core/config.py](backend/app/core/config.py)
- [backend/app/core/db.py](backend/app/core/db.py)
- [backend/app/core/security.py](backend/app/core/security.py)
- [backend/app/core/scheduler.py](backend/app/core/scheduler.py)
- [backend/app/api/deps.py](backend/app/api/deps.py)

### Router backend

- [backend/app/api/routers/public.py](backend/app/api/routers/public.py)
- [backend/app/api/routers/admin_auth.py](backend/app/api/routers/admin_auth.py)
- [backend/app/api/routers/admin_bookings.py](backend/app/api/routers/admin_bookings.py)
- [backend/app/api/routers/admin_ops.py](backend/app/api/routers/admin_ops.py)
- [backend/app/api/routers/admin_settings.py](backend/app/api/routers/admin_settings.py)
- [backend/app/api/routers/payments.py](backend/app/api/routers/payments.py)

### Dominio e servizi backend

- [backend/app/models/__init__.py](backend/app/models/__init__.py)
- [backend/app/services/booking_service.py](backend/app/services/booking_service.py)
- [backend/app/services/payment_service.py](backend/app/services/payment_service.py)
- [backend/app/services/email_service.py](backend/app/services/email_service.py)
- [backend/app/services/settings_service.py](backend/app/services/settings_service.py)
- [backend/app/services/report_service.py](backend/app/services/report_service.py)

### Migrazioni e test backend

- [backend/alembic.ini](backend/alembic.ini)
- [backend/alembic/env.py](backend/alembic/env.py)
- [backend/alembic/versions/20260415_0001_initial.py](backend/alembic/versions/20260415_0001_initial.py)
- [backend/alembic/versions/20260417_0002_payment_refunds.py](backend/alembic/versions/20260417_0002_payment_refunds.py)
- [backend/tests/conftest.py](backend/tests/conftest.py)
- [backend/tests/test_booking_api.py](backend/tests/test_booking_api.py)
- [backend/tests/test_admin_and_recurring.py](backend/tests/test_admin_and_recurring.py)
- [backend/tests/test_payment_flows.py](backend/tests/test_payment_flows.py)
- [backend/tests/test_security.py](backend/tests/test_security.py)

### Frontend rilevante

- [frontend/src/App.tsx](frontend/src/App.tsx)
- [frontend/src/services/api.ts](frontend/src/services/api.ts)
- [frontend/src/services/publicApi.ts](frontend/src/services/publicApi.ts)
- [frontend/src/services/adminApi.ts](frontend/src/services/adminApi.ts)
- [frontend/src/pages/PublicBookingPage.tsx](frontend/src/pages/PublicBookingPage.tsx)
- [frontend/src/pages/PublicCancellationPage.tsx](frontend/src/pages/PublicCancellationPage.tsx)
- [frontend/src/pages/PaymentStatusPage.tsx](frontend/src/pages/PaymentStatusPage.tsx)
- [frontend/src/pages/AdminLoginPage.tsx](frontend/src/pages/AdminLoginPage.tsx)
- [frontend/src/pages/AdminPasswordResetPage.tsx](frontend/src/pages/AdminPasswordResetPage.tsx)
- [frontend/src/pages/AdminDashboardPage.tsx](frontend/src/pages/AdminDashboardPage.tsx)
- [frontend/src/pages/AdminBookingsPage.tsx](frontend/src/pages/AdminBookingsPage.tsx)
- [frontend/src/pages/AdminCurrentBookingsPage.tsx](frontend/src/pages/AdminCurrentBookingsPage.tsx)
- [frontend/src/pages/AdminBookingDetailPage.tsx](frontend/src/pages/AdminBookingDetailPage.tsx)
- [frontend/src/pages/AdminLogsPage.tsx](frontend/src/pages/AdminLogsPage.tsx)
- [frontend/src/types.ts](frontend/src/types.ts)

## Assunzioni confermate

- Il repository e oggi single-tenant.
- Il dominio attuale non contiene tenant esplicito, Club, club_id o tenant_id.
- Il booking pubblico e l'admin condividono la stessa base dati e gli stessi router applicativi.
- L'auth admin e cookie-based, con controllo utente in [backend/app/api/deps.py](backend/app/api/deps.py).
- Le booking rules sono globali in [backend/app/services/settings_service.py](backend/app/services/settings_service.py).
- Le metriche dashboard sono globali in [backend/app/services/report_service.py](backend/app/services/report_service.py).
- Le email operative si appoggiano a impostazioni globali environment e a [backend/app/models/__init__.py](backend/app/models/__init__.py) tramite EmailNotificationLog.
- Il frontend pubblico vive su / e l'area admin su route dedicate, senza concetto di tenant nel client.
- Il progetto supporta gia PostgreSQL in produzione e SQLite in locale/test; questo e compatibile con la strategia shared database.

## Assunzioni smentite

- Non e emerso alcun layer SaaS gia pronto nel repository.
- Non esiste una tenant resolution gia implementata da host, slug o dominio.
- Non esistono control plane, billing subscription o ruoli platform.
- Non esiste alcun motivo tecnico gia presente nel repo che imponga database-per-tenant.
- I primi FAIL emersi sul backend non dipendevano dal codice del repo ma dall'uso dell'interprete system invece della [.venv](.venv).

## Contratti attuali da preservare

### Public API

- GET /api/public/config
- GET /api/public/availability
- POST /api/public/bookings
- POST /api/public/bookings/{booking_id}/checkout
- GET /api/public/bookings/{public_reference}/status
- GET /api/public/bookings/cancel/{cancel_token}
- POST /api/public/bookings/cancel/{cancel_token}

### Admin API

- POST /api/admin/auth/login
- POST /api/admin/auth/logout
- POST /api/admin/auth/password-reset/request
- POST /api/admin/auth/password-reset/confirm
- GET /api/admin/auth/me
- GET /api/admin/bookings
- GET /api/admin/bookings/{id}
- POST /api/admin/bookings
- PUT /api/admin/bookings/{id}
- POST /api/admin/bookings/{id}/cancel
- POST /api/admin/bookings/{id}/status
- POST /api/admin/bookings/{id}/balance-paid
- GET /api/admin/blackouts
- POST /api/admin/blackouts
- POST /api/admin/recurring/preview
- POST /api/admin/recurring
- PUT /api/admin/recurring/{series_id}
- POST /api/admin/recurring/cancel-occurrences
- POST /api/admin/recurring/{series_id}/cancel
- GET /api/admin/reports/summary
- GET /api/admin/events
- GET /api/admin/settings
- PUT /api/admin/settings

## Hardcode single-tenant da rimuovere in ordine

1. Bootstrap di un solo admin globale in [backend/app/main.py](backend/app/main.py).
2. Modello Admin senza tenant association in [backend/app/models/__init__.py](backend/app/models/__init__.py) e lookup per email globale in [backend/app/api/deps.py](backend/app/api/deps.py).
3. Booking rules globali in [backend/app/services/settings_service.py](backend/app/services/settings_service.py) e payload settings globale in [backend/app/api/routers/admin_settings.py](backend/app/api/routers/admin_settings.py).
4. Entita core senza tenant key: Booking, Customer, BlackoutPeriod, RecurringBookingSeries, BookingEventLog, EmailNotificationLog, AppSetting in [backend/app/models/__init__.py](backend/app/models/__init__.py).
5. Query globali su prenotazioni, blackout, eventi e report in [backend/app/services/booking_service.py](backend/app/services/booking_service.py), [backend/app/api/routers/admin_ops.py](backend/app/api/routers/admin_ops.py) e [backend/app/services/report_service.py](backend/app/services/report_service.py).
6. Email operative admin-centriche verso settings.admin_email in [backend/app/services/email_service.py](backend/app/services/email_service.py).
7. Configurazione pubblica e branding globale in [backend/app/api/routers/public.py](backend/app/api/routers/public.py) e [frontend/src/pages/PublicBookingPage.tsx](frontend/src/pages/PublicBookingPage.tsx).
8. Lock di concorrenza single-court globale in [backend/app/services/booking_service.py](backend/app/services/booking_service.py): mutex unico e advisory lock costante, oggi condiviso da tutta l'applicazione.
9. Payment webhook e payment tracking privi di scope tenant in [backend/app/models/__init__.py](backend/app/models/__init__.py) e [backend/app/services/payment_service.py](backend/app/services/payment_service.py).
10. Redirect admin, sessione client e client API privi di contesto tenant in [frontend/src/services/api.ts](frontend/src/services/api.ts) e [frontend/src/pages/AdminDashboardPage.tsx](frontend/src/pages/AdminDashboardPage.tsx).

## Rischi architetturali reali

- Il lock single-court globale serializzerebbe i booking di tenant diversi se venisse mantenuto invariato in un SaaS shared database.
- Le query globali di dashboard, log, blackout e booking produrrebbero leakage cross-tenant appena si introducessero piu tenant.
- Il lookup admin per sola email non e sufficiente in un contesto multi-tenant con shared database.
- [backend/app/services/email_service.py](backend/app/services/email_service.py) usa ancora destinazioni e timezone globali via settings; senza tenant scoping notificherebbe il tenant sbagliato.
- [backend/app/services/payment_service.py](backend/app/services/payment_service.py) separa bene payment provider e booking flow, ma non ha ancora il boundary tenant sui dati commerciali e di webhook.
- L'assenza di tenant resolution a livello request impedisce di estendere in sicurezza i router esistenti senza una dependency condivisa.

## Rischi di regressione

- Rompere il booking pubblico su / durante l'introduzione del tenant context.
- Rompere login admin e reset password durante l'associazione admin -> tenant.
- Rompere idempotenza pagamenti e refund durante l'aggiunta del tenant scope.
- Rompere recurring e blackout se il backfill tenant viene applicato in ordine sbagliato.
- Introdurre filtri tenant parziali in alcune query lasciandone altre globali.

## Conferma esplicita sul modello dati

- La roadmap confermata usa database unico condiviso.
- Nessuna evidenza tecnica raccolta in FASE 1 richiede database-per-tenant.
- La trasformazione corretta e: introdurre tenant root, propagare tenant key, filtrare query, rendere tenant-aware servizi e contratti, poi aggiungere layer commerciale.

## Micro-fix preparatori strettamente necessari

- Nessun micro-fix di prodotto e indispensabile prima della FASE 2.
- Serve mantenere come baseline di esecuzione backend la [.venv](.venv) del repo, non l'interprete system Python.

## Ordine esatto delle fasi successive

1. FASE_2: introdurre tenant root, tenant domain, colonne di scoping e backfill legacy nello stesso database condiviso.
2. FASE_3: rendere tenant-aware backend, auth admin, settings, email operative, query booking/report/log e tenant resolution.
3. FASE_4: adattare frontend pubblico e admin ai nuovi payload tenant-aware, con branding e settings tenant-scoped.
4. FASE_5: introdurre piani, subscription, provisioning tenant e control plane minimo, mantenendo shared database.
5. FASE_6: hardening operativo, runbook, osservabilita, protezioni cross-tenant e go-live readiness.

## Note per FASE_2

- La scelta piu pragmatica e introdurre Club come tenant root, perche il dominio di business del prodotto ruota gia intorno a un circolo singolo.
- La FASE_2 deve partire da Admin, Booking, Customer, AppSetting e Blackout/Recurring come superfici minime di isolamento.
- Il disegno dei vincoli deve evitare di dover riscrivere subito tutti i router: prima foundation dati e backfill, poi estensione servizi/router nella FASE_3.