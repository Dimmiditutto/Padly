# PROMPT FINALE PLAY - CHIUSURA OPERATIVA DI /play

Usa `play_master.md` come contesto fisso. NON modificare la logica di business fuori dal perimetro gia deciso. Mantieni il codice coerente con il repository reale e con quanto chiuso in Fase 4, 5, 6 e 7.

Prima di iniziare devi leggere obbligatoriamente:
- `play_master.md`
- `play_1.md`
- `play_2.md`
- `play_3.md`
- `play_4.md`
- `play_5.md`
- `play_6.md`
- `play_7.md`
- `STATO_PLAY_1.md`
- `STATO_PLAY_2.md`
- `STATO_PLAY_3.md`
- `STATO_PLAY_4.md`
- `STATO_PLAY_5.md`
- `STATO_PLAY_6.md`
- `STATO_PLAY_7.md`

Se `STATO_PLAY_7.md` non e `PASS`, fermati e non procedere.

Agisci come:
- Senior Prompt Engineer orientato all'implementazione reale
- Senior Software Architect pragmatico
- Senior Full-Stack Engineer su FastAPI + React + TypeScript
- Senior QA tecnico rigoroso

Rispetta rigorosamente l'ordine di output obbligatorio definito in `play_master.md`.

## Obiettivo della fase finale

Chiudere davvero il backlog residuo reale del modulo `/play`, senza riaprire foundation, pagamenti community, discovery pubblica o route gia stabilizzate nelle fasi precedenti.

Questa fase finale deve assorbire solo i gap ancora aperti e documentati dopo Fase 7:

- consegna `WEB_PUSH` server-side reale per le notifiche private `/play`, riusando la foundation gia esistente di `PlayerPushSubscription`, service worker e chiavi VAPID
- `mark-as-read` esplicito, stato `read/unread` realmente usabile e unread count per il feed notifiche private `/play`
- centro notifiche `/play` minimo ma piu utile della lista v1, senza trasformarlo in una inbox complessa
- ranking pubblico read-only dei club/community basato su segnali pubblici e disponibilita recente, senza esporre dati personali e senza costruire una mini piattaforma analytics
- chiusura finale del perimetro prodotto `/play` con un nuovo file stato dedicato

Non devi reimplementare o rimettere in discussione cio che e gia chiuso:

- dominio `Player`, `Match`, `MatchPlayer`, join/create/leave/cancel, share flow e booking finale 4/4
- pagamento community default offline e caparra opzionale tenant-scoped
- directory pubblica `/clubs`, `/clubs/nearby`, `/c/:clubSlug`
- discovery pubblica con watchlist, digest nearby e contact request

## Scope minimo chiudibile

Per evitare deriva di scope, considera `PASS` della fase finale solo se chiudi davvero questo percorso minimo end-to-end:

1. le notifiche private `/play` non risultano piu solo `SIMULATED` quando esiste una subscription push attiva e valida
2. il player puo distinguere notifiche lette e non lette nella UI `/play` e marcarle come lette
3. la UI `/play` espone un unread count affidabile e un pannello notifiche minimamente piu maturo della lista v1
4. `/clubs` e `/c/:clubSlug` espongono un ranking pubblico minimale, utile e read-only basato su segnali pubblici e disponibilita recente
5. il ranking pubblico non espone nomi player, token share, note interne o altri dettagli community privati
6. i flussi gia chiusi di Fase 1-7 non vengono rotti

Regola di riduzione obbligatoria:

- se una parte del backlog residuo si rivela piu larga del previsto, chiudi la versione minima realmente rilasciabile e documenta in `STATO_PLAY_FINAL.md` l'eventuale residuo non bloccante
- il tuning fine del punteggio notifiche e il throttling sofisticato non devono bloccare il `PASS` se il dispatch reale, il read-state e il ranking pubblico sono chiusi davvero

## Punto critico 1 - Web push private `/play` davvero reali

Lo stato attuale confermato dal codice e questo:

- la registrazione browser della subscription e reale
- il service worker esiste gia
- il backend persiste `PlayerPushSubscription`
- i log `WEB_PUSH` privati oggi risultano ancora `SIMULATED`

Questa fase deve chiudere il dispatch reale solo per il dominio privato `/play` player-based.

Regole obbligatorie:

- non introdurre discovery web push pubbliche: il perimetro e il canale push privato `/play`
- non duplicare subscription o notifiche su modelli discovery pubblici
- usa una libreria esterna standard e sobria per VAPID/web push solo se serve davvero a chiudere il dispatch reale lato server
- nessuna chiamata reale a provider esterni nei test: mock o stub obbligatori
- se il provider push restituisce errore definitivo coerente con subscription scaduta o non piu valida, revoca o disattiva la subscription in modo consistente
- i log notifiche devono riflettere lo stato reale del tentativo di invio; evita di lasciare `SIMULATED` sui path che fanno dispatch effettivo
- mantieni idempotenza e deduplica gia chiuse in Fase 4

Preferenza forte di implementazione:

- riusa `play_notification_service.py` per il dispatch reale delle notifiche private, senza trasformarlo in un contenitore generico di funzioni discovery pubbliche
- usa `settings.play_push_vapid_public_key` e `settings.play_push_vapid_private_key` se gia coerenti col codebase; se manca una guard rail di configurazione, aggiungila nel punto minimo coerente

## Punto critico 2 - Read state e centro notifiche privato minimamente completo

Lo stato attuale confermato e questo:

- il feed notifiche in-app privato esiste gia
- `NotificationLog` espone gia un `read_at`
- manca pero una chiusura prodotto vera su `mark-as-read`, unread count e UX del feed privato `/play`

Questa fase deve chiudere una soluzione minima ma reale:

- action per marcare letta una singola notifica privata `/play`
- unread count esposto al client in modo affidabile
- distinzione visuale tra letta e non letta
- pannello notifiche nella `PlayPage` piu utile della lista v1

Regole di riduzione:

- non creare una nuova pagina inbox separata se un pannello nella `PlayPage` basta
- `mark-all-as-read` e opzionale: aggiungilo solo se resta piccolo e naturale
- evita filtri avanzati, cartelle, categorie o preference center complessi

Preferenza forte di contratto:

- estendi `GET /api/play/me` o il payload notifiche gia esistente prima di creare endpoint paralleli non necessari
- aggiungi un endpoint write minimale, autoesplicativo e coerente con il router `play.py`, ad esempio su `/api/play/notifications/{notification_id}/read`

## Punto critico 3 - Ranking pubblico read-only senza deriva analytics

La Fase 7 ha lasciato esplicitamente fuori scope il ranking pubblico con disponibilita media recente. Questa fase deve chiudere proprio quel residuo, ma nel modo piu piccolo, leggibile e difendibile possibile.

Obiettivo prodotto del ranking pubblico:

- aiutare l'utente esterno a capire quali club sembrano avere una community piu attiva o una disponibilita recente piu interessante
- farlo usando solo segnali pubblici o aggregati non personali
- non trasformare `/clubs` o `/c/:clubSlug` in una dashboard analytics

Regole obbligatorie:

- usa solo dati pubblici o aggregati non personali
- non esporre mai nomi player, creator, token share, note o payload privati
- mantieni il ranking read-only e informativo: nessun impatto su join, membership o discovery identity
- nessun geocoding esterno e nessuna dipendenza mappe

Strategia minima preferita, salvo conflitto tecnico reale:

- ranking o `public_activity_score` deterministico basato su segnali pubblici come:
  - volume attuale di match open visibili nel breve orizzonte pubblico
  - peso maggiore a `3/4`, poi `2/4`, poi `1/4`
  - un indicatore semplice di disponibilita recente o attivita recente su una finestra limitata e documentabile
- esposizione nel payload pubblico di campi aggregati minimali o di una label derivata, senza introdurre un nuovo sistema di analytics persistente se una query o proiezione leggera basta

Vincolo importante:

- se per dare una nozione di disponibilita recente basta una query aggregata o una proiezione minimale, preferiscila a nuove tabelle analytics o a job complessi
- non introdurre un event bus, una coda esterna o un data mart dedicato

## Integrazione obbligatoria col repo attuale

Lavora sui punti proprietari del comportamento, senza duplicare superfici gia stabili:

- `backend/app/models/__init__.py`
- `backend/app/schemas/play.py`
- `backend/app/api/routers/play.py`
- `backend/app/services/play_notification_service.py`
- `backend/app/schemas/public.py`
- `backend/app/api/routers/public.py`
- `backend/app/services/public_discovery_service.py`
- `backend/app/services/play_service.py` solo se serve davvero per segnali pubblici o nozioni aggregate gia legate ai match
- `backend/app/core/config.py` se servono guard rail o config minime per il dispatch push reale
- `frontend/src/types.ts`
- `frontend/src/services/playApi.ts`
- `frontend/src/services/publicApi.ts`
- `frontend/src/pages/PlayPage.tsx`
- `frontend/src/pages/ClubDirectoryPage.tsx`
- `frontend/src/pages/PublicClubPage.tsx`

Se il repo lo richiede davvero, puoi aggiungere un helper o service piccolo e dedicato, ma evita di frammentare inutilmente:

- per il push privato, preferenza forte su evoluzione sobria di `play_notification_service.py`
- per il ranking pubblico, preferenza forte su evoluzione sobria di `public_discovery_service.py` o su helper read-only dedicato

## Cose da NON riaprire o riusare in modo improprio

- non riaprire la logica di pagamento community di Fase 5
- non spostare di nuovo il confine pubblico/community chiuso in Fase 6 e 7
- non introdurre discovery web push pubbliche per questa fase finale
- non costruire CRM lead management, dashboard admin dedicate ai lead o campagne email
- non assorbire revoca/rotazione share token come obiettivo della fase finale
- non rifondare KPI o reporting admin delle booking `/play` salvo un micro-allineamento read-only strettamente necessario
- non introdurre login/password tradizionale, chat, AI o ranking fantasy

## API minime richieste

Chiudi una superficie piccola e chiara.

Minimo richiesto lato `/play` privato:

- estensione coerente del payload `GET /api/play/me` oppure del payload notifiche gia esistente per includere unread count e stato di lettura utile al frontend
- `POST /api/play/notifications/{notification_id}/read` oppure path equivalente chiaro e coerente

Minimo richiesto lato discovery pubblica:

- estensione di `GET /api/public/clubs`
- estensione di `GET /api/public/clubs/{club_slug}`

Preferenza forte:

- non creare un endpoint ranking separato se i dati possono stare nei payload pubblici gia esistenti di directory e dettaglio club
- se serve un ordinamento opzionale nella directory, mantienilo esplicito e documentabile, non opaco

## UX minima richiesta

### PlayPage privata

Chiudi almeno:

- badge o contatore notifiche non lette
- stato visivo chiaro letto/non letto
- azione `Segna come letta` o equivalente per singola notifica
- feedback utente coerente su notifiche push attive, invio reale e fallback in-app

Non serve:

- una nuova pagina inbox dedicata
- un sistema filtri avanzato
- un centro preferenze enorme

### Directory pubblica `/clubs`

Chiudi almeno:

- un indicatore ranking o disponibilita recente chiaramente pubblico e non personale
- eventuale ordinamento o badge che aiuti a capire quali club hanno piu attivita recente, senza oscurare distanza e segnali gia introdotti in Fase 6

### Pagina pubblica club `/c/:clubSlug`

Chiudi almeno:

- un riepilogo read-only della disponibilita/attivita recente del club coerente con la directory
- nessuna esposizione di dati community privati o personali

## Test richiesti

Backend, almeno:

- dispatch `WEB_PUSH` privato reale con provider mockato: caso successo
- dispatch `WEB_PUSH` privato reale con provider mockato: caso errore definitivo che revoca o invalida la subscription
- nessuna chiamata esterna reale nei test
- `mark-as-read` della notifica privata con aggiornamento di `read_at`
- unread count corretto prima e dopo il `mark-as-read`
- nessuna regressione sul feed in-app e sulla deduplica notifiche `/play`
- ranking pubblico deterministico basato su segnali non personali
- nessun leak di nomi player, token share, note o dettagli interni nei nuovi payload pubblici di ranking
- nessuna regressione sulle API pubbliche discovery di Fase 6 e 7

Frontend, se toccato:

- test mirati su `PlayPage` per unread count, distinzione letta/non letta e azione di `mark-as-read`
- test mirati su `PlayPage` per feedback coerente del canale push e del fallback in-app
- test mirati su `/clubs` e `/c/:clubSlug` per rendering del ranking o della disponibilita recente pubblica
- test che confermino che il ranking pubblico non introduce CTA private improprie
- test che confermino che `/`, `/clubs`, `/clubs/nearby`, `/c/:clubSlug`, `/c/:clubSlug/play` restano funzionanti
- build frontend finale

Per i test backend usa il Python del repo:

- `D:/Padly/PadelBooking/.venv/Scripts/python.exe`

Se per chiudere il dispatch push reale serve una dipendenza backend nuova, aggiungila in modo esplicito e testala con mock, non con invii reali.

## Verifica di fine fase obbligatoria

La fase passa solo se:

- il canale `WEB_PUSH` privato `/play` non resta piu soltanto `SIMULATED` quando il server esegue davvero il dispatch
- il feed privato `/play` espone uno stato `read/unread` realmente usabile dal player
- il player puo marcare una notifica privata come letta
- l'unread count e coerente lato backend e frontend
- `/clubs` e `/c/:clubSlug` espongono un ranking o indicatore equivalente di disponibilita recente usando soli segnali pubblici
- nessun dato personale o interno viene esposto nei nuovi payload pubblici
- le fasi 1-7 non vengono rotte
- i test mirati sono verdi
- la build frontend e verde se tocchi contratti o routing

## File stato da produrre obbligatoriamente

Crea `STATO_PLAY_FINAL.md` con almeno:

- esito `PASS` / `FAIL`
- backlog residuo di `STATO_PLAY_4.md` e `play_7.md` assorbito davvero in questa fase finale
- canali notifiche finali usati nel dominio privato `/play` e nel dominio discovery pubblico
- strategia finale di dispatch `WEB_PUSH` privato e gestione errori subscription
- endpoint aggiunti o estesi lato `/play` privato
- strategia finale di ranking pubblico e campi/label restituiti ai payload pubblici
- file principali toccati backend/frontend
- validazioni realmente eseguite con esito
- eventuali residui post-chiusura che non bloccano il prodotto v1
- `## Note operative finali`

## Fuori scope approvato

Questa fase finale non deve assorbire:

- discovery web push pubbliche
- CRM/admin pipeline per i lead pubblici
- revoca/rotazione share token come lavorazione principale
- revisione KPI o reporting admin `/play` come progetto separato
- tuning avanzato del ranking pubblico come sistema analytics
- mappe avanzate, geocoding esterno, Places API o Google Maps
- split payment, refund dedicati o altre estensioni payment fuori Fase 5

Questi temi non devono bloccare il `PASS` della chiusura finale di `/play`, salvo priorita esplicita diversa richiesta dal prodotto.