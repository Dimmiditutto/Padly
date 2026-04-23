# VERIFICA FASE 9 — TIMEZONE TENANT-AWARE END-TO-END

## 1. Esito sintetico generale

`FAIL PARZIALE`

Il backend della FASE 9 e coerente: [backend/app/services/booking_service.py](backend/app/services/booking_service.py), [backend/app/api/routers/public.py](backend/app/api/routers/public.py), [backend/app/api/routers/admin_ops.py](backend/app/api/routers/admin_ops.py) e [backend/app/core/scheduler.py](backend/app/core/scheduler.py) sono allineati con l'obiettivo tenant-aware e i controlli statici non mostrano errori. Anche la validazione eseguibile resta verde: backend completo a 141 passed e, dal contesto terminale corrente, build frontend e test frontend verdi.

La review pero ha trovato una criticita reale di integrazione cross-layer: il frontend admin continua a usare conversioni e formatter Rome-only o browser-local, quindi la FASE 9 non e davvero end-to-end per tenant non `Europe/Rome`. In particolare il dettaglio prenotazione admin precompila e reinvia orari usando `toRomeTimeValue`, mentre la UI di reporting e detail usa formatter senza `club.timezone`. Questo puo produrre orari mostrati o reinviati sbagliati anche se il backend ora gestisce correttamente `club.timezone`.

## 2. Verifica per area

### Coerenza complessiva del codice

- Esito: `FAIL PARZIALE`
# VERIFICA FASE 9 — TIMEZONE TENANT-AWARE END-TO-END

## 1. Esito sintetico generale

`FAIL PARZIALE`

La parte backend della FASE 9 e coerente: i nuovi helper timezone-aware in [backend/app/services/booking_service.py](backend/app/services/booking_service.py), la propagazione del `club.timezone` da [backend/app/api/routers/public.py](backend/app/api/routers/public.py), [backend/app/api/routers/admin_bookings.py](backend/app/api/routers/admin_bookings.py) e [backend/app/api/routers/admin_ops.py](backend/app/api/routers/admin_ops.py), e la base scheduler neutra in [backend/app/core/scheduler.py](backend/app/core/scheduler.py) sono consistenti tra loro e la regressione backend completa resta verde con 141 passed.

La verifica rigorosa ha pero trovato una criticita reale che impedisce di considerare la fase davvero end-to-end: il frontend admin conserva ancora hardcode `Europe/Rome` e formatter browser-local che non rispettano `club.timezone`. In particolare il dettaglio prenotazione continua a derivare `start_time` da [frontend/src/pages/AdminBookingDetailPage.tsx](frontend/src/pages/AdminBookingDetailPage.tsx#L455), [frontend/src/pages/AdminBookingDetailPage.tsx](frontend/src/pages/AdminBookingDetailPage.tsx#L470) e [frontend/src/pages/AdminBookingDetailPage.tsx](frontend/src/pages/AdminBookingDetailPage.tsx#L504), mentre i formatter condivisi in [frontend/src/utils/format.ts](frontend/src/utils/format.ts#L19) e [frontend/src/utils/format.ts](frontend/src/utils/format.ts#L37) restano browser-local o Rome-only. Inoltre il path blackout admin resta solo parzialmente DST-safe: il form usa `datetime-local` in [frontend/src/pages/AdminDashboardPage.tsx](frontend/src/pages/AdminDashboardPage.tsx#L494) e [frontend/src/pages/AdminDashboardPage.tsx](frontend/src/pages/AdminDashboardPage.tsx#L498), ma il backend sceglie sempre la prima occorrenza ambigua per i naive datetime in [backend/app/api/routers/admin_ops.py](backend/app/api/routers/admin_ops.py), senza un meccanismo di disambiguazione per il secondo slot del fallback DST.

## 2. Verifica per area

### Coerenza complessiva del codice

- Esito: `FAIL PARZIALE`
- Problemi trovati:
  - backend e test backend sono coerenti tra loro sulla nuova logica tenant-aware
  - il frontend non e allineato al nuovo contratto implicito di fase: diversi path admin continuano a interpretare o mostrare orari fuori da `club.timezone`
  - il risultato e uno scollamento cross-layer tra source of truth backend e UI admin operativa
- Gravita: `alta`
- Impatto reale: il progetto resta stabile, ma la promessa di timezone tenant-aware end-to-end non e ancora vera nelle superfici admin piu sensibili

### Coerenza tra file modificati

- Esito: `FAIL PARZIALE`
- Problemi trovati:
  - i file backend toccati sono coerenti tra loro e non mostrano mismatch statici
  - la FASE 9 non ha toccato il frontend admin che rimane agganciato a Roma o al timezone del browser: [frontend/src/pages/AdminBookingDetailPage.tsx](frontend/src/pages/AdminBookingDetailPage.tsx#L455), [frontend/src/pages/AdminBookingDetailPage.tsx](frontend/src/pages/AdminBookingDetailPage.tsx#L470), [frontend/src/pages/AdminDashboardPage.tsx](frontend/src/pages/AdminDashboardPage.tsx#L422) e [frontend/src/utils/format.ts](frontend/src/utils/format.ts#L37)
  - il file di stato [prompts SaaS/STATO_FASE_9.MD](prompts%20SaaS/STATO_FASE_9.MD) dichiara end-to-end una superficie che nel frontend admin non e ancora chiusa
- Gravita: `alta`
- Impatto reale: la coerenza interna della patch backend non basta a chiudere la fase per tenant non Europe/Rome

### Conflitti o blocchi introdotti dai file modificati

- Esito: `FAIL PARZIALE`
- Problemi trovati:
  - l'edit form admin puo inviare `slot_id` corretto ma `start_time` convertito su Roma, generando mismatch verso il backend tenant-aware per tenant non Rome
  - il path blackout admin non consente di distinguere la seconda occorrenza del fallback DST quando il form usa `datetime-local`
  - build frontend e test backend risultano verdi, ma la copertura corrente non intercetta questi casi reali di produzione
- Gravita: `alta`
- Impatto reale: per tenant non Europe/Rome l'operatore admin puo vedere orari sbagliati o fallire l'aggiornamento di booking e serie ricorrenti gia esistenti

### Criticita del progetto nel suo insieme

- Esito: `PASS CON RISERVE`
- Problemi trovati:
  - non emergono blocchi architetturali nuovi nel progetto nel suo insieme
  - la fragilita e concentrata sulla chiusura cross-layer della FASE 9, non sul resto del backend SaaS gia consolidato
  - i test e i check eseguiti dimostrano solidita backend, ma non ancora completezza UI multi-timezone
- Gravita: `media`
- Impatto reale: il prodotto non e in regressione generale, ma la fase corrente non e ancora sicura per essere dichiarata completata end-to-end

### Rispetto della logica di business

- Esito: `FAIL PARZIALE`
- Problemi trovati:
  - la logica di business della fase richiede che admin, slot, recurring e blackout rispettino il timezone del tenant reale
  - oggi il backend rispetta questa regola, ma il frontend admin continua a usare `Europe/Rome` o il timezone del browser per comporre, mostrare o reinviare orari
  - il fallback DST sui blackout resta solo parzialmente gestito: la prima occorrenza viene scelta implicitamente senza possibilita di scegliere la seconda dal form standard
- Gravita: `alta`
- Impatto reale: il comportamento osservato dall'operatore non coincide sempre con il timezone del tenant dichiarato dal sistema

## 3. Elenco criticita

### 1. Frontend admin ancora Rome-only o browser-local nei flussi di edit timezone-sensitive

- Descrizione tecnica:
  - [frontend/src/pages/AdminBookingDetailPage.tsx](frontend/src/pages/AdminBookingDetailPage.tsx#L455) e [frontend/src/pages/AdminBookingDetailPage.tsx](frontend/src/pages/AdminBookingDetailPage.tsx#L470) precompilano `start_time` usando `toRomeTimeValue()`
  - [frontend/src/pages/AdminBookingDetailPage.tsx](frontend/src/pages/AdminBookingDetailPage.tsx#L504) converte sempre `start_at` con `timeZone: 'Europe/Rome'`
  - [frontend/src/utils/format.ts](frontend/src/utils/format.ts#L19) usa `toLocaleString()` senza timezone esplicita, quindi mostra orari nel timezone del browser e non del tenant
  - [frontend/src/utils/format.ts](frontend/src/utils/format.ts#L37) e [frontend/src/pages/AdminDashboardPage.tsx](frontend/src/pages/AdminDashboardPage.tsx#L422) mantengono formatter weekday Rome-only nelle superfici admin
- Perche e un problema reale:
  - per un tenant non Europe/Rome, una booking esistente salvata correttamente dal backend puo essere riaperta nel dettaglio admin con un `start_time` locale sbagliato
  - il form invia ancora `slot_id` con UTC corretto ma `start_time` convertito su Roma; il backend tenant-aware confronta entrambi e puo rispondere con `Slot selezionato non valido` o operare su un orario incoerente
  - la UI admin puo mostrare timestamp diversi da quelli del tenant se il browser dell'operatore usa un altro timezone
- Dove si manifesta:
  - [frontend/src/pages/AdminBookingDetailPage.tsx](frontend/src/pages/AdminBookingDetailPage.tsx#L455)
  - [frontend/src/pages/AdminBookingDetailPage.tsx](frontend/src/pages/AdminBookingDetailPage.tsx#L470)
  - [frontend/src/pages/AdminBookingDetailPage.tsx](frontend/src/pages/AdminBookingDetailPage.tsx#L504)
  - [frontend/src/utils/format.ts](frontend/src/utils/format.ts#L19)
  - [frontend/src/utils/format.ts](frontend/src/utils/format.ts#L37)
  - [frontend/src/pages/AdminDashboardPage.tsx](frontend/src/pages/AdminDashboardPage.tsx#L422)
- Gravita: `alta`
- Blocca il rilascio: `si`, per considerare la FASE 9 davvero end-to-end

### 2. I blackout admin non permettono di disambiguare la seconda occorrenza nel fallback DST

- Descrizione tecnica:
  - [frontend/src/pages/AdminDashboardPage.tsx](frontend/src/pages/AdminDashboardPage.tsx#L494) e [frontend/src/pages/AdminDashboardPage.tsx](frontend/src/pages/AdminDashboardPage.tsx#L498) usano input `datetime-local`, quindi inviano datetime naive
  - [backend/app/schemas/admin.py](backend/app/schemas/admin.py#L96) - [backend/app/schemas/admin.py](backend/app/schemas/admin.py#L100) accettano solo `start_at: str` e `end_at: str`, senza fold o `slot_id`
  - [backend/app/api/routers/admin_ops.py](backend/app/api/routers/admin_ops.py) costruisce i candidati timezone-aware ma in caso ambiguo sceglie sempre `candidates[0]`
- Perche e un problema reale:
  - durante il cambio ora autunnale l'admin non puo esprimere dal form standard il secondo intervallo omonimo della repeated hour
  - il blackout viene quindi interpretato in modo implicito sulla prima occorrenza, lasciando scoperto un edge case che la fase dichiarava sensibile
- Dove si manifesta:
  - [frontend/src/pages/AdminDashboardPage.tsx](frontend/src/pages/AdminDashboardPage.tsx#L494)
  - [frontend/src/pages/AdminDashboardPage.tsx](frontend/src/pages/AdminDashboardPage.tsx#L498)
  - [backend/app/schemas/admin.py](backend/app/schemas/admin.py#L96)
  - [backend/app/schemas/admin.py](backend/app/schemas/admin.py#L99)
  - [backend/app/schemas/admin.py](backend/app/schemas/admin.py#L100)
  - [backend/app/api/routers/admin_ops.py](backend/app/api/routers/admin_ops.py)
- Gravita: `media`
- Blocca il rilascio: `no`, ma lascia aperto un edge case DST reale nella superficie admin

### 3. La copertura frontend non protegge i casi tenant-timezone e consolida ancora assunzioni Rome-only

- Descrizione tecnica:
  - [frontend/src/pages/AdminBookingDetailPage.test.tsx](frontend/src/pages/AdminBookingDetailPage.test.tsx#L233) e [frontend/src/pages/AdminBookingDetailPage.test.tsx](frontend/src/pages/AdminBookingDetailPage.test.tsx#L250) si aspettano ancora `start_time: '18:00'` su casi modellati per Roma
  - non emerge alcun test frontend che verifichi l'editing di una booking o di una serie ricorrente per tenant non Europe/Rome usando il timezone del tenant reale
  - il verde di build e test frontend non intercetta quindi il mismatch cross-layer della fase
- Perche e un problema reale:
  - la regressione e passata nonostante i controlli automatici disponibili
  - senza test tenant-timezone lato UI, il bug puo riapparire anche dopo un fix backend corretto
- Dove si manifesta:
  - [frontend/src/pages/AdminBookingDetailPage.test.tsx](frontend/src/pages/AdminBookingDetailPage.test.tsx#L233)
  - [frontend/src/pages/AdminBookingDetailPage.test.tsx](frontend/src/pages/AdminBookingDetailPage.test.tsx#L250)
- Gravita: `media`
- Blocca il rilascio: `no`, ma rende fragile la correzione della criticita principale

## 4. Prioritizzazione finale

### Da correggere prima del rilascio

- rimuovere gli hardcode Rome-only e browser-local dai flussi admin che leggono, mostrano o reinviano `start_at` e date operative del tenant
- riallineare il frontend admin al timezone del tenant reale quando costruisce i payload di update booking e recurring

### Da correggere prima della beta pubblica

- decidere una gestione esplicita del fallback DST per i blackout admin: disambiguazione della seconda occorrenza oppure rifiuto esplicito dei naive datetime ambigui
- aggiungere test frontend tenant-timezone sui path admin modificati

### Miglioramenti differibili

- uniformare i formatter UI riusabili per accettare il timezone del tenant in modo esplicito, evitando futuri re-hardcode `Europe/Rome`

## 5. Verdetto finale

Il backend della FASE 9 e quasi pronto, ma il codice non e ancora sicuro per dichiarare completata la fase timezone tenant-aware end-to-end. Servono fix mirati nel frontend admin e un chiarimento minimo sul blackout DST ambiguo.

## 6. Prompt operativo per i fix

Agisci come un Senior Software Engineer, Senior Code Reviewer e QA tecnico.

Leggi prima:

- [prompts SaaS/prompt_master.md](prompts%20SaaS/prompt_master.md)
- [prompts SaaS/STATO_FASE_9.MD](prompts%20SaaS/STATO_FASE_9.MD)
- [frontend/src/pages/AdminBookingDetailPage.tsx](frontend/src/pages/AdminBookingDetailPage.tsx)
- [frontend/src/pages/AdminDashboardPage.tsx](frontend/src/pages/AdminDashboardPage.tsx)
- [frontend/src/utils/format.ts](frontend/src/utils/format.ts)
- [frontend/src/pages/AdminBookingDetailPage.test.tsx](frontend/src/pages/AdminBookingDetailPage.test.tsx)
- [backend/app/api/routers/admin_ops.py](backend/app/api/routers/admin_ops.py)
- [backend/app/schemas/admin.py](backend/app/schemas/admin.py)

## Contesto reale gia verificato

- backend FASE 9 coerente e suite backend completa verde con 141 passed
- i test DST backend sono verdi
- frontend build e test eseguiti in workspace risultano verdi, ma non coprono ancora i casi tenant-timezone che hanno fatto emergere il bug
- non devi fare refactor ampi: devi correggere solo le criticita reali emerse sotto

## Obiettivo

Chiudere davvero la FASE 9 lato frontend/admin e sui blackout DST, con patch minime e coerenti con il codice attuale.

### 1. Rimuovere gli hardcode Rome-only e browser-local dai flussi admin timezone-sensitive

Problema confermato:

- [frontend/src/pages/AdminBookingDetailPage.tsx](frontend/src/pages/AdminBookingDetailPage.tsx#L455), [frontend/src/pages/AdminBookingDetailPage.tsx](frontend/src/pages/AdminBookingDetailPage.tsx#L470) e [frontend/src/pages/AdminBookingDetailPage.tsx](frontend/src/pages/AdminBookingDetailPage.tsx#L504) usano ancora `toRomeTimeValue`
- [frontend/src/utils/format.ts](frontend/src/utils/format.ts#L19) formatta timestamp in timezone browser-local
- [frontend/src/utils/format.ts](frontend/src/utils/format.ts#L37) e [frontend/src/pages/AdminDashboardPage.tsx](frontend/src/pages/AdminDashboardPage.tsx#L422) mantengono formatter Rome-only

Correzione richiesta:

- usa il timezone del tenant reale nelle superfici admin che mostrano o ricostruiscono orari da `start_at`
- il dettaglio booking e la form recurring non devono piu precompilare `start_time` assumendo `Europe/Rome`
- evita refactor estesi: preferisci helper di formatting/localizzazione riusabili e mirati
- se il dettaglio admin non ha gia accesso al timezone del tenant, scegli la patch minima coerente tra:
  - riusare un payload gia disponibile lato admin settings
  - oppure estendere in modo minimo il contratto letto dal dettaglio se davvero necessario

### 2. Gestire esplicitamente il caso DST ambiguo dei blackout admin

Problema confermato:

- il form blackout usa `datetime-local`
- lo schema backend accetta solo stringhe naive o offset-aware senza una strategia esplicita di disambiguazione
- il parser seleziona implicitamente la prima occorrenza nel fallback DST

Correzione richiesta:

- applica la patch minima ma esplicita
- scegli una sola strategia coerente:
  1. supportare una disambiguazione minima del secondo slot ambiguo
  2. oppure rifiutare in modo esplicito e comprensibile i datetime naive ambigui nel fallback DST
- non introdurre nuovi workflow ampi o refactor di tutte le form admin

### 3. Aggiungere solo i test realmente necessari

Test richiesti:

1. un test frontend che verifichi l'edit di una booking per tenant non Europe/Rome e dimostri che `start_time` deriva dal timezone del tenant, non da Roma
2. un test frontend equivalente per update recurring o build della relativa form
3. un test sul comportamento scelto per blackout DST ambiguo
4. aggiornare i test che oggi consolidano implicitamente l'assunzione Rome-only solo dove necessario

## Regole di lavoro

- preferisci patch minime e locali
- non toccare il backend timezone-aware gia corretto se non serve davvero per esporre il timezone minimo richiesto al frontend
- non fare refactor generici del frontend
- non modificare superfici fuori dal perimetro booking/admin/DST emerso qui

## Verifiche reali richieste

- `Set-Location 'D:/Padly/PadelBooking/frontend'`
- `npm run build`
- `npm run test:run`
- se tocchi un contratto backend o il parser blackout, esegui anche `Set-Location 'D:/Padly/PadelBooking/backend'; D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests -q -x --tb=short`

## Output obbligatorio

- file toccati
- bug corretti
- test aggiunti o aggiornati
- PASS/FAIL reale dei comandi eseguiti
- eventuali limiti residui reali, solo se restano davvero

## Correzioni richieste

1. sostituire `toRomeTimeValue` e gli altri formatter Rome-only nelle superfici admin operative con utility tenant-aware basate sulla timezone del tenant corrente
2. assicurare che `AdminBookingDetailPage` e i form ricorrenti precompilino `start_time` nella timezone del tenant reale, in coerenza con `slot_id`
3. evitare che i formatter generici mostrino i timestamp booking/admin nel fuso del browser quando il requisito e usare `club.timezone`
4. valutare una patch minima anche per il blackout admin: o supporto esplicito alla disambiguazione del fallback DST, oppure gestione UX chiara che impedisca assunzioni sbagliate
5. non toccare route o contratti backend se non emerge una necessita diretta dal fix frontend

## Regole di lavoro

- non fare refactor ampi
- non toccare booking engine backend, scheduler o persistenza UTC
- preferisci una utility frontend condivisa tenant-aware al posto di nuove conversioni locali sparse
- non correggere problemi non emersi da questa review

## Test obbligatori

Aggiungi o aggiorna test che dimostrino almeno:

1. un tenant non `Europe/Rome` vede in `AdminBookingDetailPage` l'orario precompilato coerente con la propria timezone
2. il salvataggio di edit booking o recurring riusa `slot_id` coerentemente senza mismatch con `start_time`
3. le label giorno usate dalla dashboard admin non dipendono piu da `Europe/Rome`
4. i test DST gia esistenti restano verdi

Poi esegui verifiche reali:

- `npm run test:run -- AdminBookingDetailPage.test.tsx AdminDashboardPage.test.tsx`
- `npm run build`
- rilancia il backend solo se un fix frontend rende necessario adeguare un contratto, cosa che oggi non emerge dalla review

## Output obbligatorio

- file toccati
- bug corretti
- test aggiunti o aggiornati
- PASS/FAIL reale dei comandi eseguiti
- rischi residui reali, solo se restano davvero