# Runbook Operativi SaaS

## Ambito e vincoli

- Il prodotto usa un database unico condiviso tra tenant.
- L'isolamento applicativo e garantito da `club_id` e dalla tenant resolution applicativa.
- Backup e restore sono database-wide: il ripristino di un singolo tenant non e un restore fisico separato, ma una procedura applicativa guidata.

## 1. Deploy e migrazioni

### Checklist pre-deploy

- verificare `APP_ENV=production`
- verificare `DATABASE_URL`, `SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`
- verificare `STRIPE_BILLING_WEBHOOK_SECRET` e `PLATFORM_API_KEY`
- verificare `APP_URL`, `CORS_ALLOWED_ORIGINS` e `ADMIN_SESSION_COOKIE_DOMAIN` se usati sottodomini tenant-aware
- verificare che una sola istanza abbia `SCHEDULER_ENABLED=true`
- verificare `RATE_LIMIT_BACKEND=local` se il deploy resta a 1 sola istanza
- verificare `RATE_LIMIT_BACKEND=shared` se il deploy gira con piu istanze attive e deve condividere i contatori

### Esecuzione migrazioni

Dal backend:

```powershell
D:/Padly/PadelBooking/.venv/Scripts/python.exe -m alembic upgrade head
```

### Verifica post-migrazione

- chiamare `GET /api/health` e verificare `checks.database == ok`
- verificare `checks.rate_limit.backend` coerente con il deployment reale (`local` per 1 istanza, `shared` per piu istanze)
- chiamare `GET /api/platform/ops/status` con `X-Platform-Key` e verificare scheduler, rate limit e failure recenti minime
- verificare login admin del tenant legacy di default
- verificare `GET /api/admin/billing/status` su tenant default
- verificare una richiesta `GET /api/public/config` sul default tenant e su almeno un tenant secondario

## 2. Rollback applicativo e database

### Rollback codice

- eseguire rollback del deploy all'ultima release applicativa stabile
- non eseguire rollback del codice senza verificare la compatibilita con lo schema gia migrato

### Rollback schema

Usare downgrade Alembic solo se il problema e confinato all'ultima revisione e il rollback e stato validato in ambiente controllato:

```powershell
D:/Padly/PadelBooking/.venv/Scripts/python.exe -m alembic downgrade -1
```

### Restore database completo

- se i dati sono compromessi in modo ampio, ripristinare l'intero database dall'ultimo backup consistente
- dopo il restore, riallineare i webhook provider e verificare idempotenza su `payment_webhook_events` e `billing_webhook_events`
- rieseguire la smoke checklist di login admin, `GET /api/health`, `GET /api/public/config`, `GET /api/admin/billing/status`

### Restore singolo tenant in shared database

Non esiste restore fisico per-tenant out of the box.

Procedura realistica:

- esportare dal backup solo i record del tenant filtrando per `club_id`
- verificare le tabelle indirettamente scoped via relazione, ad esempio `booking_payments` tramite `booking_id`
- reimportare in ambiente isolato di verifica
- applicare una procedura applicativa dedicata o una migrazione dati controllata verso la produzione
- non sovrascrivere direttamente record di tenant diversi nel database condiviso

## 3. Provisioning nuovo tenant

Usare il control plane interno con `X-Platform-Key`.

```powershell
curl -X POST https://tuo-dominio/api/platform/tenants ^
  -H "Content-Type: application/json" ^
  -H "X-Platform-Key: <PLATFORM_API_KEY>" ^
  -d "{\"slug\":\"club-roma\",\"public_name\":\"Club Roma\",\"notification_email\":\"ops@clubroma.it\",\"plan_code\":\"trial\",\"trial_days\":14,\"admin_email\":\"owner@clubroma.it\",\"admin_full_name\":\"Owner Club Roma\",\"admin_password\":\"PasswordForte123!\"}"
```

Verifiche immediate:

- `GET /api/public/config` sul dominio o host del tenant
- login admin sul tenant
- `GET /api/admin/settings`
- `GET /api/admin/billing/status`

## 4. Sospensione e riattivazione tenant

### Sospensione

```powershell
curl -X POST https://tuo-dominio/api/platform/tenants/<club_id>/suspend ^
  -H "Content-Type: application/json" ^
  -H "X-Platform-Key: <PLATFORM_API_KEY>" ^
  -d "{\"reason\":\"chargeback o mancato pagamento\"}"
```

### Riattivazione

```powershell
curl -X POST https://tuo-dominio/api/platform/tenants/<club_id>/reactivate ^
  -H "X-Platform-Key: <PLATFORM_API_KEY>"
```

Audit disponibile:

- eventi minimi in `billing_webhook_events` con `provider='platform'`
- log applicativi strutturati con `request_id` e contesto tenant quando risolto
- snapshot operativo minimo via `GET /api/platform/ops/status`

## 5. Supporto operativo

### Export dati essenziali

- export tenant-scoped: `GET /api/platform/tenants/<club_id>/data-export`
- export customer-scoped: `GET /api/platform/tenants/<club_id>/data-export?scope=customer&customer_id=<customer_id>`
- usare sempre `X-Platform-Key`
- l'export e JSON guidato e filtrato, non un dump completo del database

### Anonimizzazione customer

```powershell
curl -X POST https://tuo-dominio/api/platform/tenants/<club_id>/customers/<customer_id>/anonymize ^
  -H "Content-Type: application/json" ^
  -H "X-Platform-Key: <PLATFORM_API_KEY>" ^
  -d "{\"reason\":\"richiesta privacy\",\"actor\":\"support\"}"
```

Vincoli operativi:

- il workflow preserva booking e pagamenti storici
- il workflow rifiuta customer con prenotazioni future attive
- la cancellazione tenant-wide resta manuale

### Purge retention tecnica

Preview:

```powershell
curl -X POST "https://tuo-dominio/api/platform/data-retention/purge?dry_run=true" ^
  -H "X-Platform-Key: <PLATFORM_API_KEY>"
```

Esecuzione:

```powershell
curl -X POST https://tuo-dominio/api/platform/data-retention/purge ^
  -H "X-Platform-Key: <PLATFORM_API_KEY>"
```

Note:

- il job scheduler esegue anche un purge giornaliero automatico dei dati tecnici purge-safe
- vengono rimossi solo `email_notifications_log`, `payment_webhook_events` processati e `billing_webhook_events` processati oltre retention

### Audit storico dati liberi

Preview consigliata:

```powershell
curl -X POST "https://tuo-dominio/api/platform/data-governance/historical-audit?dry_run=true&window_days=365" ^
  -H "X-Platform-Key: <PLATFORM_API_KEY>"
```

Redazione selettiva della prima iterazione:

```powershell
curl -X POST "https://tuo-dominio/api/platform/data-governance/historical-audit?dry_run=false&window_days=365" ^
  -H "X-Platform-Key: <PLATFORM_API_KEY>"
```

Vincoli operativi:

- la redazione reale della prima iterazione tocca solo `booking_events_log` classificati `safe_to_redact`
- `payment_webhook_events` e `billing_webhook_events` restano audit-only o `needs_manual_review`
- usare sempre prima il `dry_run` per misurare l'impatto prima di mutare i dati storici

### Reset password admin

- usare `POST /api/admin/auth/password-reset/request` sul tenant corretto
- verificare nel log applicativo se l'invio email e fallito
- se nessun provider email e configurato in development/test, il sistema puo simulare l'invio ma non lo fa in produzione

### Troubleshooting email

- su Railway Basic/Hobby verificare prima `RESEND_API_KEY` e `RESEND_FROM`; SMTP esterno e affidabile solo su runtime che espongono le porte classiche
- controllare configurazione SMTP solo se il deploy usa davvero SMTP come fallback
- verificare `email_notifications_log` filtrando per `club_id`
- cercare log applicativi con `event` coerente e `request_id`
- controllare in `GET /api/platform/ops/status` il contatore `recent_failures.email_failed_count`

### Troubleshooting billing SaaS

- verificare `STRIPE_BILLING_WEBHOOK_SECRET`
- controllare `billing_webhook_events` per idempotenza e payload
- verificare `GET /api/admin/billing/status` dal tenant coinvolto
- se il tenant e bloccato, verificare `status`, `trial_ends_at`, `current_period_end` e `suspension_reason`
- controllare in `GET /api/platform/ops/status` il contatore `recent_failures.billing_payment_failed_count`

### Troubleshooting accessi cross-tenant

- cercare warning applicativi con `event=admin_cross_tenant_rejected` o `event=admin_session_rejected`
- confermare host o query `tenant` usati dalla richiesta
- verificare che il cookie admin sia coerente con il tenant corrente

## 6. Incident response minima

### Webhook billing non funzionante

- verificare `GET /api/health`
- verificare secret configurati in ambiente
- controllare i log `billing_webhook_signature_rejected` o errori di configurazione
- se necessario, sospendere manualmente il tenant e riallineare la subscription dopo il fix

### Picco di traffico o abuso pubblico

- verificare ritorni 429 sui path pubblici o auth admin
- controllare se il traffico e concentrato su uno stesso tenant, host o IP
- aumentare temporaneamente `RATE_LIMIT_PER_MINUTE` solo se il carico e legittimo e monitorato
- se il deploy passa da 1 istanza a piu istanze attive, verificare che `RATE_LIMIT_BACKEND` sia impostato a `shared`

### Compromissione account admin

- disattivare o resettare la password dell'admin nel tenant corretto
- invalidare la sessione cambiando password
- verificare log recenti con `request_id`, `tenant_slug` e path admin coinvolti

## 7. Backup minimo realistico

- backup giornaliero del database PostgreSQL condiviso
- retention minima consigliata: 7 backup giornalieri + 4 backup settimanali
- test di restore almeno su ambiente staging o clone isolato
- includere sempre dati di booking, audit, settings tenant, webhook idempotency e subscription state

## 8. Smoke checklist go-live

- `GET /api/health`
- `GET /`
- `GET /api/platform/ops/status` con `X-Platform-Key`
- `GET /api/public/config` tenant default
- `POST /api/public/bookings` tenant default
- login admin tenant default
- `GET /api/admin/settings` tenant default
- `GET /api/admin/billing/status` tenant default
- route privata `/c/:clubSlug/play` tenant default con identify o riconoscimento player
- join di un match open su `/c/:clubSlug/play` tenant default
- create match su `/c/:clubSlug/play` con suggerimenti anti-frammentazione
- completamento `4/4` con verifica del comportamento caparra `OFF` o `ON`
- feed notifiche `/play` con unread count, fallback in-app e stato push coerente
- `GET /api/public/clubs`
- `GET /api/public/clubs/nearby` con fallback coerente se geolocalizzazione assente o negata
- `GET /api/public/clubs/{club_slug}`
- follow/unfollow watchlist discovery
- `POST /api/public/clubs/{club_slug}/contact-request`
- conferma che la pagina pubblica club non abiliti join diretto alla community privata
- stessa triade `public config` + login admin + billing status su un tenant secondario