# FASE 1 — AUDIT REALE DEL REPOSITORY E PIANO SAAS A PATCH MINIME

BLOCCO_COMUNE — PADELBOOKING SAAS MULTI-TENANT REALE

## Identita operativa

Agisci come:
- Senior Software Architect
- Senior Full-Stack Engineer
- Senior Code Reviewer
- QA tecnico rigoroso
- SaaS Product Engineer pragmatico
- Platform Engineer orientato alla produzione

## Obiettivo

Evolvere il repository esistente di PadelBooking da applicazione single-tenant a SaaS multi-tenant serio, professionale e completo, senza rompere il booking pubblico, l'area admin, i pagamenti e gli automatismi gia presenti.

## Terminologia obbligatoria

- tenant = boundary di isolamento per dati, auth, configurazione, billing e operazioni
- club = entita di dominio del prodotto; puo coincidere con il tenant se il modello business reale e 1 tenant = 1 club/circolo
- se scegli Club come tenant root, dichiaralo esplicitamente e trattalo come entita tenant-aware, non come semplice etichetta di UI

## Strategia multi-tenant obbligatoria

La strategia target di questi prompt e:

- database unico condiviso per tutti i tenant
- isolamento logico applicativo e dati tramite tenant_id, oppure club_id se Club e la tenant key scelta
- nessun database separato per tenant come approccio di default
- nessuno schema separato per tenant come approccio di default

Questa scelta va trattata come vincolo architetturale, salvo esplicita richiesta contraria o evidenza tecnica fortissima emersa dal repository reale.

## Stato reale del repository da rispettare

Prima di proporre o scrivere codice, parti da questi fatti gia verificati nel repository reale:

- backend/app/main.py registra i router public, admin_auth, admin_bookings, admin_ops, admin_settings e payments; inoltre bootstrap un solo admin iniziale da variabili environment
- backend/app/models/__init__.py contiene oggi Admin, Customer, Booking, BookingPayment, BookingEventLog, BlackoutPeriod, RecurringBookingSeries, AppSetting, PaymentWebhookEvent, EmailNotificationLog
- backend/app/services/booking_service.py contiene la logica critica di disponibilita, lock single-court, deposito, creazione booking pubblica/admin, cancellazioni e altre regole di dominio
- backend/app/services/settings_service.py salva regole booking globali in app_settings con chiave booking_rules
- backend/app/api/routers/public.py espone config, availability, create booking, checkout, status e cancellazione pubblica
- backend/app/api/routers/admin_auth.py usa cookie httpOnly e supporta password reset via email
- backend/app/api/routers/admin_settings.py espone settings admin globali
- frontend/src/App.tsx espone il flusso pubblico su / e l'area admin su rotte dedicate
- frontend/src/pages/PublicBookingPage.tsx e frontend/src/services/publicApi.ts implementano il booking pubblico reale
- frontend/src/services/adminApi.ts e le pagine admin implementano dashboard, prenotazioni, ricorrenze, log, settings e auth
- nel repository attuale non risultano presenti tenant esplicito, Club/club_id, tenant resolution, billing SaaS, control plane di piattaforma, branding multi-tenant, chat applicativa o integrazione LLM di prodotto

## Regola fondamentale sul repository

Non assumere che feature SaaS gia esistano. Prima di ogni modifica:

- ispeziona il repository reale
- verifica quali file, enum, servizi, test e pagine esistono davvero
- usa e modifica solo superfici reali gia presenti o strettamente necessarie
- se un elemento atteso non esiste, segnala la deviazione e proponi la patch minima coerente
- non inventare compatibilita inesistenti

## Principi architetturali non derogabili

1. Il backend resta l'unica source of truth.
2. La logica critica di booking, disponibilita, pagamenti, reminder e audit resta deterministica e testata.
3. La trasformazione SaaS deve essere incrementale: prima foundation dati e tenant isolation, poi experience multi-tenant, poi billing SaaS, poi hardening operativo.
4. Ogni migrazione deve essere reversibile e prevedere bootstrap o backfill per i dati legacy.
5. La compatibilita single-tenant corrente deve continuare a funzionare durante la transizione.
6. Non introdurre refactor ampi o nuove astrazioni se il repo offre gia un punto di estensione piu semplice.
7. Non degradare i flussi esistenti di booking pubblico, admin, Stripe, PayPal, scheduler, email e password reset.
8. Non introdurre chat, LLM o matchmaking salvo richiesta esplicita successiva: non e il percorso prioritario per fare di questo progetto un SaaS serio.

## Stack da mantenere

Mantieni lo stack del repository esistente. Non proporre migrazioni di stack o refactor ampi senza necessita tecnica reale.

Stack atteso:
- Backend: FastAPI
- ORM: SQLAlchemy 2.x
- DB: PostgreSQL in produzione, SQLite in locale/test se gia supportato
- Migrazioni: Alembic
- Schemi: Pydantic v2
- Frontend: React + TypeScript + Vite
- Styling: Tailwind e componenti/layout gia presenti
- Deploy: Railway
- Payments booking pubblico: Stripe e PayPal gia presenti
- Billing SaaS: preferisci Stripe Billing se serve un provider unico per subscription e invoicing

Nota architetturale sul database:
- PostgreSQL in produzione resta il database condiviso del SaaS
- SQLite puo restare utile solo per locale/test se gia supportato
- non progettare il percorso SaaS assumendo un database per tenant

## Target SaaS realistico

### Livello 1 — Foundation multi-tenant
Il sistema deve introdurre in modo credibile:
- tenant esplicito, modellato come Club solo se coerente con il dominio del prodotto
- bootstrap del tenant di default per retrocompatibilita
- scoping dati per prenotazioni, configurazioni e operatori
- admin associato a un tenant o a un ruolo platform
- tutte le entita tenant-scoped nello stesso database condiviso

### Livello 2 — Prodotto tenant-aware
Il prodotto deve supportare:
- booking pubblico brandizzato per tenant
- area admin isolata per tenant
- settings tenant-scoped
- email operative tenant-scoped con provider centralizzato dell'app
- report e audit filtrati per tenant

### Livello 3 — Layer commerciale SaaS
Il SaaS deve poter gestire:
- piani e subscription
- trial, stato account, enforcement non distruttivo
- provisioning tenant
- webhooks billing idempotenti
- control plane minimo per la piattaforma

### Livello 4 — Hardening e go-live
Il sistema deve arrivare a:
- osservabilita
- rate limit e protezioni operative
- backup, restore, runbook
- compliance, sicurezza, metriche, supporto operativo

## Hardcodes e vincoli reali da considerare

- oggi esiste un solo campo e il lock applicativo e single-court
- timezone e currency oggi sono globali via settings
- le booking rules oggi sono globali in app_settings
- il bootstrap admin iniziale e globale
- il frontend pubblico vive su /
- l'area admin usa cookie httpOnly e redirect lato frontend su 401
- reminder ed email esistono gia e non vanno spezzati
- PaymentWebhookEvent esiste gia per idempotenza provider booking; riusalo o estendilo in modo coerente invece di duplicare concetti senza motivo

## Regole di implementazione SaaS

- Parti dal codice che gia decide il comportamento: modelli, service layer, router e client API reali.
- Se un cambiamento richiede propagare tenant_id, oppure club_id se il tenant e modellato come Club, fallo in ordine controllato e con backfill esplicito.
- Assumi come default un solo database condiviso: l'isolamento si ottiene con chiavi tenant, query corrette, vincoli e test cross-tenant.
- Non proporre database-per-tenant o schema-per-tenant a meno che il repository reale o una richiesta esplicita non lo rendano indispensabile.
- Riusa AppSetting se e davvero la scelta piu economica; se diventa ambiguo, introduci un modello tenant settings dedicato solo quando il costo/beneficio e chiaro.
- Mantieni la superficie API il piu stabile possibile; estendi le response esistenti prima di creare endpoint paralleli inutili.
- Se devi introdurre ruoli admin, parti da un set minimo e coerente con i casi reali.
- Se devi introdurre billing SaaS, non confondere il checkout booking del cliente finale con la subscription del tenant.
- Le email SaaS standard devono usare provider centralizzato dell'app; i tenant configurano destinatari, branding e preferenze, non SMTP custom come flusso principale.
- Ogni fase deve poter essere fermata e rilasciata senza lasciare il prodotto in uno stato incoerente.

## Requisiti QA

Ogni fase e accettabile solo se:
- test nuovi e pertinenti presenti
- nessuna regressione evidente sui test esistenti toccati
- migrazioni up e down verificate
- backend avviabile o almeno importabile dopo le modifiche
- frontend buildabile se toccato
- PASS/FAIL finale reale, non inventato
- rischi residui dichiarati

## Formato di output obbligatorio per ogni fase

### 1. Prerequisiti verificati
Elenco con PASS/FAIL reale.

### 2. Mappa del repository rilevante
File e componenti realmente trovati e usati.

### 3. Gap analysis della fase
Cosa manca oggi rispetto all'obiettivo della fase.

### 4. File coinvolti
File creati o modificati.

### 5. Implementazione
Codice completo solo dei file necessari.

### 6. Migrazioni e backfill
Nome migrazione, strategia di backfill, impatto sui dati legacy.

### 7. Test aggiunti o modificati
Codice completo dei test.

### 8. Verifica di fine fase
Checklist reale con PASS/FAIL.

### 9. STATO_FASE_N.MD
Blocco compatto per la fase successiva con:
- decisioni prese
- file toccati
- contratti API
- contratti dati
- strategia tenant o billing se introdotta
- eventuali deviazioni dal piano
- rischi residui

## FASE 1
## Obiettivo

Non implementare ancora il SaaS multi-tenant. Esegui prima una review tecnica reale del repository per capire:
- dove vive la logica di booking, disponibilita, pagamenti, scheduler e settings
- come sono strutturati backend e frontend oggi
- quali assunzioni single-tenant sono hardcoded
- quali patch minime servono per portare il progetto verso un SaaS serio senza rompere il prodotto esistente

Assumi come target architetturale un SaaS multi-tenant con database unico condiviso, salvo evidenza tecnica contraria realmente verificata.

## Prerequisiti da verificare

Verifica realmente, senza assumere:
- il backend si avvia oppure almeno importa correttamente
- le migrazioni esistenti sono eseguibili
- la suite test backend esiste ed e lanciabile
- il frontend compila
- il routing frontend e identificabile
- il sistema email esistente e identificabile
- il modello Booking e la logica di disponibilita sono rintracciabili
- auth admin, password reset e settings admin sono rintracciabili

Se uno di questi punti fallisce, non proseguire con implementazioni arbitrarie: segnala il problema e circoscrivi la patch minima necessaria.

## Cosa devi fare

1. Ispeziona il repository reale.
2. Elenca i file rilevanti per:
   - booking e disponibilita
   - pagamenti booking
   - admin auth e sessione
   - settings e configurazioni runtime
   - scheduler e email
   - report, audit e log
   - pagine pubbliche e pagine admin
   - migrazioni e test
3. Individua gli hardcode single-tenant reali, ad esempio:
   - bootstrap di un solo admin
   - regole booking globali in app_settings
   - timezone e currency globali
   - assenza di tenant_id esplicito o club_id se il tenant coincide con il club
   - report e query globali
   - app pubblica ancorata a un solo brand su /
4. Verifica che il percorso di migrazione verso il multi-tenant possa restare su database unico condiviso, individuando:
   - tabelle che richiedono tenant_id esplicito
   - tabelle dove basta lo scoping tramite relazione obbligatoria
   - query o servizi che oggi leggono globalmente e rischiano data leakage
   - eventuali punti che sembrano spingere verso database-per-tenant senza vera necessita
5. Evidenzia i debiti tecnici che impattano il percorso SaaS:
   - vincoli mancanti per tenant isolation
   - service layer o router da estendere con meno rischio
   - aree sensibili ai race condition
   - tabelle che richiederanno backfill
   - punti in cui billing SaaS e booking payments potrebbero confondersi
6. Definisci un piano di patch minimo a fasi per arrivare a:
   - foundation multi-tenant
   - backend tenant-aware
   - frontend tenant-aware e branding tenant
   - layer commerciale SaaS con subscription
   - hardening operativo e go-live
7. Non implementare ancora chat, LLM o matchmaking: in questo repository non sono il passo giusto per la trasformazione SaaS.

## Output obbligatorio

- mappa reale del repository
- assunzioni confermate
- assunzioni smentite
- hardcode single-tenant rilevati
- conferma esplicita che la roadmap usa database unico condiviso oppure spiegazione tecnica reale se non fosse sostenibile
- problemi tecnici e rischi architetturali reali
- rischi di regressione
- piano di patch minimo ordinato per FASE_2, FASE_3, FASE_4, FASE_5 e FASE_6
- eventuali micro-fix preparatori solo se strettamente necessari
- STATO_FASE_1.MD con:
  - file reali individuati
  - assunzioni confermate
  - assunzioni smentite
  - hardcode single-tenant da rimuovere in ordine
  - ordine esatto delle fasi successive

Quando hai terminato questa fase, non proseguire con implementazioni di FASE_2 o successive senza una richiesta esplicita. Ogni fase deve essere approvata singolarmente e deve poter essere rilasciata senza dipendere da patch future. Scrivi CONTEXT BLOCK per FASE_2 solo se FASE_1 è stata completata con successo e verificata, in modo che fase_2 possa essere implementata con tutte le informazioni reali necessarie e risulti coerente con il codice reale del repository.