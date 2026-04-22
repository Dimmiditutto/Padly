# STATO FASE 5 — LAYER COMMERCIALE SAAS

## Esito

PASS

Suite backend finale: **112 passed**.
Regressioni mirate FASE 5: **20 passed** in [backend/tests/test_billing_saas.py](backend/tests/test_billing_saas.py).
Regressioni mirate booking/admin: **45 passed** su [backend/tests/test_booking_api.py](backend/tests/test_booking_api.py) e [backend/tests/test_admin_and_recurring.py](backend/tests/test_admin_and_recurring.py).
Build frontend: **gia verde nel pass iniziale FASE 5**; non rilanciata nel pass finale perche il fix ha toccato solo il backend.

---

## Stato finale della fase

FASE 5 e chiusa lato backend.

Il repository dispone ora di:

- modello dati commerciale minimo coerente con il shared database multi-tenant
- control plane platform minimo per provisioning, sospensione e riattivazione tenant
- webhook billing SaaS separato dai booking payments legacy
- enforcement reale sulle superfici operative public e admin
- hardening production sui secret critici del layer billing
- test assertivi sul comportamento commerciale effettivo

---

## File backend toccati / creati

| File | Stato finale |
|------|--------------|
| `backend/app/models/__init__.py` | Aggiunti `BillingInterval`, `SubscriptionStatus`, `Plan`, `ClubSubscription`, `BillingWebhookEvent`; relazione `subscription` su `Club` |
| `backend/alembic/versions/20260422_0004_billing_saas.py` | Migrazione FASE 5 con tabelle `plans`, `club_subscriptions`, `billing_webhook_events` e seed del piano `trial` |
| `backend/app/schemas/billing.py` | Schemi billing e control plane |
| `backend/app/services/billing_service.py` | Provisioning tenant, gestione subscription, webhook idempotente, audit minimo, enforcement coerente |
| `backend/app/api/routers/platform.py` | Control plane (`/platform/tenants`, suspend, reactivate) protetto da `X-Platform-Key` |
| `backend/app/api/routers/billing.py` | Webhook Stripe billing e stato subscription admin; webhook fail-closed in produzione senza secret |
| `backend/app/core/config.py` | Aggiunti `stripe_billing_webhook_secret` e `platform_api_key`; inclusi nei requisiti minimi di produzione |
| `backend/app/main.py` | Registrati `billing.router` e `platform.router` |
| `backend/app/services/tenant_service.py` | `ensure_default_club` crea trial subscription automaticamente sul club di default |
| `backend/app/api/deps.py` | Aggiunte `get_current_club_enforced` e `get_current_admin_enforced` |
| `backend/app/api/routers/public.py` | Enforcement applicato alle route operative public; route read-only lasciate leggibili |
| `backend/app/api/routers/admin_bookings.py` | Enforcement admin applicato |
| `backend/app/api/routers/admin_ops.py` | Enforcement admin applicato |
| `backend/app/api/routers/admin_settings.py` | Enforcement admin applicato |
| `backend/tests/test_billing_saas.py` | Portato a 20 test assertivi su policy, hardening e audit |

## File frontend toccati nel pass iniziale FASE 5

| File | Stato finale |
|------|--------------|
| `frontend/src/types.ts` | Aggiunti `SubscriptionStatus`, `SubscriptionStatusBanner` |
| `frontend/src/services/adminApi.ts` | Aggiunta `getSubscriptionStatus()` |
| `frontend/src/pages/AdminDashboardPage.tsx` | Stato `subscription`, caricamento asincrono, banner informativo admin |

---

## Schema reale piani e subscription

### Plan

```sql
plans (
  id           TEXT PK,
  code         TEXT UNIQUE NOT NULL,
  name         TEXT NOT NULL,
  price_amount NUMERIC(10,2) DEFAULT 0,
  billing_interval ENUM('MONTHLY','YEARLY'),
  is_active    BOOLEAN,
  feature_flags JSON NULLABLE,
  created_at, updated_at
)
```

### ClubSubscription

```sql
club_subscriptions (
  id                        TEXT PK,
  club_id                   TEXT FK clubs UNIQUE,
  plan_id                   TEXT FK plans,
  provider                  TEXT DEFAULT 'none',
  provider_customer_id      TEXT NULLABLE,
  provider_subscription_id  TEXT NULLABLE,
  status                    ENUM('TRIALING','ACTIVE','PAST_DUE','SUSPENDED','CANCELLED'),
  trial_ends_at             DATETIME NULLABLE,
  current_period_end        DATETIME NULLABLE,
  cancelled_at              DATETIME NULLABLE,
  suspension_reason         TEXT NULLABLE,
  created_at, updated_at
)
```

### BillingWebhookEvent

```sql
billing_webhook_events (
  id           TEXT PK,
  provider     TEXT,
  event_id     TEXT UNIQUE,
  event_type   TEXT,
  club_id      TEXT NULLABLE,
  payload      JSON,
  processed_at DATETIME NULLABLE,
  created_at   DATETIME
)
```

Nota: `billing_webhook_events` resta separata da `payment_webhook_events` per mantenere disaccoppiati billing SaaS e pagamenti booking legacy.

---

## Policy stati subscription

| Stato | Descrizione | Accesso booking pubblico operativo | Accesso admin operativo |
|-------|-------------|------------------------------------|-------------------------|
| `TRIALING` | Trial attivo | Pieno | Pieno + banner info |
| `ACTIVE` | Abbonato attivo | Pieno | Pieno |
| `PAST_DUE` | Pagamento fallito / stato commerciale non attivo | Bloccato con 402 | Bloccato con 402 |
| `SUSPENDED` | Sospeso manualmente dalla piattaforma | Bloccato con 402 | Bloccato con 402 |
| `CANCELLED` | Abbonamento cancellato | Bloccato con 402 | Bloccato con 402 |

Regola aggiuntiva:

- trial scaduto: se `status == TRIALING` e `trial_ends_at < now`, `enforce_subscription` blocca con 402

Scelta finale di policy:

- `PAST_DUE` viene trattato come stato bloccante nel backend, non come semplice warning read-only
- le route public read-only possono restare leggibili se non eseguono operazioni operative
- lo stato billing admin resta consultabile via `/api/admin/billing/status` anche quando il tenant e bloccato, per non perdere visibilita sul motivo del blocco

---

## Superfici platform introdotte

### Control Plane (`/api/platform/*`)

Tutte le route richiedono header `X-Platform-Key` con chiave `PLATFORM_API_KEY`.

| Metodo | Path | Descrizione |
|--------|------|-------------|
| GET | `/api/platform/tenants` | Lista tenant con segnali operativi minimi |
| POST | `/api/platform/tenants` | Provisioning nuovo tenant + admin owner |
| POST | `/api/platform/tenants/{club_id}/suspend` | Sospende tenant e registra audit minimo |
| POST | `/api/platform/tenants/{club_id}/reactivate` | Riattiva tenant e registra audit minimo |

### Billing SaaS

| Metodo | Path | Autenticazione |
|--------|------|----------------|
| POST | `/api/billing/webhook/stripe` | Firma Stripe obbligatoria in produzione; fallback dev consentito solo fuori produzione |
| GET | `/api/admin/billing/status` | Cookie admin standard; route lasciata leggibile anche per tenant bloccati |

---

## Enforcement subscription

Dependency finali:

- `get_current_club_enforced`: applica `enforce_subscription` alle superfici public operative
- `get_current_admin_enforced`: applica `enforce_subscription` alle superfici admin operative

Applicazione finale:

- route public operative come availability, create booking e checkout usano il path enforced
- route admin operative usano il path enforced
- route di lettura o supporto possono continuare a usare il path non enforced quando la policy richiede leggibilita anche in stato bloccato

---

## Test FASE 5 finali

Copertura effettiva in [backend/tests/test_billing_saas.py](backend/tests/test_billing_saas.py): **20 test verdi**.

Ambiti coperti:

- provisioning tenant con piano e trial
- bootstrap automatico trial sul default club
- protezione `X-Platform-Key`
- listing tenant platform
- idempotenza webhook billing
- aggiornamento stato subscription da webhook Stripe
- hardening webhook in produzione senza secret
- transizioni di stato `SUSPENDED` e `ACTIVE`
- enforcement `SUSPENDED` sulle superfici public e admin
- enforcement `PAST_DUE` sulle superfici public e admin
- enforcement su trial scaduto
- separazione netta tra billing webhook e booking payments
- audit minimo su `suspend` e `reactivate`
- lettura stato billing admin autenticata

---

## Rischi residui

1. Self-service Stripe Billing non ancora end-to-end: customer portal e checkout subscription restano da implementare se richiesti dal rollout.
2. Esiste solo il piano seed `trial`: eventuali piani `starter`, `pro` o simili vanno creati in un pass dedicato.
3. La UX del banner admin e funzionale ma ancora migliorabile sul piano della distinzione visiva tra warning e blocco.

---

## Verdetto finale

FASE 5 e completata sul backend e validata.

Il layer commerciale SaaS non e piu solo infrastrutturale: governa realmente le superfici operative previste, applica la policy commerciale dichiarata e resta verificato da test backend assertivi e da una suite completa verde.