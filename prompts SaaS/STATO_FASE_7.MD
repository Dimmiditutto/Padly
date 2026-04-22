# STATO FASE 7 — RATE LIMIT CONFIGURABILE, SNAPSHOT OPERATIVO E TELEMETRIA MINIMA

## Data

22-04-2026

## Esito reale

- PASS: FASE 7 completata con backend rate limit configurabile e default prudente single-instance.
- PASS: aggiunto snapshot operativo protetto per control plane e supporto.
- PASS: fix post-verifica applicati su public health fail-soft e cleanup minimo dei contatori shared.
- PASS: documentazione operativa aggiornata su env, README e runbook.
- PASS: migrazione Alembic `20260422_0005_rate_limit_shared_backend.py` verificata in upgrade e downgrade su database temporaneo.
- PASS: suite hardening in [backend/tests/test_hardening_ops.py](backend/tests/test_hardening_ops.py) verde con 14 test.
- PASS: suite backend completa verde con 126 passed.

## Decisioni prese

- il rate limit resta `local` di default e rimane la scelta raccomandata per deploy a 1 sola istanza, coerentemente con [istanze.md](istanze.md)
- la modalita `shared` e ora disponibile come upgrade esplicito e usa il database condiviso esistente come shared store minimale, senza introdurre dipendenze esterne obbligatorie
- il middleware HTTP non e stato riscritto: la logica e stata estratta in un backend configurabile mantenendo invariato il punto di enforcement applicativo
- lo snapshot operativo minimo e stato esposto sia nel public healthcheck in forma ridotta e fail-soft sia nel control plane interno in forma completa tramite `GET /api/platform/ops/status`

## Cosa e stato reso pronto per il multi-instance

- selezione configurabile del backend rate limit tramite `RATE_LIMIT_BACKEND=local|shared`
- backend `shared` persistente via tabella `rate_limit_counters`
- semantica condivisa verificata con due istanze del backend che leggono e scrivono lo stesso stato persistito
- cleanup minimo globale dei contatori scaduti nel backend `shared`, senza introdurre scheduler o servizi esterni
- healthcheck che espone solo il backend rate limit attivo insieme a database e scheduler, lasciando i dettagli operativi completi allo snapshot protetto
- snapshot operativo protetto che espone:
  - scheduler state
  - modalita rate limit attiva
  - conteggio failure recenti email
  - conteggio eventi recenti `invoice.payment_failed` lato billing

## Cosa resta raccomandato per ambienti a 1 sola istanza

- mantenere `RATE_LIMIT_BACKEND=local`
- non introdurre servizi aggiuntivi solo per il rate limit
- usare lo snapshot operativo per supporto e controllo base, senza pretendere una piattaforma observability completa

## Cosa resta opzionale o non attivato finche non esiste un deploy distribuito reale

- la modalita `shared` non viene attivata automaticamente
- non e stato introdotto Redis, edge rate limiting o una mesh esterna
- non e stato introdotto Prometheus, OpenTelemetry o un sistema completo di metriche distribuite
- non e stato aggiunto alerting automatico: i segnali sono disponibili ma vanno ancora integrati nella piattaforma operativa del deploy

## File reali toccati in FASE 7

- [backend/app/core/rate_limit.py](backend/app/core/rate_limit.py)
- [backend/app/core/config.py](backend/app/core/config.py)
- [backend/app/models/__init__.py](backend/app/models/__init__.py)
- [backend/app/main.py](backend/app/main.py)
- [backend/app/services/operations_service.py](backend/app/services/operations_service.py)
- [backend/app/schemas/operations.py](backend/app/schemas/operations.py)
- [backend/app/api/routers/payments.py](backend/app/api/routers/payments.py)
- [backend/app/api/routers/platform.py](backend/app/api/routers/platform.py)
- [backend/alembic/versions/20260422_0005_rate_limit_shared_backend.py](backend/alembic/versions/20260422_0005_rate_limit_shared_backend.py)
- [backend/tests/conftest.py](backend/tests/conftest.py)
- [backend/tests/test_hardening_ops.py](backend/tests/test_hardening_ops.py)
- [.env.example](.env.example)
- [README.md](README.md)
- [docs/operations/RUNBOOKS.md](docs/operations/RUNBOOKS.md)

## Contratti introdotti o estesi

### Configurazione

- nuova variabile `RATE_LIMIT_BACKEND` con valori supportati `local` e `shared`
- nuova variabile `OPERATIONAL_SIGNAL_WINDOW_HOURS` per la finestra delle failure recenti nello snapshot operativo

### Health e control plane

- `GET /api/health` ora espone anche `checks.rate_limit`
- `GET /api/health` resta un endpoint pubblico minimale e fail-soft sul database
- `GET /api/platform/ops/status` restituisce uno snapshot protetto con scheduler, rate limit e failure recenti

### Dati

- nuova tabella `rate_limit_counters` per la modalita `shared`
- nessun cambiamento ai contratti pubblici di booking, auth admin o billing tenant-facing

## Rischi residui prima della fase successiva

- la modalita `shared` usa il database condiviso come store minimale: e adeguata come step intermedio, ma per carichi elevati o edge abuse resta possibile preferire in futuro Redis o un layer dedicato
- lo snapshot operativo e intenzionalmente minimo: non sostituisce metriche storiche, tracing o alerting automatico
- il lock di booking resta ancora globale e non tenant-aware
- la timezone del dominio booking non e ancora end-to-end tenant-aware
- data governance applicativa resta ancora parzialmente manuale

## Verifica finale reale

- PASS: `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m alembic upgrade head` su database temporaneo `sqlite:///./phase7_migration_check.sqlite`
- PASS: `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m alembic downgrade 20260422_0004` sullo stesso database temporaneo
- PASS: `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_hardening_ops.py -q --tb=short`
- PASS: `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests -q -x --tb=short`

## Prerequisiti per la fase seguente

- se la prossima fase e [prompts SaaS/FASE_8.md](prompts%20SaaS/FASE_8.md), riusare `GET /api/platform/ops/status` come superficie minima interna per supportare workflow guidati e supporto operativo
- se la prossima fase tocca lo scaling reale, decidere in modo esplicito se il backend `shared` su database basta ancora o se conviene un shared store dedicato
- mantenere come vincolo di prodotto la regola di [istanze.md](istanze.md): `local` per 1 istanza, `shared` o equivalente per 2+ istanze