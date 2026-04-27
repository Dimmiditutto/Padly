# Mini prompt - Riattivazione Stripe Billing

Agisci come un Senior Backend/DevOps Engineer esperto di Stripe, Railway, FastAPI e webhook production-hardening.

Obiettivo: riattivare Stripe Billing SaaS in produzione impostando STRIPE_BILLING_WEBHOOK_SECRET solo quando il dominio definitivo e pronto.

## Contesto reale del repo

- Il backend puo partire in produzione anche senza STRIPE_BILLING_WEBHOOK_SECRET.
- Il webhook billing Stripe e esposto su POST /api/billing/webhook/stripe.
- Se il secret manca, il webhook deve restare non operativo e rispondere 503.
- Non confondere Stripe Billing SaaS con i pagamenti Stripe legacy delle prenotazioni.
- Non allentare PLATFORM_API_KEY o gli altri controlli di produzione.

## Cosa devi fare

1. Verifica nel repo i punti che usano il secret:
   - backend/app/core/config.py
   - backend/app/api/routers/billing.py
2. Conferma il dominio pubblico definitivo del backend.
3. In Stripe Dashboard, crea o aggiorna il webhook billing verso:
   https://<dominio-definitivo>/api/billing/webhook/stripe
4. Copia il Signing secret Stripe che inizia con whsec_.
5. Inserisci quel valore nelle Variables del servizio backend su Railway come STRIPE_BILLING_WEBHOOK_SECRET.
6. Esegui un redeploy del backend.
7. Invia un test webhook da Stripe Dashboard e verifica che venga accettato.

## Vincoli

- Applica solo il minimo necessario.
- Nessun refactor generale.
- Nessuna modifica alle migration.
- Non riattivare i flussi Stripe checkout booking se non richiesto.
- Non reintrodurre nel bootstrap produzione un hard fail globale su STRIPE_BILLING_WEBHOOK_SECRET, salvo richiesta esplicita.

## Output atteso

- breve riepilogo dei passaggi eseguiti
- conferma che STRIPE_BILLING_WEBHOOK_SECRET e stato inserito su Railway
- esito del redeploy
- esito del test webhook Stripe
- eventuali blocchi residui

## Checklist finale

- /api/health risponde 200
- il deploy non fallisce in startup
- il webhook billing Stripe non restituisce piu Billing webhook non configurato
- il test webhook Stripe viene ricevuto e processato