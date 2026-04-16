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

## Environment e URL operative

### File `.env`

- copia `.env.example` in `.env` nella root del repository
- il backend legge automaticamente il file `.env` dalla root anche se i comandi vengono lanciati da `backend/`
- in locale/test puoi lasciare SQLite
- su Railway devi impostare le stesse variabili come environment variables del servizio

### Variabili minime in locale/test

- `SECRET_KEY`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`
- `DATABASE_URL` opzionale se vuoi tenere il default SQLite
- credenziali Stripe e/o PayPal solo se vuoi provare i provider reali invece del comportamento mock ammesso in development/test
- i placeholder presenti in `.env.example` sono ammessi solo come base locale; non sono valori sicuri per produzione

### Variabili minime in produzione/Railway

- `APP_ENV=production`
- `APP_URL=https://tuo-dominio-pubblico`
- `SECRET_KEY=<valore forte>`
- `ADMIN_EMAIL=<email reale>`
- `ADMIN_PASSWORD=<password forte>`
- `DATABASE_URL=<connection string PostgreSQL Railway>`
- `SCHEDULER_ENABLED=true` solo sull'istanza designata a eseguire reminder e scadenze
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` se usi Stripe
- `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID` se usi PayPal
- `PAYPAL_BASE_URL=https://api-m.paypal.com` in produzione PayPal

In produzione il bootstrap fallisce esplicitamente se `SECRET_KEY`, `ADMIN_EMAIL` o `ADMIN_PASSWORD` restano mancanti, vuoti o uguali ai placeholder di `.env.example`.

### URL webhook e redirect derivati da `APP_URL`

Con `APP_URL=https://tuo-dominio` il codice usa automaticamente:

- Stripe webhook: `https://tuo-dominio/api/payments/stripe/webhook`
- Stripe cancel redirect: `https://tuo-dominio/api/payments/stripe/cancel?booking=...`
- Stripe success redirect: `https://tuo-dominio/booking/success?booking=...`
- PayPal return: `https://tuo-dominio/api/payments/paypal/return?booking=...`
- PayPal cancel: `https://tuo-dominio/api/payments/paypal/cancel?booking=...`
- PayPal webhook: `https://tuo-dominio/api/payments/paypal/webhook`

Quando cambi dominio Railway o colleghi un custom domain, aggiorna `APP_URL` e riallinea anche le configurazioni webhook nei provider.

## Avvio locale

### 1. Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
cd backend
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 3. Check locale rapido

- API health: `http://127.0.0.1:8000/api/health`
- SPA servita dal backend: `http://127.0.0.1:8000/`
- frontend Vite in sviluppo: `http://127.0.0.1:5173/`

## Test e validazione locale

### Backend

```bash
cd backend
../.venv/bin/python -m pytest tests -q
```

### Frontend

```bash
cd frontend
npm run build
npm run test:run
```

## Docker

Il `Dockerfile` in root:

- esegue build frontend Vite in stage separato
- copia la build in `frontend_dist`
- installa dipendenze backend
- esegue `alembic upgrade head`
- avvia Uvicorn sulla porta `PORT` fornita da Railway oppure `8000`
- espone un `HEALTHCHECK` interno verso `GET /api/health`

### Build immagine

```bash
docker build -t padelbooking:local .
```

### Smoke test container

```bash
docker run --rm --env-file .env -e PORT=8000 -p 8000:8000 padelbooking:local
```

In un secondo terminale:

```bash
curl http://127.0.0.1:8000/api/health
curl -I http://127.0.0.1:8000/
```

Per smoke locali puoi lasciare `DATABASE_URL=sqlite:///./padelbooking.db`. In produzione il container deve usare PostgreSQL Railway.

## Deploy su Railway

### Passi concreti

1. crea un nuovo progetto Railway collegato a questo repository
2. aggiungi un servizio PostgreSQL Railway al progetto
3. crea o usa il servizio applicativo basato sul `Dockerfile` in root
4. configura nel servizio app le env vars minime partendo da `.env.example`
5. imposta `DATABASE_URL` con la connection string PostgreSQL fornita da Railway
6. imposta `APP_ENV=production`
7. imposta `APP_URL` con il dominio pubblico Railway assegnato al servizio
8. imposta `SCHEDULER_ENABLED=true` solo sull'istanza che deve eseguire reminder e scadenze
9. se usi repliche aggiuntive, imposta `SCHEDULER_ENABLED=false` su quelle repliche
10. configura SMTP reale se vuoi invio email operativo
11. configura Stripe e/o PayPal se vuoi i provider reali in produzione
12. avvia il deploy: il container esegue automaticamente `alembic upgrade head` e poi Uvicorn
13. verifica nei log che migrazioni e bootstrap siano completati senza errori
14. verifica `GET /api/health`
15. verifica che `GET /` serva la SPA buildata
16. verifica login admin e flusso booking base

### Strategia scheduler su Railway

- lo scheduler APScheduler gira dentro il processo FastAPI gia presente nel servizio web
- la strategia supportata e pragmatica: una sola istanza con scheduler attivo
- se usi una sola istanza backend, lascia `SCHEDULER_ENABLED=true`
- se usi piu repliche web, solo una deve avere `SCHEDULER_ENABLED=true`
- il lock applicativo e il lock advisory PostgreSQL riducono il rischio di overlap breve, ma non sostituiscono la corretta configurazione di una sola istanza scheduler attiva
- l'healthcheck Railway resta `GET /api/health`

### Configurazione provider dopo il deploy

#### Stripe

- webhook endpoint: `${APP_URL}/api/payments/stripe/webhook`
- il redirect di successo usa `${APP_URL}/booking/success?booking=...`
- il redirect di annullamento usa `${APP_URL}/api/payments/stripe/cancel?booking=...`

#### PayPal

- in produzione usa `PAYPAL_BASE_URL=https://api-m.paypal.com`
- return URL: `${APP_URL}/api/payments/paypal/return?booking=...`
- cancel URL: `${APP_URL}/api/payments/paypal/cancel?booking=...`
- webhook endpoint: `${APP_URL}/api/payments/paypal/webhook`

### Custom domain

Se colleghi un custom domain:

1. associa il dominio dal pannello Railway
2. aggiorna `APP_URL` con il nuovo dominio pubblico
3. riallinea Stripe e PayPal con i nuovi URL webhook e redirect
4. riesegui i check su `/api/health`, SPA e login admin

## Limiti noti reali

- SQLite resta supportato solo per locale/test; Railway deve usare PostgreSQL
- in development/test i pagamenti mock possono restare disponibili; in produzione servono provider reali configurati
- senza SMTP configurato le email vengono segnate come `SKIPPED` in locale/test e come `FAILED` in ambienti operativi
- lo scheduler in-process e volutamente semplice e richiede disciplina di deploy su Railway per evitare duplicazioni
