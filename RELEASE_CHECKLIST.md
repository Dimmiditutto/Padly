# Release Checklist

## Configurazione produzione

- [ ] `APP_ENV=production`
- [ ] `APP_URL` punta al dominio pubblico reale Railway o custom domain
- [ ] `DATABASE_URL` punta a PostgreSQL Railway, non a SQLite locale
- [ ] `SECRET_KEY` non e vuota e non coincide con il placeholder di `.env.example`
- [ ] `ADMIN_EMAIL` e `ADMIN_PASSWORD` sono reali e non coincidono con i placeholder di `.env.example`
- [ ] `PLATFORM_API_KEY` e reale e non placeholder
- [ ] `STRIPE_BILLING_WEBHOOK_SECRET` e reale se il layer billing SaaS e attivo in produzione
- [ ] `SCHEDULER_ENABLED=true` solo sull'istanza backend designata a reminder e scadenze
- [ ] `RATE_LIMIT_BACKEND=local` per deploy a 1 istanza oppure `shared` se il deploy e davvero multi-instance
- [ ] Se `/play` usa web push privato in produzione, `PLAY_PUSH_VAPID_PUBLIC_KEY` e `PLAY_PUSH_VAPID_PRIVATE_KEY` sono configurate oppure il fallback in-app e stato accettato esplicitamente

## Integrazioni esterne

- [ ] SMTP configurato con `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`
- [ ] Stripe configurato con `STRIPE_SECRET_KEY` e `STRIPE_WEBHOOK_SECRET`
- [ ] PayPal configurato con `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID`
- [ ] URL webhook Stripe allineato a `/api/payments/stripe/webhook`
- [ ] URL webhook PayPal allineato a `/api/payments/paypal/webhook`

## Deploy e runtime

- [ ] `railway.json` usa `healthcheckPath=/api/health`
- [ ] Il container serve sia API che SPA dal singolo servizio applicativo
- [ ] Nessuna replica aggiuntiva con scheduler attivo in parallelo
- [ ] `GET /api/health` risponde `200`
- [ ] `GET /` serve correttamente la SPA buildata
- [ ] `GET /api/platform/ops/status` risponde `200` con `X-Platform-Key` valido
- [ ] `checks.rate_limit.backend` e coerente con la topologia scelta
- [ ] Lo stato scheduler esposto da health e control plane e coerente con l'istanza designata

## Validazione automatica pre-rilascio

- [ ] Backend: `cd backend && ../.venv/bin/python -m pytest tests -q`
- [ ] Frontend build: `cd frontend && npm run build`
- [ ] Frontend test: `cd frontend && npm run test:run`
- [ ] Docker build completata senza errori
- [ ] Smoke test container eseguito su `/api/health` e `/`

## Verifiche manuali minime

### Booking e admin core

- [ ] Prenotazione pubblica felice con creazione hold, checkout e conferma finale
- [ ] Checkout annullato con ritorno coerente su stato booking
- [ ] Login admin riuscito e accesso dashboard
- [ ] Creazione booking manuale admin
- [ ] Cancellazione booking da area admin
- [ ] Marcatura `COMPLETED`, `NO_SHOW` e `saldo al campo`
- [ ] `GET /api/admin/billing/status` coerente sul tenant verificato
- [ ] Report summary admin coerente con booking confermati, pending, cancellati e caparre incassate

### Play privata `/c/:clubSlug/play`

- [ ] La route canonical tenant-aware si apre correttamente
- [ ] Il player viene riconosciuto oppure completa l identify flow senza errori
- [ ] Join di un match aperto eseguito con esito coerente
- [ ] Create match con suggerimenti anti-frammentazione verificato
- [ ] Completamento `4/4` coerente con la configurazione community: offline se caparra `OFF`, checkout immediato del quarto player se caparra `ON`
- [ ] Feed notifiche `/play` verificato con unread count e fallback in-app coerente

### Discovery pubblica

- [ ] `/clubs` carica correttamente dal backend
- [ ] `/clubs/nearby` gestisce fallback coerente se la geolocalizzazione e negata o assente
- [ ] `/c/:clubSlug` espone la pagina pubblica senza sbloccare funzioni private
- [ ] Follow/unfollow watchlist verificato
- [ ] Contact request guidata verificata

### Multi-tenant minimo

- [ ] Tenant default verificato su public config, login admin e billing status
- [ ] Tenant secondario verificato almeno su public config, login admin e billing status

## Gate finale

- GO: tutti i controlli sopra sono verdi, gli env di produzione sono reali e gli smoke `/play` e discovery pubblico sono coperti
- NO-GO: anche un solo placeholder di sicurezza, webhook non allineato, smoke core bloccato o validazione automatica fallita