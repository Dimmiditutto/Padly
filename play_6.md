# PROMPT FASE 6 - DIRECTORY CLUB PUBBLICA, GEOLOCALIZZAZIONE BASE E VISTA PUBBLICA LEGGERA DELLE PARTITE OPEN

Usa `play_master.md` come contesto fisso. Leggi anche `geo.md`. NON modificare la logica di business. Mantieni il codice coerente con il repository reale.

Prima di iniziare devi leggere obbligatoriamente:
- `play_master.md`
- `STATO_PLAY_5.md`
- `geo.md`

Per allineamento architetturale e di stile, rileggi anche:
- `play_4.md`
- `play_5.md`

Se `STATO_PLAY_5.md` non e `PASS`, fermati e non procedere.

Agisci come:
- Senior Prompt Engineer orientato all'implementazione reale
- Senior Software Architect pragmatico
- Senior Full-Stack Engineer su FastAPI + React + TypeScript
- Senior QA tecnico rigoroso

## Obiettivo della fase

Implementare la scoperta pubblica dei club senza aprire la community privata:
- directory pubblica dei club
- ricerca manuale per luogo senza Google API
- geolocalizzazione browser opzionale per trovare i club vicini
- pagina pubblica del club con informazioni minime utili
- vista pubblica leggera delle partite `/play` aperte

La regola di prodotto da rendere reale e questa:
- club pubblico e visibile
- community del club privata/chiusa
- pubblico = scoperta
- community = azione

## Punto critico da trattare come centro della fase

Nel repository reale oggi esistono gia alcuni mattoni, ma non il flusso pubblico completo:
- `Club` ha gia `id`, `slug`, `public_name`, `support_email`, `support_phone`, `timezone`, ma non ha ancora metadati pubblici di localizzazione sufficienti per directory e nearby
- il frontend ha gia la route community `frontend/src/App.tsx` su `/c/:clubSlug/play`, ma non ha ancora `/clubs`, `/clubs/nearby` o `/c/:clubSlug`
- `GET /api/public/config` e la homepage `/'` sono oggi orientati al booking pubblico del club corrente e non alla scoperta del network dei club
- `_serialize_match` in `backend/app/services/play_service.py` espone nomi profilo e partecipanti, quindi non e riusabile cosi com'e per utenti esterni
- `backend/app/main.py` imposta oggi `Permissions-Policy` con `geolocation=()`, quindi la geolocalizzazione browser e al momento bloccata lato header

La Fase 6 deve chiudere questi gap senza rompere:
- routing tenant-aware gia esistente
- booking pubblico attuale su `/'`
- community privata su `/c/{club_slug}/play`
- logica `/play` interna gia chiusa nelle fasi precedenti

## Regole prodotto da rispettare

Scoperta pubblica:
- un utente esterno deve poter scoprire che il club esiste
- deve poter vedere dati pubblici minimi del club
- deve poter capire se il club usa l'app e se puo valere la pena entrare nella community
- deve poter vedere una vista pubblica leggera delle partite aperte del club

Separazione pubblico/community:
- la directory club e pubblica
- la pagina pubblica del club e pubblica
- la vista pubblica delle partite open e pubblica ma sintetica
- join partita, gestione partita, nomi partecipanti, notifiche e funzioni community restano private

Geolocalizzazione:
- non usare Google API, Google Maps, Places API o geocoding esterno
- usa coordinate gia salvate per i club
- usa Geolocation API del browser solo come input opzionale dell'utente
- supporta sempre un fallback manuale per citta / CAP / provincia
- la ricerca manuale v1 deve funzionare sui dati strutturati gia persistiti del club, non su geocoding testuale o parsing opaco di indirizzi liberi
- supporta almeno un input manuale semplice e documentabile, preferibilmente una `query` unica applicata in modo case-insensitive a citta, provincia e CAP; se scegli filtri separati, restano comunque fuori scope geocoding e autocomplete esterno
- se la query manuale e assente, la directory pubblica deve avere comunque un ordinamento deterministico e non dipendere dalla geolocalizzazione browser

Visibilita delle partite open per utenti esterni:
- mostra solo partite `OPEN`
- mostra solo un orizzonte temporale breve e utile dei prossimi giorni
- se `geo.md` non definisce il numero esatto di giorni, scegli una finestra minima esplicita, semplice e documentabile, ad esempio `7` giorni, e riportala in `STATO_PLAY_6.md`
- filtro per livello pubblico
- ordinamento: prima `3/4`, poi `2/4`, poi `1/4`

Dati pubblici match da mostrare:
- giorno
- data
- orario
- livello
- stato giocatori `1/4`, `2/4`, `3/4`
- messaggio sintetico come `Manca 1 giocatore` o `Mancano 2 giocatori`

Dati che NON devono uscire nella vista pubblica:
- nomi dei giocatori
- telefoni
- note interne
- creator profile name
- chat
- dettagli interni community
- storico personale
- notifiche
- qualunque dato personale o sensibile

Identita pubblica del club:
- `club_id` resta la chiave interna
- `club_slug` resta l'identificatore pubblico univoco
- non usare mai `public_name` come identificatore univoco pubblico

## Integrazione obbligatoria col repo attuale

Lavora sui punti proprietari del comportamento, senza duplicare logica:
- `backend/app/models/__init__.py` per i metadati pubblici del club che oggi mancano
- `backend/app/services/settings_service.py` e relativo pannello admin per la gestione dei dati pubblici del club
- `backend/app/api/routers/public.py` o un router pubblico dedicato coerente per directory club e dettaglio pubblico club
- `backend/app/services/play_service.py` per un serializer/query pubblico dedicato delle partite open
- `frontend/src/App.tsx` per le nuove route pubbliche
- frontend pubblico per directory club e pagina pubblica del club

Preferenza forte di integrazione admin:
- estendi il blocco settings/admin gia esistente per i dati pubblici del club, invece di aprire una nuova area amministrativa separata, salvo bisogno tecnico concreto
- il club deve inserire questi dati in appositi campi del proprio pannello admin, dentro la UX settings gia esistente:
	- Nome club
	- indirizzo (via, piazza, ecc.)
	- CAP
	- Citta
	- Provincia
- usa naming tecnico coerente col codebase, ma lato UI admin le etichette devono essere chiare e aderenti ai campi sopra
- tutte le modifiche admin devono mantenere UX/UI coerente con quella esistente in `AdminDashboardPage` e nel blocco settings gia presente: stesso linguaggio visivo, stessa gerarchia, stessi pattern di form, validazione e feedback

Riusa esplicitamente, dove sensato:
- `Club.slug` come chiave pubblica unica gia esistente
- `Court` per derivare il numero campi invece di duplicare un contatore persistito se non serve
- `GET /api/public/config` e le superfici public gia esistenti solo dove il contratto resta coerente
- tenant resolution gia presente nel repository

Non riusare in modo improprio:
- non esporre o riciclare `/api/platform/tenants`, che e un endpoint interno protetto da platform key
- non riusare `_serialize_match` o i payload privati `/api/play` per utenti esterni
- non trasformare `/c/{club_slug}/play` in pagina pubblica ibrida

## Metadati pubblici minimi del club

Chiudi un set minimo e reale di dati pubblici per la scoperta del club.

Almeno:
- `public_name`
- `slug`
- indirizzo pubblico sintetico
- CAP
- citta
- provincia
- coordinate lat/lng quando disponibili
- contatto pubblico gia esistente o derivabile
- indicazione booleana se la community e aperta a nuovi ingressi

Mapping esplicito richiesto tra admin e dominio dati:
- `Nome club` -> `public_name` gia esistente
- `indirizzo (via, piazza, ecc.)` -> campo strutturato di indirizzo pubblico sintetico
- `CAP` -> campo strutturato dedicato
- `Citta` -> campo strutturato dedicato
- `Provincia` -> campo strutturato dedicato

Regola esplicita di lettura e restituzione:
- il club inserisce questi valori dal pannello admin/settings
- il backend li persiste come source of truth strutturata del club
- gli endpoint pubblici di directory e dettaglio club devono leggerli da questi campi strutturati
- i payload pubblici devono restituire all'utente esterno almeno nome club, indirizzo pubblico, CAP, citta e provincia quando valorizzati

Strategia esplicita per il source of truth v1:
- i campi strutturali usati da directory, nearby e ricerca manuale devono vivere preferibilmente nel dominio `Club`, non in un blob JSON di `AppSetting`
- `AppSetting` puo restare utile per toggle o copy configurabile, ma non deve diventare il contenitore principale dell'identita pubblica del club
- evita costanti hardcoded lato frontend o cataloghi club separati dal database reale

Campi strutturali preferiti nel modello `Club` per la v1, con naming coerente col codebase:
- indirizzo pubblico sintetico obbligatorio per la discovery manuale del club
- CAP obbligatorio
- citta pubblica obbligatoria
- provincia pubblica obbligatoria
- latitudine e longitudine opzionali ma sempre come coppia coerente
- booleano esplicito che indichi se la community e aperta a nuovi ingressi

Regola pratica per la v1:
- il numero campi deve essere derivato dai campi del club, non inserito manualmente salvo necessita tecnica strettamente motivata
- se un club non ha coordinate, deve poter comparire nella ricerca manuale ma non deve produrre un calcolo distanza falso
- se la distanza non e calcolabile, non inventarla: omettila o marcalo esplicitamente nel payload pubblico
- non usare un singolo `location_text` libero come unica sorgente di verita per ricerca e nearby
- non derivare citta, provincia o CAP parsando a runtime l'indirizzo libero
- valida le coordinate come coppia: entrambe presenti oppure entrambe assenti

Preferenza architetturale:
- preferisci mettere i metadati pubblici strutturali del club nel dominio `Club` o in una struttura strettamente coerente con esso
- se il repo richiede una migration, falla esplicita e coerente con Alembic gia in uso

## Routing corretto da chiudere

Struttura target:
- `/clubs`
- `/clubs/nearby`
- `/c/{club_slug}`
- `/c/{club_slug}/play`

Regola di compatibilita:
- non rompere il routing esistente su `/'`
- non rompere il routing esistente su `/c/{club_slug}/play`
- se mantieni `/'` come entrypoint booking pubblico corrente, fallo restare compatibile; le nuove route di discovery devono essere additive e non distruttive

## API pubbliche minime richieste

Chiudi una superficie pubblica chiara e separata dalle API private/community.

Minimo richiesto:
- elenco club pubblici
- elenco/ordinamento club vicini quando e disponibile una posizione utente valida
- ricerca manuale per citta / CAP / provincia
- dettaglio pubblico del club per `club_slug`
- vista pubblica leggera delle partite open del club

Contratto minimo preferito per ridurre ambiguita:
- un endpoint elenco pubblico che supporti la ricerca manuale sui campi strutturati del club con un input semplice e stabile
- un endpoint nearby che accetti coordinate utente esplicite e restituisca distanza solo quando realmente calcolabile
- il payload directory deve riusare gli stessi concetti pubblici del dettaglio club, senza versioni divergenti di citta, zona, contatto o stato community

Preferenza implementativa:
- preferisci calcolo distanza e ordinamento lato backend per avere output deterministico, testabile e coerente
- se usi il browser per ottenere la posizione, limita il frontend a raccogliere lat/lng e demandare al backend il ranking pubblico
- per la ricerca manuale non introdurre ranking opaco: privilegia match deterministici e documentabili su citta, provincia e CAP

## UX minima richiesta

Directory club pubblica:
- lista club con nome, indirizzo sintetico, CAP, citta, provincia, distanza se disponibile, numero campi, contatto pubblico minimo e CTA verso la pagina pubblica del club
- azione `Trova club vicino a me`
- fallback manuale sempre disponibile senza permessi browser
- feedback chiaro se l'utente nega la geolocalizzazione

Pagina pubblica del club:
- header pubblico con identita del club
- dati pubblici minimi del club, inclusi nome, indirizzo, CAP, citta e provincia quando valorizzati
- indicazione sintetica se la community accetta nuovi ingressi
- lista leggera delle partite open filtrabile per livello
- CTA verso la community del club o accesso al club

Regole UX da rispettare:
- un utente esterno non deve poter eseguire join direttamente dalla pagina pubblica del club
- la CTA deve portare verso il punto corretto di ingresso alla community, senza sbloccare funzioni private nella pagina pubblica
- non serve una mappa complessa in v1
- non serve un motore di geocoding avanzato
- la directory pubblica, la pagina pubblica del club e l'estensione del pannello admin devono mantenere UX/UI coerente con quella gia presente nel frontend, senza introdurre un design system parallelo o pattern visivi incoerenti

## Vincoli tecnici specifici emersi dal repo reale

- `backend/app/main.py` oggi blocca `geolocation` via `Permissions-Policy`; se la Fase 6 usa davvero la Geolocation API del browser, aggiorna questo punto in modo coerente e minimale
- `frontend/src/App.tsx` oggi non ha ancora route pubbliche `/clubs`, `/clubs/nearby`, `/c/:clubSlug`
- `backend/app/schemas/public.py` oggi non espone ancora i campi pubblici utili per directory club e dettaglio club
- `backend/app/services/play_service.py` oggi espone partecipanti e `creator_profile_name`, quindi serve un serializer pubblico dedicato e non una semplice ri-esposizione del payload community

## Test richiesti

Backend, almeno:
- persistenza e lettura dei nuovi dati pubblici minimi del club
- ricerca manuale case-insensitive per citta / CAP / provincia sui campi strutturati del club
- ordinamento nearby con distanza corretta e deterministica quando lat/lng sono disponibili
- comportamento corretto per club senza coordinate
- validazione della coppia lat/lng del club: entrambe valorizzate o entrambe assenti
- dettaglio pubblico del club senza leak di dati interni
- restituzione corretta di nome club, indirizzo, CAP, citta e provincia nei payload pubblici quando valorizzati
- vista pubblica partite open: solo `OPEN`, solo orizzonte futuro scelto, filtro livello, ordinamento `3/4 -> 2/4 -> 1/4`
- assenza di dati personali nei payload pubblici match
- nessuna regressione sulle API pubbliche gia esistenti del booking

Frontend, se toccato:
- test mirati per `/clubs` con ricerca manuale
- test mirati per fallback quando la geolocalizzazione browser viene negata o non disponibile
- test mirati per `/c/:clubSlug` con filtro livello e rendering delle partite open in forma pubblica
- test espliciti che confermino assenza di nomi giocatori e dettagli interni nella vista pubblica
- test mirati sul pannello admin per i nuovi campi `Nome club`, `indirizzo`, `CAP`, `Citta`, `Provincia` e per il salvataggio coerente nel blocco settings esistente
- test di routing che confermino che `/'` e `/c/:clubSlug/play` continuano a funzionare
- build frontend finale

Per i test backend usa il Python del repo:
- `D:/Padly/PadelBooking/.venv/Scripts/python.exe`

## Verifica di fine fase obbligatoria

La fase passa solo se:
- un utente esterno puo scoprire i club pubblici senza entrare nella community
- nearby e ricerca manuale funzionano senza Google API
- la ricerca manuale funziona anche senza geolocation browser e senza geocoding testuale
- la pagina pubblica del club esiste davvero su `/c/{club_slug}`
- la community privata resta separata su `/c/{club_slug}/play`
- la vista pubblica delle partite open e utile ma non espone dati personali
- il routing esistente di booking pubblico e community privata non viene rotto
- i test mirati sono verdi

## File stato da produrre obbligatoriamente

Crea `STATO_PLAY_6.md` con almeno:
- esito `PASS` / `FAIL`
- route pubbliche introdotte backend/frontend
- metadati pubblici club introdotti
- strategia distanza adottata
- strategia fallback manuale adottata
- finestra temporale effettiva scelta per le partite open pubbliche
- regole finali di visibilita pubblica vs community privata
- file principali toccati backend/frontend
- validazioni realmente eseguite con esito
- `## Note operative finali`
- `## Backlog esplicito per una futura v2 notifiche mirate`

Le ultime due sezioni devono restare coerenti con `STATO_PLAY_5.md`:
- non cancellarle
- non riscriverle in modo scollegato dalle fasi precedenti
- se in Fase 6 non cambiano, riportalo esplicitamente

## Fuori scope approvato

Questa fase non deve assorbire:
- Google Maps, Places API, geocoding esterno o mappe avanzate
- join diretto pubblico delle partite senza passaggio community
- chat pubblica, profili pubblici dei player o dettagli personali dei partecipanti
- revoca/rotazione share token, gia separata in `revoca_token.md`
- KPI/reportistica dedicata o source separato per booking nate da `/play`, gia separati in `kpi.md`

Questi temi non devono bloccare il `PASS` della Fase 6, salvo priorita esplicita diversa richiesta dal prodotto.