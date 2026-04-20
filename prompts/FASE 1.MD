# BLOCCO COMUNE DA TENERE IN TESTA A OGNI FASE

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

# PROMPT FASE 1 — ARCHITETTURA, REPO, DATABASE, BUSINESS RULES

Usa il blocco comune come contesto fisso.

Ora esegui solo la **Fase 1**.

## Obiettivo della fase

Definire in modo rigoroso e implementabile:
- architettura completa
- struttura del repository
- file tree iniziale
- decisioni tecniche chiave
- schema database
- modello dati
- API surface iniziale
- regole di business formalizzate
- flussi principali utente/admin
- design system base e mappa schermate

## Output richiesto

Fornisci, in quest’ordine:

## 1. Architettura applicativa
Descrivi in modo concreto:
- backend FastAPI
- frontend React/Vite/TypeScript/Tailwind
- PostgreSQL
- migrazioni Alembic
- integrazione Stripe
- integrazione PayPal
- scheduler/job
- gestione webhooks
- auth admin
- serving frontend/backend in produzione
- config env
- strategia deploy Railway

## 2. Struttura repository
Fornisci un file tree chiaro e realistico, ad esempio:
- `backend/`
- `frontend/`
- `infra/` o equivalente se davvero utile
- file root come `Dockerfile`, `docker-compose.yml` se utile solo per locale, `README.md`, `.env.example`

Il file tree deve essere coerente con un progetto vero.

## 3. Decisioni tecniche chiave
Spiega solo le decisioni davvero importanti, ad esempio:
- auth admin
- gestione concorrenza prenotazioni
- scelta struttura API
- strategia webhook
- scheduler
- gestione timezone Europe/Rome
- strategia deploy Railway

## 4. Schema database
Definisci le tabelle minime necessarie, almeno:
- `admins`
- `customers`
- `bookings`
- `booking_payments`
- `booking_events_log`
- `blackout_periods`
- `recurring_booking_series`
- `app_settings`

Se utili, aggiungi:
- `payment_webhook_events`
- `email_notifications_log`

Per ogni tabella fornisci:
- scopo
- campi
- tipi
- vincoli
- indici
- unique constraints
- relazioni

## 5. Modello dati prenotazione
Formalizza il modello dati della prenotazione con tutti i campi necessari, compresi:
- id
- reference code
- start_at
- end_at
- duration_minutes
- status
- deposit_amount
- payment provider
- payment status
- source
- recurring_series_id
- audit timestamps
- metadata utili

## 6. Business rules formalizzate
Scrivi in modo preciso:
- durate valide
- formula caparra
- gestione caparra Stripe/PayPal
- tariffe informative
- timeout `PENDING_PAYMENT`
- regole di conferma
- regole anti-overlap
- regole blackout
- regole ricorrenze admin
- regole cancellazione
- regole reminder
- regole stato prenotazione
- logica di rilascio slot

## 7. Superficie API iniziale
Elenca gli endpoint previsti, divisi in:
- public
- admin
- payments/webhooks
- health

Per ogni endpoint indica:
- metodo
- path
- scopo
- auth richiesta o no

## 8. Flussi funzionali principali
Descrivi in modo operativo i flussi:
- booking pubblico
- pagamento Stripe
- pagamento PayPal
- conferma prenotazione
- timeout mancato pagamento
- prenotazione manuale admin
- ricorrenza admin
- cancellazione
- marking saldo/completed/no-show

## 9. Mappa UX/UI
Fornisci:
- pagine pubbliche
- pagine admin
- componenti principali
- stati UI principali
- box tariffe informative
- box caparra
- layout mobile-first
- design system base

## 10. Rischi tecnici reali
Segnala solo i rischi veri e come intendi neutralizzarli.

## Verifica di fine fase
Esegui una validazione della fase verificando almeno:
- coerenza architettura
- coerenza schema database
- coerenza repository structure
- coerenza tra business rules e modello dati
- assenza di conflitti evidenti con pagamenti e ricorrenze
- assenza di blocchi per la fase 2

Chiudi con:
- `FASE VALIDATA - si può procedere`
oppure
- `FASE NON VALIDATA - non procedere alla fase successiva`

---

# ESITO FASE 1 — VERIFICA E ALLINEAMENTO REPOSITORY

La repository è stata verificata rispetto al nuovo prompt di Fase 1 e riallineata dove necessario. Le correzioni applicate in questa passata sono:

- `.env.example` ora punta a PostgreSQL come database target coerente con Railway e con il perimetro di prodotto.
- la disponibilità server-side marca gli slot già passati come non prenotabili, evitando mismatch tra lista slot e regole di business.
- il frontend pubblico consente la selezione del giorno corrente, coerentemente con il vincolo di campo aperto 24/7.
- il bootstrap applicativo usa Alembic come unica fonte di verità per lo schema e non ricrea più le tabelle SQLite all’avvio.
- `.dockerignore` e `.gitignore` escludono in modo ricorsivo i database SQLite locali, evitando contaminazioni del contesto Docker.

## 1. Architettura applicativa

### Backend

- FastAPI come entrypoint unico per API pubbliche, area admin, webhooks e healthcheck.
- SQLAlchemy 2.x con modelli espliciti separati per admin, clienti, prenotazioni, pagamenti, blackout, serie ricorrenti, log business e webhook idempotenti.
- Pydantic v2 per request validation, response serialization e contratti dati chiari tra backend e frontend.
- Alembic per versionare lo schema e applicare la migrazione iniziale in avvio container.
- servizio `booking_service` responsabile di disponibilità, caparra, anti-overlap, timeout, cancellazioni e ricorrenze.
- servizio `payment_service` responsabile di checkout Stripe, order/capture PayPal, callback, webhook e fallback mock locale.
- scheduler APScheduler integrato nel backend per scadenza prenotazioni pending e reminder automatici.
- auth admin con JWT firmato in cookie httpOnly, `SameSite=lax`, secure in produzione.

### Frontend

- React + TypeScript + Vite con React Router.
- Tailwind CSS con design system leggero e coerente tra area pubblica e admin.
- client API centralizzato con base `/api` e cookie credentials attivi per l’area admin.
- flusso pubblico mobile-first: data, durata, slot, dati utente, metodo pagamento, riepilogo, redirect checkout, esito.
- dashboard admin unica per filtri, prenotazioni manuali, blackout, ricorrenze, report e log essenziali.

### Database

- PostgreSQL come database target di prodotto e deploy Railway.
- supporto SQLite mantenuto solo come fallback locale/test per rapidità di test harness; non è il target architetturale del prodotto.
- timezone applicativa `Europe/Rome`, con persistenza temporale in UTC e derivazione del giorno locale per filtri e report.

### Pagamenti

- Stripe con `Checkout Session` server-side, `success_url`, `cancel_url`, webhook `checkout.session.completed` e verifica firma se configurata.
- PayPal con `create order` server-side, `approve url`, `capture order` server-side al return e webhook idempotente per conferme asincrone.
- layer di astrazione unico tra business logic e provider esterni.

### Scheduler e job

- job ogni minuto per scadere booking `PENDING_PAYMENT` oltre la finestra di hold.
- job ogni 15 minuti per reminder delle prenotazioni confermate in partenza entro 24 ore.
- i job sono disattivati in ambiente test per evitare interferenze con i test automatici.

### Webhooks

- endpoint dedicati per Stripe e PayPal.
- tabella `payment_webhook_events` per idempotenza e audit.
- conferma prenotazione solo dopo verifica server-side del pagamento e ricontrollo finale dello slot.

### Serving produzione

- un solo container Docker serve backend e asset statici frontend sullo stesso dominio.
- in produzione il backend serve `frontend_dist`; in locale può usare `frontend/dist` dopo la build.
- le migrazioni Alembic restano l’unico meccanismo di inizializzazione schema anche in runtime container.

### Config env

- configurazione centralizzata `Settings` con Pydantic Settings.
- variabili principali: URL applicazione, DB, secret key, admin bootstrap, Stripe, PayPal, SMTP, rate limiting, timeout prenotazioni, finestra cancellazione.

### Strategia deploy Railway

- Railway builda il `Dockerfile` in root.
- il container esegue `alembic upgrade head` e poi avvia Uvicorn.
- PostgreSQL Railway viene collegato via `DATABASE_URL`.
- healthcheck su `/api/health`.

## 2. Struttura repository

```text
.
├── backend/
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 20260415_0001_initial.py
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py
│   │   │   └── routers/
│   │   │       ├── admin_auth.py
│   │   │       ├── admin_bookings.py
│   │   │       ├── admin_ops.py
│   │   │       ├── payments.py
│   │   │       └── public.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── db.py
│   │   │   ├── scheduler.py
│   │   │   └── security.py
│   │   ├── models/
│   │   │   └── __init__.py
│   │   ├── schemas/
│   │   │   ├── admin.py
│   │   │   ├── common.py
│   │   │   └── public.py
│   │   ├── services/
│   │   │   ├── booking_service.py
│   │   │   ├── email_service.py
│   │   │   ├── payment_service.py
│   │   │   └── report_service.py
│   │   └── main.py
│   ├── requirements.txt
│   └── tests/
│       ├── conftest.py
│       ├── test_admin_and_recurring.py
│       └── test_booking_api.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── StatusBadge.tsx
│   │   ├── pages/
│   │   │   ├── AdminDashboardPage.tsx
│   │   │   ├── AdminLoginPage.tsx
│   │   │   ├── PaymentStatusPage.tsx
│   │   │   └── PublicBookingPage.tsx
│   │   ├── services/
│   │   │   └── api.ts
│   │   ├── App.tsx
│   │   ├── index.css
│   │   ├── main.tsx
│   │   ├── types.ts
│   │   └── vite-env.d.ts
│   ├── index.html
│   ├── package.json
│   ├── postcss.config.js
│   ├── tailwind.config.ts
│   ├── tsconfig.app.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   └── vite.config.ts
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile
├── README.md
└── railway.json
```

## 3. Decisioni tecniche chiave

### Auth admin

- scelta: JWT firmato in cookie httpOnly.
- motivo: evita bearer token persistiti in localStorage, semplifica il dominio unico e resta coerente con FastAPI + SPA servita sullo stesso host.

### Concorrenza prenotazioni

- scelta: controllo applicativo server-side + advisory lock PostgreSQL + exclusion constraint PostgreSQL sugli intervalli orari bloccanti.
- motivo: impedire doppie conferme anche in concorrenza o con webhook tardivi.

### Struttura API

- scelta: API REST con gruppi separati `public`, `admin`, `payments`, `health`.
- motivo: confini chiari tra flusso pubblico, operatività admin e integrazioni esterne.

### Strategia webhook

- scelta: webhooks idempotenti con persistenza evento e riconciliazione booking via reference pubblica.
- motivo: evitare doppie conferme e supportare provider con callback duplicate o ordine asincrono degli eventi.

### Scheduler

- scelta: APScheduler in-process per questa prima versione.
- motivo: sufficiente per un singolo campo, semplice da deployare su Railway senza introdurre Redis o un orchestratore separato.

### Gestione timezone

- scelta: input locale Europe/Rome, salvataggio UTC, `booking_date_local` persistito a parte.
- motivo: filtri, report e UI restano coerenti anche con cambi ora legale/solare.

### Deploy Railway

- scelta: singolo container con build frontend multi-stage e backend FastAPI come runtime finale.
- motivo: dominio unico, minor complessità operativa, deploy lineare.

## 4. Schema database

### `admins`

- scopo: account area riservata.
- campi: `id`, `email`, `full_name`, `password_hash`, `role`, `is_active`, `last_login_at`, `created_at`.
- vincoli: `email` univoca, `role` enum.
- indici: `email`.
- relazioni: nessuna FK diretta; l’identità admin viene tracciata nei campi `created_by` e nei log evento.

### `customers`

- scopo: anagrafica clienti esterni senza login.
- campi: `id`, `first_name`, `last_name`, `phone`, `email`, `note`, `created_at`.
- vincoli: campi anagrafici obbligatori salvo `note`.
- indici: `phone`, `email`.
- relazioni: 1:N con `bookings`.

### `bookings`

- scopo: entità centrale di prenotazione del singolo campo.
- campi: `id`, `public_reference`, `customer_id`, `start_at`, `end_at`, `duration_minutes`, `booking_date_local`, `status`, `deposit_amount`, `payment_provider`, `payment_status`, `payment_reference`, `note`, `cancel_token`, `expires_at`, `cancelled_at`, `completed_at`, `no_show_at`, `balance_paid_at`, `reminder_sent_at`, `created_by`, `source`, `recurring_series_id`, `created_at`, `updated_at`.
- vincoli: `public_reference` univoco, `cancel_token` univoco nullable, FK verso `customers` e `recurring_booking_series`.
- indici: `public_reference`, `customer_id`, `start_at`, `end_at`, `booking_date_local`, `status`, `payment_provider`, `payment_status`, `payment_reference`, `cancel_token`, `expires_at`, `source`, `recurring_series_id`.
- relazioni: N:1 con `customers`, N:1 con `recurring_booking_series`, 1:N con `booking_payments`, 1:N con `booking_events_log`.
- regola DB critica: exclusion constraint PostgreSQL su `tstzrange(start_at, end_at, '[)')` per stati bloccanti.

### `booking_payments`

- scopo: tracciare ogni tentativo o sessione di pagamento caparra.
- campi: `id`, `booking_id`, `provider`, `status`, `amount`, `currency`, `provider_order_id`, `provider_capture_id`, `checkout_url`, `created_at`, `updated_at`.
- vincoli: FK obbligatoria verso `bookings`.
- indici: `booking_id`, `provider`, `status`, `provider_order_id`.
- relazioni: N:1 con `bookings`.

### `booking_events_log`

- scopo: audit trail business e tecnico leggibile.
- campi: `id`, `booking_id`, `event_type`, `actor`, `message`, `payload`, `created_at`.
- vincoli: `booking_id` nullable per eventi globali, payload JSON opzionale.
- indici: `booking_id`, `event_type`.
- relazioni: N:1 con `bookings`.

### `blackout_periods`

- scopo: blocchi, chiusure, manutenzioni, fasce non prenotabili.
- campi: `id`, `title`, `reason`, `start_at`, `end_at`, `is_active`, `created_by`, `created_at`.
- vincoli: intervallo coerente `start_at < end_at` gestito a livello applicativo.
- indici: `start_at`, `end_at`, `is_active`.
- relazioni: nessuna FK diretta con `bookings`; impatta la disponibilità applicativa.

### `recurring_booking_series`

- scopo: raggruppare prenotazioni ricorrenti create da admin.
- campi: `id`, `label`, `weekday`, `start_time`, `duration_minutes`, `start_date`, `end_date`, `weeks_count`, `created_by`, `created_at`.
- vincoli: weekday numerico 0-6, date nello stesso anno solare validate lato servizio.
- indici: nessuno aggiuntivo necessario in questa prima versione.
- relazioni: 1:N con `bookings`.

### `app_settings`

- scopo: configurazioni applicative evolutive senza cambiare schema.
- campi: `key`, `value`, `updated_at`.
- vincoli: `key` primaria.
- relazioni: nessuna.

### `payment_webhook_events`

- scopo: idempotenza e audit dei webhook provider.
- campi: `id`, `provider`, `event_id`, `event_type`, `payload`, `processed_at`, `created_at`.
- vincoli: `event_id` univoco.
- indici: `provider`, `event_id`, `event_type`.
- relazioni: nessuna diretta; riconciliazione applicativa verso `bookings`.

### `email_notifications_log`

- scopo: log invii email a cliente e admin.
- campi: `id`, `booking_id`, `recipient`, `template`, `status`, `error`, `sent_at`, `created_at`.
- vincoli: FK opzionale verso `bookings`.
- indici: `booking_id`, `recipient`, `template`.
- relazioni: N:1 opzionale con `bookings`.

## 5. Modello dati prenotazione

La prenotazione è formalizzata così:

- `id`: UUID string, primary key interna.
- `public_reference`: codice pubblico tipo `PB-XXXXXXXX`, univoco e comunicabile al cliente.
- `customer_id`: riferimento al cliente esterno.
- `start_at`: inizio slot in UTC.
- `end_at`: fine slot in UTC.
- `duration_minutes`: durata validata sui valori consentiti.
- `booking_date_local`: data locale Europe/Rome usata per listing e report.
- `status`: `PENDING_PAYMENT`, `CONFIRMED`, `CANCELLED`, `COMPLETED`, `NO_SHOW`, `EXPIRED`.
- `deposit_amount`: importo caparra calcolato server-side.
- `payment_provider`: `STRIPE`, `PAYPAL`, `NONE`.
- `payment_status`: `UNPAID`, `INITIATED`, `PAID`, `FAILED`, `CANCELLED`, `EXPIRED`.
- `payment_reference`: riferimento esterno provider o sessione checkout.
- `note`: nota cliente o nota operativa admin.
- `cancel_token`: token sicuro per cancellazione self-service opzionale.
- `expires_at`: deadline della hold `PENDING_PAYMENT`.
- `balance_paid_at`: timestamp saldo incassato al campo.
- `reminder_sent_at`: timestamp reminder inviato.
- `created_by`: attore sintetico, utile per audit (`public`, email admin, system).
- `source`: `PUBLIC`, `ADMIN_MANUAL`, `ADMIN_RECURRING`.
- `recurring_series_id`: FK opzionale alla serie ricorrente.
- audit timestamps: `created_at`, `updated_at`, `cancelled_at`, `completed_at`, `no_show_at`.
- metadata utili già presenti nel modello operativo: `payment_reference`, `cancel_token`, `source`, `created_by`, `note`, `reminder_sent_at`.

## 6. Business rules formalizzate

### Durate valide

- consentite solo: `60, 90, 120, 150, 180, 210, 240, 270, 300`.
- qualsiasi altro valore produce errore 422 lato server.

### Formula caparra

- se `duration_minutes <= 90`, caparra `20.00 EUR`.
- se `duration_minutes > 90`, caparra `20 + 10 * ((duration_minutes - 90) / 30)`.

### Gestione caparra Stripe e PayPal

- una booking pubblica nasce `PENDING_PAYMENT`.
- il checkout viene creato solo dal backend.
- la prenotazione diventa `CONFIRMED` solo dopo pagamento riconosciuto dal backend.
- i webhook duplicati vengono ignorati usando `payment_webhook_events`.

### Tariffe informative

- mostrate solo come box informativo in UI.
- non influenzano `deposit_amount`.
- devono essere separate visivamente dal box caparra.

### Timeout `PENDING_PAYMENT`

- default `15` minuti.
- alla scadenza: `status = EXPIRED`, `payment_status = EXPIRED`, slot nuovamente disponibile.

### Regole di conferma

- prima della conferma pagamento viene rieseguito il controllo finale di disponibilità.
- se lo slot non è più disponibile e la prenotazione era già `EXPIRED`, l’evento viene loggato come conflitto di pagamento tardivo.

### Regole anti-overlap

- sono bloccanti gli stati: `PENDING_PAYMENT`, `CONFIRMED`, `COMPLETED`, `NO_SHOW`.
- `CANCELLED` e `EXPIRED` rilasciano lo slot.
- il controllo avviene lato applicazione su ogni creazione e conferma.
- in PostgreSQL esiste una seconda protezione con exclusion constraint.

### Regole blackout

- un blackout attivo rende indisponibile qualsiasi slot sovrapposto.
- il controllo blackout si applica a booking pubbliche, admin manuali e ricorrenze.

### Regole ricorrenze admin

- input: `weekday`, `start_date`, `weeks_count`, `start_time`, `duration_minutes`.
- tutte le occorrenze devono restare nello stesso anno solare.
- comportamento default: crea solo le occorrenze disponibili, salta quelle in conflitto, restituisce report `created_count`, `skipped_count`, dettagli delle saltate.

### Regole cancellazione

- admin può annullare sempre.
- utente può annullare via `cancel_token` solo se mancano almeno `24` ore all’inizio.

### Regole reminder

- reminder solo per booking `CONFIRMED` in partenza entro 24 ore.
- booking `CANCELLED`, `EXPIRED`, `NO_SHOW` e `COMPLETED` non devono ricevere reminder.

### Regole stato prenotazione

- `PENDING_PAYMENT`: hold attiva in attesa pagamento.
- `CONFIRMED`: caparra confermata oppure booking manuale admin.
- `CANCELLED`: annullata da admin o utente.
- `COMPLETED`: partita conclusa regolarmente.
- `NO_SHOW`: cliente assente.
- `EXPIRED`: hold scaduta senza pagamento.

### Logica di rilascio slot

- uno slot torna disponibile quando una prenotazione passa a `CANCELLED` o `EXPIRED`.
- le prenotazioni con stati bloccanti continuano a occupare l’intervallo fino a cambio stato.

## 7. Superficie API iniziale

### Public

- `GET /api/public/config`: configurazione pubblica app, no auth.
- `GET /api/public/availability`: disponibilità per data e durata, no auth.
- `POST /api/public/bookings`: crea booking provvisoria, no auth.
- `POST /api/public/bookings/{booking_id}/checkout`: avvia checkout provider selezionato, no auth.
- `GET /api/public/bookings/{public_reference}/status`: stato prenotazione e pagamento, no auth.
- `POST /api/public/bookings/cancel/{cancel_token}`: cancellazione self-service, no auth ma protetta da token.

### Admin

- `POST /api/admin/auth/login`: login admin, no auth.
- `POST /api/admin/auth/logout`: logout admin, auth cookie.
- `GET /api/admin/auth/me`: sessione corrente admin, auth cookie.
- `GET /api/admin/bookings`: lista prenotazioni filtrabile, auth cookie.
- `GET /api/admin/bookings/{booking_id}`: dettaglio prenotazione, auth cookie.
- `POST /api/admin/bookings`: crea prenotazione manuale, auth cookie.
- `POST /api/admin/bookings/{booking_id}/cancel`: annulla booking, auth cookie.
- `POST /api/admin/bookings/{booking_id}/status`: aggiorna a `CONFIRMED`, `CANCELLED`, `COMPLETED`, `NO_SHOW`, auth cookie.
- `POST /api/admin/bookings/{booking_id}/balance-paid`: marca saldo al campo, auth cookie.
- `GET /api/admin/blackouts`: lista blackout, auth cookie.
- `POST /api/admin/blackouts`: crea blackout, auth cookie.
- `POST /api/admin/recurring/preview`: preview ricorrenze con conflitti, auth cookie.
- `POST /api/admin/recurring`: crea serie ricorrente, auth cookie.
- `GET /api/admin/reports/summary`: report sintetico dashboard, auth cookie.
- `GET /api/admin/events`: eventi recenti, auth cookie.

### Payments / Webhooks

- `POST /api/payments/stripe/webhook`: webhook Stripe, no auth utente, firma provider.
- `GET /api/payments/paypal/return`: return URL PayPal con capture server-side, no auth utente.
- `POST /api/payments/paypal/webhook`: webhook PayPal, no auth utente, idempotenza DB.
- `GET /api/payments/mock/complete`: completamento mock locale per sviluppo, no auth.

### Health

- `GET /api/health`: healthcheck deploy/runtime, no auth.

## 8. Flussi funzionali principali

### Booking pubblico

- utente seleziona data.
- utente seleziona durata.
- frontend carica slot disponibili da API.
- utente seleziona slot, inserisce dati, accetta privacy, sceglie Stripe o PayPal.
- backend crea booking `PENDING_PAYMENT` con `expires_at`.
- backend crea checkout provider.

### Pagamento Stripe

- backend crea `Checkout Session`.
- frontend redirige al checkout Stripe.
- Stripe richiama webhook `checkout.session.completed`.
- backend registra evento, ricontrolla slot, conferma booking e invia email.

### Pagamento PayPal

- backend crea order PayPal e ritorna approve URL.
- frontend redirige a PayPal.
- PayPal torna su `return_url` con token.
- backend esegue `capture_order`, conferma booking e invia email.
- webhook PayPal resta attivo come canale asincrono/idempotente aggiuntivo.

### Conferma prenotazione

- il backend imposta `payment_status = PAID`, `status = CONFIRMED`, azzera `expires_at`, registra evento e invia notifiche.

### Timeout mancato pagamento

- job scheduler cerca booking `PENDING_PAYMENT` scadute.
- ogni booking scaduta passa a `EXPIRED`.
- lo slot torna disponibile automaticamente perché `EXPIRED` non è bloccante.

### Prenotazione manuale admin

- admin autenticato inserisce dati cliente, data, ora, durata.
- backend verifica disponibilità e crea booking `CONFIRMED` con source `ADMIN_MANUAL`.

### Ricorrenza admin

- admin definisce etichetta, giorno settimana, data iniziale, numero settimane, orario e durata.
- backend produce preview.
- backend crea la serie e poi solo le occorrenze valide, saltando i conflitti.

### Cancellazione

- admin può annullare da dashboard.
- utente può annullare tramite link sicuro entro la finestra consentita.
- backend aggiorna stato e registra evento.

### Marking saldo / completed / no-show

- admin può segnare `balance_paid_at`.
- admin può marcare `COMPLETED` o `NO_SHOW`.
- ogni azione genera evento nel log business.

## 9. Mappa UX/UI

### Pagine pubbliche

- landing / booking page.
- stato pagamento riuscito.
- stato pagamento annullato.
- stato errore gestito.

### Pagine admin

- login admin.
- dashboard admin con vista prenotazioni, KPI, form operativi e log.

### Componenti principali

- card disponibilità orari.
- selettore durata.
- form dati cliente.
- selettore metodo caparra.
- riepilogo prenotazione.
- box tariffe informative.
- badge stato prenotazione.
- alert feedback successo/errore.
- card statistiche admin.

### Stati UI principali

- loading disponibilità.
- errore caricamento slot.
- invio booking in corso.
- redirect checkout in corso.
- stato conferma pagamento in polling leggero lato pagina esito.
- empty state e lista operativa lato admin.

### Box tariffe informative

- separato dal box caparra.
- microcopy esplicita: tariffe solo indicative per giocatore.

### Box caparra

- caparra mostrata in evidenza con importo e regola sintetica di calcolo.
- separazione netta tra caparra online e saldo al campo.

### Layout mobile-first

- home pubblica a due blocchi principali: hero + pannello booking.
- griglie responsive senza overflow orizzontale.
- CTA ampie, card arrotondate, spaziature generose.

### Design system base

- palette: slate + cyan, premium ma sobria.
- superfici: card bianche sfumate su background dark sportivo.
- tipografia: gerarchia forte con heading netti e body leggibile.
- componenti riusabili: `surface-card`, `btn-primary`, `btn-secondary`, `text-input`, badge stato.

## 10. Rischi tecnici reali

- concorrenza su stesso slot: neutralizzata con controllo server-side, advisory lock PostgreSQL ed exclusion constraint.
- webhook duplicati o fuori ordine: neutralizzati con `payment_webhook_events` e logica idempotente.
- pagamento completato in ritardo rispetto alla hold: neutralizzato con ricontrollo finale disponibilità prima della conferma.
- drift timezone/DST: neutralizzato con input Europe/Rome, persistenza UTC e `booking_date_local` separato.
- reminder inviati a booking non valide: neutralizzato filtrando solo `CONFIRMED` senza `reminder_sent_at`.
- coupling eccessivo frontend/backend: neutralizzato con schemi Pydantic espliciti e API surface stabile sotto `/api`.

## Verifica di fine fase

### 1. Controlli eseguiti

- verifica coerenza architettura backend/frontend/deploy rispetto al prompt.
- verifica coerenza schema database rispetto ai modelli SQLAlchemy e alla migrazione iniziale.
- verifica coerenza repository structure rispetto ai file reali presenti.
- verifica coerenza tra business rules, servizi booking e superfici API.
- esecuzione `pytest -q` nel backend.
- build frontend di produzione con `npm run build`.
- Docker build e smoke test container con healthcheck su `/api/health`.

### 2. Esito

- coerenza architettura: PASS.
- coerenza schema database: PASS.
- coerenza repository structure: PASS.
- coerenza business rules vs modello dati: PASS.
- assenza conflitti evidenti con pagamenti e ricorrenze: PASS.
- assenza blocchi per Fase 2: PASS.
- backend tests: PASS (`3 passed`).
- frontend build: PASS.
- docker build + healthcheck container: PASS.

### 3. Criticità rilevate

- `.env.example` non era allineato al target PostgreSQL del prodotto.
- la lista slot poteva esporre orari passati come disponibili nel giorno corrente.
- il frontend partiva dal giorno successivo, non coerente con il vincolo di campo aperto 24/7.
- il bootstrap backend ricreava lo schema SQLite anche dopo `alembic upgrade head`, rompendo l’avvio container in alcune condizioni.
- i file SQLite locali sotto `backend/` potevano entrare nel contesto Docker perché gli ignore non erano ricorsivi.

### 4. Correzioni applicate

- `DATABASE_URL` di esempio aggiornato a PostgreSQL.
- `build_daily_slots` aggiornato per rendere non prenotabili gli slot già passati.
- selezione data del booking pubblico aggiornata per partire da oggi anziché domani.
- bootstrap startup semplificato: rimosso il `create_all` automatico e mantenuto Alembic come unica fonte schema.
- pattern di `.dockerignore` e `.gitignore` estesi a `**/*.db` e `**/*.sqlite3`.
- rimossi i database SQLite locali generati durante i test di validazione.

### 5. Gate di avanzamento

`FASE VALIDATA - si può procedere`