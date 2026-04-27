# VERIFICA PLAY 7 DISCOVERY PUBBLICO

## 1. Esito sintetico generale

PASS CON RISERVE

La base tecnica della Fase 7 e coerente: modelli, router, schemi, service backend e pagine frontend discovery sono allineati, i controlli statici sui file discovery non mostrano errori, e le verifiche eseguibili mirate passano davvero.

Validazioni reali rieseguite durante questa verifica:

- backend: D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest -q tests/test_play_phase7_public_discovery.py -> PASS, 3 passed
- frontend: npm run test:run -- src/pages/PublicDiscoveryPages.test.tsx -> PASS, 6 passed
- controlli statici: nessun errore su router, schemi, service e pagine discovery controllati

Riserva principale:

- restano criticita concrete di business e affidabilita nel perimetro discovery pubblico, quindi il codice non e ancora da considerare chiuso in modo netto per il rilascio senza fix mirati

Nota di perimetro:

- il file [PROMPT_VERIFICA.md](PROMPT_VERIFICA.md) resta generico e punta a riferimenti SaaS storici
- per questa verifica il perimetro reale usato e [STATO_PLAY_7.md](STATO_PLAY_7.md) piu i file backend e frontend discovery effettivamente toccati dalla Fase 7
- il working tree contiene anche modifiche locali non discovery, come [frontend/src/components/play/CreateMatchForm.tsx](frontend/src/components/play/CreateMatchForm.tsx), [frontend/src/pages/PlayPage.test.tsx](frontend/src/pages/PlayPage.test.tsx), [frontend/public/local-play-auto-join.html](frontend/public/local-play-auto-join.html) e [logochatgpt.png](logochatgpt.png); non fanno parte di questo verdetto

## 2. Verifica per area

### Coerenza complessiva del codice

Esito: PASS CON RISERVE

Problemi trovati:

- il flusso watchlist e la UI permettono di seguire qualunque club pubblico, ma il dispatch alert discovery blocca i club con community privata; il comportamento risultante non e coerente tra promessa UI e trigger backend
- il flusso richiesta contatto persiste la lead ma dichiara comunque esito positivo anche se l email operativa non viene consegnata

Gravita:

- media per la watchlist su club privati
- alta per il falso successo del contatto club

Impatto reale:

- parte dell esperienza discovery puo risultare muta o ingannevole in produzione pur con test verdi

### Coerenza tra file modificati

Esito: PASS CON RISERVE

Problemi trovati:

- contratti frontend, router e service sono coerenti sui payload discovery, unread count e mark-as-read
- il contratto del form contatto sembra restrittivo, ma lato backend accetta ancora dati sporchi o poco validati, in particolare nome solo spazi e email non validata semanticamente
- il token discovery viene marcato come toccato nelle dependency, ma sulle route di lettura il dato non viene persistito davvero

Gravita:

- media sulla validazione contatto
- bassa sul touch non persistito del token

Impatto reale:

- si crea scollamento tra ciò che suggerisce lo schema e ciò che viene davvero salvato o tracciato

### Conflitti o blocchi introdotti dai file modificati

Esito: PASS CON RISERVE

Problemi trovati:

- nessun errore statico, nessun mismatch tipico tra API e frontend, nessun test rosso nel perimetro discovery verificato
- esiste pero un conflitto logico tra follow dei club privati e assenza di alert conseguente
- esiste un rischio runtime non coperto dai test: richiesta contatto salvata ma email operativa fallita con risposta API comunque positiva

Gravita:

- media sulla watchlist incoerente
- alta sul ramo di failure email non gestito a livello di esito utente

Impatto reale:

- l integrazione puo apparire funzionante ma produrre perdite di segnale operativo o aspettative UX sbagliate

### Criticita del progetto nel suo insieme

Esito: PASS CON RISERVE

Problemi trovati:

- il perimetro discovery non mostra regressioni bloccanti su build o test mirati
- manca copertura sui rami realmente fragili: club privato seguito in watchlist, failure SMTP sul contact request, validazione input sporco del contatto
- il campo last_used_at della sessione discovery viene aggiornato in memoria ma non consolidato sulle GET, quindi il dato di audit e fuorviante

Gravita:

- alta per il ramo failure email
- media per i gap di test e validazione
- bassa per il last_used_at non persistito

Impatto reale:

- il sistema passa i test correnti ma lascia scoperti casi di produzione plausibili

### Rispetto della logica di business

Esito: FAIL PARZIALE

Problemi trovati:

- [backend/app/services/public_discovery_service.py](backend/app/services/public_discovery_service.py#L526) permette di seguire un club pubblico attivo senza filtrare lo stato community, mentre [backend/app/services/public_discovery_service.py](backend/app/services/public_discovery_service.py#L633) sopprime gli alert se il club non e community aperta; questo contraddice la semantica della watchlist esposta in [frontend/src/pages/ClubDirectoryPage.tsx](frontend/src/pages/ClubDirectoryPage.tsx#L646) e [frontend/src/pages/PublicClubPage.tsx](frontend/src/pages/PublicClubPage.tsx#L229)
- [backend/app/api/routers/public.py](backend/app/api/routers/public.py#L412) restituisce sempre il messaggio positivo di invio, ma [backend/app/services/email_service.py](backend/app/services/email_service.py#L187) puo restituire FAILED senza che il ramo discovery lo propaghi o lo trasformi in esito coerente
- [backend/app/schemas/public.py](backend/app/schemas/public.py#L261) non impone validazione email forte e non normalizza il nome prima del controllo di lunghezza, mentre [backend/app/services/public_discovery_service.py](backend/app/services/public_discovery_service.py#L817) salva il nome gia strip-pato, quindi il backend puo accettare input semanticamente vuoti

Gravita:

- alta sul contatto club
- media sulla watchlist privata e sulla validazione input

Impatto reale:

- alcune regole di prodotto dichiarate o implicite non sono ancora applicate in modo coerente end-to-end

## 3. Elenco criticita

### 1. Watchlist coerente solo per club community aperta, ma follow aperto a tutti i club pubblici

Descrizione tecnica:

- [backend/app/services/public_discovery_service.py](backend/app/services/public_discovery_service.py#L526) consente il follow di qualsiasi club pubblico attivo
- [backend/app/services/public_discovery_service.py](backend/app/services/public_discovery_service.py#L653) interrompe il dispatch alert se il club non e community aperta
- la UI invita comunque a seguire il club in [frontend/src/pages/ClubDirectoryPage.tsx](frontend/src/pages/ClubDirectoryPage.tsx#L646) e [frontend/src/pages/PublicClubPage.tsx](frontend/src/pages/PublicClubPage.tsx#L229)

Perche e un problema reale:

- l utente puo seguire un club che poi non generera mai gli alert 2 su 4 o 3 su 4 promessi dal discovery

Dove si manifesta:

- watchlist pubblica, feed alert, pagina club pubblica e directory club

Gravita: media

Blocca il rilascio: si, se il rilascio discovery deve essere coerente anche per i club con community privata

### 2. Richiesta contatto dichiarata come inviata anche quando l email operativa fallisce

Descrizione tecnica:

- [backend/app/services/email_service.py](backend/app/services/email_service.py#L187) restituisce uno stato FAILED o SKIPPED senza alzare errore
- [backend/app/services/public_discovery_service.py](backend/app/services/public_discovery_service.py#L857) invoca l invio ma ignora lo stato ritornato
- [backend/app/api/routers/public.py](backend/app/api/routers/public.py#L433) risponde sempre con Richiesta inviata al circolo

Perche e un problema reale:

- il lead viene salvato ma il club potrebbe non essere notificato; l utente riceve comunque un messaggio di successo pieno e il team puo perdere richieste di contatto senza segnali applicativi adeguati

Dove si manifesta:

- POST /api/public/clubs/{club_slug}/contact-request

Gravita: alta

Blocca il rilascio: si

### 3. Validazione backend troppo debole sul contact request discovery

Descrizione tecnica:

- [backend/app/schemas/public.py](backend/app/schemas/public.py#L261) usa str semplice per email e non normalizza il nome prima del controllo minimo
- [backend/app/services/public_discovery_service.py](backend/app/services/public_discovery_service.py#L817) salva name dopo strip, quindi un valore fatto solo di spazi puo diventare stringa vuota persistita

Perche e un problema reale:

- l endpoint puo accettare via API payload formalmente passanti ma semanticamente sporchi, degradando qualita lead e affidabilita operativa

Dove si manifesta:

- POST /api/public/clubs/{club_slug}/contact-request

Gravita: media

Blocca il rilascio: no, ma va corretto prima della beta pubblica

### 4. Touch del token discovery non persistito sulle route read-only

Descrizione tecnica:

- [backend/app/api/deps.py](backend/app/api/deps.py#L108) risolve il subscriber con touch attivo
- [backend/app/services/public_discovery_service.py](backend/app/services/public_discovery_service.py#L247) aggiorna last_used_at in sessione
- [backend/app/core/db.py](backend/app/core/db.py#L18) chiude la sessione senza commit automatico; route come [backend/app/api/routers/public.py](backend/app/api/routers/public.py#L292) e [backend/app/api/routers/public.py](backend/app/api/routers/public.py#L374) non fanno commit

Perche e un problema reale:

- il dato di ultimo utilizzo del token non rappresenta l uso reale sulle consultazioni discovery e puo trarre in inganno su audit, cleanup o analisi sessioni

Dove si manifesta:

- GET /api/public/discovery/me e GET /api/public/discovery/watchlist

Gravita: bassa

Blocca il rilascio: no

## 4. Prioritizzazione finale

### Da correggere prima del rilascio

- gestire in modo coerente l esito del contact request quando la notifica email fallisce o non e configurata
- allineare la semantica watchlist dei club privati: o il follow e consentito davvero con alert coerenti, oppure va esplicitamente impedito o degradato in modo chiaro tra backend e frontend

### Da correggere prima della beta pubblica

- rafforzare la validazione backend del form contatto discovery su nome ed email
- aggiungere test dedicati sui rami failure SMTP e sul comportamento watchlist per club non community aperta

### Miglioramenti differibili

- rendere consistente la persistenza di last_used_at del token discovery sulle route di lettura, oppure rimuovere il touch se non serve davvero come dato affidabile

## 5. Verdetto finale

Il codice discovery pubblico della Fase 7 e quasi pronto ma richiede fix mirati prima di poter essere considerato chiuso con sicurezza.

La struttura generale e solida, i contratti sono coerenti e i test mirati attuali passano, ma restano due problemi da non lasciare in coda: il falso successo del contact request in caso di failure email e l incoerenza tra follow dei club privati e generazione reale degli alert watchlist.

## 6. Prompt operativo per i fix

Agisci solo sul perimetro Play 7 discovery pubblico. Non fare refactor ampi e non toccare file fuori dal perimetro discovery salvo test strettamente necessari.

Obiettivi in ordine di priorita:

1. Correggi il flusso POST /api/public/clubs/{club_slug}/contact-request in modo che l esito restituito all utente sia coerente con l esito reale della notifica operativa al club. Mantieni la persistenza della richiesta, ma non dichiarare successo pieno se email_service segnala FAILED o SKIPPED. Introduci la patch minima coerente con l infrastruttura email gia esistente e aggiungi un test backend sul ramo di failure.

2. Rendi coerente la watchlist discovery per i club con community privata. Scegli una sola semantica e applicala end-to-end con patch minima: oppure il club privato non e followabile, oppure i suoi eventi generano alert discovery come promesso dalla UI. Allinea backend, eventuale copy frontend e test mirato senza refactor superflui.

3. Rafforza la validazione backend del contact request discovery: trim prima della validazione, rifiuta name vuoto o solo spazi, usa una validazione email coerente con gli altri schemi del progetto. Aggiungi solo i test davvero necessari per coprire questi casi limite.

4. Verifica se last_used_at del token discovery deve essere un dato affidabile. Se si, persisti davvero il touch sulle route read-only con patch minima e test mirato. Se no, elimina la semantica ingannevole del touch senza introdurre refactor.

Validazioni richieste a fine fix:

- backend discovery: tests/test_play_phase7_public_discovery.py
- frontend discovery: src/pages/PublicDiscoveryPages.test.tsx
- eventuali test aggiunti solo sui casi critici sopra, senza allargare il perimetro inutilmente