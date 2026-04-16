# Release Checklist

## Configurazione produzione

- [ ] `APP_ENV=production`
- [ ] `APP_URL` punta al dominio pubblico reale Railway o custom domain
- [ ] `DATABASE_URL` punta a PostgreSQL Railway, non a SQLite locale
- [ ] `SECRET_KEY` non e vuota e non coincide con il placeholder di `.env.example`
- [ ] `ADMIN_EMAIL` e `ADMIN_PASSWORD` sono reali e non coincidono con i placeholder di `.env.example`
- [ ] `SCHEDULER_ENABLED=true` solo sull'istanza backend designata a reminder e scadenze

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

## Validazione automatica pre-rilascio

- [ ] Backend: `cd backend && ../.venv/bin/python -m pytest tests -q`
- [ ] Frontend build: `cd frontend && npm run build`
- [ ] Frontend test: `cd frontend && npm run test:run`
- [ ] Docker build completata senza errori
- [ ] Smoke test container eseguito su `/api/health` e `/`

## Verifiche manuali minime

- [ ] Prenotazione pubblica felice con creazione hold, checkout e conferma finale
- [ ] Checkout annullato con ritorno coerente su stato booking
- [ ] Login admin riuscito e accesso dashboard
- [ ] Creazione booking manuale admin
- [ ] Cancellazione booking da area admin
- [ ] Marcatura `COMPLETED`, `NO_SHOW` e `saldo al campo`
- [ ] Report summary admin coerente con booking confermati, pending, cancellati e caparre incassate

## Gate finale

- GO: tutti i controlli sopra sono verdi e gli env di produzione sono reali
- NO-GO: anche un solo placeholder di sicurezza, webhook non allineato o validazione automatica fallita