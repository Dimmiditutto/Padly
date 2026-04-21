# FASE 4 — FRONTEND MULTI-TENANT: BRANDING PUBBLICO E WORKSPACE ADMIN

Includi: BLOCCO_COMUNE_V5 + STATO_FASE_1.MD + STATO_FASE_2.MD + STATO_FASE_3.MD

## Obiettivo

Rendere il frontend coerente con il nuovo backend tenant-aware, riusando l'architettura reale gia esistente invece di inventare una nuova applicazione.

Questa fase deve adattare:
- la pagina pubblica su /
- i client API reali
- le pagine admin gia presenti
- i tipi TypeScript e i componenti condivisi necessari

## Risultato atteso

Il frontend deve poter mostrare e gestire almeno:
- branding pubblico del tenant corrente
- configurazione pubblica tenant-aware
- area admin che espone chiaramente il tenant attivo
- settings del tenant modificabili dalla superficie admin piu coerente col repository reale

## Regole

- non rifare il design system
- usa componenti, classi e pattern gia presenti quando esistono davvero
- nessuna logica critica lato client
- il tenant deve arrivare dal backend o dal contesto host, non da supposizioni client-side
- feedback chiari su loading, success, error
- accessibilita di base: focus, label, disabled state, messaggi errore leggibili
- se devi creare nuove pagine, fallo solo quando la UI esistente non offre una superficie pulita per il nuovo flusso

## Superfici reali da preferire

Parti da file reali gia presenti, ad esempio:
- PublicBookingPage
- App.tsx
- publicApi.ts
- adminApi.ts
- types.ts
- pagine admin e componenti admin gia esistenti

## Flussi minimi da implementare

### Booking pubblico tenant-aware
- la pagina pubblica su / legge il tenant corrente da GET /api/public/config
- renderizza nome tenant, oppure nome club se il tenant coincide col club, branding minimo e contatti reali se disponibili
- mantiene invariato il flusso booking, checkout e cancellazione gia esistente

### Area admin tenant-aware
- la UI admin mostra il tenant attivo e lo stato operativo minimo utile
- la superficie che oggi modifica settings deve diventare tenant-scoped
- l'utente admin non deve avere dubbi su quale tenant sta amministrando

### Branding e configurazione
- aggiorna i tipi TypeScript coerentemente con i nuovi payload backend
- aggiungi o adatta i componenti minimi per logo, intestazione, contatti, settings profilo tenant e notification_email
- se aggiungi theme o colori per tenant, fallo in modo sobrio e coerente col design attuale

### Compatibilita e routing
- la route pubblica principale resta / salvo necessita tecnica forte
- le route admin esistenti devono continuare a funzionare
- se introduci una route nuova per settings tenant o control plane minimo, documenta perche non bastava riusare quelle esistenti

## Test obbligatori

- la pagina pubblica renderizza config tenant-aware corretta
- il branding o il nome tenant cambiano correttamente tra due tenant
- i tipi e i client API consumano i nuovi payload senza regressioni
- la UI admin mostra il tenant corretto
- il form settings tenant salva e ricarica dati coerenti
- redirect e gestione 401 restano funzionanti
- build frontend verde
- zero regressioni sui test esistenti toccati

## Output obbligatorio

- file frontend reali toccati
- route aggiunte o modificate
- componenti creati o adattati e props reali
- contratti frontend-backend aggiornati
- test aggiunti
- PASS/FAIL reale
- STATO_FASE_4.MD con:
  - componenti finali
  - contract frontend-backend
  - punti pronti per il layer commerciale SaaS
