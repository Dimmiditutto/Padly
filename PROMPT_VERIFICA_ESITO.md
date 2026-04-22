Agisci come un Senior Software Engineer, Senior Code Reviewer e QA tecnico.

Leggi prima:

- prompts SaaS/prompt_master.md
- prompts SaaS/STATO_FASE_6.MD

Contesto reale gia verificato:

- FASE 6 e stata chiusa con backend suite verde e build frontend verde.
- La verifica successiva ha pero trovato alcune criticita reali nel nuovo hardening operativo.
- Devi correggere solo le criticita qui sotto, senza refactor ampi e senza toccare parti non necessarie.

## Obiettivo

Applicare patch minime e mirate per correggere esclusivamente queste criticita confermate.

### 1. Bypass reale del rate limit tramite tenant hint fittizi

Problema confermato:

- [backend/app/main.py](backend/app/main.py) costruisce la chiave di rate limit in `get_rate_limit_tenant_scope()` usando lo slug o host dichiarato dal client, non il tenant realmente risolto.
- [backend/app/api/deps.py](backend/app/api/deps.py) risolve invece il tenant con fallback al default club tramite `resolve_tenant_context(..., allow_default_fallback=True)`.
- [backend/app/services/tenant_service.py](backend/app/services/tenant_service.py) conferma che slug o host invalidi ricadono sul tenant di default.
- Verifica eseguibile gia osservata: con `rate_limit_per_minute = 1`, due richieste verso lo stesso tenant reale ma con `?tenant=foo` e `?tenant=bar` passano entrambe, e due login admin con host invalidi diversi finiscono in bucket diversi pur puntando entrambi al default tenant.

Correzione richiesta:

- il rate limit deve usare il tenant realmente risolto quando disponibile, non il tenant hint grezzo del client
- i tenant hint invalidi non devono permettere di creare bucket separati se la request ricade sullo stesso tenant reale
- mantieni comunque isolamento tra tenant validi distinti

File probabili:

- backend/app/main.py
- backend/app/api/deps.py
- backend/app/services/tenant_service.py
- backend/tests/test_hardening_ops.py oppure test backend mirati equivalenti

### 2. Healthcheck falso positivo quando lo scheduler dovrebbe essere attivo ma risulta fermo

Problema confermato:

- [backend/app/api/routers/payments.py](backend/app/api/routers/payments.py) restituisce `status: ok` e HTTP 200 anche quando `settings.scheduler_enabled == true` e `scheduler.running == false`.
- [backend/app/core/scheduler.py](backend/app/core/scheduler.py) in `start_scheduler()` intercetta `RuntimeError` e ritorna in silenzio.
- Questo rende il segnale operativo poco affidabile per readiness e incident response: l'istanza puo apparire sana anche se i job richiesti non sono operativi.

Correzione richiesta:

- se l'istanza e configurata per eseguire i job (`scheduler_enabled=true` fuori da test) e lo scheduler non e running, il healthcheck non deve risultare pienamente sano
- scegli una soluzione minima e coerente: o HTTP 503/degraded, oppure un comportamento equivalente chiaramente testato e allineato al deployment reale
- evita refactor ampi del subsystem scheduler

File probabili:

- backend/app/api/routers/payments.py
- backend/app/core/scheduler.py
- backend/tests/test_hardening_ops.py oppure test backend mirati equivalenti

### 3. Osservabilita dei job schedulati ancora parziale

Problema confermato:

- [backend/app/core/observability.py](backend/app/core/observability.py) viene agganciato soprattutto sul path HTTP.
- [backend/app/core/scheduler.py](backend/app/core/scheduler.py) emette warning ed exception sui job senza bind esplicito di `club_id` o `tenant_slug` durante i loop per tenant.
- Risultato: nei flussi reminder/expiry l'osservabilita resta meno utile proprio nei path operativi fuori request-response.

Correzione richiesta:

- aggiungi il minimo contesto osservabile utile ai log dei job schedulati, almeno per tenant o booking coinvolto nei punti di warning/errore principali
- non introdurre un sistema tracing nuovo
- mantieni il cambiamento piccolo e coerente con l'observability layer esistente

File probabili:

- backend/app/core/scheduler.py
- backend/app/core/observability.py
- eventuali test backend mirati se davvero necessari

## Regole di lavoro

- non fare refactor ampi
- non toccare frontend se non emerge una necessita reale da questi fix
- non cambiare contratti API se non strettamente necessario
- preferisci patch locali e test mirati
- non correggere problemi non emersi da questa verifica

## Test obbligatori

Devi aggiungere o aggiornare test che dimostrino almeno:

1. tenant hint invalidi diversi non bypassano il rate limit quando la request ricade sullo stesso tenant reale
2. tenant validi distinti restano isolati ai fini del rate limit
3. il healthcheck segnala correttamente un'istanza con scheduler richiesto ma non running
4. il tenant legacy default continua a funzionare

Poi esegui verifiche reali:

- test backend mirati sui file toccati
- suite backend completa se le patch toccano middleware o segnali operativi globali
- build frontend solo se tocchi il frontend, altrimenti dichiaralo esplicitamente non necessario

## Output obbligatorio

- file toccati
- bug corretti
- test aggiunti o aggiornati
- PASS/FAIL reale dei comandi eseguiti
- rischi residui, solo se restano davvero