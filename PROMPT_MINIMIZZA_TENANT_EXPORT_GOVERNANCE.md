Agisci come un Senior Software Architect, Senior Software Engineer, Senior Code Reviewer e QA tecnico.

Leggi prima:

- prompts SaaS/prompt_master.md
- prompts SaaS/STATO_FASE_8.MD
- PROMPT_VERIFICA_ESITO.md
- docs/operations/DATA_GOVERNANCE.md
- docs/operations/RUNBOOKS.md

## Contesto reale gia verificato

- il control plane interno espone gia workflow di data governance tramite [backend/app/api/routers/platform.py](backend/app/api/routers/platform.py)
- [backend/app/services/data_governance_service.py](backend/app/services/data_governance_service.py) ha gia ridotto il customer export omettendo `tenant_data` interni e non riesponendo piu `email_notifications.error` nel customer export
- il rischio residuo dichiarato e diverso: il tenant export puo ancora includere testo tecnico raw nei log email, pur essendo una superficie di governance e non un endpoint di supporto tecnico puro
- il database e shared-database e i log tecnici a database non vanno mutati per questo lavoro
- la suite backend completa e verde; il frontend non va toccato

## Obiettivo

Ridurre il tenant export a una proiezione governance text-safe per default, senza modificare la logica di business, senza alterare i record storici a database e senza rompere il supporto operativo.

Questo lavoro NON deve:

- cambiare booking, pagamenti, scheduler o webhook processing
- cancellare o riscrivere `EmailNotificationLog.error` a database
- introdurre nuove regole di dominio o nuove dipendenze esterne
- modificare la logica di business

Deve invece separare meglio:

- export governance minimizzato
- eventuale supporto tecnico dettagliato, che non deve stare nello stesso payload governance se non gia necessario e giustificato

## Risultato atteso

Implementare una patch minima che renda il tenant export coerente con il principio gia applicato al customer export:

1. il payload governance deve essere sicuro per default
2. i testi tecnici raw non devono essere riesposti inutilmente
3. i dati operativi utili devono restare disponibili in forma sintetica o strutturata

## Perimetro obbligatorio

### 1. Minimizzazione del blocco `email_notifications`

Nel tenant export, riesamina il blocco `customer_data.email_notifications` o l'equivalente se ristrutturato minimamente.

Vincoli:

- non esporre `error` raw nel payload governance tenant-scoped se contiene testo libero tecnico o customer-related
- mantenere campi sicuri e gia utili come `id`, `booking_id`, `recipient`, `template`, `status`, `sent_at`, `created_at` solo se coerenti con il contratto governance esistente
- se serve preservare il segnale di failure, preferisci un indicatore sintetico o un campo strutturato sicuro invece del testo completo

### 2. Nessuna mutazione dei log storici

Il fix deve essere di proiezione, non di scrittura:

- niente update di `EmailNotificationLog.error` a database
- niente purge, redaction o bonifica retroattiva dei log per questo task
- il comportamento di invio email e logging in [backend/app/services/email_service.py](backend/app/services/email_service.py) deve restare invariato

### 3. Nessuna regressione sul tenant export utile

Il tenant export deve restare funzionale e strutturato:

- non eliminare dati realmente necessari all'uso governance del tenant export
- non cambiare inutilmente gli altri blocchi del payload se il rischio emerso riguarda solo il testo tecnico raw dei log email
- non introdurre endpoint nuovi se la patch puo stare nel contratto esistente

## Regole di lavoro

- non fare refactor ampi
- non toccare frontend
- non modificare la logica di business
- non cambiare i workflow di anonimizzazione customer oltre quanto strettamente necessario a mantenere coerenza del contratto
- preferisci patch locali su [backend/app/services/data_governance_service.py](backend/app/services/data_governance_service.py) e, solo se indispensabile, su [backend/app/schemas/data_governance.py](backend/app/schemas/data_governance.py)
- aggiorna la documentazione solo se il contratto esposto cambia davvero in modo osservabile

## Domande tecniche a cui il codice deve rispondere

Prima di chiudere il lavoro, il risultato deve chiarire concretamente:

- il tenant export continua a fornire abbastanza contesto operativo senza testo raw?
- il blocco `email_notifications` e ora text-safe per default?
- il fix resta confinato al layer di export senza effetti collaterali sul logging reale?

## Test obbligatori

Devi aggiungere o aggiornare test che dimostrino almeno:

1. il tenant export non espone piu `email_notifications.error` raw quando presente
2. il customer export continua a non riesporre `email_notifications.error`
3. il tenant export continua a restituire il blocco `email_notifications` con i campi ancora ammessi dal contratto scelto
4. gli altri blocchi del tenant export restano coerenti
5. il tenant legacy default continua a funzionare se toccato indirettamente dai test

## Verifiche reali obbligatorie

- test backend mirati sui file toccati
- suite backend completa se tocchi servizi condivisi del control plane o contratti usati da piu endpoint
- build frontend non necessaria salvo modifica UI, e in quel caso dichiaralo esplicitamente

## Output obbligatorio

- file toccati
- contratto finale scelto per `email_notifications` nel tenant export
- test aggiunti o aggiornati
- PASS/FAIL reale dei comandi eseguiti
- eventuali rischi residui reali

## Regola finale

Non trasformare questo task in una revisione generale della governance dati.

Chiudi solo il rischio residuo del tenant export troppo verboso, con una patch minima di proiezione coerente con il codice attuale.