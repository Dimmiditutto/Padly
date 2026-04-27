# PROMPT GO-LIVE - RILASCIO PRODUZIONE, ROLLOUT E GATE FINALE

Agisci come:
- Senior Prompt Engineer orientato all'esecuzione reale
- Senior Platform Engineer pragmatico
- Senior Full-Stack Engineer su FastAPI + React + TypeScript
- Senior QA tecnico rigoroso
- Release Manager orientato al `GO / NO-GO`

Il tuo compito non e inventare un go-live teorico. Devi portare il repository reale di PadelBooking a una decisione di rilascio concreta, documentata e difendibile, intervenendo sul codice o sulla documentazione solo dove emergono blocker reali di produzione.

## Prima di iniziare

Leggi obbligatoriamente:

- `RELEASE_CHECKLIST.md`
- `docs/operations/RUNBOOKS.md`
- `istanze.md`
- `README.md`
- `.env.example`
- `railway.json`
- `Dockerfile`
- `prompts SaaS/STATO_FASE_6.MD`
- `prompts SaaS/STATO_FASE_9.MD`
- `STATO_PLAY_7.md`

Se esiste gia, leggi anche:

- `STATO_PLAY_FINAL.md`

Per i punti tecnici piu sensibili verifica anche il codice reale, almeno dove il prompt o la documentazione possono essere stale:

- `backend/app/core/config.py`
- `backend/app/core/rate_limit.py`
- `backend/app/core/scheduler.py`
- `backend/app/api/routers/payments.py`
- `backend/app/api/routers/platform.py`
- `backend/app/services/booking_service.py`
- `backend/tests/test_hardening_ops.py`
- `backend/tests/test_multi_courts_backend.py`

## Obiettivo del prompt

Chiudere il percorso di go-live reale del prodotto, tenendo presente che il gap principale non e piu l'assenza di feature core ma:

- configurazione produzione reale
- rollout coerente
- allineamento provider e webhook
- topologia di deploy esplicita
- validazione automatica e smoke test reali
- documentazione e checklist go-live aggiornate al prodotto effettivo, incluso il perimetro `/play`

## Premesse non negoziabili

### 1. Gap principale reale

Non trattare il go-live come una fase di nuova feature delivery generale.

La priorita reale e:

- verificare env di produzione
- verificare secret e provider
- verificare deploy/runtime
- eseguire test e smoke reali
- riallineare checklist e runbook dove oggi sono incompleti rispetto al prodotto reale

### 2. Decisione topologica di default da usare

Salvo vincolo infrastrutturale concreto emerso dal deploy reale, la scelta piu efficiente e coerente con il repository attuale e con la logica di business e:

- `1` sola istanza backend applicativa
- `RATE_LIMIT_BACKEND=local`
- una sola istanza designata con `SCHEDULER_ENABLED=true`

Non attivare `RATE_LIMIT_BACKEND=shared` per principio.

Passa a `shared` solo se il deploy reale usa davvero piu istanze backend attive contemporaneamente e il backend condiviso dei contatori e gia operativo e verificato.

### 3. Rischio single-court da non trattare come blocker automatico

Il rischio documentato in `prompts SaaS/STATO_FASE_9.MD` sul presunto lock single-court globale non va considerato blocker automatico di go-live senza un audit reale.

Se il codice conferma ancora che il lock usa chiavi per `court_id` e i test multi-campo restano verdi, tratta quel punto come documentazione almeno in parte stale e riallinea report o checklist invece di aprire un refactor architetturale non richiesto.

### 4. Residuo tecnico da auditare davvero

Il residuo tecnico da tenere sotto osservazione prima del go-live pieno e piu stretto:

- eventuali superfici extra-booking che possano ancora interpretare datetime naive fuori dal perimetro gia verificato in Fase 9

Non trasformare pero questo audit in una caccia infinita.

Regola:

- concentrati sulle superfici attive di prodotto o operative che possono ancora ricevere input datetime naive in produzione
- se trovi un caso reale ambiguo nel perimetro di rilascio, correggilo e testalo
- se non trovi un caso attivo bloccante, documenta il rischio residuo e non bloccare il rilascio per ipotesi astratte

## Obiettivo operativo concreto

Portare il repository a una decisione finale `GO` o `NO-GO` con evidenza reale.

Per arrivarci devi chiudere davvero questi punti:

1. topologia di deploy scelta e motivata
2. env di produzione e provider checklist verificabili
3. healthcheck, scheduler, rate limit e control plane coerenti col deployment scelto
4. validazione automatica pre-rilascio eseguita davvero
5. smoke checklist manuale estesa anche ai flussi `/play` e discovery pubblica, oggi non coperti a sufficienza dalle checklist esistenti
6. eventuali blocker reali corretti o documentati con esito `NO-GO`

## Ordine di attacco obbligatorio

Esegui il lavoro in questo ordine, senza saltare avanti:

1. verifica documentazione e stato reale del repository
2. scegli e rendi esplicita la topologia di deploy iniziale
3. verifica env, provider, webhook e runtime
4. esegui validazione automatica pre-rilascio
5. estendi checklist e runbook dove oggi manca il perimetro `/play`
6. esegui smoke test manuali reali o documenta i blocker oggettivi che li impediscono
7. produci un report finale `GO / NO-GO`

## Verifiche operative obbligatorie

### A. Configurazione produzione

Verifica e tratta come gate reale:

- `APP_ENV=production`
- `APP_URL` reale e coerente con dominio Railway o custom domain
- `DATABASE_URL` PostgreSQL reale
- `SECRET_KEY` non placeholder
- `ADMIN_EMAIL` e `ADMIN_PASSWORD` non placeholder
- `SCHEDULER_ENABLED=true` su una sola istanza designata
- `PLATFORM_API_KEY` reale
- `STRIPE_BILLING_WEBHOOK_SECRET` reale dove richiesto dal layer SaaS
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
- `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID`

Se il prodotto finale `/play` richiede davvero web push server-side privato, verifica anche le chiavi VAPID di produzione e il comportamento fail-closed quando non sono configurate.

Regola di rilascio:

- non inventare mai valori di produzione
- se manca un env gate critico o resta un placeholder di sicurezza, l'esito deve essere `NO-GO`

### B. Topologia deploy e rate limit

Scelta di default da applicare salvo prova contraria:

- una sola istanza backend
- `RATE_LIMIT_BACKEND=local`
- nessuna replica aggiuntiva con scheduler attivo

Se il deploy reale richiede piu istanze:

- verifica che il backend `shared` del rate limit sia davvero pronto e usato
- se non lo e, non forzare il multi-instance: considera `NO-GO` o riduci il rollout a una sola istanza

### C. Health, runtime e control plane

Verifica davvero:

- `GET /api/health`
- `GET /`
- `GET /api/platform/ops/status` con `X-Platform-Key`
- coerenza tra `checks.rate_limit.backend` e topologia scelta
- stato scheduler coerente con l'istanza designata

### D. Provider, webhook e redirect

Verifica davvero:

- URL webhook Stripe allineato a `/api/payments/stripe/webhook`
- URL webhook PayPal allineato a `/api/payments/paypal/webhook`
- redirect success/cancel coerenti con `APP_URL`
- webhook billing SaaS coerenti se il layer billing e attivo in produzione

Se gli URL non sono riallineati al dominio reale, l'esito deve restare `NO-GO` finche il mismatch non viene chiuso.

## Validazione automatica obbligatoria

Esegui almeno:

- backend full suite: `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests -q -x --tb=short`
- frontend build: `npm run build`
- frontend test: `npm run test:run`
- test hardening/ops dedicati
- test multi-campo backend
- test mirati timezone/DST se emerge un fix nel perimetro datetime
- Docker build

Se la suite completa non e eseguibile per vincoli di ambiente, riduci solo quanto strettamente necessario e documenta esplicitamente il motivo nel report finale.

## Smoke checklist manuale obbligatoria

La checklist attuale copre il core booking/admin, ma per il go-live reale deve coprire anche il prodotto `/play`.

Devi quindi verificare e, se mancano, aggiornare `RELEASE_CHECKLIST.md` e `docs/operations/RUNBOOKS.md` per includere smoke espliciti anche su:

### Booking e admin core

- prenotazione pubblica felice con hold, checkout e conferma finale
- checkout annullato
- login admin e accesso dashboard
- creazione booking manuale admin
- cancellazione booking admin
- marcatura `COMPLETED`, `NO_SHOW` e saldo al campo
- `GET /api/admin/billing/status`

### Play privata `/c/:clubSlug/play`

- caricamento route canonical tenant-aware
- riconoscimento player o identify flow
- join di un match aperto
- create match con suggerimenti anti-frammentazione
- completamento 4/4 con comportamento coerente alla configurazione community:
  - default offline se caparra `OFF`
  - checkout immediato del pagatore finale se caparra `ON`

### Discovery pubblica

- `/clubs`
- `/clubs/nearby` con fallback se geolocalizzazione assente o negata
- `/c/:clubSlug`
- follow/unfollow watchlist
- contact request guidata
- conferma che la superficie pubblica non sblocchi join o funzioni community private

### Multi-tenant minimo

- smoke su tenant default
- smoke minimo su almeno un tenant secondario per `public config`, login admin, billing status e route pubbliche principali

## Audit datetime naive mirato

Esegui un audit mirato e breve, non una mappatura infinita.

Obiettivo:

- cercare superfici extra-booking fuori da `booking_service` e `admin_ops` che possano ancora interpretare datetime naive in modo ambiguo

Preferenza di attacco:

- router admin o public che accettano datetime input
- servizi operativi o scheduler che potrebbero leggere input locali ambigui
- superfici reali di prodotto o supporto, non codice morto o puramente interno senza input utente

Gate:

- se trovi un path attivo ambiguo nel perimetro go-live, correggilo e coprilo con test
- se non trovi casi attivi bloccanti, documenta il rischio residuo in modo sintetico e non bloccare il rilascio

## Correzioni ammesse durante il go-live

Sono ammesse solo correzioni piccole e direttamente legate al rilascio, ad esempio:

- allineamento checklist e runbook al prodotto reale
- fix minimi a health/runtime/env validation
- fix minimi a smoke blocker reali
- riallineamento di documentazione stale quando il codice e i test smentiscono il rischio documentato
- fix piccoli su datetime naive extra-booking se davvero emersi nel perimetro attivo

Non trasformare questo prompt in:

- rifondazione architetturale
- nuova fase prodotto
- redesign del rate limit o del booking engine senza fallimento reale
- progetto di observability enterprise

## Verifica finale obbligatoria

Il rilascio puo risultare `GO` solo se:

- la topologia di deploy e esplicita e coerente con `istanze.md`
- gli env gate critici sono reali e non placeholder
- i webhook e i redirect provider sono allineati al dominio reale
- health, scheduler e ops status sono coerenti col deploy scelto
- la validazione automatica essenziale e verde
- la smoke checklist manuale include anche `/play` e discovery pubblica
- eventuali rischi rimasti sono davvero residuali e non blocchi operativi immediati

Il rilascio deve risultare `NO-GO` se emerge anche solo uno di questi casi:

- secret critici mancanti o placeholder
- webhook non allineati
- deploy multi-instance senza rate limit condiviso realmente pronto quando necessario
- scheduler attivo su piu istanze senza coordinamento
- test essenziali falliti
- smoke core o `/play` bloccati da bug reali non risolti

## File stato da produrre obbligatoriamente

Crea `STATO_GO_LIVE.md` con almeno:

- esito finale `GO` / `NO-GO`
- topologia di deploy scelta e motivazione
- decisione finale su `RATE_LIMIT_BACKEND`
- env gate verificati, mancanti o ancora placeholder
- stato provider e webhook
- validazioni automatiche eseguite davvero con esito
- smoke manuali eseguiti davvero con esito, includendo `/play` e discovery pubblica
- esito dell'audit mirato su datetime naive extra-booking
- eventuali doc/checklist aggiornate
- blocker residui da chiudere prima del rilascio, se presenti
- `## Decisione finale`

Nella sezione `## Decisione finale` devi scrivere in modo esplicito e non ambiguo:

- `GO - si puo andare live`
oppure
- `NO-GO - non andare live`

## Fuori scope approvato

Questo prompt non deve assorbire:

- nuove feature di prodotto non strettamente necessarie al rilascio
- redesign del dominio multi-campo solo per il rischio documentale stale sul single-court
- introduzione prematura di infrastrutture extra solo per il rate limit se il deploy resta a 1 istanza
- progetto completo di metriche, dashboard o alerting esterno
- revisione estesa di tutte le timezone del progetto oltre il perimetro attivo realmente esposto al go-live

Questi temi possono restare backlog post go-live se non emergono blocker reali durante la verifica di rilascio.