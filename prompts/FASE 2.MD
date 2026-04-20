Agisci come un Senior Full-Stack Engineer, Software Architect pragmatico, Product Designer mobile-first, Payments Integrator e DevOps Engineer per Railway.

Stai costruendo una web app completa di prenotazione per 1 solo campo da padel, pronta per essere sviluppata in repository e deployata su Railway.

## Contesto fisso del prodotto

L’app deve permettere a utenti esterni di:
- vedere disponibilità e slot prenotabili
- scegliere data, orario e durata
- inserire i propri dati
- pagare una caparra online
- scegliere se pagare la caparra con Stripe oppure PayPal
- ricevere conferma prenotazione

Il saldo residuo viene pagato manualmente al campo.

L’admin deve poter gestire:
- disponibilità
- chiusure/blocchi
- prenotazioni manuali
- prenotazioni ricorrenti
- stati delle prenotazioni
- report essenziali
- pagamenti caparra e saldo al campo

## Vincoli fissi

- 1 solo campo da padel
- niente multi-club
- niente multi-campo
- niente marketplace
- niente social/chat/classifiche
- niente app nativa
- utenti esterni senza login obbligatorio nella prima versione
- area admin protetta
- campo aperto 24/7
- durata prenotabile minima: 60 minuti
- durata prenotabile massima: 5 ore
- durata selezionabile solo in blocchi da 30 minuti
- timezone: Europe/Rome
- valuta: EUR
- deploy su Railway
- backend: FastAPI + SQLAlchemy + PostgreSQL + Alembic + Pydantic v2
- frontend: React + TypeScript + Vite + Tailwind CSS
- niente overengineering
- niente dipendenze inutili

## Regole di business fisse

### Durate valide
- 60
- 90
- 120
- 150
- 180
- 210
- 240
- 270
- 300

### Caparra
- €20 fino a 90 minuti inclusi
- +€10 per ogni ulteriore blocco di 30 minuti oltre i 90 minuti

Esempi:
- 60 min = €20
- 90 min = €20
- 120 min = €30
- 150 min = €40
- 180 min = €50
- 210 min = €60
- 240 min = €70
- 270 min = €80
- 300 min = €90

### Tariffe informative da mostrare all’utente
- Tesserati: €7/ora per giocatore
- Non tesserati: €9/ora per giocatore
- 90 minuti: €10 tesserati per giocatore, €13 non tesserati per giocatore

Queste tariffe sono solo informative e non sostituiscono la caparra.

### Stati prenotazione minimi
- `PENDING_PAYMENT`
- `CONFIRMED`
- `CANCELLED`
- `COMPLETED`
- `NO_SHOW`
- `EXPIRED`

### Regole critiche
- nessuna doppia prenotazione confermata sullo stesso slot
- validazione server-side forte
- controllo finale disponibilità prima della conferma
- timeout default prenotazioni `PENDING_PAYMENT`: 15 minuti
- scaduta la prenotazione, lo slot torna disponibile
- finestra cancellazione default: 24 ore prima
- admin può creare prenotazioni ricorrenti:
  - stesso giorno della settimana
  - stesso orario
  - stessa durata
  - per N settimane
  - entro lo stesso anno solare
  - creare solo occorrenze valide
  - saltare quelle in conflitto
  - restituire report finale con create / saltate / motivi

## Regole UX/UI fisse

La UI deve essere:
- moderna
- bella
- pulita
- mobile-first
- ordinata
- con card ben disegnate
- con pulsanti grandi e chiari
- con forte gerarchia visiva
- con feedback comprensibili
- con look professionale e non da demo tecnica

Il frontend non deve sembrare:
- una demo
- un template cheap
- un backend travestito
- un form grezzo con poco CSS
- una UI anonima generata automaticamente

## Regola di comportamento

- non divagare
- non fare teoria inutile
- non proporre 10 alternative
- non cambiare stack
- non cambiare perimetro
- scegli la soluzione più pratica e implementabile
- produci output concreti
- niente pseudo-codice spacciato per codice
- niente TODO vuoti
- niente placeholder finti

## Regola di validazione obbligatoria

Alla fine di ogni fase devi aggiungere una sezione chiamata `Verifica di fine fase` con:
- controlli eseguiti
- esito PASS / FAIL / NOT APPLICABLE
- criticità rilevate
- correzioni applicate
- gate finale:
  - `FASE VALIDATA - si può procedere`
  - `FASE NON VALIDATA - non procedere alla fase successiva`

Non considerare completata una fase solo perché il codice è stato scritto. Una fase è completata solo se il codice o la progettazione della fase sono coerenti, verificati e senza blocchi evidenti per la fase successiva.

Mantieni sempre il focus sull’implementazione reale.

# PROMPT FASE 2 — BACKEND COMPLETO

Usa il blocco comune come contesto fisso e considera validata la Fase 1.

Ora esegui solo la **Fase 2**.

## Obiettivo della fase

Costruire il backend completo e reale del progetto.

## Output richiesto

Fornisci il backend completo, organizzato per file reali, includendo:

## 1. Struttura backend
Fornisci il file tree del backend, coerente e pronto per repo reale.

## 2. Configurazione
Genera:
- configurazione settings/env
- gestione environment variables
- connessione DB
- config timezone
- config providers pagamenti
- config scheduler

## 3. Modelli SQLAlchemy
Scrivi tutti i modelli necessari con campi, relazioni, vincoli e indici coerenti.

## 4. Schemi Pydantic
Scrivi tutti gli schemi request/response necessari.

## 5. Alembic
Genera base migrazioni e prima migrazione iniziale coerente con i modelli.

## 6. Servizi core
Implementa servizi reali per:
- disponibilità slot
- creazione prenotazione provvisoria
- verifica overlap
- calcolo caparra
- gestione booking admin
- gestione ricorrenze
- gestione blackout
- scadenza prenotazioni
- aggiornamento stati
- log eventi business

## 7. Auth admin
Implementa auth admin reale e semplice:
- login
- logout
- me
- protezione endpoint admin
- hashing password
- sessione/cookie oppure JWT httpOnly cookie, scegli la soluzione più coerente

## 8. API FastAPI
Genera router completi per:
- public booking
- admin booking
- admin recurring bookings
- blackouts
- settings essenziali
- healthcheck

## 9. Gestione errori
Implementa:
- eccezioni applicative
- response error coerenti
- validazione robusta
- messaggi coerenti

## 10. Logging tecnico e business
Implementa logging tecnico e audit/business log minimi utili.

## Requisiti di qualità
- niente pseudo-codice
- file completi
- codice eseguibile
- dipendenze coerenti
- naming pulito
- patch minime e niente ridondanze inutili

## Verifica di fine fase
Esegui una validazione della fase verificando almeno:
- fase precedente
- avvio backend
- import corretti
- migrazioni applicabili
- coerenza modelli/schemi/router
- test integrazione database
- test endpoint principali
- test simulato concorrenza booking
- assenza di mismatch tra API e business rules
- assenza di blocchi per la fase 3

Chiudi con:
- `FASE VALIDATA - si può procedere` e fermati.
oppure
- `FASE NON VALIDATA - non procedere alla fase successiva`

---

# OUTPUT FASE 2

## 1. Struttura backend

File tree reale del backend implementato:

```text
backend/
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 20260415_0001_initial.py
├── alembic.ini
├── app/
│   ├── api/
│   │   ├── deps.py
│   │   └── routers/
│   │       ├── admin_auth.py
│   │       ├── admin_bookings.py
│   │       ├── admin_ops.py
│   │       ├── admin_settings.py
│   │       ├── payments.py
│   │       └── public.py
│   ├── core/
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── errors.py
│   │   ├── scheduler.py
│   │   └── security.py
│   ├── models/
│   │   └── __init__.py
│   ├── schemas/
│   │   ├── admin.py
│   │   ├── common.py
│   │   └── public.py
│   ├── services/
│   │   ├── booking_service.py
│   │   ├── email_service.py
│   │   ├── payment_service.py
│   │   ├── report_service.py
│   │   └── settings_service.py
│   └── main.py
├── requirements.txt
└── tests/
    ├── conftest.py
    ├── test_admin_and_recurring.py
    └── test_booking_api.py
```

## 2. Configurazione

- Settings e variabili ambiente in app/core/config.py con pydantic-settings.
- Connessione database in app/core/db.py con SQLAlchemy 2 e SessionLocal.
- Timezone centrale Europe/Rome usata in settings e booking_service via ZoneInfo.
- Config pagamenti in config.py:
  - Stripe secret key, publishable key, webhook secret
  - PayPal client id, client secret, base url, webhook id
- Config scheduler in config.py e app/core/scheduler.py:
  - booking_hold_minutes
  - cancellation_window_hours
  - reminder_window_hours persistito in app_settings
- Config env reale supportata da .env.example in root.

## 3. Modelli SQLAlchemy

Tutti i modelli sono definiti in app/models/__init__.py.

- Admin:
  - email univoca
  - password_hash
  - ruolo admin
  - stato attivo
- Customer:
  - first_name, last_name, phone, email, note
- Booking:
  - reference pubblico
  - start_at, end_at, booking_date_local
  - duration_minutes
  - status
  - deposit_amount
  - payment_provider, payment_status, payment_reference
  - cancel_token, expires_at
  - balance_paid_at, completed_at, no_show_at, cancelled_at
  - source, created_by, recurring_series_id
- BookingPayment:
  - stato pagamento provider
  - importo, valuta, order id, capture id, checkout url
- BookingEventLog:
  - audit log business per prenotazione e operazioni admin/payment
- BlackoutPeriod:
  - blocchi e chiusure con intervallo temporale
- RecurringBookingSeries:
  - metadati serie ricorrente admin
- AppSetting:
  - configurazioni operative persistite
- PaymentWebhookEvent:
  - idempotenza webhook Stripe e PayPal
- EmailNotificationLog:
  - log di invio email

Vincoli e protezioni reali:

- unique su public_reference booking
- unique su event_id dei webhook
- indici su start_at, end_at, status, payment_status, payment_provider, expires_at
- exclusion constraint PostgreSQL in migrazione per impedire overlap su slot bloccanti

## 4. Schemi Pydantic

Schemi request/response implementati:

- app/schemas/common.py
  - BookingCustomerData
  - BookingSummary
  - TimeSlot
  - SimpleMessage
- app/schemas/public.py
  - AvailabilityResponse
  - PublicBookingCreateRequest
  - PublicBookingCreateResponse
  - BookingStatusResponse
  - PaymentInitResponse
  - PublicConfigResponse
- app/schemas/admin.py
  - AdminLoginRequest
  - AdminMeResponse
  - AdminBookingCreateRequest
  - AdminBookingStatusUpdate
  - BlackoutCreateRequest
  - RecurringSeriesPreviewRequest
  - RecurringPreviewResponse
  - RecurringCreateResponse
  - BookingListResponse
  - ReportResponse
  - AdminSettingsResponse
  - AdminSettingsUpdateRequest

## 5. Alembic

Base Alembic completa:

- alembic.ini
- alembic/env.py
- alembic/script.py.mako
- prima migrazione iniziale in alembic/versions/20260415_0001_initial.py

La migrazione crea tutte le tabelle richieste e, in PostgreSQL, abilita la protezione DB-level contro gli overlap con exclusion constraint.

## 6. Servizi core

Servizi reali implementati:

- booking_service.py
  - calculate_deposit
  - parse_slot
  - assert_slot_available
  - build_daily_slots
  - create_public_booking
  - create_admin_booking
  - create_recurring_series
  - create_blackout
  - cancel_booking
  - mark_booking_paid
  - expire_pending_bookings
  - upcoming_reminders
  - list_bookings
  - log_event
- payment_service.py
  - avvio checkout Stripe
  - avvio order PayPal
  - capture PayPal
  - gestione webhook Stripe/PayPal
  - idempotenza webhook
  - fallback mock per ambienti senza credenziali
- settings_service.py
  - lettura e aggiornamento regole booking persistite in app_settings
- report_service.py
  - aggregazione dashboard admin
- email_service.py
  - email conferma, cancellazione, scadenza, reminder, admin notification

Protezione concorrenza implementata:

- advisory lock PostgreSQL sul singolo campo
- lock applicativo reentrante per ambiente test/SQLite
- commit tenuto dentro la stessa sezione critica per booking, blackout, ricorrenze e conferme pagamento

## 7. Auth admin

Auth admin implementata in modo semplice e coerente:

- login: app/api/routers/admin_auth.py
- logout: app/api/routers/admin_auth.py
- me: app/api/routers/admin_auth.py
- dipendenza di protezione endpoint: app/api/deps.py
- password hashing: app/core/security.py con pbkdf2_sha256
- sessione admin: JWT firmato salvato in cookie httpOnly

## 8. API FastAPI

Router completi presenti:

- Public
  - GET /api/public/config
  - GET /api/public/availability
  - POST /api/public/bookings
  - POST /api/public/bookings/{booking_id}/checkout
  - GET /api/public/bookings/{public_reference}/status
  - POST /api/public/bookings/cancel/{cancel_token}
- Admin auth
  - POST /api/admin/auth/login
  - POST /api/admin/auth/logout
  - GET /api/admin/auth/me
- Admin bookings
  - GET /api/admin/bookings
  - GET /api/admin/bookings/{booking_id}
  - POST /api/admin/bookings
  - POST /api/admin/bookings/{booking_id}/cancel
  - POST /api/admin/bookings/{booking_id}/status
  - POST /api/admin/bookings/{booking_id}/balance-paid
- Admin operations
  - GET /api/admin/blackouts
  - POST /api/admin/blackouts
  - POST /api/admin/recurring/preview
  - POST /api/admin/recurring
  - GET /api/admin/reports/summary
  - GET /api/admin/events
- Admin settings
  - GET /api/admin/settings
  - PUT /api/admin/settings
- Payments e health
  - POST /api/payments/stripe/webhook
  - GET /api/payments/paypal/return
  - POST /api/payments/paypal/webhook
  - GET /api/payments/mock/complete
  - GET /api/health

## 9. Gestione errori

Gestione errori centralizzata in app/core/errors.py:

- RequestValidationError -> 422 con payload coerente e lista errors
- HTTPException -> risposta normalizzata con detail
- Exception generica -> 500 con messaggio pulito lato client e log tecnico lato server

Validazioni robuste presenti su:

- durate consentite
- provider pagamento
- privacy obbligatoria
- intervalli blackout validi
- stesso anno solare per ricorrenze
- finestra cancellazione
- slot futuri e non sovrapposti

## 10. Logging tecnico e business

- logging middleware request/response in app/main.py
- audit log business in booking_events_log
- log webhook in payment_webhook_events
- log invio email in email_notifications_log
- log reminder e scadenze via scheduler

## Verifica di fine fase

### Controlli eseguiti

- fase precedente
- import corretti e sintassi backend
- avvio applicazione FastAPI
- healthcheck /api/health
- migrazioni Alembic applicabili con upgrade head
- coerenza modelli/schemi/router
- test integrazione database
- test endpoint principali public/admin
- test simulato concorrenza booking sullo stesso slot
- verifica settings admin persistite e riflesse sulla config pubblica
- assenza di mismatch tra API e business rules

### Esito

- fase precedente: PASS
- import corretti e sintassi backend: PASS
- avvio applicazione FastAPI: PASS
- healthcheck /api/health: PASS
- migrazioni Alembic applicabili: PASS
- coerenza modelli/schemi/router: PASS
- test integrazione database: PASS
- test endpoint principali: PASS
- test simulato concorrenza booking: PASS
- verifica settings admin: PASS
- assenza di mismatch tra API e business rules: PASS
- blocchi per la fase 3: PASS

### Criticità rilevate

- Race condition reale su SQLite test durante due richieste concorrenti sullo stesso slot.

### Correzioni applicate

- Sostituito lock semplice con RLock applicativo in booking_service.
- Spostato il commit dentro la stessa sezione critica per create booking, blackout, ricorrenze e conferma pagamento.
- Rilanciata la suite backend completa dopo il fix concorrente.

### Gate finale

FASE VALIDATA - si può procedere