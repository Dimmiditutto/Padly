# STATO GO LIVE

## Esito finale

NO-GO

## Topologia di deploy scelta e motivazione

- topologia iniziale raccomandata: `1` sola istanza backend applicativa
- `RATE_LIMIT_BACKEND=local`
- una sola istanza designata con `SCHEDULER_ENABLED=true`

Motivazione:

- la regola operativa documentata in [istanze.md](istanze.md) e coerente con il repository reale
- il backend espone un rate limit locale o shared in [backend/app/core/rate_limit.py](backend/app/core/rate_limit.py) e il path locale e la scelta economica corretta per single-instance
- il control plane e l'healthcheck espongono lo stato del backend rate limit e dello scheduler in [backend/app/services/operations_service.py](backend/app/services/operations_service.py)
- il rischio storico di lock single-court globale e stale: il lock e keyed per `court_id` in [backend/app/services/booking_service.py](backend/app/services/booking_service.py#L231-L263) e la suite multi-campo e verde

## Decisione finale su RATE_LIMIT_BACKEND

- decisione raccomandata: `RATE_LIMIT_BACKEND=local`
- cambio a `shared` solo se il deploy reale usa piu istanze backend attive contemporaneamente e il backend condiviso e operativo e verificato

## Env gate verificati, mancanti o ancora placeholder

### Verificati solo a livello di contratto o smoke sintetico

- PASS: il runtime blocca l'avvio production se `SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `STRIPE_BILLING_WEBHOOK_SECRET` o `PLATFORM_API_KEY` sono mancanti o placeholder, come mostrato in [backend/app/core/config.py](backend/app/core/config.py)
- PASS: `.env.example` documenta i gate corretti in [.env.example](.env.example)
- PASS: lo smoke locale production-like ha avviato l'app con env sintetico valido

### Mancanti o non verificabili sull'ambiente reale

- FAIL: non esiste un file `.env` reale nel workspace e non c'e accesso alle environment variables del deploy Railway o del dominio di produzione
- FAIL: non e verificabile da questo workspace che `APP_URL` punti al dominio pubblico reale del rilascio
- FAIL: non e verificabile da questo workspace che `DATABASE_URL` punti a PostgreSQL reale di produzione
- FAIL: non e verificabile da questo workspace che `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` siano reali e funzionanti
- FAIL: non e verificabile da questo workspace che `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID` siano reali e correttamente configurati
- FAIL: non e verificabile da questo workspace che le chiavi VAPID `/play` di produzione siano presenti, oppure che il fallback in-app sia stato accettato esplicitamente nel rollout

Impatto:

- questi gate ambientali non sono inferibili dal codice e impediscono una decisione `GO`

## Stato provider e webhook

### Implementazione codice

- PASS: il deploy Railway usa `healthcheckPath=/api/health` in [railway.json](railway.json)
- PASS: il container serve backend e SPA dallo stesso servizio in [Dockerfile](Dockerfile)
- PASS: Stripe success/cancel redirect e PayPal return/cancel sono costruiti dal codice tramite `build_club_app_url(...)` in [backend/app/services/payment_service.py](backend/app/services/payment_service.py#L56-L85) e [backend/app/services/payment_service.py](backend/app/services/payment_service.py#L146-L180)
- PASS: i webhook applicativi reali restano su `/api/payments/stripe/webhook` e `/api/payments/paypal/webhook` in [backend/app/api/routers/payments.py](backend/app/api/routers/payments.py)

### Configurazione provider reale

- FAIL: non c'e evidenza diretta dal workspace che gli URL webhook configurati su Stripe, PayPal e billing SaaS siano allineati al dominio reale di produzione
- FAIL: non c'e evidenza diretta dal workspace che `APP_URL` del deploy sia il dominio effettivamente registrato nei provider

## Validazioni automatiche eseguite davvero con esito

### Backend

- PASS: `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests -q -x --tb=short`
  - esito: `192 passed`
- PASS: `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_hardening_ops.py -q --tb=short`
  - esito: `14 passed`
- PASS: `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_multi_courts_backend.py -q --tb=short`
  - esito: `4 passed`

### Frontend

- PASS: `npm run test:run`
  - esito: `14 test files`, `112 tests passed`
  - nota: emersi solo warning React `act(...)` non bloccanti durante test admin
- PASS: `npm run build`
  - esito: build produzione completata con successo

### Container

- FAIL/BLOCKED: `docker --version`
  - esito: CLI Docker non presente sulla macchina di verifica
- BLOCKED: `docker build -t padelbooking-go-live-smoke .`
  - non eseguito per assenza del comando Docker nel sistema

## Smoke manuali eseguiti davvero con esito

### Smoke locale production-like con schema migrato

Contesto:

- database SQLite temporaneo fresco
- `APP_ENV=production`
- env minimi sintetici impostati esplicitamente
- `alembic upgrade head` eseguito prima del bootstrap app
- smoke eseguito via `FastAPI TestClient`

Esiti:

- PASS: `GET /api/health` -> `200`, `status=ok`, `checks.scheduler=running`, `checks.rate_limit.backend=local`
- PASS: `GET /` -> `200`, SPA servita correttamente
- PASS: `GET /api/platform/ops/status` con `X-Platform-Key` -> `200`, `scheduler.should_be_running=True`, `scheduler.state=running`, `rate_limit.backend=local`
- PASS: `GET /api/public/config` -> `200`, `tenant_slug=default-club`
- PASS: `GET /clubs` -> `200`, SPA servita correttamente
- PASS: `GET /c/default-club` -> `200`, SPA servita correttamente
- PASS: `GET /c/default-club/play` -> `200`, SPA servita correttamente

### Smoke reali ancora mancanti o bloccati

- BLOCKED: prenotazione pubblica reale con provider reali e redirect su dominio di deploy
- BLOCKED: login admin e `GET /api/admin/billing/status` sul vero tenant di produzione
- BLOCKED: smoke manuali completi di `/play` privata con identify, join, create match e completamento `4/4` sull'ambiente reale
- BLOCKED: smoke manuali discovery pubblico con watchlist, nearby geolocation fallback e contact request sul dominio reale
- BLOCKED: smoke multi-tenant minimo sul tenant secondario reale di produzione

Motivo del blocco:

- manca accesso al deployment reale, alle sue credenziali e ai provider configurati

## Esito dell'audit mirato su datetime naive extra-booking

- PASS CON RISERVA: non emergono blocker attivi fuori dal perimetro booking/admin_ops gia chiuso in Fase 9
- verifica svolta su match principali emersi dal grep tecnico nel backend
- il caso piu sensibile extra-booking e la normalizzazione dei datetime provider in [backend/app/services/payment_service.py](backend/app/services/payment_service.py#L392-L399), che porta eventuali valori naive a UTC senza introdurre ambiguita DST business-local
- non sono emersi path extra-booking attivi di go-live che richiedano fix immediato prima del rilascio

Rischio residuo:

- eventuali futuri nuovi ingressi datetime naive in superfici fuori booking/admin_ops vanno comunque riesaminati quando entreranno in perimetro

## Documenti o checklist aggiornati

- aggiornato [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) con gate runtime, `/play`, discovery pubblico, billing status e topologia rate limit
- aggiornato [docs/operations/RUNBOOKS.md](docs/operations/RUNBOOKS.md) con smoke checklist go-live estesa a `/play`, discovery pubblico e control plane

## Blocker residui da chiudere prima del rilascio

1. fornire evidenza reale dell'ambiente di produzione: `APP_URL`, `DATABASE_URL`, secret critici, SMTP, Stripe, PayPal, billing webhook secret, `PLATFORM_API_KEY`, VAPID `/play` se richiesto
2. verificare realmente nei provider che i webhook siano registrati sul dominio corretto e sui path applicativi attesi
3. eseguire smoke manuali reali sul deployment: booking pubblico, login admin, billing status, `/play`, discovery pubblico e tenant secondario
4. eseguire una Docker build reale in un ambiente che abbia il CLI Docker disponibile oppure sostituire la prova con una build Railway osservabile e documentata

## Decisione finale

NO-GO - non andare live

Motivazione sintetica:

- il codice e il runtime locale sono in stato buono: test completi verdi, build frontend verde, hardening ops verde, multi-campo verde, smoke locale production-like verde
- i blocker residui non sono bug di repository ma blocker di rilascio reale: assenza di evidenza degli env di produzione, assenza di verifica dei webhook/provider sul dominio reale, smoke manuali di produzione non eseguiti e Docker build non verificabile in questo ambiente
- finche questi gate restano senza evidenza osservabile, il rilascio non e difendibile come `GO`