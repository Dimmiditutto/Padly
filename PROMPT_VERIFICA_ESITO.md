# VERIFICA OTP COMMUNITY, LINK DI GRUPPO E RIENTRO DA HOME BOOKING

## 1. Esito sintetico generale

FAIL PARZIALE

L'integrazione OTP/community e stata realizzata in modo ampio e nel complesso coerente tra backend, frontend, migrazione e test mirati, ma la verifica tecnica rigorosa ha fatto emergere due criticita reali che oggi impediscono di considerare il flusso sicuro per il rilascio:

- un profilo player esistente puo essere riassociato a una nuova email verificata partendo solo dal numero di telefono nel flusso DIRECT o GROUP
- il challenge OTP non implementa un vero limite di tentativi per codice errato, quindi manca un lockout per-challenge richiesto dal disegno stesso del flusso

Contesto reale verificato sulle modifiche recenti:

- backend: estensione di `Player` con `email` ed `email_verified_at`, nuova enum `PlayAccessPurpose`, nuove entita `CommunityAccessLink` e `PlayerAccessChallenge`, nuova migrazione `20260428_0014_play_email_otp_access.py`
- backend API: nuova superficie pubblica `/api/public/play-access/start`, `/verify`, `/{challenge_id}/resend` e nuove API admin per creare/listare/revocare i link gruppo community
- frontend: nuova pagina `PlayAccessPage`, nuove route `/c/:clubSlug/play/access` e `/c/:clubSlug/play/access/:groupToken`, `InviteAcceptPage` trasformata in wrapper della nuova pagina, CTA di rientro in `PublicBookingPage`, CTA anonima anche in `PlayPage`, nuovo blocco admin per i link gruppo
- test e validazioni rieseguiti durante questa verifica:
  - backend: `../.venv/Scripts/python.exe -m pytest tests/test_play_email_otp_migration.py tests/test_play_access_otp.py tests/test_play_phase1.py -k "community_invite or admin_can_create_community_invite" -q` -> PASS
  - frontend test: `npm run test:run -- src/pages/PlayPage.test.tsx src/pages/PublicBookingPage.test.tsx src/pages/AdminDashboardPage.test.tsx` -> PASS
  - frontend build: `npm run build` -> PASS

Il codice quindi non e rotto: build e subset di test passano. Il problema e che la sicurezza del legame identita email-player non e ancora sufficientemente robusta.

## 2. Verifica per area

### Coerenza complessiva del codice

Esito: PASS CON RISERVE

Problemi trovati:

- modelli, schemi, router, servizi e client frontend sono coerenti nel nuovo perimetro OTP/community
- la migrazione e allineata con i nuovi modelli e il test up/down dedicato passa
- la nuova UX e coerente con il progetto: home booking -> accesso community dedicato -> OTP -> sessione Play
- resta pero una incoerenza tra l'obiettivo di autenticazione individuale via email OTP e il modo in cui l'identita esistente viene risolta nel service layer

Gravita del problema:

- alta sul service layer di identita

Impatto reale:

- la struttura tecnica regge, ma il flusso puo attribuire il player sbagliato a una nuova email verificata

### Coerenza tra file modificati

Esito: FAIL PARZIALE

Problemi trovati:

- `backend/app/services/play_service.py` usa `_resolve_player_identity_conflict()` per agganciare un player esistente tramite telefono oppure email, ma `_upsert_player_profile()` aggiorna poi sempre `player.email` quando la nuova email e verificata
- questo comportamento e coerente con il codice tra model/service/router, ma non e coerente con la logica di business attesa del login via email OTP, dove un profilo gia consolidato non deve poter cambiare email solo perche il chiamante conosce il telefono
- il prompt implementativo richiedeva un challenge OTP con limite tentativi esplicito; nei file modificati non esiste nessun `attempt_count` o campo equivalente, e la verifica OTP non aggiorna nessun contatore di errori

Gravita del problema:

- critica sul rebinding email del player
- alta sull'assenza di limite tentativi OTP

Impatto reale:

- il primo problema mina il boundary identitario del profilo community
- il secondo lascia il challenge difeso solo dal rate limit HTTP generico, non da una protezione dedicata al codice OTP

### Conflitti o blocchi introdotti dai file modificati

Esito: FAIL PARZIALE

Problemi trovati:

- non emergono conflitti di build, import, routing o serializzazione payload
- non emergono regressioni evidenti sul flusso invite/group/recovery coperte dai test mirati
- esiste pero un blocco di sicurezza: l'onboarding DIRECT/GROUP puo diventare un takeover del player esistente se il numero di telefono e noto e l'email immessa e nuova
- esiste una fragilita auth: il challenge OTP non si blocca dopo un numero limitato di codici errati e resta valido fino a scadenza, salvo il rate limit applicativo generale per path/IP

Gravita del problema:

- critica sul takeover
- alta sul brute-force per challenge

Impatto reale:

- il rilascio del flusso auth/community non e ancora sicuro nonostante build e test verdi

### Criticita del progetto nel suo insieme

Esito: PASS CON RISERVE

Problemi trovati:

- il perimetro modificato e ben isolato e non rompe booking pubblico, route Play o pannello admin
- il rate limit middleware generale su `/api/public/**` esiste in `backend/app/main.py`, quindi c'e una protezione trasversale di base
- manca pero una protezione specifica del challenge OTP a livello di dominio, che e il punto corretto per difendere autenticazione e recovery
- manca inoltre una copertura frontend dedicata per `PlayAccessPage` nei rami DIRECT, RECOVERY e GROUP: oggi la copertura UI passa soprattutto da `PlayPage.test.tsx`, `PublicBookingPage.test.tsx` e `AdminDashboardPage.test.tsx`

Gravita del problema:

- media sulla copertura test frontend

Impatto reale:

- i problemi di dominio maggiori sono nel backend auth; il rischio residuo sul frontend e di regressione non intercettata nella nuova pagina dedicata

### Rispetto della logica di business

Esito: FAIL PARZIALE

Problemi trovati:

- la logica di business richiesta dal prompt OTP diceva che, se il player esiste gia nel club, il sistema deve recuperare o riattivare lo stesso `Player` senza creare duplicati inutili; questo e stato implementato, ma in modo troppo permissivo
- oggi il sistema considera sufficiente il match per telefono per riusare quel `Player`, e poi consente di sostituire l'email verificata con una nuova email fornita dal chiamante
- il requisito di limite tentativi OTP esplicito non risulta rispettato nel modello dati ne nella verifica applicativa
- il resto della business logic richiesta risulta invece centrato: sessione solo dopo verify, invito usato solo dopo verify, link gruppo distinto dall'invito singolo, CTA di rientro visibile dalla home booking, test mirati backend e frontend verdi

Gravita del problema:

- critica sul recupero/riuso player non sufficientemente vincolato
- alta sul requisito OTP attempt limit non rispettato

Impatto reale:

- il flusso e funzionale ma non ancora abbastanza affidabile sul piano identitario e di sicurezza auth

## 3. Elenco criticita

### 1. Takeover del player esistente tramite telefono noto e nuova email

Descrizione tecnica:

- in `backend/app/services/play_service.py`, `_resolve_player_identity_conflict()` restituisce il `Player` trovato per telefono oppure per email
- in `start_player_access_challenge()` i flussi `DIRECT` e `GROUP` associano subito il challenge a quel player se il telefono esiste gia
- in `verify_player_access_challenge()` il challenge verificato confluisce in `_upsert_player_profile()`, che aggiorna `player.email` e `player.email_verified_at` con la nuova email verificata senza richiedere che essa coincida con l'eventuale email gia consolidata del player

Perche e un problema reale:

- chi conosce il numero di telefono di un player esistente puo avviare il flusso con una propria email, verificare l'OTP ricevuto sulla propria casella e prendere possesso dell'identita community di quel player

Dove si manifesta:

- `backend/app/services/play_service.py`
- funzioni coinvolte: `_resolve_player_identity_conflict()`, `start_player_access_challenge()`, `_upsert_player_profile()`, `verify_player_access_challenge()`

Gravita: critica

Blocca il rilascio: si

### 2. Nessun limite tentativi OTP per challenge

Descrizione tecnica:

- il modello `PlayerAccessChallenge` contiene `resend_count`, ma non contiene `attempt_count` o un campo equivalente
- `verify_player_access_challenge()` ritorna `409 Codice OTP non valido` in caso di codice errato, ma non incrementa nessun contatore e non invalida il challenge dopo troppi errori
- esiste solo il rate limit middleware generale per i path pubblici in `backend/app/main.py`, non un lockout specifico sul challenge

Perche e un problema reale:

- l'OTP e un meccanismo auth; lasciarlo senza un attempt cap dedicato indebolisce il flusso e non rispetta il disegno richiesto dal prompt stesso

Dove si manifesta:

- `backend/app/models/__init__.py`
- `backend/alembic/versions/20260428_0014_play_email_otp_access.py`
- `backend/app/services/play_service.py`

Gravita: alta

Blocca il rilascio: si

### 3. Copertura frontend incompleta della nuova pagina `PlayAccessPage`

Descrizione tecnica:

- la nuova pagina `frontend/src/pages/PlayAccessPage.tsx` concentra una parte importante della UX OTP/community
- non esiste oggi un file test dedicato per quella pagina
- la copertura frontend esistente valida bene i punti di integrazione principali, ma non esercita in modo diretto i rami DIRECT, RECOVERY e GROUP della nuova pagina dedicata

Perche e un problema reale:

- la UI principale del nuovo flusso ha molta logica locale di stato, redirect, toggle modalita, start/verify/resend OTP e riconciliazione con sessione esistente
- senza test diretti, una regressione della pagina puo passare piu facilmente rispetto ai punti coperti solo indirettamente

Dove si manifesta:

- `frontend/src/pages/PlayAccessPage.tsx`
- assenza di test dedicati in `frontend/src/pages/*`

Gravita: media

Blocca il rilascio: no, ma va chiuso prima della beta pubblica del nuovo flusso

### 4. Warning di test ancora presente nella dashboard admin

Descrizione tecnica:

- la suite `AdminDashboardPage.test.tsx` passa, ma continua a produrre warning React `act(...)` collegati a `AdminTimeSlotPicker`

Perche e un problema reale:

- non rompe il prodotto, ma rende meno pulita la suite e puo nascondere warning utili in futuro

Dove si manifesta:

- `frontend/src/pages/AdminDashboardPage.test.tsx`
- `frontend/src/components/AdminTimeSlotPicker.tsx`

Gravita: bassa

Blocca il rilascio: no

## 4. Prioritizzazione finale

### Da correggere prima del rilascio

- impedire il rebinding di un `Player` esistente a una nuova email solo sulla base del telefono
- introdurre un vero limite tentativi OTP per challenge con lockout o invalidazione dopo troppi errori
- aggiungere test backend mirati che dimostrino che il takeover via telefono non e piu possibile e che il challenge si blocca dopo troppi OTP errati

### Da correggere prima della beta pubblica

- aggiungere test frontend dedicati a `PlayAccessPage` per i rami DIRECT, RECOVERY e GROUP

### Miglioramenti differibili

- ripulire i warning `act(...)` della suite admin se il fix resta locale e non invasivo
- rimuovere o consolidare eventuali helper legacy non piu usati, come il vecchio client `acceptCommunityInvite`, solo se la pulizia resta piccola e priva di refactor laterali

## 5. Verdetto finale

Il codice non e ancora sicuro per il rilascio del nuovo accesso community.

La parte positiva e chiara: l'integrazione e concreta, coerente e validata con test/build mirati; non siamo davanti a una feature rotta o incompleta. La parte bloccante e altrettanto chiara: il legame tra player esistente, telefono ed email verificata e troppo permissivo, e il challenge OTP non ha ancora una protezione di tentativi adeguata. Finche questi due punti restano aperti, il flusso auth/community non va considerato chiuso.

## 6. Prompt operativo per i fix

Agisci come un Senior Software Architect, Senior Backend Engineer FastAPI/SQLAlchemy e QA tecnico rigoroso.

Devi correggere solo le criticita reali emerse dalla verifica del nuovo flusso OTP/community. Non fare refactor ampi, non toccare booking pubblico, ranking pubblico, notifiche Play non collegate all'auth, billing o tenant resolution.

### Contesto gia integrato da preservare

Le seguenti integrazioni sono gia presenti e non vanno rifatte:

- `Player` ha ora `email` ed `email_verified_at`
- esistono `PlayAccessPurpose`, `CommunityAccessLink` e `PlayerAccessChallenge`
- esistono le API pubbliche `/api/public/play-access/start`, `/verify`, `/{challenge_id}/resend`
- esistono le API admin per i link gruppo community
- esiste la pagina `frontend/src/pages/PlayAccessPage.tsx`
- `InviteAcceptPage` e gia stata convertita a wrapper del nuovo flusso
- `PublicBookingPage` espone gia il bottone `Entra o rientra nella community`
- i test mirati backend/frontend e la build sono gia verdi

### Obiettivi obbligatori, in ordine di priorita

1. Correggi il takeover del player esistente.

	In `backend/app/services/play_service.py` modifica la risoluzione identitaria del flusso OTP in modo che un player gia esistente e gia consolidato con una email non possa essere riassociato a una nuova email solo perche il chiamante conosce il telefono.

	Regole minime da rispettare:

	- se esiste un player per telefono e ha gia una email verificata diversa da quella fornita, il flusso DIRECT/GROUP deve fallire con un conflitto esplicito e sobrio
	- se esiste un player per telefono e non ha ancora email consolidata, il flusso puo completare il consolidamento sulla nuova email verificata
	- se esiste un player per email, il recovery deve continuare a riattivare quello stesso player
	- il flusso INVITE non deve mai poter cambiare silenziosamente l'email di un player gia consolidato a una nuova email diversa
	- evita di creare duplicati non necessari, ma non sacrificare la sicurezza del binding identitario

2. Introduci un vero limite tentativi OTP per challenge.

	In modello, migrazione e service layer aggiungi un contatore tentativi o equivalente per `PlayerAccessChallenge` e applica un lockout chiaro dopo un numero limitato di codici OTP errati.

	Regole minime da rispettare:

	- ogni OTP errato incrementa il contatore
	- oltre il limite il challenge va invalidato o bloccato
	- il comportamento deve restare coerente con il rate limit HTTP generale gia esistente, senza sostituirlo
	- i messaggi di errore non devono rivelare dettagli inutili

3. Aggiungi i test backend mancanti e solo quelli necessari.

	Aggiorna o estendi i test in `backend/tests/test_play_access_otp.py` e, se serve, in `backend/tests/test_play_phase1.py` per coprire almeno:

	- tentativo DIRECT o GROUP con telefono di un player esistente e email diversa gia non associata -> deve fallire e non deve cambiare il player esistente
	- consolidamento consentito di un player legacy senza email
	- challenge OTP bloccato dopo troppi tentativi errati
	- recovery ancora funzionante sullo stesso player gia associato all'email corretta

4. Aggiungi copertura frontend dedicata minima su `PlayAccessPage`.

	Crea o estendi i test frontend per validare in modo diretto almeno:

	- modalita RECOVERY con richiesta OTP
	- modalita DIRECT con validazione minima dei campi e start OTP
	- modalita GROUP con raccolta dati individuali e start OTP

	Mantieni patch piccole: non fare refactor della pagina se non strettamente necessario al test.

5. Solo se resta locale e naturale, riduci i warning `act(...)` della suite admin, ma questa parte non deve ritardare la chiusura dei fix di sicurezza OTP.

### Vincoli operativi

- patch minime e focalizzate
- nessun refactor architetturale
- nessuna modifica al booking pubblico fuori dalle superfici gia toccate
- nessun cambio di contratto API non necessario
- nessuna dipendenza nuova se non indispensabile
- non toccare la business logic Play non collegata all'accesso OTP/community

### Validazioni richieste a fine fix

- backend: `../.venv/Scripts/python.exe -m pytest tests/test_play_access_otp.py tests/test_play_phase1.py -k "community_invite or admin_can_create_community_invite" -q`
- backend migrazione: `../.venv/Scripts/python.exe -m pytest tests/test_play_email_otp_migration.py -q`
- frontend test: `npm run test:run -- src/pages/PlayPage.test.tsx src/pages/PublicBookingPage.test.tsx src/pages/AdminDashboardPage.test.tsx` piu l'eventuale nuova suite dedicata a `PlayAccessPage`
- frontend build: `npm run build`

Chiudi il lavoro solo se i fix eliminano davvero il takeover del profilo, introducono un attempt limit OTP reale e mantengono verdi le validazioni sopra.