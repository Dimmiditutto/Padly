# Data Governance Minima

## Confini dei dati

### Dati del tenant

- anagrafica `clubs` e `club_domains`
- admin del tenant
- configurazione tenant in `app_settings`
- stato commerciale e subscription SaaS del tenant

### Dati del cliente finale

- anagrafica cliente per prenotazione
- prenotazioni, cancellazioni, pagamenti booking e reminder
- token pubblici di stato e cancellazione collegati al booking

## Retention minima consigliata

Le policy sotto sono ora applicate in modo minimo ai dati tecnici purge-safe tramite job scheduler giornaliero e endpoint interno guidato `POST /api/platform/data-retention/purge`.

- log applicativi strutturati: 30 giorni su piattaforma di logging
- `billing_webhook_events`: 180 giorni minimi per audit commerciale e troubleshooting
- `payment_webhook_events`: 180 giorni minimi per idempotenza e audit pagamenti booking
- `email_notifications_log`: 90 giorni minimi
- booking ed eventi di booking: retention definita dal tenant secondo obblighi fiscali e operativi; non automatizzata dall'app

## Export dati essenziali

Stato attuale: guidato lato control plane interno.

Workflow disponibile:

- `GET /api/platform/tenants/{club_id}/data-export`
- query `scope=tenant` per export tenant-scoped completo ma filtrato
- query `scope=customer&customer_id=...` per export customer-scoped minimale
- nel caso `scope=customer` il payload non espone `tenant_data` interni come admin, settings o subscription; il contesto tenant resta limitato al blocco `club`
- l'export separa `tenant_data` da `customer_data`
- sono inclusi anche i `booking_payments` indirettamente scoped via `booking_id`
- non viene esposto un dump totale e non filtrato del database

## Cancellazione o anonimizzazione

Stato attuale: parziale ma con workflow applicativo minimo per customer finali.

- `POST /api/platform/tenants/{club_id}/customers/{customer_id}/anonymize` anonimizza il customer in-place e preserva booking, pagamenti e riferimenti storici
- il workflow redige anche il testo libero customer-related nei `booking.note` collegati, per evitare riesposizione nel perimetro governance
- il workflow rifiuta il caso con prenotazioni future attive, che resta manuale per non rompere operativita e notifiche
- i log email collegati ai booking del customer vengono riallineati al dato anonimizzato

- non esiste ancora un endpoint self-service di cancellazione tenant-wide
- la cancellazione di un singolo tenant richiede procedura applicativa dedicata per evitare effetti collaterali sul database condiviso
- la cancellazione dati cliente finale va valutata con il tenant considerando obblighi fiscali, contestazioni pagamento e finestre di rimborso

## Rischi residui dichiarati

- il purge automatico copre solo `email_notifications_log`, `payment_webhook_events` processati e `billing_webhook_events` processati
- export e delete tenant-wide non sono ancora workflow di prodotto completi
- restore per singolo tenant richiede intervento tecnico guidato, non un restore DB diretto

## Audit storico e bonifica prudente

Workflow disponibile lato control plane interno:

- `POST /api/platform/data-governance/historical-audit?dry_run=true`
- l'endpoint analizza `booking_events_log`, `payment_webhook_events`, `billing_webhook_events` e `email_notifications_log.error` nella finestra temporale richiesta
- l'output restituisce solo conteggi, classificazioni e campioni minimizzati; per i webhook include anche una review projection strutturata con provider, event type, path sensibili e preview sicura solo dove disponibile, senza esporre payload completi o testo integrale dei record sospetti
- le classificazioni minime restituite sono `safe_to_redact`, `needs_manual_review` e `keep_for_audit`

Scelta prudente della prima iterazione:

- la redazione reale e disponibile solo per `booking_events_log`
- i raw webhook payload restano in review manuale o audit-only, non vengono redatti automaticamente
- l'obiettivo e ridurre l'incertezza operativa senza rompere audit, idempotenza o troubleshooting