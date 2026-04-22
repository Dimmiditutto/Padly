Agisci come un Senior Software Engineer, Senior Code Reviewer e QA tecnico.

Leggi prima:

- prompts SaaS/prompt_master.md
- prompts SaaS/STATO_FASE_7.MD
- istanze.md

Contesto reale gia verificato:

- FASE 7 ha introdotto un backend rate limit configurabile `local|shared`, uno snapshot operativo interno e un healthcheck arricchito.
- La suite backend completa e verde, ma la verifica tecnica ha trovato criticita reali ancora aperte sul perimetro FASE 7.
- Devi correggere solo le criticita qui sotto, senza refactor ampi e senza toccare parti non necessarie.

## Obiettivo

Applicare patch minime e mirate per correggere esclusivamente queste criticita confermate.

### 1. Il healthcheck puo esplodere in 500 proprio nel path di errore database

Problema confermato:

- [backend/app/api/routers/payments.py](backend/app/api/routers/payments.py) chiama `build_operational_status_snapshot(db)` prima del `try/except` che dovrebbe convertire i problemi DB in risposta degraded/503.
- [backend/app/services/operations_service.py](backend/app/services/operations_service.py) esegue query reali su `email_notifications_log` e `billing_webhook_events` dentro `build_operational_status_snapshot()`.
- Risultato: se il database o la sessione falliscono in quelle query preliminari, l'eccezione esce prima del `db.execute('SELECT 1')` protetto e il healthcheck puo restituire 500 invece di un segnale operativo coerente.
- Verifica eseguibile gia osservata: chiamando `health(fake_db)` con un fake DB il cui `scalar()` lancia `RuntimeError('db down')`, la funzione propaga `RuntimeError`.

Correzione richiesta:

- il healthcheck deve restare fail-soft sul database e tornare un segnale coerente degraded/503, non 500 non gestito
- evita di far dipendere il percorso base di readiness da query opzionali prima del controllo DB protetto
- se necessario, separa il ping DB minimo dallo snapshot operativo dettagliato o rendi quest'ultimo resiliente ai failure DB
- mantieni piccolo il cambiamento e non riscrivere il router payments

File probabili:

- backend/app/api/routers/payments.py
- backend/app/services/operations_service.py
- backend/tests/test_hardening_ops.py oppure test backend mirati equivalenti

### 2. Il backend shared del rate limit non pulisce davvero i contatori scaduti a cardinalita alta

Problema confermato:

- [backend/app/core/rate_limit.py](backend/app/core/rate_limit.py) elimina i record scaduti solo per `scope_key == key` corrente.
- Questo significa che IP/path/tenant visti una sola volta o raramente non vengono piu ripuliti, quindi `rate_limit_counters` puo crescere senza limite nel tempo in presenza di traffico reale o abuso distribuito.
- Il rischio e coerente col design attuale: la chiave include IP + tenant + path, quindi la cardinalita potenziale e alta e il problema e operativo, non solo teorico.

Correzione richiesta:

- aggiungi una strategia minima e prudente di cleanup dei contatori scaduti che non dipenda solo dalla stessa chiave corrente
- non introdurre scheduler nuovi o componenti esterni solo per questo fix
- mantieni la compatibilita con `RATE_LIMIT_BACKEND=local` e con la regola di [istanze.md](istanze.md)
- aggiungi un test mirato che dimostri la semantica di cleanup minima oppure l'assenza di accumulo indefinito nel caso coperto dalla patch

File probabili:

- backend/app/core/rate_limit.py
- backend/tests/test_hardening_ops.py oppure test backend mirati equivalenti

### 3. Il public health espone dettagli di rate limit piu adatti allo snapshot interno

Problema confermato:

- [backend/app/api/routers/payments.py](backend/app/api/routers/payments.py) include in `GET /api/health` l'intero oggetto `rate_limit`.
- [backend/app/services/operations_service.py](backend/app/services/operations_service.py) include anche `per_minute`, oltre a backend e storage.
- Esiste gia [backend/app/api/routers/platform.py](backend/app/api/routers/platform.py) con `GET /api/platform/ops/status`, che e il posto giusto per dettagli operativi interni protetti da `X-Platform-Key`.
- Risultato: il public health espone configurazione difensiva e dettagli operativi non necessari a un endpoint di readiness pubblico.

Correzione richiesta:

- riduci `GET /api/health` a un segnale minimo coerente per readiness/liveness pubblica
- sposta o mantieni i dettagli operativi piu sensibili solo su `GET /api/platform/ops/status`
- non rompere il control plane interno e non cambiare inutilmente il contratto dello snapshot protetto

File probabili:

- backend/app/api/routers/payments.py
- backend/app/services/operations_service.py
- backend/tests/test_hardening_ops.py oppure test backend mirati equivalenti
- README.md e docs/operations/RUNBOOKS.md solo se serve riallineare la documentazione al contratto finale

## Regole di lavoro

- non fare refactor ampi
- non toccare frontend se non emerge una necessita reale da questi fix
- non cambiare la logica tenant-aware gia corretta del rate limit
- non introdurre Redis, metriche esterne o nuovi servizi
- preferisci patch locali e test mirati
- non correggere problemi non emersi da questa verifica

## Test obbligatori

Devi aggiungere o aggiornare test che dimostrino almeno:

1. il healthcheck non propaga 500 non gestiti quando il database fallisce nel percorso di snapshot operativo
2. il public health espone solo il livello di dettaglio coerente con il contratto scelto dopo il fix
3. il backend shared del rate limit mantiene una strategia minima di cleanup dei record scaduti
4. `GET /api/platform/ops/status` continua a funzionare come endpoint operativo protetto
5. il tenant legacy default continua a funzionare

Poi esegui verifiche reali:

- test backend mirati sui file toccati
- suite backend completa se le patch toccano middleware, healthcheck o segnali operativi globali
- build frontend solo se tocchi il frontend, altrimenti dichiaralo esplicitamente non necessario

## Output obbligatorio

- file toccati
- bug corretti
- test aggiunti o aggiornati
- PASS/FAIL reale dei comandi eseguiti
- rischi residui, solo se restano davvero