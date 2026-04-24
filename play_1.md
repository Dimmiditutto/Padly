# PROMPT FASE 1 - FOUNDATION BACKEND E CONTRATTI DEL MODULO /play

Usa `play_master.md` come contesto fisso.

In questa fase devi costruire la foundation reale del modulo `/play` senza rompere il booking pubblico esistente su `/` e senza modificare la logica di business.

## Prima di iniziare

Leggi e rispetta obbligatoriamente:
- `play_master.md`
- il repository reale

In questa fase non esiste ancora `STATO_PLAY_1.md`: devi produrlo tu a fine lavoro.

## Obiettivo della fase

Introdurre in modo concreto e verificabile il dominio backend del modulo `/play`, i contratti API minimi e l'identita player persistente, lasciando il frontend complesso alla fase successiva.

## Criteri di perimetro

In Fase 1:
- si lavora soprattutto su backend, migrazioni, modelli, servizi e contratti
- si possono aggiungere route frontend minime solo se strettamente necessarie ai test o al wiring iniziale, ma non la UX completa
- non si implementano ancora notifiche avanzate o profilo probabilistico completo
- non si implementa ancora tutta la UX di share/join lato frontend

## Implementazione richiesta

Implementa il minimo coerente per abilitare le fasi successive.

### 1. Dominio dati

Introduci le entita minime per `/play`, tutte tenant-scoped con `club_id`:
- `Player`
- `CommunityInviteToken`
- `PlayerAccessToken`
- `Match`
- `MatchPlayer`

Se serve per chiarezza del dominio, aggiungi enum minimi e sobri, ad esempio:
- stato match
- livello dichiarato o preferenza livello
- stato invite token

Regole:
- non duplicare concetti del booking engine senza motivo
- usa `court_id` sui match, perche il repo e gia multi-campo
- match da 90 minuti fissi
- max 4 player per match
- `Player` e distinto da `Customer`
- il nome prodotto del player e `profile_name`
- il telefono e il canale identitario principale

### 2. Cookie e token

Implementa la base tecnica di:
- player access token opaco
- hash salvato lato server
- cookie httpOnly persistente
- validazione token lato backend
- revoca o invalidazione minima

Non usare JWT come scelta primaria se non strettamente necessario.

### 3. Invite foundation

Implementa il dominio e il contratto base per l'invito community:
- token opaco
- scadenza
- monouso
- revoca
- audit minimo di accettazione privacy

In questa fase puoi implementare il flow minimo backend anche senza UX finale completa.

### 4. API minime da chiudere in Fase 1

Chiudi almeno questi contratti backend reali:
- `GET /api/play/me`
- `POST /api/play/identify`
- `GET /api/play/matches`
- `GET /api/play/matches/{id}`
- `POST /api/public/community-invites/{token}/accept`

Se emerge utile per la pagina reale, puoi aggiungere un endpoint minimale anche per il dettaglio share match, ma senza aprire superfici ridondanti.

### 5. Risposta pagina `/play`

Per evitare over-fetching lato frontend, preferisci un payload gia adatto alla pagina reale, ad esempio con:
- match aperti gia ordinati per priorita
- informazioni base del player corrente se riconosciuto
- eventuali `my_matches` o sezione analoga se il costo resta basso e leggibile

Non introdurre una mappa API iper-frammentata se una risposta piu utile alla pagina e piu semplice e coerente.

### 6. Compatibilita col sistema esistente

Devi esplicitare e implementare in modo chiaro:
- come `/play` convive con il booking pubblico esistente
- come il tenant viene risolto per le nuove route play usando i meccanismi gia presenti
- se introduci un nuovo `BookingSource` per i match community, fallo solo se realmente utile e propaga la modifica in modo coerente

## Non fare in questa fase

- non spostare la home `/`
- non rifare il router frontend intero
- non implementare chat
- non implementare notifiche push complete
- non implementare profilazione avanzata
- non costruire il completamento transazionale del quarto player in modo approssimativo: se non e completo, lascia la hardening alla fase 3 ma prepara il dominio correttamente

## Test richiesti

Aggiungi test backend mirati almeno per:
- identificazione player e riconoscimento via cookie
- `GET /api/play/me` con e senza token valido
- ordinamento prioritario dei match aperti
- accettazione invite token valida / scaduta / gia usata
- isolamento tenant/club dei record play

Se introduci migrazioni, verifica up e down.

## Verifica di fine fase obbligatoria

La fase passa solo se:
- backend importa correttamente
- le migrazioni sono coerenti
- i test mirati backend sono verdi
- i contratti dati della fase 2 sono chiari

## File stato da produrre obbligatoriamente

A fine fase devi creare `STATO_PLAY_1.md` con almeno:
- esito PASS / FAIL
- file toccati
- migrazioni create
- nuovi modelli ed enum
- cookie/token introdotti
- endpoint chiusi
- shape del payload principale di `/api/play/matches`
- decisione presa su `BookingSource` per i match community
- rischi residui per la Fase 2