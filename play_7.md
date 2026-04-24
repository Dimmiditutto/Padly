# PROMPT FASE 7 - NOTIFICHE MIRATE V2, WATCHLIST CLUB, DIGEST NEARBY E RICHIESTA CONTATTO GUIDATA

Usa `play_master.md` come contesto fisso. NON modificare la logica di business fuori dal perimetro gia deciso. Mantieni il codice coerente con il repository reale e con quanto chiuso in Fase 4, 5 e 6.

Prima di iniziare devi leggere obbligatoriamente:
- `play_master.md`
- `STATO_PLAY_6.md`
- `play_4.md`
- `play_6.md`

Se `STATO_PLAY_6.md` non e `PASS`, fermati e non procedere.

Agisci come:
- Senior Prompt Engineer orientato all'implementazione reale
- Senior Software Architect pragmatico
- Senior Full-Stack Engineer su FastAPI + React + TypeScript
- Senior QA tecnico rigoroso

Rispetta rigorosamente l'ordine di output obbligatorio definito in `play_master.md`.

## Obiettivo della fase

Partendo dal backlog esplicito fissato in `STATO_PLAY_6.md`, implementare il primo strato reale di retention e notifiche mirate per la discovery pubblica dei club, senza trasformare la directory pubblica in una community ibrida e senza rompere i flussi esistenti.

Questa Fase 7 deve chiudere in modo concreto e coerente almeno questi punti del backlog:
- notifiche opt-in per nuovi match open compatibili con livello e fascia oraria preferita
- watchlist di club preferiti con alert su nuove partite open `3/4` o `2/4`
- digest geolocalizzato per club vicini con community aperta
- landing pubblica del club con richiesta contatto guidata prima dell ingresso community

Questa Fase 7 NON deve assorbire come obiettivo principale il punto backlog:
- ranking pubblico arricchito con disponibilita media recente, senza esporre dati personali

Quel tema resta backlog esplicito per una fase successiva, salvo micro-arricchimento read-only strettamente necessario e chiaramente motivato dallo stesso codice della Fase 7. Non costruire una mini piattaforma analytics dentro questa fase.

## Scope minimo chiudibile della fase

Per evitare deriva di scope, considera `PASS` della Fase 7 solo se chiudi davvero questo percorso minimo end-to-end:

1. identita/sessione discovery pubblica dedicata
2. watchlist club con opt-in esplicito
3. feed notifiche discovery persistito e leggibile dalla UI pubblica
4. digest nearby giornaliero come notifica discovery dedicata, non come report analytics
5. richiesta contatto guidata sulla pagina pubblica del club, persistita e resa operativa per il club

Regola di riduzione obbligatoria:
- il canale minimo richiesto per watchlist alert e digest nearby e un feed notifiche discovery persistito, restituito da API pubblica e visibile in UI
- web push discovery e preferibile ma non obbligatorio per il `PASS` se la sua introduzione richiederebbe una seconda foundation identity/subscription troppo larga
- email operativa e richiesta solo per la `contact request`, non per watchlist o digest

Questa scelta serve a tenere la fase coerente con il repository reale, che oggi ha gia foundation player-based per `/play`, ma non una foundation cross-club gia pronta per utenti discovery esterni.

## Ordine di attacco consigliato

Esegui la fase in questo ordine, senza saltare avanti:

1. modelli dati e migrazioni minime per identity/session/watchlist/contact request/feed notifiche discovery
2. schemi e API pubbliche discovery (`me`, `identify`, `preferences`, `watchlist`, `contact request`)
3. integrazione nei punti reali di mutation dei match open per creare alert watchlist `2/4` e `3/4`
4. scheduler per digest nearby giornaliero con dedupe
5. UI minima su `/clubs` e `/c/:clubSlug`

Non iniziare da UI o microcopy se non hai prima chiuso i contratti dati e i trigger reali lato backend.

## Punto critico da trattare come centro della fase

Nel repository reale oggi esistono gia fondamenta utili, ma non il comportamento richiesto dal backlog:

- in `backend/app/services/play_notification_service.py` esiste gia la foundation notifiche `/play` per i `Player` del club corrente:
  - scoring su giorno/fascia oraria/livello
  - preferenze `notify_match_three_of_four`, `notify_match_two_of_four`, `notify_match_one_of_four`
  - supporto web push e log notifiche
- pero questa foundation e club-scoped e player-scoped:
  - `PlayerNotificationPreference`
  - `PlayerPushSubscription`
  - `NotificationLog`
  - `padel_play_session`
- la Fase 6 ha introdotto discovery pubblica reale:
  - `/clubs`
  - `/clubs/nearby`
  - `/c/:clubSlug`
  - metadati pubblici strutturati su `Club`
  - `is_community_open`
  - serializer pubblico leggero dei match open
- le pagine pubbliche oggi permettono scoperta e navigazione, ma non hanno ancora:
  - identita pubblica opt-in persistente
  - watchlist club
  - preferenze mirate discovery-level
  - digest nearby persistito
  - richiesta contatto guidata

Il centro della fase e questo:
- riusare le fondamenta notifiche e profilo probabilistico gia esistenti dove ha senso
- senza forzare `Player` a rappresentare anche l utente esterno della discovery pubblica
- senza rompere la separazione pubblico/community chiusa in Fase 6

## Conflitto tecnico reale da gestire esplicitamente

Esiste un conflitto reale tra due vincoli:

- `play_master.md` privilegia entita tenant-scoped tramite `club_id`
- il backlog di `STATO_PLAY_6.md` chiede watchlist e digest cross-club, quindi per definizione non confinati a un solo club

La risoluzione ammessa e minima e deve essere esplicitata nel prompt e nel codice:

- e ammessa una sola entita tecnica globale di identita/sessione per la discovery pubblica, solo se davvero necessaria a supportare il caso cross-club
- questa entita globale NON deve contenere semantica community, booking o membership
- tutto cio che e club-facing deve restare tenant-scoped:
  - watchlist item per club
  - log notifiche per club
  - lead/richieste contatto per club
  - eventuali subscription/alert rows per club

In altre parole:
- identita tecnica globale minima, se necessaria
- dati di business e operativi sempre ancorati al club quando riguardano un club specifico

Non lasciare questo punto implicito.

Default architetturale da usare salvo conflitto tecnico reale:
- una entita globale minima per il subscriber discovery
- una tabella dedicata dei token/sessioni discovery
- tabelle club-scoped per watchlist item, notifiche discovery per club e richieste contatto per club
- nessun riuso di tabelle player-based esistenti con foreign key fittizie o semantica piegata

Se scegli naming diverso, mantieni comunque questa semantica minima. Preferenza forte, salvo conflitto tecnico reale:
- `PublicDiscoverySubscriber`
- `PublicDiscoverySessionToken`
- `PublicClubWatch`
- `PublicDiscoveryNotification`
- `PublicClubContactRequest`

`PublicDiscoveryPushSubscription` e opzionale e va introdotta solo se implementi davvero web push discovery in questa fase.

## Regole prodotto da rispettare

### Separazione pubblico/community

- la directory pubblica resta pubblica
- la pagina pubblica del club resta pubblica
- la community privata resta su `/c/{club_slug}/play`
- seguire un club non significa entrare nella community
- ricevere alert non significa poter fare join diretto da superfici pubbliche
- una richiesta contatto non crea automaticamente un `Player`, un `Customer`, un invite token o una membership community

### Watchlist club

- un utente esterno deve poter aggiungere un club pubblico alla propria watchlist
- l opt-in deve essere esplicito
- seguire un club richiede prima una sessione discovery valida; non usare localStorage come unica source of truth della watchlist
- gli alert watchlist devono riguardare solo nuovi match pubblicamente visibili e solo per stati utili alla conversione:
  - `3/4`
  - `2/4`
- `1/4` resta fuori scope per la watchlist pubblica v1 di questa fase, salvo motivazione tecnica forte e test espliciti
- la watchlist deve funzionare anche se il club ha community privata; in quel caso l alert porta alla pagina pubblica del club e alla richiesta contatto, non a funzioni community private

### Notifiche mirate opt-in

- gli alert devono essere compatibili con:
  - livello preferito
  - fascia oraria preferita
- usa fasce orarie semplici e deterministiche, coerenti con il codice esistente:
  - `morning`
  - `afternoon`
  - `evening`
- usa semantica livello coerente con `PlayLevel` gia esistente
- se il subscriber non ha ancora espresso preferenze esplicite, usa un default minimale documentabile:
  - livello `NO_PREFERENCE`
  - tutte le fasce orarie abilitate
  - watchlist alert `3/4` e `2/4` attivi solo dopo opt-in esplicito al follow del club
- la fase deve rendere visibili queste notifiche almeno dentro un feed discovery recente, non solo come side effect server-side

### Digest nearby

- il digest nearby deve includere solo club con:
  - coordinate reali disponibili
  - `is_community_open = true`
- il digest nearby deve essere opt-in separato
- se l utente non ha coordinate salvate come coppia valida, il digest nearby deve restare disattivato in modo esplicito e non ambiguo
- nessuna distanza inventata
- nessun geocoding esterno
- nessuna dipendenza Google Maps / Places / geocoding di terze parti

### Richiesta contatto guidata

- la pagina pubblica del club deve offrire un percorso guidato di richiesta contatto prima dell ingresso community
- il form deve raccogliere il minimo utile e reale, ad esempio:
  - nome
  - almeno un contatto tra email e telefono
  - consenso privacy
  - eventuale livello preferito
  - eventuale nota breve
- la richiesta contatto deve essere persistita e resa operativa per il club
- default richiesto:
  - persistenza DB
  - invio email operativa al club verso `support_email` oppure fallback su `notification_email`
- solo se il riuso dell infrastruttura email del repo si dimostra tecnicamente incoerente, puoi sostituire l email operativa con una superficie minima read-only lato admin o platform, ma devi motivarlo esplicitamente e testarlo
- non costruire in questa fase una nuova dashboard CRM completa

### Dati pubblici e privacy

Gli alert, il digest e la watchlist pubblica possono usare solo dati gia legittimamente pubblici o resi pubblici dalla Fase 6, ad esempio:
- nome club
- slug club
- indirizzo pubblico sintetico
- citta / provincia / CAP
- distanza, se realmente calcolabile
- stato community aperta/privata
- giorno/data/orario del match open
- livello richiesto
- stato `2/4` o `3/4`
- messaggio sintetico tipo `Manca 1 giocatore`

NON devono uscire:
- nomi player
- telefoni
- note interne
- creator profile name
- token share
- payload community privati
- storico personale di altri utenti
- qualunque dato personale dei partecipanti

## Integrazione obbligatoria col repo attuale

Lavora sui punti proprietari del comportamento, senza duplicare logica chiusa nelle fasi precedenti:

- `backend/app/models/__init__.py`
- `backend/app/schemas/public.py`
- `backend/app/api/routers/public.py`
- `backend/app/services/play_notification_service.py`
- `backend/app/services/play_service.py`
- `backend/app/core/scheduler.py` o superficie scheduler equivalente gia in uso
- `backend/app/services/email_service.py` solo se il riuso per `contact request` resta pulito
- `frontend/src/services/publicApi.ts`
- `frontend/src/types.ts`
- `frontend/src/pages/ClubDirectoryPage.tsx`
- `frontend/src/pages/PublicClubPage.tsx`

Se il repo lo richiede, aggiungi un service dedicato, ad esempio:
- `backend/app/services/public_discovery_service.py`

Preferenza forte:
- crea un service dedicato per la nuova logica discovery/watchlist/digest/contact request
- non gonfiare `play_notification_service.py` fino a farlo diventare un contenitore di tutto
- puoi pero riusare helper puri esistenti su:
  - compatibilita livelli
  - bucket orari
  - scoring minimo
solo se la condivisione e davvero piccola e non forza un refactor ampio di codice gia stabile

## Cose da riusare esplicitamente

- `Club.slug` come identificatore pubblico univoco
- metadati strutturati pubblici su `Club` introdotti in Fase 6
- `is_community_open`
- il serializer/query pubblico dei match open gia introdotto in Fase 6, come base dei segnali pubblici
- `PlayLevel`
- la semantica di compatibilita livello gia usata in `play_notification_service.py`
- il concetto di bucket orari `morning/afternoon/evening`
- foundation scheduler gia esistente
- foundation web push/VAPID gia esistente solo se l estensione discovery resta pulita e non costringe a riusare modelli player-based

## Cose da NON riusare in modo improprio

- non usare `Player` come identita pubblica cross-club
- non usare `Customer` per watchlist o lead discovery
- non scrivere alert watchlist dentro `NotificationLog` player-based con fake `player_id`
- non riusare `PlayerPushSubscription` per utenti che non sono `Player`
- non trasformare `GET /api/public/clubs/{club_slug}` in endpoint ibrido che espone dettagli community privati
- non rompere `dispatch_play_notifications_for_match` gia usato per la community privata del club

## Modelli dati minimi richiesti

Chiudi un modello dati minimo, reale e coerente.

### Identita/sessione discovery pubblica

Se serve davvero una minima identita globale per supportare backlog cross-club, falla esplicita.

Pattern preferito:
- entita tecnica di identita/sessione discovery pubblica
- token opaco dedicato
- cookie dedicato, separato da `padel_play_session`

Regola di modellazione:
- il subscriber discovery non e un player del club
- il subscriber discovery non deve avere `club_id`
- la relazione col club nasce solo tramite watchlist item, notifiche discovery o contact request tenant-scoped

Regole obbligatorie del cookie discovery:
- nome dedicato, ad esempio `padel_discovery_session`
- host-only
- `httpOnly`
- `SameSite=Lax`
- `secure` quando appropriato
- durata lunga ma semplice e documentabile, preferibilmente 90 giorni come il token play, salvo motivo tecnico forte contrario
- hash token salvato lato server

### Entita club-scoped minime attese

Almeno:
- relazione watchlist subscriber <-> club
- preferenze mirate discovery rilevanti per i club seguiti
- log notifiche discovery coerente e deduplicabile
- eventuale push subscription discovery solo se implementi davvero web push discovery in questa fase
- richiesta contatto pubblica verso il club

Preferenza di shape dati, senza irrigidire troppo il naming finale:
- watch item tenant-scoped via `club_id`
- flag alert `3/4` e `2/4`
- livello preferito
- fasce orarie preferite
- coordinate utente opzionali come coppia coerente
- raggio nearby minimo documentabile, ad esempio `25 km`
- toggle esplicito `nearby_digest_enabled`
- timestamp per dedupe digest e alert

Regola importante di scope:
- non introdurre una tabella separata per ogni singolo tipo di alert se un singolo modello discovery notification deduplicabile copre bene watchlist alert e nearby digest
- non introdurre un event bus dedicato o una coda esterna se il repository non lo usa gia

Per la richiesta contatto:
- `club_id`
- riferimento eventuale all identita discovery se esiste
- nome
- email e/o telefono
- nota breve opzionale
- dati minimi utili al club per ricontattare
- `privacy_accepted_at`
- `created_at`

Non introdurre una modellazione CRM larga. Questa fase richiede solo il minimo operativo.

## API pubbliche minime richieste

Chiudi una superficie pubblica chiara, separata da `/api/play` privata.

Minimo richiesto:

- `GET /api/public/discovery/me`
  - restituisce stato sessione discovery corrente
  - preferenze discovery
  - watchlist attuale
  - notifiche discovery recenti
  - stato push discovery solo se implementato davvero in questa fase

- `POST /api/public/discovery/identify`
  - crea o rinnova la sessione discovery opt-in
  - richiede almeno consenso privacy
  - puo ricevere preferenze iniziali minime

- `PUT /api/public/discovery/preferences`
  - aggiorna livello preferito
  - aggiorna fasce orarie preferite
  - aggiorna coordinate nearby come coppia
  - aggiorna `nearby_digest_enabled`

- `GET /api/public/discovery/watchlist`

- `POST /api/public/discovery/watchlist/{club_slug}`

- `DELETE /api/public/discovery/watchlist/{club_slug}`

- endpoint discovery push subscription coerenti col pattern gia usato in `/api/play`, solo se implementi davvero web push discovery

- `POST /api/public/clubs/{club_slug}/contact-request`
  - crea la richiesta contatto per quel club
  - non richiede membership community

Se scegli path leggermente diversi, devono restare:
- pubblici
- coerenti con `public.py`
- autoesplicativi
- separati dagli endpoint community privata

Non aggiungere nuove route frontend standalone salvo necessita tecnica forte. Preferenza forte:
- riusa `/clubs` e `/c/:clubSlug`
- eventuali preferenze discovery possono vivere in drawer, modal o pannelli inline
- non creare una nuova area "account discovery" separata in questa fase

## Regole di dispatch e digest da rendere reali

### Alert watchlist

- i trigger devono agganciarsi ai punti reali in cui cambia lo stato utile di un match open pubblico:
  - creazione match
  - join che porta a `2/4`
  - join che porta a `3/4`
  - eventuale leave che riporta il match a uno stato nuovamente notificabile, solo se il comportamento e davvero desiderato e chiaramente deduplicato
- preferenza forte:
  - integra il dispatch nello stesso punto di decisione dove gia oggi si innescano le notifiche `/play` del club
  - non creare un secondo poller opaco se non serve
- deduplica per subscriber/club/match/kind/canale in modo testabile
- default di prodotto da usare:
  - alert su `2/4` e `3/4` vengono generati come nuove righe di notifica discovery
  - il canale minimo e `IN_APP` discovery/feed persisted
  - il canale `WEB_PUSH` discovery e additivo e non obbligatorio per il `PASS`

### Compatibilita mirata

Usa regole semplici e documentabili:
- compatibilita livello coerente con `PlayLevel` e con la logica gia esistente
- match sulla fascia oraria tramite bucket `morning/afternoon/evening`
- solo opt-in espliciti
- cap giornaliero semplice per evitare flood, se necessario

### Digest nearby

- il digest nearby deve essere deterministico
- deve includere solo club con `is_community_open = true`
- deve usare coordinate utente salvate e coordinate club reali
- se manca una delle due coordinate del subscriber, niente digest nearby
- no geocoding, no inferenze testuali di localita
- massimo un digest per giorno per subscriber, salvo scelta diversa fortemente motivata e testata
- il digest deve usare solo dati pubblici minimi e linkare alla pagina pubblica del club
- default di scheduling da usare salvo conflitto tecnico reale:
  - un job giornaliero unico, deterministico e testabile
  - dedupe per subscriber e giorno
  - output come notifica discovery dedicata, non come report separato

### Canali

Preferenza architetturale:
- canale minimo richiesto per il `PASS`: feed notifiche discovery persistito e letto da API pubblica
- `WEB_PUSH` discovery: preferibile ma opzionale
- email operativa: richiesta per la sola `contact request`
- non introdurre in questa fase un sistema email marketing, newsletter o campagne massive

## UX minima richiesta

### Directory pubblica `/clubs`

Chiudi almeno:
- CTA `Segui club` o equivalente sulla card/lista del club
- gestione stato seguito/non seguito
- ingresso leggero al flusso opt-in discovery se manca la sessione discovery
- accesso o pannello minimo per preferenze alert/digest
- visualizzazione minima del feed alert discovery recente se questo aiuta a rendere il comportamento verificabile senza una nuova pagina dedicata
- messaggi chiari se il digest nearby non e disponibile per mancanza di coordinate o consenso geolocalizzazione

### Pagina pubblica club `/c/:clubSlug`

Chiudi almeno:
- CTA watchlist coerente
- CTA `Richiedi contatto` o equivalente
- se `is_community_open = true`, mantieni la CTA community ma non eliminare il percorso contatto
- se `is_community_open = false`, la richiesta contatto puo diventare la CTA primaria
- il form contatto deve stare nella pagina pubblica del club o in un flow strettamente adiacente, non in una pagina admin o community privata

### Area admin

Per questa fase l area admin non e il focus.

Regola esplicita:
- non aprire una nuova dashboard lead management completa
- tocca l admin solo se serve una superficie minima strettamente necessaria a rendere operativa la `contact request` nel caso in cui l email operativa non sia riusabile in modo coerente
- in assenza di questa necessita, il `PASS` deve arrivare senza nuove UI admin

### Regole UX da rispettare

- nessuna password tradizionale
- nessun onboarding community automatico
- nessun join match dalla superficie pubblica
- nessuna UI che faccia sembrare pubblico cio che e ancora privato
- coerenza piena con il linguaggio visivo gia introdotto in Fase 6 su `ClubDirectoryPage` e `PublicClubPage`

## Vincoli tecnici specifici emersi dal repo reale

- `frontend/src/pages/PublicClubPage.tsx` oggi mostra CTA community ma non ha watchlist o contact request
- `frontend/src/pages/ClubDirectoryPage.tsx` oggi mostra directory e geolocalizzazione nearby ma non ha stato utente o preferenze discovery persistite
- `backend/app/api/routers/public.py` oggi e gia il posto naturale per le API pubbliche di discovery
- `backend/app/services/play_notification_service.py` oggi contiene logica forte ma player-based; non e corretto riusarla tale e quale per identita discovery esterne
- `NotificationLog` e `PlayerPushSubscription` oggi sono semanticamente legati a `Player`

## Test richiesti

Backend, almeno:
- nuova sessione discovery creata con cookie dedicato e token hash server-side
- recupero `GET /api/public/discovery/me` con sessione valida e fallback corretto senza sessione
- CRUD watchlist con dedupe su stesso club
- persistenza preferenze discovery per livello e fasce orarie
- validazione coppia lat/lng del subscriber: entrambe presenti o entrambe assenti
- feed notifiche discovery recente restituito correttamente da `GET /api/public/discovery/me`
- alert watchlist creati solo per match `3/4` e `2/4` compatibili
- nessun alert watchlist per match incompatibili per livello/fascia oraria
- digest nearby con soli club `is_community_open = true` e con coordinate calcolabili
- nessun digest nearby se il subscriber non ha coordinate valide
- dedupe digest giornaliero
- richiesta contatto persistita correttamente e, se implementato, email operativa inviata/loggata correttamente
- se `WEB_PUSH` discovery non viene implementato, dichiaralo esplicitamente come `NOT APPLICABLE` nella verifica finale e copri comunque il feed notifiche discovery
- nessun leak di dati personali nei payload/log discovery pubblici
- nessuna regressione sulle notifiche `/play` private gia esistenti
- nessuna regressione sulle API pubbliche della Fase 6

Frontend, se toccato:
- test mirati su `/clubs` per watch/unwatch e opt-in discovery
- test mirati su `/clubs` o `/clubs/nearby` per preferenze digest e fallback quando posizione non disponibile
- test mirati su `/c/:clubSlug` per richiesta contatto guidata
- test che confermino che il follow di un club non sblocca join o funzioni community
- test che confermino che `/`, `/clubs`, `/clubs/nearby`, `/c/:clubSlug` e `/c/:clubSlug/play` continuano a funzionare
- build frontend finale

Per i test backend usa il Python del repo:
- `D:/Padly/PadelBooking/.venv/Scripts/python.exe`

Se introduci nuove tabelle o colonne:
- migration Alembic obbligatoria
- validazione upgrade/downgrade obbligatoria

## Verifica di fine fase obbligatoria

La fase passa solo se:
- esiste davvero una identita opt-in discovery pubblica distinta dal `Player` community oppure una soluzione equivalente esplicitamente motivata e coerente
- la watchlist club esiste davvero e genera alert solo su segnali pubblici utili
- esiste almeno un feed notifiche discovery realmente leggibile dalle superfici pubbliche
- il digest nearby usa solo dati strutturati reali e non geocoding esterno
- la richiesta contatto guidata esiste davvero sulla pagina pubblica del club
- la separazione pubblico/community non viene violata
- le notifiche `/play` private gia chiuse nelle fasi precedenti non vengono rotte
- `/`, `/clubs`, `/clubs/nearby`, `/c/:clubSlug` e `/c/:clubSlug/play` restano funzionanti
- i test mirati sono verdi
- la build frontend e verde se tocchi contratti o routing

## File stato da produrre obbligatoriamente

Crea `STATO_PLAY_7.md` con almeno:
- esito `PASS` / `FAIL`
- scope effettivamente chiuso dalla Fase 7
- backlog di `STATO_PLAY_6.md` assorbito davvero in questa fase
- backlog rimasto esplicitamente fuori scope con motivazione
- nuova semantica della sessione discovery pubblica
- cookie/token scelto e regole di durata/sicurezza
- modelli principali introdotti
- API pubbliche introdotte
- regole finali di watchlist, alert e digest
- regole finali della richiesta contatto guidata
- canali notifiche effettivamente usati e motivazione
- `WEB_PUSH` discovery implementato oppure `NOT APPLICABLE` con motivazione tecnica esplicita
- email operativa `contact request` implementata oppure alternativa operativa adottata con motivazione esplicita
- file principali toccati backend/frontend
- validazioni realmente eseguite con esito
- `## Note operative finali`
- `## Backlog esplicito per una futura fase 8`

## Fuori scope approvato

Questa fase non deve assorbire:
- un nuovo sistema account/password per utenti discovery pubblici
- onboarding community automatico da watchlist o da contact request
- CRM/admin pipeline completa per lead pubblici
- ranking pubblico completo con disponibilita media recente come feature principale
- mappe avanzate, geocoding esterno, Places API o Google Maps
- un sistema email marketing/general purpose non gia giustificato dal repo
- refactor ampi di `play_notification_service.py` non strettamente necessari

Questi temi non devono bloccare il `PASS` della Fase 7, salvo priorita esplicita diversa richiesta dal prodotto.