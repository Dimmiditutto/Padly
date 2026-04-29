# GEOHOME

Agisci come un Senior Full Stack Engineer esperto in FastAPI, SQLAlchemy 2.x, Pydantic 2, React 18, TypeScript, Vite, Tailwind e UX/UI product-oriented.

Stai lavorando nel repository PadelBooking gia esistente. Devi implementare la feature richiesta in coerenza con il codice attuale, con patch minime, senza cambiare la business logic e senza rompere i confini pubblico/community gia presenti.

Prima di proporre o modificare codice, leggi davvero questi file e riusa cio che esiste gia:

- `prompt_engineering.md`
- `geo.md`
- `frontend/src/pages/PublicBookingPage.tsx`
- `frontend/src/pages/ClubDirectoryPage.tsx`
- `frontend/src/pages/PublicClubPage.tsx`
- `frontend/src/services/publicApi.ts`
- `frontend/src/types.ts`
- `frontend/src/utils/play.ts`
- `backend/app/api/routers/public.py`
- `backend/app/schemas/public.py`
- `backend/app/services/play_service.py`

## Contesto reale del repository

Non partire da zero. Nel codice attuale esistono gia queste superfici:

- directory pubblica club: `/clubs`
- directory pubblica geolocalizzata: `/clubs/nearby`
- pagina pubblica del club: `/c/:clubSlug`
- pagina community del club: `/c/:clubSlug/play`
- endpoint backend gia presenti per club pubblici e club vicini
- filtro livello e lista `open_matches` gia presenti nella pagina pubblica del club
- ordinamento pubblico delle partite gia coerente con priorita 3/4, 2/4, 1/4
- form pubblico di contatto club gia esistente
- discovery/watchlist pubblica gia esistenti

Quindi la feature va costruita estendendo queste superfici, non creando un flusso parallelo.

## Obiettivo operativo

Implementa la feature seguente in modo coerente con il repository attuale:

1. aggiungere nella home pubblica una sezione con i 10 club piu vicini
2. per ogni club mostrare una card sintetica con segnali utili per capire se vale la pena aprire la scheda del club
3. usare come scheda interna del club la pagina pubblica gia esistente `/c/:clubSlug`, migliorandola senza cambiare la logica di business
4. nella scheda del club mostrare prima le partite da chiudere 3/4, poi le 2/4, poi le 1/4
5. dare all utente esterno una CTA coerente:
   - community aperta: accesso alla community del club
   - community chiusa: richiesta accesso alla community del club

## Principi prodotto da mantenere

Integra nel lavoro questi principi espliciti, gia definiti a livello di prodotto:

- il club puo essere pubblico e visibile anche a utenti esterni
- la community del club resta privata o chiusa dove previsto
- pubblico = scoperta
- community = azione
- la pagina pubblica del club deve aiutare un utente esterno a capire rapidamente se vale la pena entrare nella community del club
- la feature deve essere utile soprattutto per utenti in viaggio, in vacanza o fuori dal proprio club abituale
- la home e la discovery devono valorizzare il network dei club presenti, non solo il singolo club attivo

## Regole strutturali da rendere esplicite nel codice e nel prompt

- il nome del club non e l identificatore pubblico univoco
- usa sempre `club_id` come chiave interna e `club_slug` come identificatore pubblico univoco
- non introdurre route alternative che indeboliscono la convenzione attuale:
  - `/clubs`
  - `/clubs/nearby`
  - `/c/:clubSlug`
  - `/c/:clubSlug/play`
- anche se in alcuni ambienti esiste un solo club, la soluzione deve restare club-specifica e network-aware

## Vincoli non negoziabili

- non introdurre refactor ampi non richiesti
- non cambiare la business logic di Play, OTP, join match, visibilita community o privacy
- non esporre mai nomi player, telefono, chat o dati interni nella parte pubblica
- non creare nuove dipendenze esterne
- non usare Google Maps API o servizi esterni per la geolocalizzazione base
- riusa browser Geolocation API e le superfici pubbliche gia presenti
- mantieni esplicitamente il modello: club pubblico visibile, community privata/chiusa
- mantieni UI e UX coerenti con il design attuale: stessa grammatica visuale, stessi componenti dove possibile, stessa gerarchia, stesso tono
- mantieni mobile-first e responsive
- non creare una nuova route per la scheda club: riusa `/c/:clubSlug`
- non introdurre nuove entita di business o nuovi workflow di approvazione se non strettamente necessari
- se la community e chiusa, per la richiesta accesso riusa il form/flow pubblico gia esistente invece di inventare un nuovo backend di approvazione
- non introdurre onboarding self-service da link partita o flussi nuovi se non gia supportati realmente dal repository

## Strategia richiesta

### 1. Home pubblica: estensione minima e coerente

Usa `frontend/src/pages/PublicBookingPage.tsx` come home pubblica reale.

Devi aggiungere una sezione secondaria ma visibile, senza disturbare il flusso booking principale. La home deve continuare ad avere come primo focus la prenotazione pubblica del club attivo, ma deve offrire anche una discovery geolocalizzata del network.

Indicazioni pratiche:

- aggiungi una sezione del tipo `Club vicini a te` o equivalente, coerente con il copy attuale
- usa l endpoint gia esistente `/public/clubs/nearby` tramite `listPublicClubsNearby`
- non introdurre un endpoint nuovo solo per la home se non strettamente necessario
- per la v1 e accettabile mostrare in home solo i primi 10 risultati della lista ordinata per distanza
- gestisci geolocalizzazione negata o indisponibile con fallback sobrio e utile
- offri sempre un percorso alternativo manuale verso `/clubs` o `/clubs/nearby`
- il fallback manuale deve essere coerente con quanto gia previsto dal prodotto: ricerca per citta, CAP o provincia dentro la directory pubblica, senza introdurre servizi esterni
- non rendere invasivo il prompt di geolocalizzazione: evita UX aggressiva o bloccante

Ogni card club in home deve mostrare almeno:

- nome club
- distanza, se disponibile
- citta/zona sintetica
- numero campi
- eventuale contatto pubblico solo se gia disponibile nei dati e se resta coerente con la densita informativa della card
- stato community aperta/chiusa
- contatori partite pubbliche da chiudere:
  - 3/4
  - 2/4
  - 1/4
- CTA principale verso la scheda pubblica del club `/c/:clubSlug`

La home geolocalizzata deve anche far capire implicitamente che:

- i club presenti nell app sono scopribili pubblicamente
- il network ha valore anche fuori dal club abituale
- la scheda club e il punto corretto per valutare se entrare o richiedere accesso

### 2. Estensione contratti dati senza toccare la business logic

Per evitare chiamate multiple inutili dal frontend, estendi il summary pubblico del club con campi derivati minimi e backward-compatible.

Preferisci aggiungere campi flat a `PublicClubSummary`, ad esempio:

- `open_matches_three_of_four_count`
- `open_matches_two_of_four_count`
- `open_matches_one_of_four_count`

Questi campi devono essere:

- derivati dai match pubblici gia visibili oggi
- calcolati con la stessa finestra temporale e le stesse regole di visibilita pubblica gia esistenti
- senza nuove tabelle
- senza nuove colonne database
- senza migrazioni se non davvero inevitabili

Non cambiare il significato di `open_matches`, `recent_open_matches_count`, `public_activity_score` o `public_activity_label`. Puoi solo aggiungere dati derivati utili alla presentazione.

### 3. Scheda interna del club: riuso della pagina pubblica esistente

La richiesta `pagina/scheda interna` va implementata riusando `frontend/src/pages/PublicClubPage.tsx`, non creando una nuova route.

Intervieni cosi:

- mantieni il filtro per livello gia presente
- mantieni la privacy attuale della vista pubblica
- trasforma la sezione `Partite open del club` in una sezione piu orientata a chiudere match, con copy coerente tipo `Partite da chiudere`
- raggruppa o evidenzia le partite nell ordine:
  - 3/4
  - 2/4
  - 1/4
- se una categoria non ha match, non forzare rumore visivo inutile
- non cambiare il criterio di ordinamento di business se e gia corretto; riusa quello esistente e lavora soprattutto sulla presentazione

La vista pubblica del match deve restare sintetica e pubblica:

- giorno
- data
- orario
- livello
- campo
- stato `1/4`, `2/4`, `3/4`
- messaggio sintetico tipo `Manca 1 giocatore`, `Mancano 2 giocatori`

La scheda pubblica del club deve rendere evidente questo scopo:

- capire se il club ha partite aperte
- capire se ci sono partite compatibili con il livello dell utente
- capire se il club e interessante per lui
- capire se ha senso entrare nella community per agire

Non mostrare:

- recapiti
- dettagli interni community
- join diretto privato dalla vista pubblica
- storico personale
- notifiche private
- informazioni riservate del club

Mostra:

- Nome partecipanti delle partite

### 4. CTA community o richiesta accesso

Mantieni il comportamento coerente con lo stato del club:

- se `is_community_open` e vero, la CTA principale puo portare a `/c/:clubSlug/play`
- se `is_community_open` e falso, la CTA principale non deve simulare un ingresso automatico: deve riusare il form pubblico gia esistente come `Richiedi accesso alla community`

Le CTA devono restare dentro questo perimetro:

- `Entra nella community`
- `Accedi al club`
- `Richiedi accesso`

Usa la label piu coerente con lo stato del club e con il copy gia presente nelle superfici attuali.

Questa parte e importante:

- non creare un nuovo workflow backend di approval
- non creare nuove entita tipo membership request se non strettamente necessario
- riusa `createPublicClubContactRequest` e la UI esistente di contatto, adattando copy e posizionamento per farla funzionare come richiesta accesso/community interest
- non trasformare la vista pubblica in un join flow privato mascherato

In pratica:

- community aperta = scoperta pubblica -> community
- community chiusa = scoperta pubblica -> richiesta contatto/accesso

### 5. UX/UI da mantenere coerente

Segui il linguaggio gia presente in `PublicBookingPage`, `ClubDirectoryPage` e `PublicClubPage`.

Indicazioni obbligatorie:

- usa componenti gia presenti come `SectionCard`, `AlertBanner`, `LoadingBlock` quando appropriato
- mantieni palette, spaziature, bordi, gerarchia visiva e stile dei pulsanti coerenti con il resto
- evita layout nuovi troppo distanti dalla UI attuale
- niente hero ridondanti o pagine che sembrano prodotti diversi
- niente dark mode forzata o temi scollegati dal resto
- nessuna UI generica o da template indistinto
- ottimizza leggibilita mobile prima del desktop

## Fasi operative obbligatorie

### Fase 1 - Verifica contesto e delta reale

Obiettivo:

- verificare che i file e le route sopra indicate esistano davvero
- confermare cosa e gia disponibile e cosa manca solo a livello di contratto o UI

Attivita:

- mappa i file reali coinvolti
- conferma che `/clubs/nearby`, `/c/:clubSlug` e `/c/:clubSlug/play` siano gia operativi
- conferma che `list_public_open_matches` sia gia coerente con l ordine 3/4 -> 2/4 -> 1/4
- conferma che il repository tratti gia `club_slug` come identificatore pubblico canonicale
- definisci il delta minimo necessario

Output atteso:

- gap analysis concreta, non teorica
- lista precisa dei file da toccare
- decisione esplicita su come esporre i 3 contatori nel summary pubblico

Verifica finale:

- se il repository supporta gia la maggior parte della feature, non reinventare architetture

### Fase 2 - Backend minimale e contratti

Obiettivo:

- esporre al frontend i dati minimi per la home geolocalizzata senza cambiare la business logic

Attivita:

- aggiorna `backend/app/schemas/public.py`
- aggiorna l endpoint o la serializzazione usata da `/public/clubs` e `/public/clubs/nearby`
- calcola i bucket 3/4, 2/4, 1/4 riusando le regole pubbliche gia esistenti
- mantieni compatibilita backward-friendly
- aggiorna `frontend/src/types.ts` di conseguenza

Output atteso:

- summary pubblico del club esteso con i tre contatori derivati

Verifica finale:

- nessuna migrazione se non necessaria
- nessun cambiamento a privacy, routing o join logic
- nessun cambiamento al modello pubblico club visibile / community privata

### Fase 3 - Frontend home e scheda club

Obiettivo:

- inserire la discovery geolocalizzata in home e rifinire la scheda club pubblica

Attivita:

- aggiorna `frontend/src/pages/PublicBookingPage.tsx` per mostrare i 10 club piu vicini
- riusa `listPublicClubsNearby` e fallback coerente se la posizione non e disponibile
- limita la resa home ai primi 10 club
- mostra card sintetiche leggibili e cliccabili
- aggiorna `frontend/src/pages/PublicClubPage.tsx` per far emergere le `partite da chiudere`
- mantieni il filtro livello
- raggruppa o ordina visivamente 3/4, 2/4, 1/4
- per club chiuso, riusa il contact form come richiesta accesso alla community con copy coerente

Output atteso:

- home pubblica arricchita ma non stravolta
- scheda club piu orientata alla conversione discovery -> community

Verifica finale:

- nessun dato privato esposto
- nessuna UX incoerente con il resto dell app
- nessuna diluizione della gerarchia attuale della home booking

### Fase 4 - Test e verifica finale

Obiettivo:

- dimostrare che la feature e implementata senza regressioni locali evidenti

Attivita:

- aggiorna o aggiungi test backend mirati per i contatori pubblici
- aggiorna o aggiungi test frontend mirati per:
  - sezione home con club vicini
  - scheda club con priorita 3/4, 2/4, 1/4
  - CTA community aperta/chiusa coerenti
- esegui solo le verifiche strette rilevanti prima di allargare lo scope

Verifica finale:

- esegui test mirati backend e frontend
- se tocchi piu superfici UI, esegui anche build frontend

## Regole implementative aggiuntive

- preferisci patch piccole e locali
- evita estrazioni o componentizzazioni inutili se il beneficio e minimo
- se riusi logica geolocalizzazione tra pagine, fallo solo con una refactor piccola e chiaramente utile
- non rompere `ClubDirectoryPage` o `PublicClubPage` esistenti mentre aggiungi la home geo
- non cambiare naming di route gia consolidate
- non cambiare la semantica dei path canonici con `/c/:clubSlug`

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
- crea o aggiorna `STATO_GEOHOME.md`
- il file stato deve essere compatto, fattuale e leggibile dalla fase successiva

## Controllo qualita finale

Prima di chiudere il lavoro verifica esplicitamente che:

- la feature sia coerente con il codice attuale e non con un modello teorico
- non siano stati introdotti cambi di business logic
- il modello `club pubblico visibile / community privata` sia rimasto integro
- `club_slug` resti l identificatore pubblico usato per routing e linking
- i match pubblici restino pubblici solo in forma sintetica
- il join privato/community non venga esposto nella parte pubblica
- la home non sia diventata una pagina incoerente rispetto al booking pubblico attuale
- la scheda club resti la stessa surface pubblica, solo migliorata
- non siano state introdotte dipendenze non necessarie
- siano indicati chiaramente file toccati, test eseguiti e limiti residui

Se trovi un conflitto tra la richiesta e il comportamento reale del repository, scegli la soluzione piu piccola, coerente e verificabile, senza inventare nuove architetture.