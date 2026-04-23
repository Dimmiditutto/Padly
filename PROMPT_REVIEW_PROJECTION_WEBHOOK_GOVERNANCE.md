Agisci come un Senior Software Architect, Senior Software Engineer, Senior Code Reviewer e QA tecnico.

Leggi prima:

- prompts SaaS/prompt_master.md
- prompts SaaS/STATO_FASE_8.MD
- PROMPT_BONIFICA_STORICI_GOVERNANCE.md
- PROMPT_VERIFICA_ESITO.md
- docs/operations/DATA_GOVERNANCE.md
- docs/operations/RUNBOOKS.md

## Contesto reale gia verificato

- [backend/app/services/historical_governance_service.py](backend/app/services/historical_governance_service.py) introduce gia un audit storico prudente con classificazioni `safe_to_redact`, `needs_manual_review` e `keep_for_audit`
- nella prima iterazione i raw webhook payload restano volutamente review-only e non vengono redatti automaticamente
- questo e corretto sul piano prudenziale, ma resta un rischio operativo residuo: l'audit sa dire che un webhook merita review, ma non offre ancora una proiezione strutturata abbastanza utile per una review operativa consistente senza riaprire i payload raw
- la logica di business e l'idempotenza dei provider non vanno toccate

## Obiettivo

Introdurre una review projection prudente dei webhook per il control plane interno, lasciando intatti i payload raw a database e senza modificare la logica di business.

Questo lavoro NON deve:

- redigere o mutare i raw webhook payload in [backend/app/models/__init__.py](backend/app/models/__init__.py)
- cambiare il processing dei webhook in [backend/app/services/payment_service.py](backend/app/services/payment_service.py) o nei flussi billing
- introdurre deduplicazione, regole idempotenza o validazioni di dominio nuove
- la logica di business

Deve invece migliorare il layer di audit/review in modo strutturato e sicuro.

## Risultato atteso

Implementare una proiezione di review che permetta di vedere, per i webhook classificati `needs_manual_review` o `keep_for_audit`, un riepilogo utile ma minimizzato:

1. metadati del record
2. indicatori sensibili trovati
3. campi o path rilevanti individuati
4. eventuale preview strutturata sicura, solo se difendibile e senza riesporre testo raw

## Perimetro obbligatorio

### 1. Review projection per `payment_webhook_events` e `billing_webhook_events`

Estendi l'audit storico in modo che la risposta contenga un riepilogo piu utile per la review manuale.

La projection deve essere costruita solo da dati sicuri o minimizzati, ad esempio:

- `provider`
- `event_type`
- `club_id` quando disponibile
- `created_at`
- elenco dei path sensibili individuati
- conteggio indicatori o famiglie di indicatori
- eventuale preview provider-specific minimizzata, solo se chiaramente sicura

Vincoli:

- niente payload completi in risposta
- niente testo raw customer-related in risposta
- niente dump di nested object completi solo per comodita

### 2. Strategia provider-specifica prudente

Se introduci preview strutturate oltre ai semplici indicatori, falle solo dove il codice reale lo consente in modo difendibile.

Regole:

- usa whitelist di campi o path noti, non regex globali sul JSON per costruire preview arbitrarie
- se un provider o event type non e abbastanza chiaro, resta su indicatori e path soltanto
- il default sicuro deve continuare a essere `needs_manual_review` senza esposizione raw

### 3. Nessuna mutazione dei raw payload

Il payload autoritativo a database resta intatto:

- niente update dei record webhook esistenti
- niente redazione in place
- niente trasformazioni che cambiano troubleshooting o audit trail

## Regole di lavoro

- non fare refactor ampi
- non toccare frontend
- non modificare la logica di business di booking o billing
- non introdurre nuove dipendenze esterne
- preferisci patch locali su [backend/app/services/historical_governance_service.py](backend/app/services/historical_governance_service.py), [backend/app/schemas/data_governance.py](backend/app/schemas/data_governance.py) e, solo se necessario, [backend/app/api/routers/platform.py](backend/app/api/routers/platform.py)
- aggiorna la documentazione solo se la risposta dell'endpoint cambia davvero in modo rilevante

## Domande tecniche a cui il codice deve rispondere

Prima di chiudere il lavoro, il risultato deve chiarire concretamente:

- un operatore puo fare una prima review utile senza aprire il payload raw?
- i webhook continuano a restare review-only e immutati?
- i dati restituiti dal control plane sono minimizzati ma abbastanza leggibili da essere operativamente utili?

## Test obbligatori

Devi aggiungere o aggiornare test che dimostrino almeno:

1. l'audit storico continua a non esporre payload raw dei webhook
2. la risposta contiene la nuova review projection o i nuovi campi di riepilogo per webhook quando ci sono indicatori
3. i path o indicatori sensibili vengono restituiti in forma minimizzata e strutturata
4. i record webhook a database restano invariati
5. i casi senza regola provider-specific restano comunque utili alla review senza uscire dal perimetro minimizzato
6. il tenant legacy default continua a funzionare se toccato indirettamente dai test

## Verifiche reali obbligatorie

- test backend mirati sui file toccati
- suite backend completa se tocchi servizi condivisi del control plane o contratti di risposta gia usati
- build frontend non necessaria salvo modifica UI, e in quel caso dichiaralo esplicitamente

## Output obbligatorio

- file toccati
- forma finale della review projection introdotta
- campi o path restituiti per i webhook
- conferma esplicita che i raw payload restano invariati
- test aggiunti o aggiornati
- PASS/FAIL reale dei comandi eseguiti
- rischi residui reali

## Regola finale

Non trasformare questa attivita in una bonifica webhook invasiva.

La prima iterazione deve aumentare la qualita della review operativa, non cambiare i payload autoritativi o la logica di processamento dei webhook.