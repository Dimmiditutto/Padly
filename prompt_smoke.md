# PROMPT SMOKE - VERIFICA MANUALE DI RILASCIO

Agisci come:
- Senior Prompt Engineer orientato all'esecuzione reale
- Senior QA tecnico rigoroso
- Senior Full-Stack Engineer su FastAPI + React + TypeScript
- Release Tester pragmatico orientato al `PASS / FAIL`

Il tuo compito non e fare review teorica. Devi eseguire o guidare una smoke verification reale del prodotto in vista del rilascio, usando il repository e il deployment effettivo disponibili, senza inventare esiti e senza mascherare blocker reali.

## Prima di iniziare

Leggi obbligatoriamente:

- `RELEASE_CHECKLIST.md`
- `docs/operations/RUNBOOKS.md`
- `prompt_live.md`
- `STATO_PLAY_7.md`

Se esiste gia, leggi anche:

- `STATO_PLAY_FINAL.md`
- `STATO_GO_LIVE.md`

Prima di dichiarare uno smoke `PASS`, verifica anche le superfici reali che lo sostengono nel codice o nei test quando serve disambiguare comportamenti attesi.

## Setup operativo consigliato

Per rendere gli smoke ripetibili e leggibili, usa una traccia operativa concreta.

Sessioni browser consigliate:

- Browser A o finestra `Incognito` pulita per flussi pubblici anonimi: `/`, `/clubs`, `/clubs/nearby`, `/c/:clubSlug`
- Browser B o secondo profilo pulito per flussi `/play` con player identificato
- Browser C o profilo separato per l'admin, cosi non mischi cookie admin, cookie play e sessione discovery

Se devi verificare un flusso `/play` che richiede un match gia quasi completo, puoi usare:

- Browser B come player finale che esegue il join conclusivo
- un seed gia presente nell'ambiente oppure una preparazione minima coerente del match `2/4` o `3/4`

Strumenti da tenere aperti durante gli smoke:

- DevTools `Network`, filtrando `Fetch/XHR` e usando `Preserve log`
- DevTools `Application` o `Storage` per verificare cookie come `padel_play_session`, `padel_discovery_session` e cookie admin
- Console browser solo per blocchi reali di runtime, non come fonte principale dell'esito
- un client HTTP o terminale per i controlli API diretti

Preferenza pratica:

- per i flussi UI raccogli sempre sia evidenza browser sia almeno una evidenza di rete coerente
- per i flussi solo API raccogli status code e i campi minimi utili del payload, non dump completi non necessari

## Traccia minima di esecuzione consigliata

Per evitare smoke disordinati, usa questa sequenza operativa:

1. API client: `GET /api/health`
2. Browser A: apertura `GET /`
3. Browser A: discovery pubblica `/clubs`, `/clubs/nearby`, `/c/:clubSlug`
4. Browser B: `/c/:clubSlug/play` con identify o riconoscimento player
5. Browser C: login admin e smoke dashboard/settings/billing status
6. API client: eventuali controlli diretti di supporto su `public config`, `billing status`, `ops status`

Se l'ambiente lo consente, conserva screenshot, status code e ultime richieste XHR principali per ogni smoke core.

## Obiettivo del prompt

Eseguire una smoke checklist manuale corta ma reale, sufficiente a capire se il prodotto e rilasciabile dal punto di vista dei flussi essenziali.

Questo prompt NON sostituisce `prompt_live.md`.

Questo prompt serve a chiudere solo la parte di smoke verification manuale, cioe:

- confermare che i flussi core si aprono e si completano davvero
- confermare che `/play` e discovery pubblica non sono stati dimenticati nel rilascio
- produrre un esito netto `PASS`, `PARTIAL` o `FAIL` per ogni smoke

## Regole non negoziabili

### 1. Nessun esito inventato

- se uno smoke non puo essere eseguito davvero per mancanza di env, provider o accesso, segnalo come `BLOCKED`, non come `PASS`
- se uno smoke fallisce, riportalo come `FAIL`
- se uno smoke passa solo parzialmente o con workaround non standard, segnalo come `PARTIAL`

### 2. Nessuna deriva di scope

Questo prompt non deve diventare:

- una nuova fase feature
- una review architetturale ampia
- un audit infinito del codice
- un refactor di go-live

Le correzioni ammesse durante l'esecuzione sono solo micro-fix direttamente collegati a uno smoke blocker reale e riproducibile.

### 3. Evidenza prima di sintesi

Per ogni smoke devi raccogliere almeno una evidenza reale tra:

- risposta HTTP coerente
- rendering UI coerente
- transizione di stato coerente
- log o feedback utente coerente
- test o comando di supporto mirato quando serve disambiguare il comportamento

## Ordine di esecuzione obbligatorio

Esegui gli smoke in questo ordine:

1. smoke infrastrutturali minimi
2. smoke booking pubblico e admin core
3. smoke `/play` privato
4. smoke discovery pubblica
5. smoke multi-tenant minimo
6. riepilogo finale con gate `PASS / PARTIAL / FAIL`

Non saltare ai flussi secondari se falliscono gli smoke infrastrutturali minimi.

## Prerequisiti minimi da verificare prima degli smoke

Verifica almeno:

- il servizio risponde su `GET /api/health`
- la SPA risponde su `GET /`
- esiste almeno un tenant testabile
- se il rilascio usa autenticazione admin, le credenziali sono disponibili
- se il percorso da verificare richiede provider reali, l'ambiente e configurato abbastanza da eseguire lo smoke oppure lo dichiari `BLOCKED`

Se questi prerequisiti minimi mancano, fermati e segnalo il blocco prima di procedere oltre.

## Evidenze minime da raccogliere per ogni smoke

Per ogni smoke cerca di raccogliere sempre queste quattro informazioni, anche in forma breve:

- azione eseguita in browser o API client
- URL o endpoint colpito
- evidenza osservata lato UI o lato payload
- esito finale `PASS`, `PARTIAL`, `FAIL` oppure `BLOCKED`

Template preferito:

- `SMOKE:` nome del flusso
- `Canale:` browser oppure API
- `URL/Endpoint:` path reale verificato
- `Evidenza:` status code, elemento UI, redirect, cookie o messaggio coerente
- `Esito:` `PASS`, `PARTIAL`, `FAIL` o `BLOCKED`

## Smoke da eseguire davvero

### 1. Infrastruttura minima

Verifica almeno:

- `GET /api/health`
- `GET /`
- se disponibile e coerente con l'ambiente, `GET /api/platform/ops/status` con `X-Platform-Key`

Checklist API concreta:

- chiamare `GET /api/health`
- verificare `200`
- verificare che il payload riporti almeno un database sano
- verificare che il campo scheduler sia coerente con il deployment scelto

Checklist browser concreta:

- aprire `GET /`
- verificare che la SPA carichi senza pagina bianca o errore immediato
- verificare che il bootstrap frontend non fallisca subito per errore API bloccante

Esito atteso:

- servizio vivo
- database raggiungibile
- scheduler coerente con il deployment scelto
- SPA servita correttamente

### 2. Booking pubblico e admin core

Verifica almeno:

- prenotazione pubblica felice con creazione hold, checkout e conferma finale
- checkout annullato con ritorno coerente sullo stato booking
- login admin riuscito e accesso dashboard
- creazione booking manuale admin
- cancellazione booking admin
- marcatura `COMPLETED`, `NO_SHOW` e saldo al campo
- `GET /api/admin/billing/status`

Checklist browser/UI concreta:

- Browser A: aprire la homepage booking pubblica
- Browser A: scegliere uno slot disponibile e avviare il flusso booking
- se il provider e disponibile nell'ambiente, completare uno smoke di checkout reale o coerente con l'ambiente di test
- ripetere il percorso con annullamento checkout e verificare il ritorno coerente
- Browser C: login admin, apertura dashboard, creazione booking manuale, cancellazione booking e aggiornamento stato booking

Checklist API/supporto concreta:

- verificare almeno una `GET /api/public/config`
- se il booking pubblico viene creato da UI, confermare dal `Network` la chiamata booking principale senza limitarsi alla sola UI
- dopo login admin, verificare `GET /api/admin/billing/status`
- se il pannello admin mostra dati incoerenti, usare la risposta API come discriminante primaria

Se uno di questi smoke e fuori perimetro dell'ambiente disponibile, dichiaralo `BLOCKED` con motivo preciso.

### 3. `/play` privato

Verifica almeno:

- caricamento route canonica `/c/:clubSlug/play`
- identify o riconoscimento player gia persistito
- visualizzazione coerente dei match aperti
- join di un match aperto
- create match con suggerimenti anti-frammentazione se applicabili
- completamento `4/4` con comportamento coerente alla configurazione corrente:
  - default offline se caparra community `OFF`
  - CTA checkout immediata del pagatore finale se caparra community `ON`

Checklist browser/UI concreta:

- Browser B: aprire `/c/:clubSlug/play`
- verificare se il player viene riconosciuto oppure se compare il flusso identify
- verificare che i match aperti si carichino davvero e non tramite placeholder statici
- eseguire almeno un join reale di un match aperto, se il dataset dell'ambiente lo consente
- se l'ambiente consente create match, verificare il percorso con suggerimento anti-frammentazione
- se e disponibile un match `3/4`, verificare il comportamento del join conclusivo `4/4`
- se caparra `OFF`, verificare messaggio coerente di booking confermata e pagamento al campo
- se caparra `ON`, verificare che il pagatore finale veda la CTA checkout coerente e immediata

Se il feed notifiche private e parte del prodotto finale gia chiuso, verifica anche almeno:

- caricamento del pannello notifiche
- unread count coerente, se disponibile nel build corrente

Checklist API/supporto concreta:

- confermare nel `Network` almeno `GET /api/play/me`
- confermare nel `Network` almeno `GET /api/play/matches`
- se avviene identify, confermare `POST /api/play/identify`
- se avviene join, confermare `POST /api/play/matches/{match_id}/join` o path equivalente reale
- se avviene create, confermare `POST /api/play/matches`
- se si entra nel percorso checkout community, confermare la chiamata play checkout o il redirect coerente con il provider scelto

### 4. Discovery pubblica

Verifica almeno:

- `/clubs`
- `/clubs/nearby`
- fallback corretto se geolocalizzazione assente o negata
- `/c/:clubSlug`
- follow/unfollow watchlist, se il build corrente lo include
- contact request guidata
- conferma che la superficie pubblica non sblocchi join o funzioni community private

Checklist browser/UI concreta:

- Browser A: aprire `/clubs`
- verificare che la directory si carichi davvero dal backend
- Browser A: aprire `/clubs/nearby`
- se la geolocalizzazione e negata o assente, verificare il fallback esplicito e la continuita della ricerca manuale
- Browser A: aprire `/c/:clubSlug`
- se il build corrente lo supporta, seguire e smettere di seguire un club
- aprire e completare il form `Richiedi contatto`
- confermare che dalla superficie pubblica non si possa fare join privato diretto

Checklist API/supporto concreta:

- confermare `GET /api/public/clubs`
- confermare `GET /api/public/clubs/nearby` quando usato davvero
- confermare `GET /api/public/clubs/{club_slug}`
- se si entra nel flusso discovery, confermare `POST /api/public/discovery/identify`
- se si usa watchlist, confermare `POST /api/public/discovery/watchlist/{club_slug}` e `DELETE /api/public/discovery/watchlist/{club_slug}` quando applicabili
- se si invia il contatto, confermare `POST /api/public/clubs/{club_slug}/contact-request`
- se il feed discovery e nel build corrente, confermare anche `GET /api/public/discovery/me`

### 5. Multi-tenant minimo

Verifica almeno:

- tenant default: `public config`, booking pubblico o dashboard admin secondo disponibilita
- tenant secondario: almeno `GET /api/public/config`, login admin e una route pubblica principale se disponibile

Checklist concreta:

- usare il tenant default come baseline
- ripetere almeno un controllo pubblico e uno admin su tenant secondario reale
- verificare che il tenant secondario non mostri dati del tenant default
- se l'ambiente usa host diversi, mantenerli separati; se usa query o header tenant-aware, rispettare il meccanismo reale del deployment

Non servono test esaustivi cross-tenant: serve solo una prova minima che il prodotto non sia legato a un solo tenant effettivo nel rilascio.

## Regole specifiche per `/play` e discovery

Per evitare regressioni di perimetro, devi confermare esplicitamente queste regole di prodotto:

- la community privata resta su `/c/:clubSlug/play`
- la discovery pubblica resta pubblica
- seguire un club non significa entrare nella community
- la pagina pubblica del club non deve permettere join diretto privato
- il comportamento `OFFLINE` della booking `/play` con caparra disattivata resta coerente con Fase 5

## Quando usare strumenti di supporto

Se uno smoke fallisce o e ambiguo, puoi usare strumenti di supporto minimi e mirati, ad esempio:

- un comando o test mirato per distinguere problema UI da problema backend
- una lettura locale di log o risposta API specifica
- un singolo test del modulo toccato se e il modo piu rapido per falsificare il dubbio

Non riaprire pero la suite completa se non serve a discriminare il problema.

## Correzioni ammesse durante gli smoke

Sono ammesse solo correzioni piccole e direttamente collegate a uno smoke blocker riproducibile, ad esempio:

- wiring UI rotto su una route gia prevista
- copy o redirect incoerente che blocca il flusso
- bug leggero di contratto tra frontend e backend
- checklist smoke stale rispetto al prodotto reale

Non sono ammesse in questo prompt:

- nuove feature
- refactor architetturali
- redesign di product flow
- lavorazioni speculative non bloccanti

## Output obbligatorio durante l'esecuzione

Per ogni smoke, riporta in modo esplicito:

- `SMOKE`
- perimetro verificato
- esito `PASS`, `PARTIAL`, `FAIL` oppure `BLOCKED`
- evidenza sintetica reale
- eventuale blocker o deviazione osservata

Usa una forma sintetica ma coerente, ad esempio:

- `SMOKE: /clubs fallback geolocalizzazione`
- `Esito: PASS`
- `Evidenza: la pagina mostra il messaggio di fallback e continua a proporre la ricerca manuale`

Per gli smoke core preferisci una forma ancora piu concreta quando possibile:

- `SMOKE: /c/:clubSlug/play join match aperto`
- `Canale: browser + network`
- `URL/Endpoint: /c/roma/play ; POST /api/play/matches/abc/join`
- `Evidenza: join completato, card aggiornata e richiesta XHR 200`
- `Esito: PASS`

## Verifica finale obbligatoria

La smoke verification complessiva puo risultare:

- `PASS` solo se tutti gli smoke essenziali eseguibili risultano verdi e non emergono blocker di rilascio immediati
- `PARTIAL` se il core e sano ma alcuni smoke secondari restano bloccati per env incompleto o problemi non bloccanti immediati
- `FAIL` se uno o piu smoke core di booking/admin, `/play` o discovery pubblica falliscono davvero

## File stato da produrre obbligatoriamente

Crea `STATO_SMOKE.md` con almeno:

- data esecuzione
- ambiente verificato
- browser, profili o sessioni usate
- prerequisiti disponibili o mancanti
- elenco smoke eseguiti davvero
- esito per ciascuno: `PASS`, `PARTIAL`, `FAIL` o `BLOCKED`
- URL o endpoint principali verificati per gli smoke core
- eventuali blocker emersi
- eventuali micro-fix applicati durante gli smoke
- esito complessivo finale
- `## Decisione finale`

Nella sezione `## Decisione finale` scrivi in modo esplicito una sola delle tre stringhe:

- `SMOKE PASS - rilascio verificato a livello manuale minimo`
- `SMOKE PARTIAL - rilascio non ancora verificato completamente`
- `SMOKE FAIL - non procedere al rilascio`

## Fuori scope approvato

Questo prompt non deve assorbire:

- validazione completa di produzione e segreti, gia nel perimetro di `prompt_live.md`
- redesign delle checklist di go-live salvo minimi allineamenti smoke
- audit ampio su timezone, rate limit o observability
- nuove feature di prodotto
- review estesa di tutto il codicebase

Questi temi possono essere richiamati solo se bloccano direttamente l'esecuzione di uno smoke reale.