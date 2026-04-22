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

Le policy sotto sono operative e documentali. Il repository non applica ancora purge automatiche.

- log applicativi strutturati: 30 giorni su piattaforma di logging
- `billing_webhook_events`: 180 giorni minimi per audit commerciale e troubleshooting
- `payment_webhook_events`: 180 giorni minimi per idempotenza e audit pagamenti booking
- `email_notifications_log`: 90 giorni minimi
- booking ed eventi di booking: retention definita dal tenant secondo obblighi fiscali e operativi; non automatizzata dall'app

## Export dati essenziali

Stato attuale: manuale o semi-guidato.

Procedura minima:

- esportare i dati filtrando per `club_id`
- includere tabelle indirettamente scoped via relazione, in particolare `booking_payments`
- consegnare export separando dati cliente finale dai metadati commerciali del tenant

## Cancellazione o anonimizzazione

Stato attuale: parziale e manuale.

- non esiste ancora un endpoint self-service di cancellazione tenant-wide
- la cancellazione di un singolo tenant richiede procedura applicativa dedicata per evitare effetti collaterali sul database condiviso
- la cancellazione dati cliente finale va valutata con il tenant considerando obblighi fiscali, contestazioni pagamento e finestre di rimborso

## Rischi residui dichiarati

- nessuna purge automatica attiva nel repository
- export e delete per tenant non sono ancora workflow di prodotto completi
- restore per singolo tenant richiede intervento tecnico guidato, non un restore DB diretto