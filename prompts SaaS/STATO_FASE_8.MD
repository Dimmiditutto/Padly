# STATO FASE 8 — DATA GOVERNANCE OPERATIVA, EXPORT E DELETE GUIDATI

## Data

23-04-2026

## Esito reale

- PASS: introdotti workflow interni guidati per export dati tenant-scoped e customer-scoped.
- PASS: introdotto workflow minimo di anonimizzazione customer che preserva booking e pagamenti storici.
- PASS: fix post-verifica applicati su minimizzazione reale dell'anonimizzazione e sul contratto customer-scoped dell'export.
- PASS: export governance minimizzato anche lato tenant, senza riesporre `email_notifications.error` nei payload di export.
- PASS: introdotta retention tecnica reale con purge guidato via control plane e job scheduler giornaliero.
- PASS: audit storico webhook esteso con review projection minimizzata, senza riesporre payload raw e senza mutare i record tecnici a database.
- PASS: documentazione operativa aggiornata su env, README, runbook e governance dati.
- PASS: nuova suite mirata [backend/tests/test_data_governance.py](backend/tests/test_data_governance.py) verde con 10 test.
- PASS: suite backend completa verde con 137 passed.

## Decisioni prese

- la data governance applicativa resta minima e pragmatica: nessuna pretesa di compliance completa o motore policy generico
- il punto di estensione scelto e il control plane interno gia protetto con `X-Platform-Key`, senza introdurre nuove superfici pubbliche
- l'export restituisce JSON filtrato e strutturato, separando `tenant_data` da `customer_data`, invece di esporre dump completi del database
- il workflow di delete applicativo introdotto e l'anonimizzazione del customer finale; la cancellazione tenant-wide resta manuale perche il database e shared-database
- la retention automatica copre solo dati tecnici purge-safe: `email_notifications_log`, `payment_webhook_events` processati e `billing_webhook_events` processati

## Workflow ora automatizzati o guidati

- `GET /api/platform/tenants/{club_id}/data-export`
  - `scope=tenant` per export tenant-scoped filtrato
  - i log email espongono solo metadati sicuri e non riespongono `email_notifications.error`
  - `scope=customer&customer_id=...` per export customer-scoped
- `POST /api/platform/tenants/{club_id}/customers/{customer_id}/anonymize`
  - anonimizza il customer in-place
  - preserva booking, pagamenti e integrita referenziale
  - redige il testo libero customer-related nei `booking.note` associati
  - riallinea i recipient nei log email collegati ai booking del customer
  - rifiuta il caso con prenotazioni future attive
- `GET /api/platform/tenants/{club_id}/data-export?scope=customer&customer_id=...`
  - omette `tenant_data` interni e mantiene solo il contesto pubblico del blocco `club`
- `POST /api/platform/data-retention/purge`
  - supporta `dry_run=true`
  - applica la retention minima ai dati tecnici purge-safe
- job scheduler giornaliero `purge_technical_retention`

## Workflow ancora manuali

- cancellazione tenant-wide o delete fisico tenant-scoped nel database condiviso
- restore di un singolo tenant da backup
- valutazione dei casi customer con vincoli fiscali o contestazioni che richiedano review manuale prima di una rimozione piu aggressiva
- purge di dati di dominio booking o commerciali, volutamente non automatizzato in questa fase

## Estensione prudente post-fase

- `POST /api/platform/data-governance/historical-audit` disponibile come audit storico interno con `dry_run=true` di default
- la redazione reale della prima iterazione tocca solo `booking_events_log` classificati `safe_to_redact`
- `payment_webhook_events` e `billing_webhook_events` restano review-only o `needs_manual_review` nella prima iterazione
- i sample webhook possono includere una review projection minimizzata con provider, event type, famiglie di indicatori, path sensibili e preview sicura solo dove difendibile

## File reali toccati in FASE 8

- [backend/app/schemas/data_governance.py](backend/app/schemas/data_governance.py)
- [backend/app/services/data_governance_service.py](backend/app/services/data_governance_service.py)
- [backend/app/api/routers/platform.py](backend/app/api/routers/platform.py)
- [backend/app/core/config.py](backend/app/core/config.py)
- [backend/app/core/scheduler.py](backend/app/core/scheduler.py)
- [backend/tests/test_data_governance.py](backend/tests/test_data_governance.py)
- [.env.example](.env.example)
- [README.md](README.md)
- [docs/operations/DATA_GOVERNANCE.md](docs/operations/DATA_GOVERNANCE.md)
- [docs/operations/RUNBOOKS.md](docs/operations/RUNBOOKS.md)

## Contratti introdotti o estesi

### API interne

- `GET /api/platform/tenants/{club_id}/data-export`
- `POST /api/platform/tenants/{club_id}/customers/{customer_id}/anonymize`
- `POST /api/platform/data-retention/purge`

### Configurazione

- nuova variabile `EMAIL_LOG_RETENTION_DAYS`
- nuova variabile `PAYMENT_WEBHOOK_RETENTION_DAYS`
- nuova variabile `BILLING_WEBHOOK_RETENTION_DAYS`

### Scheduler

- nuovo job giornaliero `purge_technical_retention`

## Migrazioni e backfill

- nessuna migrazione Alembic necessaria
- nessun backfill strutturale richiesto: i workflow lavorano sui modelli esistenti

## Rischi residui lato governance dati

- l'anonimizzazione customer non riscrive automaticamente ogni possibile payload storico libero eventualmente presente in log business o webhook payload
- i webhook non processati restano fuori purge automatica per scelta prudente
- il delete tenant-wide resta una procedura manuale e richiede ancora guida operativa dedicata
- il sistema non espone un portale self-service privacy per tenant o cliente finale

## Verifica finale reale

- PASS: `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_data_governance.py -q --tb=short`
- PASS: `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests -q -x --tb=short`

## Prerequisiti per la fase seguente

- se la prossima fase e [prompts SaaS/FASE_9.md](prompts%20SaaS/FASE_9.md), mantenere i nuovi workflow data governance tenant-aware su `club_id` senza introdurre eccezioni timezone-specifiche nel dominio booking
- se la prossima fase tocca audit o supporto operativo, riusare il control plane interno invece di aprire endpoint pubblici aggiuntivi
- mantenere esplicita la distinzione tra workflow guidati disponibili e casi che restano manuali nel database condiviso