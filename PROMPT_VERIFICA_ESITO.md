# VERIFICA PLAY SHARE WHATSAPP + CERCA GIOCATORI

## 1. Esito sintetico generale

PASS CON RISERVE

Il perimetro Play appena introdotto e tecnicamente coerente, integrato correttamente tra backend, frontend, API, test e migrazioni locali, e non mostra blocker immediati di build o runtime nel perimetro verificato. La feature implementa davvero i due binari richiesti, cioe:

- `Condividi` con share sheet riusabile e fallback WhatsApp `wa.me`
- `Cerca giocatori` come trigger manuale del motore notifiche gia esistente
- shared page pubblica sobria per i non partecipanti
- superficie admin minima per condividere gli stessi link attivi del club

Evidenze reali raccolte durante la verifica:

- backend tests `tests/test_play_phase3.py tests/test_play_phase4.py` -> PASS, 35 test passati
- frontend tests `src/pages/PlayPage.test.tsx src/pages/SharedMatchPage.test.tsx src/pages/AdminDashboardPage.test.tsx` -> PASS, 57 test passati
- frontend build `npm run build` -> PASS
- migrazione Alembic locale su SQLite temporaneo con `upgrade head` e `downgrade -1` -> PASS
- controlli statici editor/language service sui file toccati -> nessun errore rilevato

Non emergono conflitti strutturali o regressioni manifeste nel codice verificato. Restano pero alcune riserve reali che impediscono un sign-off pieno della feature cosi come richiesta dal prompt notifiche:

1. copertura incompleta di alcuni casi obbligatori e negativi richiesti dal prompt
2. downgrade PostgreSQL della nuova migrazione enum non realmente reversibile
3. semantica non perfettamente allineata del campo `notifications_created` tra service layer e response del trigger manuale

## 2. Verifica per area

### Coerenza complessiva del codice

Esito: PASS CON RISERVE

Punti verificati:

- backend, frontend e contratti dati sono allineati sul nuovo flusso share/search
- `share_token` resta opaco e non viene sostituito da una seconda source of truth
- la shared page continua a usare la route e il backend gia esistenti, senza duplicazioni architetturali inutili
- il trigger manuale riusa davvero `dispatch_play_notifications_for_match` invece di introdurre un secondo motore di matching
- il frontend usa tipi e client API coerenti con i nuovi endpoint

Problemi trovati:

- la migrazione `20260505_0017_play_search_players_event.py` e forward-safe ma non ripristina davvero lo stato schema su PostgreSQL in downgrade
- il nome `notifications_created` non ha la stessa semantica nei due livelli della feature: nel dispatcher conta log/canali, nella response UI del trigger conta player unici avvisati

Gravita:

- migrazione downgrade: media
- naming del contatore: bassa

Impatto reale:

- il codice applicativo funziona nel percorso verificato, ma il rollback schema su PostgreSQL non e pulito e il contratto del contatore puo creare fraintendimenti futuri in test, analytics o integrazioni successive

### Coerenza tra file modificati

Esito: PASS

Punti verificati:

- `backend/app/services/play_service.py`, `backend/app/api/routers/play.py` e `backend/app/schemas/play.py` sono coerenti tra route, service e response model del trigger `search-players`
- `backend/app/api/routers/admin_settings.py` e `frontend/src/services/adminApi.ts` sono coerenti sulla lista admin dei link Play condivisibili
- `frontend/src/utils/play.ts`, `frontend/src/components/play/PlayShareDialog.tsx`, `frontend/src/pages/PlayPage.tsx`, `frontend/src/pages/SharedMatchPage.tsx` e `frontend/src/pages/AdminDashboardPage.tsx` condividono lo stesso contratto di share URL e testo WhatsApp
- `frontend/src/components/play/MatchCard.tsx` si adatta correttamente al payload pubblico piu sobrio senza rompere le card private

Problemi trovati:

- nessun conflitto di import/export, typing o wiring rilevato nei file modificati

Gravita:

- nessuna criticita strutturale aperta

Impatto reale:

- il pacchetto di file toccati e coerente e non mostra mismatch evidenti tra frontend, backend e contratti dati

### Conflitti o blocchi introdotti dai file modificati

Esito: PASS CON RISERVE

Punti verificati:

- non sono emersi errori statici sui file toccati
- build frontend e test mirati passano
- la shared page non mostra piu creator, nota e partecipanti ai non partecipanti
- il match `FULL` resta leggibile ma non joinabile
- il trigger `search-players` applica cooldown e creator-only guard nel service layer

Problemi trovati:

- mancano alcune regressioni mirate che il prompt notifiche richiedeva esplicitamente e che oggi restano garantite piu dalla lettura del codice che da test blindati
- in particolare non risultano blindati da test dedicati tutti questi casi:
  - link shared non disponibile dopo `cancel` del match
  - `search-players` lanciato da utente non autorizzato
  - share da partecipante non creator nel perimetro privato
  - fallback `Copia link` su Play/shared/admin
  - feedback frontend `Cerca giocatori` nei casi `zero candidati` e `cooldown`

Gravita:

- media

Impatto reale:

- non c e un bug manifesto gia riprodotto, ma ci sono invarianti business rilevanti non ancora protetti da regressioni automatiche

### Criticita del progetto nel suo insieme

Esito: PASS CON RISERVE

Punti verificati:

- il perimetro nuovo non rompe i flussi Play gia chiusi che sono stati ritestati
- non emergono conflitti con pagamenti, OTP, discovery pubblico o share token lifecycle preesistente
- la nuova superficie admin resta locale all area settings e non introduce una seconda area di gestione Play

Problemi trovati:

- la migrazione enum e validata localmente su SQLite, ma il vero caveat resta operativo su PostgreSQL rollback
- il prompt notifiche e stato implementato quasi integralmente, ma la sua checklist testuale non e ancora soddisfatta al 100% lato regressioni automatiche

Gravita:

- media

Impatto reale:

- il progetto non mostra fragilita architetturali nuove nel perimetro verificato, ma il livello di hardening non e ancora completo quanto richiesto dal prompt originale

### Rispetto della logica di business

Esito: PASS CON RISERVE

Punti verificati:

- il link pubblico resta opaco e riusa il `share_token` esistente
- creator, partecipanti e club riusano lo stesso link pubblico attivo del match
- la pagina pubblica del match e ora piu sobria e privacy-safe per i non partecipanti
- `Cerca giocatori` resta separato da `Condividi`
- `Cerca giocatori` non usa WhatsApp e non introduce un motore notifiche parallelo
- il cooldown a 15 minuti e presente e tracciato via `PlayerActivityEvent`

Problemi trovati:

- il comportamento business desiderato risulta implementato, ma non tutti i casi richiesti dal prompt sono coperti da test specifici e questo abbassa il livello di affidabilita del rilascio

Gravita:

- media

Impatto reale:

- il codice rispetta il funnel richiesto, ma il sign-off finale resta incompleto finche le regressioni mancanti non vengono aggiunte o la loro esclusione non viene accettata esplicitamente

## 3. Elenco criticita

### 1. Copertura insufficiente sui casi obbligatori del prompt notifiche

Descrizione tecnica:

- il nuovo perimetro ha buone regressioni di base, ma mancano test espliciti su alcune condizioni richieste dal prompt originale
- backend: manca una regressione che verifichi che il link shared diventa non disponibile dopo `cancel` del match e una regressione che verifichi il `403` su `POST /api/play/matches/{match_id}/search-players` per utente non creator/non gestore
- frontend: manca una regressione esplicita sul fallback `Copia link`, sui messaggi `zero candidati` e `cooldown` di `Cerca giocatori`, e sulla disponibilita di share per un partecipante gia dentro il match ma non creator

Perche e un problema reale:

- sono invarianti business e UX dichiarati esplicitamente in `notifiche.md`
- oggi risultano credibili leggendo il codice, ma non sono tutti protetti da test automatici dedicati

Dove si manifesta:

- `backend/tests/test_play_phase3.py`
- `backend/tests/test_play_phase4.py`
- `frontend/src/pages/PlayPage.test.tsx`
- `frontend/src/pages/SharedMatchPage.test.tsx`
- `frontend/src/pages/AdminDashboardPage.test.tsx`

Gravita: media

Blocca il rilascio oppure no:

- non blocca una demo o un collaudo interno
- dovrebbe bloccare il sign-off finale della feature rispetto ai requisiti del prompt

### 2. Downgrade PostgreSQL non realmente reversibile per la migrazione enum

Descrizione tecnica:

- `backend/alembic/versions/20260505_0017_play_search_players_event.py` aggiunge il valore enum `MATCH_SEARCH_TRIGGERED` in upgrade
- il `downgrade()` e dichiarato come no-op per PostgreSQL e quindi non ripristina davvero lo schema precedente

Perche e un problema reale:

- il repo e i prompt QA chiedono migrazioni verificabili in up/down
- la validazione locale su SQLite passa, ma in PostgreSQL il rollback resta solo parziale e non reversibile in senso stretto

Dove si manifesta:

- `backend/alembic/versions/20260505_0017_play_search_players_event.py`

Gravita: media

Blocca il rilascio oppure no:

- non blocca il deploy forward della feature
- blocca un rollback schema realmente pulito su PostgreSQL se questo e requisito operativo del rilascio

### 3. Semantica ambigua del campo notifications_created tra dispatcher e API manuale

Descrizione tecnica:

- `dispatch_play_notifications_for_match()` continua a usare `notifications_created` per il numero di log/canali creati
- `search_players_for_play_match()` espone nella response `notifications_created` con il valore di `recipients_count`, cioe player unici avvisati

Perche e un problema reale:

- il comportamento corrente e accettabile per la UI, ma il naming non e piu autoesplicativo e puo generare test o integrazioni future basate su un assunto sbagliato

Dove si manifesta:

- `backend/app/services/play_notification_service.py`
- `backend/app/services/play_service.py`
- `backend/app/schemas/play.py`
- `frontend/src/types.ts`

Gravita: bassa

Blocca il rilascio oppure no:

- no, ma merita un allineamento minimo o una documentazione esplicita

## 4. Prioritizzazione finale

### Da correggere prima del rilascio

- aggiungere regressioni backend per `shared link after cancel` e `search-players unauthorized 403`
- aggiungere regressioni frontend per:
  - fallback `Copia link`
  - share da partecipante non creator
  - feedback `zero candidati`
  - feedback `cooldown`
- allineare o documentare esplicitamente la semantica di `notifications_created` nel trigger manuale

### Da correggere prima della beta pubblica

- decidere se la migrazione enum deve essere veramente reversibile su PostgreSQL
- se la policy del progetto richiede rollback pulito, implementare un downgrade reale
- se la policy accetta migration forward-only per enum, dichiararlo esplicitamente nel runbook/release note e non lasciare un downgrade fittizio implicito

### Miglioramenti differibili

- valutare in un secondo momento se introdurre anche `navigator.share` come enhancement opzionale del dialog di condivisione, senza cambiare il comportamento base gia corretto

## 5. Verdetto finale

Il codice e quasi pronto ma richiede fix mirati prima di un sign-off pieno della feature.

La parte applicativa principale e sana: i contratti sono coerenti, le validazioni mirate sono verdi, la build e verde e il comportamento business atteso e stato implementato in modo credibile e stretto. Le riserve residue non indicano un bug grave gia osservato nel perimetro verificato, ma indicano un livello di hardening ancora incompleto rispetto alla checklist dichiarata dal prompt notifiche.

## 6. Prompt operativo per i fix

Agisci come Senior Full-Stack Engineer + QA tecnico rigoroso.

Obiettivo: chiudere solo i gap reali emersi dalla verifica del perimetro Play share WhatsApp + Cerca giocatori, senza refactor ampi e senza toccare feature non coinvolte.

Regole operative:

- non rifondare nulla
- non cambiare UX o architettura oltre il minimo necessario
- non toccare pagamenti, OTP, discovery pubblico o booking pubblico fuori dal perimetro Play
- preserva gli endpoint e i contratti gia introdotti, salvo minimo allineamento del naming se davvero necessario
- preferisci patch piccole e test-first dove possibile

Fix richiesti, in ordine:

1. Backend test hardening
- estendi `backend/tests/test_play_phase3.py` con una regressione che verifichi che un match cancellato non sia piu leggibile via `GET /api/play/shared/{share_token}`
- estendi `backend/tests/test_play_phase4.py` con una regressione che verifichi il `403` del trigger `POST /api/play/matches/{match_id}/search-players` per un utente non creator/non gestore

2. Frontend test hardening
- estendi `frontend/src/pages/PlayPage.test.tsx` con:
  - regressione esplicita sul fallback `Copia link`
  - regressione per share disponibile a un partecipante gia dentro il match ma non creator
  - regressione sul messaggio `Nessun nuovo player compatibile da avvisare in questo momento.`
  - regressione sul messaggio di cooldown `Abbiamo gia cercato giocatori compatibili poco fa. Riprova tra qualche minuto.`
- se serve, aggiungi o estendi test dedicati in `frontend/src/pages/SharedMatchPage.test.tsx` o `frontend/src/pages/AdminDashboardPage.test.tsx` senza duplicare casi gia coperti

3. Allineamento minimo del contatore
- verifica se `PlayMatchSearchPlayersResponse.notifications_created` deve rappresentare davvero player unici o log/canali creati
- se il valore corretto per la UI e `player unici avvisati`, mantieni il comportamento ma documentalo in modo esplicito con naming, commento o test che eliminino l ambiguita
- evita breaking change inutili; se introduci un alias piu chiaro come `recipients_count`, fallo in modo backward-compatible

4. Migrazione enum
- verifica la policy del progetto sulle migrazioni PostgreSQL con enum
- se il requisito e rollback realmente reversibile, aggiorna `backend/alembic/versions/20260505_0017_play_search_players_event.py` con una strategia di downgrade reale
- se il requisito accetta enum migration forward-only, non fingere reversibilita: rendi esplicita la natura one-way nella documentazione operativa del rilascio

Validazioni finali richieste:

- `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_play_phase3.py tests/test_play_phase4.py -q --tb=short`
- `npm run test:run -- src/pages/PlayPage.test.tsx src/pages/SharedMatchPage.test.tsx src/pages/AdminDashboardPage.test.tsx`
- `npm run build`

Esito atteso del ciclo fix:

- nessuna regressione nel perimetro Play gia chiuso
- checklist test del prompt notifiche sostanzialmente completa
- ambiguita residue ridotte al minimo

## Gate finale

PROMPT NON VALIDATO - non procedere

Motivo del gate:

- il codice e vicino al via libera, ma la verifica rigorosa non puo considerarsi completamente chiusa finche i gap di regressione obbligatori e il caveat operativo della migrazione non vengono affrontati esplicitamente
