# STATO_FASE_3

## Data

21-04-2026

## Esito reale

- PASS: FASE 3 completata sul backend tenant-aware.
- PASS: suite backend completa verde con 91 passed in 58.35s.
- PASS: nuova suite multi-tenant backend in [backend/tests/test_tenant_backend_context.py](backend/tests/test_tenant_backend_context.py) con 7 test verdi.

## Decisioni confermate

- La tenant key applicativa resta club_id con Club come tenant root e ClubDomain come meccanismo primario di tenant resolution.
- La tenant resolution reale e centralizzata in [backend/app/services/tenant_service.py](backend/app/services/tenant_service.py) e consumata via dependency condivisa in [backend/app/api/deps.py](backend/app/api/deps.py).
- La risoluzione tenant usa in ordine: host mappato su club_domains, slug esplicito, fallback controllato al default club.
- Il fallback controllato resta necessario per retrocompatibilita locale/test e per non rompere il deploy single-tenant esistente.
- L'admin auth e tenant-scoped: login, sessione cookie e password reset ora dipendono dal tenant corrente.
- I contratti public e admin vengono estesi sulle superfici esistenti; non sono stati creati router paralleli inutili.

## File reali toccati

- [backend/app/api/deps.py](backend/app/api/deps.py)
- [backend/app/api/routers/admin_auth.py](backend/app/api/routers/admin_auth.py)
- [backend/app/api/routers/admin_settings.py](backend/app/api/routers/admin_settings.py)
- [backend/app/api/routers/public.py](backend/app/api/routers/public.py)
- [backend/app/core/security.py](backend/app/core/security.py)
- [backend/app/core/scheduler.py](backend/app/core/scheduler.py)
- [backend/app/main.py](backend/app/main.py)
- [backend/app/schemas/admin.py](backend/app/schemas/admin.py)
- [backend/app/schemas/public.py](backend/app/schemas/public.py)
- [backend/app/services/booking_service.py](backend/app/services/booking_service.py)
- [backend/app/services/email_service.py](backend/app/services/email_service.py)
- [backend/app/services/payment_service.py](backend/app/services/payment_service.py)
- [backend/app/services/settings_service.py](backend/app/services/settings_service.py)
- [backend/app/services/tenant_service.py](backend/app/services/tenant_service.py)
- [backend/tests/test_tenant_backend_context.py](backend/tests/test_tenant_backend_context.py)

## Endpoint definitivi aggiornati

### Public API

- GET /api/public/config
- GET /api/public/availability
- POST /api/public/bookings
- POST /api/public/bookings/{booking_id}/checkout
- GET /api/public/bookings/{public_reference}/status
- GET /api/public/bookings/cancel/{cancel_token}
- POST /api/public/bookings/cancel/{cancel_token}

Aggiornamenti reali:

- ogni endpoint public risolve il tenant corrente tramite dependency condivisa
- availability filtra gli slot sul club corrente
- create booking scrive booking e customer sul club corrente
- checkout, status e cancellazione cercano la booking solo dentro il club corrente

### Admin Auth API

- POST /api/admin/auth/login
- POST /api/admin/auth/logout
- POST /api/admin/auth/password-reset/request
- POST /api/admin/auth/password-reset/confirm
- GET /api/admin/auth/me

Aggiornamenti reali:

- login lookup admin per club_id + email
- token admin e token reset includono club_id e club_slug
- /me rifiuta cookie validi ma riferiti a tenant diverso da quello risolto nella request
- password reset usa il tenant corrente e genera reset_url con tenant=slug

### Admin Settings API

- GET /api/admin/settings
- PUT /api/admin/settings

Aggiornamenti reali:

- booking rules tenant-scoped su app_settings
- profilo minimo tenant-scoped letto e scritto su Club
- provider flag ancora derivati dall'ambiente applicativo condiviso

### Admin Booking e Report API

- gli endpoint in [backend/app/api/routers/admin_bookings.py](backend/app/api/routers/admin_bookings.py) e [backend/app/api/routers/admin_ops.py](backend/app/api/routers/admin_ops.py) restano tenant-scoped tramite admin.club_id
- la FASE 3 completa l'isolamento a monte rendendo tenant-safe auth e tenant context

## Schema payload aggiornati

### Public config response reale

Definita in [backend/app/schemas/public.py](backend/app/schemas/public.py):

- app_name
- tenant_id
- tenant_slug
- public_name
- timezone
- currency
- contact_email
- support_email
- support_phone
- booking_hold_minutes
- cancellation_window_hours
- stripe_enabled
- paypal_enabled

Note reali:

- app_name e public_name coincidono col public_name del club corrente
- contact_email usa support_email se presente, altrimenti notification_email

### Admin session response reale

Definita in [backend/app/schemas/admin.py](backend/app/schemas/admin.py):

- email
- full_name
- role
- club_id
- club_slug
- club_public_name

### Admin settings response reale

Definita in [backend/app/schemas/admin.py](backend/app/schemas/admin.py):

- club_id
- club_slug
- public_name
- timezone
- currency
- notification_email
- support_email
- support_phone
- booking_hold_minutes
- cancellation_window_hours
- reminder_window_hours
- stripe_enabled
- paypal_enabled

### Admin settings update request reale

Definita in [backend/app/schemas/admin.py](backend/app/schemas/admin.py):

- public_name opzionale
- notification_email opzionale
- support_email opzionale
- support_phone opzionale
- booking_hold_minutes
- cancellation_window_hours
- reminder_window_hours

## Strategia reale di isolamento tenant

### Resolution e context

- [backend/app/services/tenant_service.py](backend/app/services/tenant_service.py) introduce TenantContext, resolve_tenant_context e list_active_clubs.
- [backend/app/api/deps.py](backend/app/api/deps.py) introduce get_tenant_context e get_current_club.
- La request puo risolvere il tenant da host oppure da slug esplicito.
- Il fallback al default club e controllato e usato solo quando nessun host/slug valido viene risolto.

### Auth e sessione

- [backend/app/api/routers/admin_auth.py](backend/app/api/routers/admin_auth.py) effettua lookup admin per club_id + email.
- [backend/app/core/security.py](backend/app/core/security.py) porta club_id e club_slug nei token admin e reset password.
- [backend/app/api/deps.py](backend/app/api/deps.py) rifiuta sessioni il cui club_id nel token non coincide col tenant corrente della request.

### Query critiche e mutazioni

- [backend/app/api/routers/public.py](backend/app/api/routers/public.py) filtra config, availability, checkout, status e cancellazione sul club corrente.
- [backend/app/services/booking_service.py](backend/app/services/booking_service.py) usa club_id su public booking, slot availability, update booking admin, payment confirm, expire pending e upcoming reminders.
- [backend/app/services/settings_service.py](backend/app/services/settings_service.py) legge e scrive booking rules per club e centralizza il payload settings tenant-aware.
- [backend/app/services/payment_service.py](backend/app/services/payment_service.py) usa il cancellation cutoff del club della booking.

### Side effect e scheduler

- [backend/app/services/email_service.py](backend/app/services/email_service.py) localizza date e destinatari usando il club della booking dove applicabile.
- email log e password reset log sono persistiti col club corretto.
- [backend/app/core/scheduler.py](backend/app/core/scheduler.py) itera i club attivi e usa reminder_window_hours tenant-scoped.
- expire_pending_job e reminder_job non sono piu limitati al default club.

### Bootstrap coerente

- [backend/app/main.py](backend/app/main.py) bootstrap il solo admin del default club, non un admin globale arbitrario.

## Servizi creati o estesi

### Creati o estesi in modo strutturale

- [backend/app/services/tenant_service.py](backend/app/services/tenant_service.py): tenant resolution, tenant context, lista club attivi.
- [backend/app/services/settings_service.py](backend/app/services/settings_service.py): get_tenant_settings e update_tenant_settings oltre a booking rules club-scoped.
- [backend/app/services/booking_service.py](backend/app/services/booking_service.py): public booking, slot availability, reminder/expiry tenant-scoped.
- [backend/app/services/email_service.py](backend/app/services/email_service.py): timezone e destinatari tenant-aware.
- [backend/app/services/payment_service.py](backend/app/services/payment_service.py): refund cutoff tenant-aware.

## Test aggiunti o modificati

### Nuovi test

File: [backend/tests/test_tenant_backend_context.py](backend/tests/test_tenant_backend_context.py)

Copertura reale:

- tenant resolution e session admin scoped by host su default club e secondo tenant
- public availability filtrata per tenant
- create booking pubblico scrive dati sul tenant corretto
- admin non puo leggere booking di altro tenant
- admin settings e public config restano isolati per tenant
- password reset request tenant-scoped
- reminder_job usa reminder_window_hours tenant-scoped

### Regressioni verificate

- suite completa backend verde
- nessuna regressione residua sui test legacy toccati

## Punti di impatto frontend

- il frontend pubblico puo leggere da /api/public/config nuovi campi: tenant_id, tenant_slug, public_name, contact_email, support_email, support_phone.
- il frontend admin riceve da /api/admin/auth/me metadati tenant: club_id, club_slug, club_public_name, role.
- il frontend admin puo leggere e scrivere da /api/admin/settings i campi public_name, notification_email, support_email e support_phone oltre alle booking rules.
- i flussi non devono cambiare endpoint: devono solo consumare i campi aggiuntivi.
- in ambienti di test o fallback controllato, la tenant resolution puo essere forzata via slug esplicito; in produzione il path principale resta il dominio/host mappato.

## Deviazioni intenzionali dal piano

- non e stato introdotto un endpoint separato di tenant profile: il profilo minimo tenant e stato esposto estendendo i contratti public e admin esistenti.
- non e stato introdotto RBAC aggiuntivo: il ruolo admin minimo resta quello gia presente nel repository.

## Rischi residui reali

- la logica di calendario e parsing slot in [backend/app/services/booking_service.py](backend/app/services/booking_service.py) usa ancora la timezone applicativa globale per il calcolo degli slot; con club in timezone diverse serve un passaggio ulteriore di hardening.
- il fallback tenant da slug/header/query va mantenuto come strumento compatibile e controllato; in produzione il dominio mappato deve restare il meccanismo principale.
- il frontend non e ancora stato aggiornato per mostrare branding e contatti tenant-aware: questo resta lavoro della FASE 4.
- payment_webhook_events resta ancora log tecnico globale come gia deciso in FASE 2.

## PASS/FAIL finale

- PASS reale.

## CONTEXT BLOCK PER FASE_4

- Il backend e ora request-aware rispetto al tenant su public, admin auth e admin settings.
- I contratti public e admin espongono gia i metadati minimi per branding e contatti tenant-aware.
- Il frontend deve essere adattato a consumare questi campi senza duplicare router o client API.
- Le route restano invariate: la FASE 4 deve lavorare soprattutto su types, service client e pagine React esistenti.
- Il deploy resta compatibile single-tenant grazie al default club fallback.