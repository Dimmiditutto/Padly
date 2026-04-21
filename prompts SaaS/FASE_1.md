# FASE 1 — AUDIT REALE DEL REPOSITORY E PIANO SAAS A PATCH MINIME

Includi: BLOCCO_COMUNE_V5

## Obiettivo

Non implementare ancora il SaaS multi-tenant. Esegui prima una review tecnica reale del repository per capire:
- dove vive la logica di booking, disponibilita, pagamenti, scheduler e settings
- come sono strutturati backend e frontend oggi
- quali assunzioni single-tenant sono hardcoded
- quali patch minime servono per portare il progetto verso un SaaS serio senza rompere il prodotto esistente

Assumi come target architetturale un SaaS multi-tenant con database unico condiviso, salvo evidenza tecnica contraria realmente verificata.

## Prerequisiti da verificare

Verifica realmente, senza assumere:
- il backend si avvia oppure almeno importa correttamente
- le migrazioni esistenti sono eseguibili
- la suite test backend esiste ed e lanciabile
- il frontend compila
- il routing frontend e identificabile
- il sistema email esistente e identificabile
- il modello Booking e la logica di disponibilita sono rintracciabili
- auth admin, password reset e settings admin sono rintracciabili

Se uno di questi punti fallisce, non proseguire con implementazioni arbitrarie: segnala il problema e circoscrivi la patch minima necessaria.

## Cosa devi fare

1. Ispeziona il repository reale.
2. Elenca i file rilevanti per:
   - booking e disponibilita
   - pagamenti booking
   - admin auth e sessione
   - settings e configurazioni runtime
   - scheduler e email
   - report, audit e log
   - pagine pubbliche e pagine admin
   - migrazioni e test
3. Individua gli hardcode single-tenant reali, ad esempio:
   - bootstrap di un solo admin
   - regole booking globali in app_settings
   - timezone e currency globali
   - assenza di tenant_id esplicito o club_id se il tenant coincide con il club
   - report e query globali
   - app pubblica ancorata a un solo brand su /
4. Verifica che il percorso di migrazione verso il multi-tenant possa restare su database unico condiviso, individuando:
   - tabelle che richiedono tenant_id esplicito
   - tabelle dove basta lo scoping tramite relazione obbligatoria
   - query o servizi che oggi leggono globalmente e rischiano data leakage
   - eventuali punti che sembrano spingere verso database-per-tenant senza vera necessita
5. Evidenzia i debiti tecnici che impattano il percorso SaaS:
   - vincoli mancanti per tenant isolation
   - service layer o router da estendere con meno rischio
   - aree sensibili ai race condition
   - tabelle che richiederanno backfill
   - punti in cui billing SaaS e booking payments potrebbero confondersi
6. Definisci un piano di patch minimo a fasi per arrivare a:
   - foundation multi-tenant
   - backend tenant-aware
   - frontend tenant-aware e branding tenant
   - layer commerciale SaaS con subscription
   - hardening operativo e go-live
7. Non implementare ancora chat, LLM o matchmaking: in questo repository non sono il passo giusto per la trasformazione SaaS.

## Output obbligatorio

- mappa reale del repository
- assunzioni confermate
- assunzioni smentite
- hardcode single-tenant rilevati
- conferma esplicita che la roadmap usa database unico condiviso oppure spiegazione tecnica reale se non fosse sostenibile
- problemi tecnici e rischi architetturali reali
- rischi di regressione
- piano di patch minimo ordinato per FASE_2, FASE_3, FASE_4, FASE_5 e FASE_6
- eventuali micro-fix preparatori solo se strettamente necessari
- STATO_FASE_1.MD con:
  - file reali individuati
  - assunzioni confermate
  - assunzioni smentite
  - hardcode single-tenant da rimuovere in ordine
  - ordine esatto delle fasi successive
