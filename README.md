# PadelBooking

Web app completa per la prenotazione di un solo campo da padel, pensata per utenti pubblici senza login obbligatorio e per una gestione admin protetta. Stack: FastAPI, PostgreSQL, SQLAlchemy 2, Alembic, React, TypeScript, Tailwind, Stripe, PayPal, deploy su Railway.

## Cosa include

- booking pubblico mobile-first con selezione data, orario e durata
- caparra dinamica online con Stripe o PayPal
- conferma prenotazione solo dopo pagamento riuscito
- area admin protetta con login via cookie httpOnly
- filtri prenotazioni, blackout, ricorrenze, saldo al campo, completed e no-show
- log business essenziali e reminder automatici
- Dockerfile, healthcheck e guida deploy Railway

## Architettura scelta

### Backend

- FastAPI con API sotto prefisso `/api`
- SQLAlchemy 2.x con modelli espliciti
- Pydantic v2 per validazione e serializzazione
- Alembic per migrazione iniziale
- scheduler leggero con APScheduler per scadenze e reminder
- password admin hashata e sessione admin con cookie httpOnly
- astrazione pagamenti separata dalla logica booking

### Frontend

- React + TypeScript + Vite
- React Router per flussi pubblico e admin
- Tailwind CSS con design system leggero e coerente
- interfaccia mobile-first con card, CTA chiare e feedback chiari
- stessa base API `/api`, pronta per servire la SPA dallo stesso dominio in produzione

## Struttura repository

```text
.
├── backend/
│   ├── alembic/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── services/
│   └── package.json
├── Dockerfile
├── railway.json
└── .env.example
```

## Schema database

| Tabella | Scopo | Campi chiave |
| --- | --- | --- |
| admins | accesso admin | email, password_hash, is_active |
| customers | dati cliente esterno | first_name, last_name, email, phone |
| bookings | prenotazioni e stato | start_at, end_at, duration_minutes, status, deposit_amount, payment_provider, payment_status |
| booking_payments | traccia tentativi e riferimenti provider | provider_order_id, provider_capture_id, checkout_url |
| booking_events_log | audit trail business | event_type, actor, message, payload |
| blackout_periods | blocchi o chiusure | title, start_at, end_at, is_active |
| recurring_booking_series | serie ricorrenti admin | weekday, start_time, duration_minutes, weeks_count |
| app_settings | configurazioni base evolutive | key, value |
| payment_webhook_events | idempotenza webhooks | provider, event_id, event_type |
| email_notifications_log | log invii email | template, recipient, status |

## Regole di business implementate

### Durata valida

- minimo 60 minuti
- massimo 300 minuti
- solo step da 30 minuti

### Caparra online

- 60 min = €20
- 90 min = €20
- da 120 min in poi: +€10 ogni 30 minuti oltre i 90

Formula:

```text
deposit = 20€ fino a 90 minuti inclusi
oltre i 90 minuti: 20€ + 10€ × numero blocchi extra da 30 minuti
```

### Protezione anti-doppia prenotazione

- controllo server-side su ogni creazione o conferma
- lock transazionale per il singolo campo in PostgreSQL
- vincolo univoco su riferimento pubblico
- constraint di overlap a livello database in PostgreSQL tramite exclusion constraint

### Timeout pagamento

- default 15 minuti
- stato automatico `EXPIRED`
- slot nuovamente disponibile dopo la scadenza

### Ricorrenze admin

- stesso giorno della settimana
- stesso orario
- stessa durata
- per N settimane
- nello stesso anno solare
- default: crea le occorrenze valide e salta quelle in conflitto

## Stati booking previsti

- `PENDING_PAYMENT`
- `CONFIRMED`
- `CANCELLED`
- `COMPLETED`
- `NO_SHOW`
- `EXPIRED`

## API principali

### Public API

- `GET /api/public/config`
- `GET /api/public/availability`
- `POST /api/public/bookings`
- `POST /api/public/bookings/{booking_id}/checkout`
- `GET /api/public/bookings/{public_reference}/status`
- `POST /api/public/bookings/cancel/{cancel_token}`

### Admin API

- `POST /api/admin/auth/login`
- `POST /api/admin/auth/logout`
- `GET /api/admin/auth/me`
- `GET /api/admin/bookings`
- `POST /api/admin/bookings`
- `POST /api/admin/bookings/{id}/cancel`
- `POST /api/admin/bookings/{id}/status`
- `POST /api/admin/bookings/{id}/balance-paid`
- `GET /api/admin/reports/summary`
- `POST /api/admin/blackouts`
- `POST /api/admin/recurring/preview`
- `POST /api/admin/recurring`

### Payments e health

- `POST /api/payments/stripe/webhook`
- `GET /api/payments/paypal/return`
- `POST /api/payments/paypal/webhook`
- `GET /api/health`

## Avvio locale

### 1. Variabili ambiente

Copia `.env.example` in `.env` e compila almeno:

- `DATABASE_URL`
- `SECRET_KEY`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`
- credenziali Stripe e/o PayPal se vuoi il flusso reale

### 2. Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

## Deploy su Railway

### Passi concreti

1. crea un nuovo progetto Railway collegato al repository
2. aggiungi un servizio PostgreSQL Railway
3. configura le env vars del servizio app usando `.env.example`
4. imposta `DATABASE_URL` con la connection string Railway PostgreSQL
5. Railway userà il `Dockerfile` presente in root
6. al deploy partiranno migrazione Alembic e app FastAPI
7. verifica `https://tuo-dominio/api/health`
8. testa il flusso booking e login admin
9. opzionale: collega un custom domain dal pannello Railway

### Env vars minime produzione

- `APP_ENV=production`
- `APP_URL=https://tuo-dominio`
- `SECRET_KEY=<valore forte>`
- `DATABASE_URL=<url postgres railway>`
- `SCHEDULER_ENABLED=true` solo sull'istanza designata a eseguire i job
- `ADMIN_EMAIL=<email reale>`
- `ADMIN_PASSWORD=<password forte>`
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
- `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`
- parametri SMTP per email reali

### Strategia job su Railway

- lo scheduler APScheduler gira nel processo web FastAPI gia presente nel repository
- abilita `SCHEDULER_ENABLED=true` solo sull'istanza designata a eseguire reminder e scadenze
- eventuali repliche web o processi aggiuntivi devono avere `SCHEDULER_ENABLED=false`
- se mantieni una sola istanza backend attiva, lascia `SCHEDULER_ENABLED=true` su quella sola istanza
- l'healthcheck resta invariato su `/api/health`
- il lock applicativo e il lock advisory PostgreSQL riducono il rischio di doppia esecuzione anche in caso di overlap breve, ma la configurazione corretta resta avere una sola istanza scheduler attiva

## Verifica di fine fase

### Fase 1
- Controlli eseguiti: coerenza architettura, schema dati, struttura repo
- Esito: PASS
- Gate di avanzamento: FASE VALIDATA - si può procedere

### Fase 2
- Controlli eseguiti: test backend, creazione booking, anti-overlap, admin login, ricorrenze
- Esito: PASS
- Evidenza: `3 passed` su pytest
- Gate di avanzamento: FASE VALIDATA - si può procedere

### Fase 3
- Controlli eseguiti: build frontend, type-check TypeScript, integrazione API client
- Esito: PASS
- Evidenza: build Vite completata con successo
- Gate di avanzamento: FASE VALIDATA - si può procedere

### Fase 4
- Controlli eseguiti: avvio checkout Stripe/PayPal, mock fallback locale, webhook handlers idempotenti
- Esito: PASS
- Gate di avanzamento: FASE VALIDATA - si può procedere

### Fase 5
- Controlli eseguiti: log business, email log, reminder e scadenze scheduler
- Esito: PASS
- Gate di avanzamento: FASE VALIDATA - si può procedere

### Fase 6
- Controlli eseguiti: Dockerfile, env vars, healthcheck, configurazione Railway
- Esito: PASS strutturale
- Gate di avanzamento: FASE VALIDATA - si può procedere

### Fase 7
- Controlli eseguiti: smoke test booking pubblico, admin flow, casi limite principali da checklist
- Esito: PASS su smoke e test automatici presenti
- Gate di avanzamento: FASE VALIDATA - si può procedere

## Checklist test minima

- [x] booking pubblico 90 minuti
- [x] conferma caparra e stato `CONFIRMED`
- [x] prevenzione doppia prenotazione sullo stesso slot
- [x] login admin e prenotazione manuale
- [x] preview ricorrenza con conflitti
- [ ] collegamento provider reali in ambiente di produzione
- [ ] verifica SMTP reale in ambiente di produzione
- [ ] smoke test post deploy Railway con dominio finale

## Hardening successivo consigliato

- CSRF token sulle mutate admin se si estende l’area riservata
- rate limiting distribuito con Redis per traffico elevato
- invio email tramite provider dedicato come Resend o Postmark
- logging centralizzato con Sentry o OpenTelemetry
- refund automatico nei rari casi di pagamento tardivo su slot ormai occupato
