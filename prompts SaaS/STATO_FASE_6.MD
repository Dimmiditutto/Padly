# STATO FASE 6 — HARDENING SAAS, OPERATIONS E GO-LIVE READINESS

## Data

22-04-2026

## Esito reale

- PASS: FASE 6 completata con hardening backend, test dedicati, runbook minimi e documentazione go-live.
- PASS: suite backend completa verde con 121 passed.
- PASS: nuova suite hardening in [backend/tests/test_hardening_ops.py](backend/tests/test_hardening_ops.py) con 9 test verdi.
- PASS: build frontend verde con `npm run build` in [frontend/package.json](frontend/package.json).

## Cosa rende il SaaS realmente pronto o quasi pronto

- logging applicativo strutturato JSON con `request_id` e contesto tenant disponibile quando il tenant viene risolto
- response header `X-Request-ID` per correlazione supporto e incident response
- hardening HTTP con security headers minimi su tutte le response applicative
- rate limit operativo reso tenant-aware tramite chiave composta da IP, tenant reale risolto e path normalizzato, senza bypass tramite tenant hint invalidi
- healthcheck reale su [backend/app/api/routers/payments.py](backend/app/api/routers/payments.py) con verifica database e stato scheduler, degradato quando lo scheduler dovrebbe essere attivo ma non e running
- cookie domain admin configurabile per setup multi-tenant a sottodomini condivisi
- warning operativi espliciti per login admin falliti, riuso cross-tenant di sessione admin, firma billing invalida e accessi platform con chiave errata
- warning ed exception dei job schedulati arricchiti con contesto tenant nei path reminder ed expiry
- smoke test reali su tenant legacy default e tenant secondario per booking pubblico, auth admin, settings e billing state
- runbook operativi minimi per deploy, migrazioni, rollback, provisioning tenant, sospensione, riattivazione, backup/restore e incident response
- documento di data governance minima con confini dati, retention consigliata e limiti dichiarati del shared database

## File reali toccati in FASE 6

- [backend/app/core/observability.py](backend/app/core/observability.py)
- [backend/app/core/config.py](backend/app/core/config.py)
- [backend/app/core/scheduler.py](backend/app/core/scheduler.py)
- [backend/app/main.py](backend/app/main.py)
- [backend/app/api/deps.py](backend/app/api/deps.py)
- [backend/app/api/routers/admin_auth.py](backend/app/api/routers/admin_auth.py)
- [backend/app/api/routers/payments.py](backend/app/api/routers/payments.py)
- [backend/app/api/routers/platform.py](backend/app/api/routers/platform.py)
- [backend/app/api/routers/billing.py](backend/app/api/routers/billing.py)
- [backend/tests/test_hardening_ops.py](backend/tests/test_hardening_ops.py)
- [.env.example](.env.example)
- [README.md](README.md)
- [docs/operations/RUNBOOKS.md](docs/operations/RUNBOOKS.md)
- [docs/operations/DATA_GOVERNANCE.md](docs/operations/DATA_GOVERNANCE.md)

## Contratti e policy introdotti o consolidati

### Logging e osservabilita

- i log HTTP applicativi escono in formato JSON strutturato
- i record includono `request_id` e, quando risolti, `tenant_slug` e `club_id`
- warning operativi hanno `event` coerente per filtraggio supporto e audit operativo
- i job schedulati principali propagano `tenant_slug` e `club_id` nei log fuori dal ciclo request-response

### Security e sessione

- `CORS_ALLOWED_ORIGINS` consente origini extra oltre ad `APP_URL`
- `ADMIN_SESSION_COOKIE_DOMAIN` permette di condividere il cookie admin tra sottodomini se richiesto dal deploy
- response headers minimi: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`
- `Strict-Transport-Security` viene emesso in produzione su traffico HTTPS rilevato

### Health e supporto operativo

- `GET /api/health` ora espone `status`, `environment`, `checked_at` e `checks` con database e scheduler
- se lo scheduler e richiesto dalla configurazione ma non e running, `GET /api/health` non risulta pienamente sano e degrada il segnale operativo
- i runbook documentano chiaramente cosa e automatico e cosa resta manuale nel shared database

## Cosa resta manuale o parziale

- retention e purge non sono automatizzate: la policy e documentata ma non applicata via job applicativo
- export e delete tenant-wide restano procedure manuali o semi-guidate, non endpoint di prodotto
- restore di un singolo tenant non e un restore fisico nativo: richiede procedura applicativa dedicata filtrata per `club_id`
- rate limit resta in-memory e per-processo: accettabile per deploy iniziali single-instance, non ancora distribuito per multi-instance ad alto traffico
- non e stato introdotto un sistema completo di metriche numeriche o dashboard centralizzata esterna

## Rischi residui prima del go-live

- in deploy multi-replica il rate limit locale puo essere aggirato distribuendo il traffico tra processi o istanze
- la timezone del motore slot non e ancora per-tenant end-to-end, come gia emerso nelle fasi precedenti
- la governance dati e solo documentata: senza workflow applicativi dedicati, export/delete restano a carico del supporto tecnico
- i log strutturati sono pronti, ma la persistenza e queryability dipendono ancora dalla piattaforma di log del deploy

## Backlog post go-live consigliato

1. Preparare o attivare storage condiviso o edge layer per il rate limit quando il deploy passa a multi-instance.
2. Introdurre metriche applicative minime su booking, webhook, reminder e auth failure.
3. Aggiungere workflow applicativo guidato per export e delete per tenant o cliente finale.
4. Completare la gestione timezone tenant-aware nel motore slot e nei job schedulati piu sensibili.
5. Integrare alerting operativo su `health`, webhook billing falliti e picchi di 429.

## Verifica finale reale

- PASS: `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests -q -x --tb=short`
- PASS: `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_hardening_ops.py -q --tb=short`
- PASS: `npm run build` in [frontend/package.json](frontend/package.json)