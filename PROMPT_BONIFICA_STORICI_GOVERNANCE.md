Agisci come un Senior Software Architect, Senior Software Engineer, Senior Code Reviewer e QA tecnico.

Leggi prima:

- prompts SaaS/prompt_master.md
- prompts SaaS/STATO_FASE_8.MD
- docs/operations/DATA_GOVERNANCE.md
- docs/operations/RUNBOOKS.md

## Contesto reale gia verificato

- la FASE 8 ha introdotto workflow interni minimi per export tenant/customer, anonimizzazione customer e purge tecnica dei dati purge-safe
- i fix post-verifica di FASE 8 hanno gia corretto due punti: export `scope=customer` davvero minimale e anonimizzazione che redige anche `booking.note`
- la suite backend completa e verde
- resta un rischio residuo dichiarato e fuori scope dei fix FASE 8: payload storici liberi in log business o webhook possono ancora contenere testo precedente all'anonimizzazione

## Obiettivo

Aprire un lavoro separato e prudente di bonifica storica dei dati liberi, senza confonderlo con la FASE 8 e senza compromettere audit, idempotenza o troubleshooting e senza modificare la logica di business

Questa attivita NON deve partire da una redazione cieca dei webhook raw.
Deve partire da un audit tecnico guidato, con output utile e basso rischio operativo.

## Risultato atteso

Implementare una superficie interna minima che permetta di:

1. ispezionare in `dry_run` la presenza di testo potenzialmente sensibile o customer-related nei record storici
2. separare chiaramente i record safe-to-redact da quelli che richiedono decisione esplicita o review manuale
3. introdurre, solo dove e davvero sicuro, una redazione selettiva e minimamente invasiva

## Perimetro iniziale obbligatorio

### 1. Audit interno dry run

Introdurre un audit in sola lettura, preferibilmente nel control plane interno gia esistente, che analizzi almeno:

- `booking_events_log`
- `payment_webhook_events`
- `billing_webhook_events`
- eventuali campi testuali tecnici plausibili come `email_notifications_log.error`, se presenti e utili

Vincoli:

- non restituire payload completi o testo integrale dei record sospetti
- restituire conteggi, classi di rischio e campioni minimizzati dove utile
- distinguere almeno per tabella, tenant quando disponibile, e finestra temporale
- supportare `dry_run=true` come modalita predefinita o equivalente

### 2. Classificazione dei dati storici

L'audit deve classificare i record almeno in queste categorie:

- `safe_to_redact`
- `needs_manual_review`
- `keep_for_audit`

Regole pragmatiche:

- `booking_events_log` con note cliente duplicate, email o telefono in chiaro e il candidato principale a `safe_to_redact`
- i raw webhook payload NON vanno marcati automaticamente `safe_to_redact` senza una regola provider-specific chiara
- i record non classificabili in modo difendibile devono finire in `needs_manual_review`

### 3. Bonifica selettiva opzionale ma solo per superfici davvero sicure

Se dal codice reale emerge una superficie sicura da bonificare subito, limita la prima redazione a:

- `booking_events_log.message`
- `booking_events_log.payload`

solo quando i campi contengono testo libero customer-related che il repository controlla direttamente.

Vincoli:

- niente redazione massiva via regex generiche su tutto il database
- non toccare retroattivamente i raw webhook payload nella prima iterazione
- non toccare record necessari all'idempotenza dei provider
- non toccare dati booking commerciali o fiscali se non sono chiaramente duplicati e safe-to-redact

## Regole di lavoro

- non fare refactor ampi
- non toccare frontend
- non introdurre una compliance suite generica
- non introdurre nuove dipendenze esterne solo per questa attivita
- riusare il control plane interno e i pattern gia introdotti in FASE 7 e FASE 8
- evitare bonifiche irreversibili su dati storici ad alto rischio senza una classificazione difendibile
- se un ambito non e sufficientemente chiaro, preferire audit e classificazione alla mutazione del dato

## Domande tecniche a cui il codice deve rispondere

Prima di chiudere il lavoro, il risultato deve chiarire concretamente:

- quante tabelle storiche contengono davvero testo libero rilevante
- quante occorrenze sembrano safe-to-redact
- quante richiedono review manuale
- quali record non vanno toccati per ragioni di audit, supporto o idempotenza

## Test obbligatori

Devi aggiungere o aggiornare test che dimostrino almeno:

1. l'audit interno funziona in `dry_run` senza esporre payload completi
2. l'output distingue almeno tra `safe_to_redact`, `needs_manual_review` e `keep_for_audit`
3. i record `booking_events_log` chiaramente customer-related vengono rilevati correttamente
4. i raw webhook payload non vengono redatti o classificati automaticamente come `safe_to_redact` senza regola esplicita
5. il tenant legacy default continua a funzionare

Se introduci anche una bonifica selettiva reale nella prima iterazione, aggiungi test che dimostrino almeno:

6. la redazione tocca solo i campi dichiarati safe-to-redact
7. i record webhook restano invariati
8. i dati necessari a booking, pagamenti e troubleshooting non vengono rotti

## Verifiche reali obbligatorie

- test backend mirati sui file toccati
- suite backend completa se tocchi servizi condivisi, control plane o scheduler
- build frontend non necessaria salvo modifica UI, e in quel caso dichiaralo esplicitamente

## Output obbligatorio

- file toccati
- superfici storiche analizzate
- classificazione introdotta
- eventuali superfici bonificate davvero
- superfici lasciate volutamente in sola review manuale
- test aggiunti o aggiornati
- PASS/FAIL reale dei comandi eseguiti
- rischi residui reali

## Regola finale

Non vendere questa attivita come “GDPR completa”.

Se il repository non offre abbastanza confidenza per mutare un dato storico, fai audit e classificazione, non mutazione.

La priorita della prima iterazione e ridurre l'incertezza operativa senza rompere audit o integrazioni esterne.