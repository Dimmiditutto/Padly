# VERIFICA PLAY FASE 2

## 1. Esito sintetico generale

`PASS CON RISERVE`

La superficie `/play` e coerente nei percorsi canonici e non rompe i flussi esistenti di booking pubblico o area admin. Le validazioni eseguite sono verdi:

- frontend: `npx vitest run src/pages/PlayPage.test.tsx` -> `6 passed`
- frontend: `npm run build` -> `PASS`
- backend: `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_play_phase1.py tests/test_play_phase1_migration.py -q --tb=short --maxfail=5` -> `6 passed`

La review rigorosa ha pero trovato due criticita logiche reali e una criticita minore di hygiene/testing:

- le route alias pubbliche `/play/invite/:token` e `/play/matches/:shareToken` fanno fallback silenzioso su `default-club`, quindi un link valido di un altro tenant puo essere instradato sul club sbagliato e fallire anche se il token o la partita sono corretti
- la shared page continua a usare `match.id` come `shareToken`, mentre il backend e il modello dati dichiarano un concetto diverso tramite `public_share_token_hash`; la feature oggi funziona, ma il contratto pubblico non e realmente chiuso
- nel worktree e presente il file generato `frontend/playpage-vitest.json`, e i test coprono l alias `/play` ma non proteggono gli alias invite/share che oggi sono proprio la parte piu fragile

## 2. Verifica per area

### Coerenza complessiva del codice

- Esito: `PASS CON RISERVE`
- Problemi trovati:
  - i percorsi canonici `/c/:clubSlug/play`, `/c/:clubSlug/play/invite/:token` e `/c/:clubSlug/play/matches/:shareToken` sono coerenti con la propagazione tenant attuale
  - il frontend usa i contratti backend reali di Fase 1 senza rompere il booking pubblico su `/`
  - resta pero una incoerenza di prodotto sulle route alias pubbliche e sul significato reale di `shareToken`
- Gravita: `media`
- Impatto reale: l esperienza canonica e stabile, ma la superficie pubblica alias/share non e ancora sufficientemente robusta per essere considerata chiusa senza riserve

### Coerenza tra file modificati

- Esito: `PASS CON RISERVE`
- Problemi trovati:
  - [frontend/src/App.tsx](frontend/src/App.tsx#L18) - [frontend/src/App.tsx](frontend/src/App.tsx#L42) introduce alias `/play/*` coerenti con il routing canonico solo quando il tenant e gia noto
  - [frontend/src/services/playApi.ts](frontend/src/services/playApi.ts#L41) - [frontend/src/services/playApi.ts](frontend/src/services/playApi.ts#L42) tratta `shareToken` come semplice `matchId`
  - [backend/app/models/__init__.py](backend/app/models/__init__.py#L245) continua invece a dichiarare `public_share_token_hash`, quindi nome del contratto e implementazione effettiva non coincidono
- Gravita: `media`
- Impatto reale: il codice compila e i test passano, ma rimane uno scollamento tra naming pubblico, modello dati e comportamento reale del link condiviso

### Conflitti o blocchi introdotti dai file modificati

- Esito: `PASS CON RISERVE`
- Problemi trovati:
  - [frontend/src/App.tsx](frontend/src/App.tsx#L20) forza `DEFAULT_PLAY_ALIAS_SLUG` quando il tenant non e ricavabile dalla location
  - [backend/app/api/deps.py](backend/app/api/deps.py#L15) - [backend/app/api/deps.py](backend/app/api/deps.py#L19) e [backend/app/api/routers/public_play.py](backend/app/api/routers/public_play.py) fanno scoping forte sul tenant corrente, quindi un alias mal risolto trasforma un link valido in `not found` o `link non valido`
  - i test attuali non coprono questo caso: [frontend/src/pages/PlayPage.test.tsx](frontend/src/pages/PlayPage.test.tsx#L148) verifica solo l alias `/play?tenant=roma-club`
- Gravita: `media`
- Impatto reale: non ci sono blocchi di build o runtime generalizzati, ma i link alias invite/share possono rompersi per tenant non default

### Criticita del progetto nel suo insieme

- Esito: `PASS CON RISERVE`
- Problemi trovati:
  - non emergono regressioni sul dominio booking esistente
  - non emergono mismatch statici nei file toccati backend/frontend
  - resta un debito architetturale circoscritto al public sharing del modulo `/play`
  - nel worktree e presente il file generato [frontend/playpage-vitest.json](frontend/playpage-vitest.json), che non aggiunge valore di prodotto e puo sporcare il commit
- Gravita: `bassa`
- Impatto reale: il progetto resta stabile, ma il repository non e ancora pulito e la superficie share non e definitiva

### Rispetto della logica di business

- Esito: `PASS CON RISERVE`
- Problemi trovati:
  - la logica principale di fase e rispettata: bacheca open match, identificazione player, invite accept, tenant propagation e shared page canonica funzionano
  - la promessa implicita di un `shareToken` pubblico separato dall identificativo interno del match non e ancora rispettata davvero
  - gli alias opzionali non rispettano il vincolo di sicurezza del prompt di fase quando il tenant non e determinabile in modo affidabile
- Gravita: `media`
- Impatto reale: la business logic centrale e pronta, ma il sottoflusso pubblico alias/share richiede ancora una chiusura coerente prima di essere considerato finito

## 3. Elenco criticita

### 1. Alias invite/share instradati sul tenant di default anche quando il tenant reale non e noto

- Descrizione tecnica:
  - [frontend/src/App.tsx](frontend/src/App.tsx#L18) - [frontend/src/App.tsx](frontend/src/App.tsx#L20) usa `resolveTenantSlugFromLocation(location) || DEFAULT_PLAY_ALIAS_SLUG`
  - [frontend/src/App.tsx](frontend/src/App.tsx#L25) - [frontend/src/App.tsx](frontend/src/App.tsx#L33) applica questa logica anche a `/play/invite/:token` e `/play/matches/:shareToken`
  - backend e router play sono tenant-scoped, quindi il fallback su `default-club` puo rendere invalido un link di un altro club
- Perche e un problema reale:
  - il problema non rompe i percorsi canonici, ma rompe proprio gli alias pubblici opzionali se usati fuori dal tenant default
  - un utente puo ricevere un link alias valido e vedere un errore non per token errato, ma per tenant sbagliato
- Dove si manifesta:
  - [frontend/src/App.tsx](frontend/src/App.tsx#L18)
  - [frontend/src/App.tsx](frontend/src/App.tsx#L25)
  - [frontend/src/App.tsx](frontend/src/App.tsx#L31)
  - [backend/app/api/deps.py](backend/app/api/deps.py#L15)
  - [backend/app/api/routers/public_play.py](backend/app/api/routers/public_play.py)
- Gravita: `media`
- Blocca il rilascio: `no`, ma va corretto prima di dichiarare affidabili gli alias pubblici

### 2. Il contratto `shareToken` non coincide con il comportamento reale della shared page

- Descrizione tecnica:
  - [frontend/src/services/playApi.ts](frontend/src/services/playApi.ts#L41) - [frontend/src/services/playApi.ts](frontend/src/services/playApi.ts#L42) inoltra `shareToken` a `getPlayMatchDetail(matchId)`
  - [frontend/src/pages/PlayPage.tsx](frontend/src/pages/PlayPage.tsx#L126) e [frontend/src/pages/SharedMatchPage.tsx](frontend/src/pages/SharedMatchPage.tsx#L69) costruiscono link condivisi usando `match.id`
  - [backend/app/api/routers/play.py](backend/app/api/routers/play.py#L74) espone solo `/play/matches/{match_id}`
  - [backend/app/models/__init__.py](backend/app/models/__init__.py#L245) conserva invece `public_share_token_hash`, che oggi non viene usato dal frontend ne dal read endpoint condiviso
- Perche e un problema reale:
  - il codice oggi funziona solo perche tratta l identificativo interno del match come se fosse il token pubblico di condivisione
  - il naming pubblico e fuorviante e la strategia dati non e coerente con il comportamento esposto agli utenti
  - questa ambiguita rende piu costosa la fase successiva, perche il repo dichiara gia un concetto di share token ma non lo usa davvero end-to-end
- Dove si manifesta:
  - [frontend/src/services/playApi.ts](frontend/src/services/playApi.ts#L41)
  - [frontend/src/pages/PlayPage.tsx](frontend/src/pages/PlayPage.tsx#L126)
  - [frontend/src/pages/PlayPage.tsx](frontend/src/pages/PlayPage.tsx#L141)
  - [frontend/src/pages/SharedMatchPage.tsx](frontend/src/pages/SharedMatchPage.tsx#L40)
  - [frontend/src/pages/SharedMatchPage.tsx](frontend/src/pages/SharedMatchPage.tsx#L69)
  - [backend/app/api/routers/play.py](backend/app/api/routers/play.py#L74)
  - [backend/app/models/__init__.py](backend/app/models/__init__.py#L245)
- Gravita: `media`
- Blocca il rilascio: `no`, ma va corretto prima di chiamare completa la condivisione pubblica del match

### 3. Artifact di test generato nel repo e copertura insufficiente sugli alias fragili

- Descrizione tecnica:
  - il file [frontend/playpage-vitest.json](frontend/playpage-vitest.json) e un artifact generato da una run intermedia fallita
  - [frontend/src/pages/PlayPage.test.tsx](frontend/src/pages/PlayPage.test.tsx#L148) copre l alias `/play`, ma non copre `/play/invite/:token` e `/play/matches/:shareToken`
- Perche e un problema reale:
  - l artifact non e parte del prodotto e puo confondere revisioni o commit futuri
  - l assenza di test sugli alias fragili lascia scoperto proprio il comportamento che oggi ha la maggiore probabilita di regressione logica
- Dove si manifesta:
  - [frontend/playpage-vitest.json](frontend/playpage-vitest.json)
  - [frontend/src/pages/PlayPage.test.tsx](frontend/src/pages/PlayPage.test.tsx#L148)
- Gravita: `bassa`
- Blocca il rilascio: `no`

## 4. Prioritizzazione finale

### Da correggere prima del rilascio

- rendere sicuri o rimuovere gli alias `/play/invite/:token` e `/play/matches/:shareToken` quando il tenant non e determinabile senza ambiguita

### Da correggere prima della beta pubblica

- allineare in modo esplicito il contratto `shareToken` con il comportamento reale della shared page
- aggiungere test mirati per alias invite/share e per il comportamento del link condiviso

### Miglioramenti differibili

- rimuovere dal repo gli artifact di validazione generati e mantenere solo output riproducibili via comando

## 5. Verdetto finale

Il codice e quasi pronto ma richiede fix mirati prima di considerare chiusa senza riserve la superficie pubblica `/play`. I percorsi canonici sono stabili e validati; gli aggiustamenti necessari sono confinati al sottoflusso alias/share e alla pulizia del worktree.

## 6. Prompt operativo per i fix

Agisci come un Senior Software Engineer, Senior Code Reviewer e QA tecnico.

Leggi prima:

- [play_master.md](play_master.md)
- [STATO_PLAY_1.md](STATO_PLAY_1.md)
- [STATO_PLAY_2.md](STATO_PLAY_2.md)
- [frontend/src/App.tsx](frontend/src/App.tsx)
- [frontend/src/services/playApi.ts](frontend/src/services/playApi.ts)
- [frontend/src/pages/PlayPage.tsx](frontend/src/pages/PlayPage.tsx)
- [frontend/src/pages/SharedMatchPage.tsx](frontend/src/pages/SharedMatchPage.tsx)
- [frontend/src/pages/InviteAcceptPage.tsx](frontend/src/pages/InviteAcceptPage.tsx)
- [frontend/src/pages/PlayPage.test.tsx](frontend/src/pages/PlayPage.test.tsx)
- [backend/app/api/routers/play.py](backend/app/api/routers/play.py)
- [backend/app/api/routers/public_play.py](backend/app/api/routers/public_play.py)
- [backend/app/services/play_service.py](backend/app/services/play_service.py)
- [backend/app/models/__init__.py](backend/app/models/__init__.py)

## Contesto reale gia verificato

- i percorsi canonici `/c/:clubSlug/play`, `/c/:clubSlug/play/invite/:token` e `/c/:clubSlug/play/matches/:shareToken` funzionano
- `npx vitest run src/pages/PlayPage.test.tsx` e verde con `6 passed`
- `npm run build` e verde
- i test backend play `tests/test_play_phase1.py` e `tests/test_play_phase1_migration.py` sono verdi con `6 passed`
- non devi fare refactor ampi e non devi toccare il booking pubblico su `/` o l area admin fuori da cio che emerge qui

## Obiettivo

Correggere solo le criticita reali emerse nella review della Fase 2 `/play`, con patch minime e coerenti con il codice attuale.

### 1. Chiudere in modo sicuro gli alias pubblici invite/share

Problema confermato:

- oggi `/play/invite/:token` e `/play/matches/:shareToken` fanno fallback silenzioso su `default-club` quando il tenant non e ricavabile dalla location
- questo comportamento non e sicuro per link appartenenti a tenant diversi dal default

Correzione richiesta:

- applica la patch minima ma esplicita
- non lasciare piu che gli alias invite/share instradino un link su `default-club` se il tenant reale non e noto con affidabilita
- scegli una sola strategia coerente:
  1. rimuovere gli alias invite/share e mantenere solo i percorsi canonici tenant-aware
  2. oppure farli fallire in modo esplicito e comprensibile, senza redirect al tenant sbagliato
- l alias `/play` semplice puo restare solo se continua a essere coerente con il tenant noto o con il default realmente supportato

### 2. Allineare il contratto pubblico del shared match

Problema confermato:

- il frontend chiama `shareToken` un valore che oggi e solo `match.id`
- il backend e il modello dati dichiarano gia `public_share_token_hash`, ma il percorso condiviso legge ancora `/play/matches/{match_id}`

Correzione richiesta:

- rendi esplicito e coerente il contratto, con la patch minima sostenibile
- non introdurre un refactor ampio del modulo play
- scegli una sola direzione coerente e portala end-to-end:
  1. se vuoi mantenere davvero il concetto di `shareToken`, aggiungi il supporto backend minimo necessario per esporre e consumare un identificatore pubblico reale di condivisione
  2. se un vero token pubblico non e ancora economicamente implementabile in questa fase, smetti di trattare `match.id` come `shareToken` implicito e riallinea naming, test e documentazione al comportamento reale
- evita soluzioni ibride che lascino ancora mismatch tra nome del contratto, route, API e modello dati

### 3. Pulire gli artifact e chiudere la copertura test minima necessaria

Problema confermato:

- e presente il file generato `frontend/playpage-vitest.json`
- i test coprono l alias `/play`, ma non i casi fragili su invite/share

Correzione richiesta:

- rimuovi gli artifact temporanei non necessari dal repo
- aggiungi solo i test davvero necessari per proteggere i fix sopra
- non espandere la suite oltre il perimetro dei bug emersi

## Test richiesti

1. un test che dimostri il comportamento corretto scelto per `/play/invite/:token` quando il tenant non e determinabile
2. un test equivalente per `/play/matches/:shareToken`
3. un test che dimostri il contratto finale scelto per il link condiviso del match
4. mantieni verdi i test gia presenti su `/c/:clubSlug/play`

## Regole di lavoro

- patch minime e locali
- non fare refactor ampi
- non toccare booking engine, admin area o flussi pagamento se non serve davvero
- non introdurre nuove feature fuori dai fix richiesti
- se scegli di rimuovere gli alias fragili, fallo in modo pulito e aggiorna solo i test e la documentazione strettamente toccati

## Verifiche reali richieste

- `Set-Location 'D:/Padly/PadelBooking/frontend'`
- `npx vitest run src/pages/PlayPage.test.tsx`
- `npm run build`
- se tocchi i contratti backend play o il modello dati match, esegui anche `Set-Location 'D:/Padly/PadelBooking/backend'; D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_play_phase1.py tests/test_play_phase1_migration.py -q --tb=short --maxfail=5`

## Output obbligatorio

- file toccati
- bug corretti
- test aggiunti o aggiornati
- PASS/FAIL reale dei comandi eseguiti
- eventuali limiti residui reali, solo se restano davvero
