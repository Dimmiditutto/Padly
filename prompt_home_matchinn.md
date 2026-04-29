# HOME_MATCHINN

Agisci come un Senior Full Stack Engineer esperto in FastAPI, SQLAlchemy 2.x, Pydantic 2, React 18, TypeScript, Vite, Tailwind e UX/UI product-oriented.

Stai lavorando nel repository PadelBooking gia esistente. Devi implementare la home Matchinn descritta in `home_matchinn.md` in coerenza con il codice attuale, con patch minime, senza cambiare la business logic di booking pubblico, Play, OTP, inviti, notifiche, ranking pubblico, tenant resolution o privacy.

Prima di proporre o modificare codice, leggi davvero questi file e riusa cio che esiste gia:

- `prompt_engineering.md`
- `home_matchinn.md`
- `STATO_GEOHOME.md`
- `STATO_PLAY_FINAL.md`
- `frontend/src/App.tsx`
- `frontend/src/pages/PublicBookingPage.tsx`
- `frontend/src/pages/ClubDirectoryPage.tsx`
- `frontend/src/pages/PublicClubPage.tsx`
- `frontend/src/pages/PlayAccessPage.tsx`
- `frontend/src/pages/PlayPage.tsx`
- `frontend/src/services/publicApi.ts`
- `frontend/src/services/playApi.ts`
- `frontend/src/types.ts`
- `frontend/src/utils/play.ts`
- `backend/app/models/__init__.py`
- `backend/app/api/routers/play.py`
- `backend/app/api/routers/public.py`
- `backend/app/schemas/play.py`
- `backend/app/schemas/public.py`
- `backend/app/services/play_service.py`
- `backend/app/services/public_discovery_service.py`

## Contesto reale del repository

Non partire da zero. Nel codice attuale esistono gia queste superfici e questi vincoli reali:

- la root `/` rende oggi `PublicBookingPage`, quindi la home attuale e booking-first e non Matchinn-first;
- esistono gia le route pubbliche `/clubs`, `/clubs/nearby`, `/c/:clubSlug`;
- esistono gia le route community `/c/:clubSlug/play`, `/c/:clubSlug/play/access`, `/c/:clubSlug/play/invite/:token`, `/c/:clubSlug/play/matches/:shareToken`;
- esiste gia la dashboard admin su `/admin`;
- esiste gia il flusso OTP di accesso community in `PlayAccessPage` e nel backend Play;
- esistono gia discovery pubblica, watchlist e feed persistente pubblico;
- esistono gia ranking pubblico e contatori 3/4, 2/4, 1/4 lato directory e club pubblici, introdotti e validati da `STATO_GEOHOME.md`;
- esistono gia notifiche private `/play`, endpoint `GET /api/play/me` e accesso cookie-based, validati da `STATO_PLAY_FINAL.md`;
- la sessione Play attuale e club-specifica: i token `PlayerAccessToken` sono legati al `club_id`;
- il cookie Play attuale usa un nome unico `padel_play_session`, quindi oggi il browser non rappresenta nativamente piu community attive in parallelo;
- non esiste oggi un account Matchinn globale, non esiste login/password globale e non esiste una home app-level separata dal booking.

Quindi la feature va costruita come estensione minima e coerente del sistema attuale, non come re-platforming auth o redesign del dominio Play.

## Obiettivo operativo

Implementa la home Matchinn descritta in `home_matchinn.md` in modo coerente con il repository attuale.

La nuova home deve diventare l hub operativo di prodotto e deve permettere:

1. mostrare `Le tue community` per l utente gia riconosciuto nel browser corrente;
2. mostrare `Trova campi vicino a te` con geolocalizzazione esplicita o ricerca manuale;
3. mostrare una vista leggera di `Partite aperte vicino a te` senza trasformare la home in una playboard completa;
4. esporre un accesso secondario a `Area club` per admin o gestori;
5. preservare integralmente il booking pubblico esistente, spostandolo o rendendolo raggiungibile in modo esplicito senza alterarne la logica.

## Principi prodotto da mantenere

Integra esplicitamente questi principi, gia definiti in `home_matchinn.md`:

- la home Matchinn non e la home di un singolo club;
- la home Matchinn e un hub operativo di prodotto, non una landing marketing e non una dashboard complessa;
- community = azione;
- pubblico = scoperta;
- l accesso alla community in V1 deve essere self-service via OTP;
- niente login/password nella V1;
- niente preferiti server-side nella V1;
- l invito del club continua a esistere, ma non deve essere l unico meccanismo di ingresso;
- mobile-first e gerarchia chiara: prima community, poi discovery, poi partite, poi area club.

## Regole strutturali da rendere esplicite nel codice e nel prompt

- `club_slug` resta l identificatore pubblico canonico per routing e linking;
- non introdurre route alternative che indeboliscono le convenzioni attuali di club e Play;
- il booking pubblico esistente deve restare funzionante, ma non deve piu occupare semanticamente la root `/` se la nuova home Matchinn va su `/`;
- i confini tra pubblico e community privata vanno preservati;
- i match pubblici restano view-only leggeri;
- la CTA pubblica deve portare a scheda club o accesso community, non a join privati mascherati;
- se il documento ideale e il codice reale divergono, scegli la soluzione piu piccola, coerente e verificabile, dichiarando il compromesso in output.

## Vincoli non negoziabili

- non cambiare la business logic di booking pubblico, Play, OTP, inviti, group access, join match, notifiche o ranking pubblico gia validato;
- non introdurre refactor ampi non richiesti;
- non creare un account Matchinn globale con password;
- non introdurre nuove dipendenze esterne se non strettamente necessarie;
- non esporre mai nomi player, telefono, email, chat o dati interni nella parte pubblica;
- non rompere `STATO_GEOHOME.md` o `STATO_PLAY_FINAL.md`;
- non rimuovere gli attuali flussi `/c/:clubSlug/play/access`, `/c/:clubSlug/play/invite/:token` o `/c/:clubSlug/play/matches/:shareToken`;
- non introdurre una feature separata di magic link di recupero accesso in questa fase;
- non introdurre preferiti server-side in questa fase;
- non inventare una tabella `PlayerClubMembership` o un nuovo modello globale se il repository puo supportare la V1 con un estensione piu piccola e backward-safe;
- ogni nuova API, se davvero necessaria, deve essere read-only o strettamente di supporto alla home, con naming minimale e test mirati.

## Strategia richiesta

### 1. Home Matchinn come nuova root, senza rompere il booking esistente

Usa `frontend/src/App.tsx` come punto di controllo del routing reale.

Oggi `/` punta a `PublicBookingPage`. La nuova home Matchinn deve vivere su `/`, quindi devi:

- introdurre una pagina dedicata per la nuova home prodotto Matchinn;
- spostare o rendere raggiungibile `PublicBookingPage` tramite una route esplicita e coerente, preferibilmente semplice e leggibile;
- preservare tenant context, query param, booking flow, payment status e pagine di cancel/success/error;
- aggiornare solo i link e i testi strettamente necessari che oggi assumono implicitamente che `/` sia la home booking;
- evitare una riscrittura diffusa della navigazione se bastano pochi aggiustamenti mirati.

Se esiste piu di una strategia possibile, scegli quella con meno impatto sui flussi attuali e piu facilmente testabile.

### 2. Blocco `Le tue community` senza reinventare l autenticazione

Questo e il punto piu delicato e deve essere affrontato partendo dal vincolo reale del repository:

- i token Play attuali sono club-specifici;
- il cookie attuale ha nome unico `padel_play_session`;
- non esiste oggi una vera sessione multi-community nativa.

Quindi non devi introdurre un account globale Matchinn da zero.

Devi invece verificare e implementare la minima estensione coerente con la V1 per rendere possibile `Le tue community`.

Linee guida obbligatorie:

- preserva `Player`, `PlayerAccessToken`, `PlayerAccessChallenge`, invite flow, group link flow e OTP flow attuali;
- non cambiare il significato del token Play: autentica sempre un player gia modellato nel sistema attuale;
- se oggi il cookie unico impedisce piu community attive nello stesso browser, estendi la strategia di sessione nel modo piu piccolo e backward-safe possibile;
- preferisci una soluzione tecnica che permetta al browser di mantenere piu sessioni club-specifiche senza introdurre password, identita globale o nuove regole di business;
- se serve un endpoint read-only per alimentare `Le tue community`, introduci un endpoint minimo dedicato alla home, che derivi i club dell utente da sessioni Play valide gia presenti nel browser;
- se il browser non ha alcuna sessione community valida, mostra lo stato anonimo con CTA a OTP self-service, non un blocco vuoto.

Ogni card community deve mostrare almeno:

- nome club;
- numero partite aperte utili o segnale riassuntivo minimo;
- miglior segnale visibile tipo `Manca 1 giocatore` se disponibile senza nuova logica complessa;
- CTA `Entra` verso `/c/:clubSlug/play`.

Non trasformare `Le tue community` in un nuovo sistema di membership business.
Se per la V1 la lista e derivata dalle sessioni Play valide del browser corrente, va bene, purche sia dichiarato chiaramente e coerente con `home_matchinn.md`.

### 3. Discovery club vicino a te: riuso del pubblico gia esistente

Per `Trova campi vicino a te` devi riusare il piu possibile le superfici gia validate in `STATO_GEOHOME.md`.

Indicazioni pratiche:

- riusa `ClubDirectoryPage`, `PublicClubPage`, `publicApi` e i contratti pubblici esistenti quando possibile;
- riusa geolocalizzazione esplicita e fallback manuale gia presenti;
- mantieni il modello pubblico read-only;
- se la home richiede una card sintetica diversa da quella della directory, valuta una piccola estrazione condivisa solo se davvero utile;
- non creare una seconda directory parallela.

Ogni card club in home deve mostrare almeno:

- nome club;
- citta o zona;
- distanza se disponibile;
- numero partite aperte o segnale riassuntivo gia derivabile;
- miglior stato pubblico disponibile, preferendo i contatori 3/4, 2/4, 1/4 gia esistenti;
- CTA principale verso `/c/:clubSlug`.

Mostra lo sport solo se e gia disponibile nel modello o banalmente derivabile, senza introdurre nuove entita o contratti sproporzionati solo per questa etichetta.

### 4. Partite aperte vicino a te: aggiungi solo il minimo che manca davvero

La home deve mostrare una vista leggera delle partite aperte vicino a te, ma oggi il repository non espone ancora una vera lista cross-club di match pubblici vicino all utente.

Quindi:

- verifica prima se esiste gia un endpoint o una combinazione di endpoint riusabile senza workaround fragili lato client;
- se non esiste, introduci un solo endpoint read-only minimale per la home, riusando le regole gia esistenti di visibilita pubblica e finestra temporale dei match open;
- riusa dove possibile `list_public_open_matches`, ranking pubblico e discovery preferences esistenti;
- se l utente ha una discovery session pubblica con preferenze livello o posizione, sfruttala;
- se non esiste una discovery session, mantieni un fallback utile e semplice.

La card partita deve mostrare solo:

- data;
- ora;
- livello;
- stato 3/4, 2/4, 1/4;
- club;
- distanza;
- CTA.

Ordinamento richiesto:

- prima 3/4 compatibili con livello utente;
- poi 2/4 compatibili con livello utente;
- poi 1/4 compatibili con livello utente;
- poi distanza;
- poi prossimita temporale.

CTA consigliata:

- `Apri club` per utente anonimo;
- `Entra e gioca` solo se il browser ha gia una sessione community valida per quel club.

Non esporre mai nomi player, dettagli interni, share token, note private o azioni private direttamente dalla card pubblica della home.

### 5. Area club: utility secondaria, non asse portante

L accesso admin deve restare secondario.

Indicazioni obbligatorie:

- usa label del tipo `Area club`;
- mantieni `/admin` come destinazione primaria attuale;
- posizione secondaria coerente con home prodotto, non hero primaria;
- nessuna semantica tecnica o amministrativa troppo dominante per l utente finale.

### 6. UX/UI da mantenere coerente

Segui il linguaggio gia presente in `PublicBookingPage`, `ClubDirectoryPage`, `PublicClubPage`, `PlayAccessPage` e `PlayPage`.

Indicazioni obbligatorie:

- usa componenti gia presenti come `SectionCard`, `AlertBanner`, `LoadingBlock` quando appropriato;
- mantieni palette, spaziature, bordi, gerarchia visiva e stile dei pulsanti coerenti con il resto;
- riduci l effetto `troppe schede tutte uguali`: la gerarchia deve essere piu netta di quella attuale della root booking;
- evita layout nuovi troppo distanti dalla UI attuale;
- niente hero marketing ridondanti;
- niente dark mode forzata o temi scollegati dal resto;
- niente home che sembri una dashboard tecnica;
- ottimizza leggibilita mobile prima del desktop;
- se il booking pubblico viene spostato su route dedicata, assicurati che la CTA verso il booking resti chiara ma non dominante sulla nuova home Matchinn.

## Fasi operative obbligatorie

### Fase 1 - Verifica contesto e delta reale

Obiettivo:

- verificare che i file e le route indicate esistano davvero;
- confermare cosa e gia disponibile e cosa manca solo a livello di orchestrazione, routing o contratto dati;
- individuare esplicitamente il vincolo del cookie Play unico e scegliere la minima strategia compatibile.

Attivita:

- mappa i file reali coinvolti;
- conferma che `App.tsx` punta oggi `/` a `PublicBookingPage`;
- conferma che esistono `/clubs`, `/clubs/nearby`, `/c/:clubSlug`, `/c/:clubSlug/play`, `/c/:clubSlug/play/access`, `/admin`;
- conferma che `STATO_GEOHOME.md` e `STATO_PLAY_FINAL.md` siano `PASS` e identificane i contratti gia chiusi;
- conferma il modello sessione Play attuale: cookie unico, token club-specifico;
- definisci il delta minimo necessario per supportare `Le tue community` senza reingegnerizzare auth o business logic.

Output atteso:

- gap analysis concreta, non teorica;
- lista precisa dei file da toccare;
- decisione esplicita su come rendere possibile la home multi-community v1 nel browser corrente;
- decisione esplicita su dove spostare o come rendere raggiungibile il booking pubblico esistente.

Verifica finale:

- se il repository supporta gia la maggior parte della feature, non reinventare architetture;
- se il vincolo del cookie unico e il blocco principale, risolvi quello con l estensione piu piccola e verificabile.

### Fase 2 - Routing e shell della nuova home

Obiettivo:

- introdurre la nuova home Matchinn sulla root `/` e preservare il booking pubblico.

Attivita:

- crea la nuova pagina home Matchinn;
- aggiorna `frontend/src/App.tsx`;
- mantieni `PublicBookingPage` raggiungibile tramite route esplicita;
- aggiorna i link interni strettamente necessari che oggi puntano a `/` come home booking;
- preserva payment status e flussi gia esistenti.

Output atteso:

- nuova root Matchinn coerente con `home_matchinn.md`;
- booking pubblico ancora raggiungibile e invariato nella logica.

Verifica finale:

- nessuna regressione evidente su route Play, admin e booking;
- nessuna rottura delle route canoniche di invito, accesso o partita condivisa.

### Fase 3 - Community home state e sessioni browser

Obiettivo:

- rendere possibile `Le tue community` nel browser corrente con la minima estensione compatibile.

Attivita:

- implementa o estendi la gestione sessione solo quanto basta a supportare piu community attive sul browser corrente;
- se serve, aggiungi un endpoint home read-only per elencare le community riconosciute del browser;
- riusa i token Play e i modelli gia presenti;
- non cambiare OTP, inviti, group link o join logic;
- gestisci stato anonimo e stato riconosciuto nella nuova home.

Output atteso:

- blocco `Le tue community` funzionante;
- stato anonimo con CTA OTP coerente;
- strategia esplicita e testata per il supporto a piu community nello stesso browser.

Verifica finale:

- nessun account globale introdotto;
- nessuna regressione del Play esistente;
- nessun cambio di semantica del token Play.

### Fase 4 - Discovery club e partite aperte in home

Obiettivo:

- portare in home discovery club e partite aperte leggere, riusando il piu possibile il perimetro pubblico gia validato.

Attivita:

- riusa contratti e UI gia presenti per club vicini;
- implementa la vista leggera `Partite aperte vicino a te`;
- se necessario, aggiungi un solo endpoint read-only minimale per partite cross-club in home;
- rispetta visibilita pubblica, ordinamento richiesto e privacy.

Output atteso:

- blocco club vicini coerente e leggibile;
- blocco partite aperte leggere utile ma non invasivo;
- CTA corrette per utente anonimo e utente gia riconosciuto.

Verifica finale:

- nessun dato privato esposto;
- nessuna duplicazione incoerente di directory o club page;
- ordinamento partite coerente con il prodotto.

### Fase 5 - Area club, test e chiusura

Obiettivo:

- chiudere la home Matchinn con verifiche strette e stato di fase riusabile.

Attivita:

- aggiungi o aggiorna test backend e frontend per i nuovi blocchi e per il routing;
- valida la preservazione dei contratti gia chiusi da geohome e play final;
- esegui i test mirati strettamente rilevanti;
- esegui build frontend se hai toccato route e piu superfici UI;
- crea o aggiorna `STATO_HOME_MATCHINN.md`.

Verifica finale:

- la nuova home e coerente con `home_matchinn.md` e con il repository reale;
- il booking pubblico esistente e ancora raggiungibile e funzionante;
- i flussi OTP e community restano integri;
- la separazione pubblico/community resta intatta;
- la soluzione scelta per `Le tue community` e la piu piccola e verificabile.

## Regole implementative aggiuntive

- preferisci patch piccole e locali;
- evita estrazioni o componentizzazioni inutili se il beneficio e minimo;
- non rompere i contratti pubblici gia introdotti da geohome se non strettamente necessario;
- se aggiungi un endpoint per la home, tienilo minimale e mirato;
- non cambiare naming delle route canoniche gia consolidate;
- non cambiare la semantica di `/c/:clubSlug`, `/c/:clubSlug/play`, `/c/:clubSlug/play/access`;
- non toccare la business logic delle notifiche Play o del ranking pubblico se non per leggere e riusare dati gia esposti;
- se il documento `home_matchinn.md` richiede un modello ideale piu grande del repository attuale, implementa la miglior approssimazione V1 coerente e dichiaralo esplicitamente nell output finale.

## Output finale obbligatorio

Produci l output finale in questo ordine esatto:

## 1. Prerequisiti verificati
- elenco PASS / FAIL reale

## 2. Mappa del repository rilevante
- file reali trovati e superfici toccate

## 3. Gap analysis della fase
- cosa manca oggi rispetto all obiettivo

## 4. File coinvolti
- file creati o modificati

## 5. Implementazione
- spiegazione concreta delle patch applicate

## 6. Migrazioni e backfill
- nome migrazione oppure `NOT APPLICABLE`
- impatto su tenant e dati esistenti

## 7. Test aggiunti o modificati
- elenco preciso

## 8. Verifica di fine fase
- controlli eseguiti
- esito `PASS` / `FAIL` / `NOT APPLICABLE`
- criticita residue
- gate finale:
  - `FASE VALIDATA - si puo procedere`
  - `FASE NON VALIDATA - non procedere`

## 9. File stato della fase
- crea o aggiorna `STATO_HOME_MATCHINN.md`
- il file stato deve essere compatto, fattuale e leggibile dalla fase successiva

## Controllo qualita finale

Prima di chiudere il lavoro verifica esplicitamente che:

- la soluzione sia coerente con il codice attuale e non con un modello teorico;
- non siano stati introdotti cambi di business logic in booking, Play, OTP, inviti, notifiche o ranking pubblico;
- la nuova home su `/` sia davvero Matchinn-first e non una variazione cosmetica della vecchia booking home;
- il booking pubblico resti raggiungibile e funzionante;
- `Le tue community` non richieda un account globale o password nella V1;
- la strategia scelta per la multi-community nel browser corrente sia esplicita, piccola e testata;
- i blocchi club vicini e partite aperte riusino davvero il perimetro pubblico gia esistente quando possibile;
- nessun dato privato o community-only venga esposto nella home pubblica;
- l accesso admin resti secondario;
- siano indicati chiaramente file toccati, test eseguiti, compromessi scelti e limiti residui.

Se trovi un conflitto tra `home_matchinn.md` e il comportamento reale del repository, scegli la soluzione piu piccola, coerente e verificabile, senza inventare nuove architetture e senza usare il conflitto come pretesto per allargare lo scope.