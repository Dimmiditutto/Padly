# FASE 3 — BACKEND TENANT-AWARE: BOOKING PUBBLICO, ADMIN E SETTINGS TENANT-SCOPED

Includi: BLOCCO_COMUNE_V5 + STATO_FASE_1.MD + STATO_FASE_2.MD

## Obiettivo

Rendere il backend realmente tenant-aware, estendendo le superfici gia presenti invece di crearne di parallele senza bisogno.

Questa fase deve adattare:
- booking pubblico
- admin auth e sessione
- settings admin
- report, log e query operative
- email e scheduler dove impattano il tenant

## Principio non derogabile

Il tenant non deve essere un dettaglio cosmetico: ogni query critica, ogni mutazione e ogni side effect rilevante devono sapere a quale tenant appartengono.

Questo vale dentro un database unico condiviso: la tenant isolation deve essere garantita da chiavi, query, dependency di contesto, validazioni e test, non dalla separazione fisica dei database.

La retrocompatibilita single-tenant deve continuare a funzionare:
- se esiste un solo tenant, l'app deve continuare a comportarsi come oggi
- se la tenant resolution non trova un host mappato, puo esistere un fallback controllato al default tenant solo se documentato e sicuro

## Servizi o punti di estensione da introdurre

### TenantResolutionService o equivalente
Responsabile di:
- risolvere il tenant corrente da host, slug o fallback controllato
- centralizzare la logica di risoluzione tenant
- evitare duplicazioni nei router

### TenantContext / ClubContext dependency
Responsabile di:
- fornire il tenant corrente ai router e ai servizi
- impedire accessi a dati di tenant diversi

### TenantSettingsService o estensione coerente di settings_service
Responsabile di:
- leggere regole booking tenant-scoped
- fondere fallback environment e override del tenant
- esporre branding minimo e contatti necessari al frontend pubblico e admin

### Estensioni ai service layer esistenti
Adatta i servizi reali gia presenti, in particolare quelli che toccano booking, report, email e scheduler, per:
- filtrare per tenant
- scrivere audit con contesto tenant
- usare notification_email e settings del tenant quando servono
- operare sempre sul database condiviso senza query globali non filtrate

## Endpoint minimi da estendere o introdurre

Estendi preferibilmente le superfici esistenti:

- GET /api/public/config
- GET /api/public/availability
- POST /api/public/bookings
- POST /api/public/bookings/{booking_id}/checkout
- GET /api/public/bookings/{public_reference}/status
- GET e PUT /api/admin/settings
- GET /api/admin/auth/me
- gli endpoint admin booking e report gia presenti

Se necessario, puoi introdurre endpoint minimi aggiuntivi, ad esempio per profilo tenant o tenant resolution, ma solo se l'estensione dei contratti esistenti diventerebbe innaturalmente confusa.

## Contratti minimi attesi

### Public config
La response pubblica deve poter includere, se davvero implementato in questa fase:
- nome tenant oppure public_name del Club se il tenant coincide con il club
- timezone e currency del tenant
- branding minimo utile al frontend
- contatti o support info essenziali
- flags provider coerenti col tenant o con l'ambiente

### Admin settings
La response admin settings deve diventare tenant-scoped e coprire almeno:
- booking rules del tenant
- notification_email
- eventuali campi di profilo/branding minimo decisi nella foundation

### Admin session
Valuta se includere nel payload sessione almeno:
- tenant_id o slug
- tenant public_name
- ruolo admin minimo se introdotto

## Auth e isolamento

Questa fase deve chiarire e implementare con patch minima:
- come l'admin viene associato al proprio tenant
- come gli endpoint admin impediscono l'accesso a dati di altri tenant
- come password reset, cookie e sessione restano coerenti in un contesto multi-tenant

Se introduci ruoli, resta minimale e coerente con il codice reale. Non costruire un RBAC enciclopedico se il repository oggi non lo richiede.

## Test obbligatori

- tenant resolution corretta sul default tenant e su almeno un secondo tenant
- public availability filtrata per tenant
- create booking pubblico scopa i dati del tenant giusto
- admin non puo leggere o mutare prenotazioni di un altro tenant
- admin settings leggono e scrivono solo il tenant corretto
- auth admin e password reset non si rompono
- scheduler o email usano il contesto tenant dove applicabile
- nessuna query critica nuova o modificata resta globale nel database condiviso
- zero regressioni evidenti sui flussi legacy toccati

## Output obbligatorio

- contratti API reali aggiornati
- file toccati
- servizi creati o estesi
- strategia di tenant resolution reale
- test creati o modificati
- PASS/FAIL reale
- STATO_FASE_3.MD con:
  - endpoint definitivi
  - schema dei payload aggiornati
  - strategia di isolamento tenant
  - punti di impatto frontend
