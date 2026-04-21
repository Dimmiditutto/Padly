# FASE 2 — FONDAMENTA DATI SAAS: TENANT, DOMINI E SCOPING LEGACY

Includi: BLOCCO_COMUNE_V5 + STATO_FASE_1.MD

## Obiettivo

Introdurre la foundation dati minima per trasformare il prodotto in un SaaS multi-tenant, senza cambiare ancora in profondita tutti i router e tutti i flussi frontend.

Questa fase deve aggiungere solo le fondamenta dati indispensabili, con migrazioni e backfill credibili.

Vincolo di questa fase: il multi-tenant va implementato nello stesso database condiviso. Non introdurre database separati per tenant e non introdurre schema-per-tenant come default.

## Modelli target minimi

Introduci un root entity di tenant.
Se nel dominio del prodotto il tenant coincide con un club/circolo, il modello puo chiamarsi Club; se scegli un nome piu astratto, documenta chiaramente il mapping tra tenant platform e dominio di business.

Aggiungi, solo se coerente con il repository reale e con patch minima:

### Tenant root: Club o equivalente
Campi minimi attesi:
- id
- slug unique
- public_name
- legal_name nullable
- notification_email
- billing_email nullable
- support_email nullable
- support_phone nullable
- timezone default coerente col repo
- currency default coerente col repo
- is_active
- created_at
- updated_at

Nota:
se serve branding iniziale, preferisci un set minimo e semplice. Puoi usare poche colonne dedicate oppure un payload JSON solo se coerente con lo stile del repository e veramente conveniente.

### TenantDomain / ClubDomain o equivalente
Campi minimi attesi:
- id
- tenant_id o club_id
- host unique
- is_primary
- is_active
- created_at

Nota:
se la tenant resolution iniziale sara solo per slug o default club, puoi introdurre il modello domain gia in questa fase oppure documentarlo e prepararlo con una patch minima compatibile. Non rimandarlo senza motivo se serve davvero.

## Propagazione minima del tenant

Aggancia tenant_id, oppure club_id se il tenant e modellato come Club, alle entita legacy che devono essere isolate per un SaaS multi-tenant serio, con ordine ragionato e backfill esplicito.

L'obiettivo e rendere sicuro il database condiviso: ogni tabella o relazione critica deve poter essere filtrata, validata e auditata in modo tenant-safe.

Tabelle da valutare come target prioritario:
- admins
- customers
- bookings
- recurring_booking_series
- blackout_periods
- app_settings
- booking_events_log
- email_notifications_log

Tabelle da valutare con criterio, evitando over-engineering:
- booking_payments
- payment_webhook_events

Regola:
se una tabella puo essere tenant-scoped in modo sicuro tramite relazione gia obbligatoria, puoi evitare tenant_id diretto solo se documenti chiaramente la scelta, mantieni query efficienti e non perdi auditabilita.

Non usare l'assenza temporanea di tenant_id come pretesto per spostare il problema su database separati: il risultato atteso resta shared database con isolamento logico.

## Bootstrap e retrocompatibilita

Questa fase deve prevedere:
- creazione di un default tenant per i dati gia esistenti
- backfill deterministico di tutte le righe legacy che diventano tenant-scoped
- assegnazione dell'admin esistente al default tenant o al ruolo platform scelto
- compatibilita piena del deploy attuale single-tenant durante la transizione

## Regole

- non introdurre ancora billing SaaS
- non riscrivere tutti i router in questa fase se basta preparare il layer dati
- non rompere booking pubblico, admin auth, pagamenti e recurring esistenti
- mantieni migrazione reversibile
- aggiungi enum Python coerenti con lo stile del repo solo se necessari
- evita una proliferazione di tabelle settings se AppSetting puo ancora essere usato in modo chiaro con scoping tenant

## Test obbligatori

- la migrazione crea le nuove tabelle e i nuovi vincoli
- viene creato il default tenant per la retrocompatibilita
- i dati legacy ottengono tenant_id, oppure club_id se questa e la tenant key scelta, coerente dove richiesto
- slug e host hanno vincoli univoci coerenti
- l'admin legacy resta utilizzabile dopo la migrazione
- insert e query su booking legacy continuano a funzionare
- il modello dati risultante e coerente con database unico condiviso e non richiede database-per-tenant
- downgrade e re-upgrade senza errori

## Output obbligatorio

- file reali toccati
- schema finale reale dell'entita tenant, del TenantDomain / ClubDomain se introdotto e delle colonne di scoping aggiunte
- nome migrazione
- strategia di bootstrap e backfill
- test aggiunti
- PASS/FAIL reale
- STATO_FASE_2.MD con schema, decisioni di dominio e note di retrocompatibilita
