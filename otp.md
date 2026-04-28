# PROMPT OTP - ACCESSO COMMUNITY VIA EMAIL OTP, LINK DI GRUPPO E RIENTRO DA HOME PRENOTAZIONI

Usa `prompt_engineering.md` come guida di scrittura del prompt e `play_master.md` come source of truth del perimetro `/play`, ma se alcune sezioni statiche di `play_master.md` sono superate dal repository reale o da `STATO_PLAY_FINAL.md`, prevalgono il codice reale e `STATO_PLAY_FINAL.md`.

NON modificare la logica di business gia chiusa del modulo `/play` o del booking pubblico. Mantieni il codice coerente nel suo complesso e intervieni solo sul perimetro identita/accesso richiesto in questo prompt.

Prima di iniziare devi leggere obbligatoriamente:
- `prompt_engineering.md`
- `play_master.md`
- `STATO_PLAY_FINAL.md`
- `backend/app/models/__init__.py`
- `backend/app/schemas/play.py`
- `backend/app/api/routers/play.py`
- `backend/app/api/routers/public_play.py`
- `backend/app/services/play_service.py`
- `backend/app/services/email_service.py`
- `frontend/src/types.ts`
- `frontend/src/services/playApi.ts`
- `frontend/src/pages/PlayPage.tsx`
- `frontend/src/pages/InviteAcceptPage.tsx`
- `frontend/src/pages/PublicBookingPage.tsx`
- `frontend/src/App.tsx`

Se `STATO_PLAY_FINAL.md` non e `PASS`, fermati e non procedere.

Agisci come:
- Senior Prompt Engineer orientato all'implementazione reale
- Senior Software Architect pragmatico
- Senior Full-Stack Engineer su FastAPI + React + TypeScript
- Senior QA tecnico rigoroso
- UX/UI designer Senior

Rispetta rigorosamente l'ordine di output obbligatorio definito in `play_master.md`.

## Obiettivo della fase

Integrare un accesso community via email OTP coerente con il repository reale, coprendo in modo minimo ma completo:

- accesso del singolo utente invitato dal club
- accesso individuale da link condivisibile in gruppi numerosi
- recupero e rientro nella community via email OTP
- rientro da un bottone esplicito nella home prenotazioni pubblica

Il tutto senza introdurre password tradizionali, senza rompere il booking pubblico e senza riaprire le logiche gia chiuse di match, ranking, notifiche, tenant propagation o payment flow.

## Esito minimo richiesto end-to-end

Considera la fase `PASS` solo se chiudi davvero questo percorso minimo:

1. un utente puo entrare per la prima volta nella community con email obbligatoria e verifica OTP email
2. un utente puo rientrare nella community da un bottone visibile nella home prenotazioni pubblica
3. un utente puo recuperare l'accesso anche da browser o device nuovo usando email OTP, senza password
4. il flusso di invito singolo del club continua a esistere, ma non apre piu la sessione definitiva senza verifica email OTP
5. un link condivisibile di gruppo puo essere pubblicato in un gruppo WhatsApp o simile e ogni click apre un onboarding individuale separato, non un accesso condiviso
6. se l'utente esiste gia nel club, il sistema recupera o riattiva lo stesso `Player` invece di creare duplicati inutili
7. la business logic gia chiusa di `/play` resta invariata: ordine match, completamento 4/4, booking finale, notifiche, ranking pubblico e tenant propagation non vanno rifondati

## Ground truth da rispettare

Tratta questi fatti come gia verificati nel repository reale attuale:

- il modulo `/play` esiste gia ed e chiuso fino a `STATO_PLAY_FINAL.md`
- `Player`, `Match`, `MatchPlayer`, `PlayerAccessToken`, `CommunityInviteToken`, notifiche private, ranking pubblico e route `/play` sono gia presenti nel codice reale anche se alcune righe storiche di `play_master.md` risultano superate
- il booking pubblico su `/` e tenant-aware e non va rotto
- la home prenotazioni pubblica reale e `frontend/src/pages/PublicBookingPage.tsx`
- esiste gia un servizio email riusabile in `backend/app/services/email_service.py` con configurazione SMTP in `backend/app/core/config.py`
- il token di sessione player resta un cookie httpOnly opaco, persistente, server-hashed, `SameSite=Lax`, `secure` quando appropriato
- il flusso corrente di invito singolo usa `CommunityInviteToken` ed emette la sessione player troppo presto rispetto al nuovo requisito OTP

## Vincoli architetturali obbligatori

- non introdurre password tradizionali
- non introdurre provider esterni di identita
- non introdurre WhatsApp OTP in questa fase: il canale OTP e solo email
- non spostare o rifondare le route canoniche gia stabilizzate di `/play`
- non rompere il booking pubblico, il checkout, il tenant routing o l'area admin
- non cambiare stack
- non creare una seconda app separata
- non introdurre dipendenze nuove se l'infrastruttura email gia presente basta davvero
- non modificare logiche di consolidamento match, join/create/leave/cancel, booking 4/4, push o ranking pubblico oltre cio che serve strettamente a tenere coerente il login community
- ogni nuova entita deve restare tenant-scoped tramite `club_id`

## Decisioni implementative da trattare come default

Se non emerge un conflitto reale nel repository, usa questi default:

- email obbligatoria al primo accesso community completato con successo
- accesso e recupero via email OTP, senza password
- `Player` esteso con email normalizzata e metadati minimi di verifica email
- i player legacy possono restare senza email fino al primo nuovo ingresso o recupero, ma ogni nuovo accesso completato deve consolidare l'email
- OTP sempre server-side con codice hashato, TTL breve e rate limit
- riuso obbligatorio di `EmailService` per l'invio email OTP, salvo impedimento tecnico reale documentato
- il singolo invito club resta monouso e nominale
- il link di gruppo e una superficie distinta dal singolo invito: multiuso, revocabile, con scadenza opzionale, auditabile, mai autenticante da solo
- il bottone in home prenotazioni deve essere evidente e portare nel flusso community senza richiedere che l'utente clicchi prima `Unisciti` o `Crea nuova partita`

## Distinzione obbligatoria tra i tre flussi di accesso

### 1. Invito singolo del club

Questo flusso esiste gia e va preservato, ma va reso coerente con l'OTP email.

Regole:

- il link resta club-scoped e monouso
- puo continuare a precompilare o portare con se `profile_name` e `phone`
- deve raccogliere email obbligatoria se non gia disponibile nel contesto dell'invito
- deve inviare OTP email e completare la sessione solo dopo verifica riuscita
- l'invito va marcato `USED` solo dopo OTP verificata e sessione player emessa
- se l'utente esiste gia, non creare un nuovo player senza motivazione forte

### 2. Link di gruppo condivisibile

Questo flusso e nuovo e distinto dal token di invito singolo.

Regole:

- il club puo generare un link condivisibile in gruppi numerosi
- il link non identifica una persona specifica e non autentica nessuno da solo
- ogni persona che clicca apre un onboarding individuale separato
- l'onboarding individuale raccoglie `profile_name`, `phone`, `email`, `privacy_accepted` e poi richiede OTP email
- dopo OTP valida il sistema crea o recupera il `Player` coerente per quel club
- il link puo essere multiuso ma deve supportare revoca, scadenza opzionale, audit e contatore di utilizzi se utile in modo sobrio
- il link di gruppo non deve riusare la semantica `accepted_player_id` del singolo invito

### 3. Recupero/rientro accesso

Questo flusso e per utenti gia esistenti che hanno perso la sessione o sono su un browser nuovo.

Regole:

- deve partire da un bottone esplicito nella home prenotazioni pubblica
- deve funzionare senza password
- deve usare email OTP come meccanismo di recupero accesso
- se esiste gia una sessione valida, il sistema puo instradare direttamente a `/c/:clubSlug/play`
- se la sessione manca o e stale, il sistema deve avviare il flusso OTP email invece di lasciare l'utente anonimo nella `PlayPage` senza un ingresso chiaro

## Direzione UX obbligatoria

Evita UX implicite o nascoste.

Direzione obbligatoria:

- introdurre una superficie esplicita di accesso community dedicata, invece di affidarsi al modal anonimo aperto da `pendingAction` in `PlayPage`
- la route frontend da implementare deve essere una route dedicata e stabile, ad esempio:
  - `/c/:clubSlug/play/access`
  - `/c/:clubSlug/play/access/:groupToken`
- `InviteAcceptPage` deve essere semplificata o resa un wrapper coerente verso la nuova superficie accesso quando il contesto e un invito singolo
- il bottone della home prenotazioni deve puntare a questa superficie dedicata
- `PlayPage` puo mostrare solo un richiamo secondario coerente per utenti anonimi, ma non deve piu essere il punto primario in cui nasce il login community

Non accetto come soluzione finale:

- lasciare `/c/:clubSlug/play` come unico punto di ingresso anonimo
- dipendere da CTA indirette come `Unisciti` o `Crea nuova partita` per aprire il flusso di riconoscimento
- mantenere il login community come modal nascosto in stato UI implicito

## Coerenza UX/UI obbligatoria

La nuova superficie di accesso community deve sembrare una pagina nativa dell'app, non una schermata auth separata o generica.

Regole obbligatorie:

- mantieni gerarchia visuale, spacing, tone of voice e componenti coerenti con `PublicBookingPage`, `InviteAcceptPage`, `PublicClubPage` e `PlayPage`
- riusa quando possibile i pattern gia presenti nel frontend reale, ad esempio `AlertBanner`, `SectionCard`, CTA con classi `btn-primary` e `btn-secondary`, header con hero coerente e branding community gia esistente
- evita layout da login tradizionale, card centrata isolata o UX da backoffice
- il flusso deve apparire come ingresso alla community del club, non come pagina account astratta
- il bottone nella home prenotazioni deve essere integrato nella UI esistente senza rompere la priorita del booking pubblico

Preferenza forte di implementazione UI:

- header coerente con il linguaggio visuale gia usato nel booking pubblico e nella community Matchinn
- copy breve e orientato all'azione: accesso, rientro, recupero senza password
- separazione chiara tra:
  - accesso individuale da link di gruppo o invito
  - recupero/rientro utente gia esistente
- nessuna introduzione di nuovi pattern grafici fuori design system locale del repo

## Modello dati minimo richiesto

Implementa il minimo set di entita e campi necessario, senza over-engineering.

### Player

Estendi `Player` in modo sobrio per supportare identita email-based coerente:

- email normalizzata `lowercase + trim`
- `email_verified_at`
- opzionale un flag o timestamp che distingua player legacy non ancora consolidati via email, solo se serve davvero

Vincoli preferiti:

- `phone` resta chiave forte gia esistente per club
- `email` deve essere trattata come identificatore di recupero per club
- evita duplicati logici sullo stesso club per stessa email verificata
- se il database o il repo rendono scomodo un vincolo unique case-insensitive puro, documenta e applica almeno una normalizzazione forte e un controllo applicativo deterministico

### OTP challenge

Aggiungi una tabella minima dedicata, ad esempio `PlayerEmailOtpChallenge` o naming equivalente chiaro.

Campi minimi attesi:

- `club_id`
- `player_id` opzionale
- `invite_id` opzionale per invito singolo
- `group_access_link_id` opzionale per link di gruppo
- `email_normalized`
- `otp_hash`
- `purpose` esplicito, ad esempio `INVITE_ACCESS`, `GROUP_ACCESS`, `ACCESS_RECOVERY`
- `expires_at`
- `consumed_at`
- `attempt_count`
- `resend_count`
- `created_at`
- `last_sent_at` o equivalente se utile

Regole:

- non salvare il codice OTP in chiaro
- TTL breve, ad esempio 5 minuti
- limite tentativi esplicito
- rate limit su resend esplicito
- se il challenge scade o viene consumato, non deve poter essere riutilizzato

### Link di gruppo

Se non emerge un conflitto reale, aggiungi una entita dedicata e distinta da `CommunityInviteToken`, ad esempio `CommunityAccessLink`.

Campi minimi attesi:

- `club_id`
- `token_hash`
- `label` o `name` opzionale per amministrazione sobria
- `expires_at` opzionale
- `revoked_at` opzionale
- `max_uses` opzionale
- `use_count` o misura equivalente se davvero utile
- `created_at`

Evita di trasformare questa entita in un CRM o campaign manager.

## Contratti API minimi richiesti

Chiudi una superficie piccola, chiara e coerente col router attuale. Non creare una costellazione di endpoint ridondanti se puoi chiudere il flusso con 2-4 endpoint sobri.

Preferenza forte:

- un flusso unificato di start/verify/resend per OTP email
- riuso dei router `play.py` e `public_play.py` dove piu coerente col contesto pubblico o privato

Minimo richiesto:

1. endpoint per avviare il challenge OTP email
2. endpoint per verificare OTP email e solo allora emettere la sessione player
3. endpoint per resend OTP email, se non riusabile il primo start in modo pulito
4. endpoint o comportamento chiaro per ottenere il contesto di accesso da link di gruppo o invito singolo

Vincoli di contratto:

- nessuna sessione definitiva prima della verifica OTP
- payload chiari e autoesplicativi
- messaggi di errore sobri e non troppo rivelatori
- nessuna enumerazione facile di email o player esistenti
- se il player esiste gia, il comportamento deve restare deterministico e non ambiguo

## Flusso prodotto preferito

### Accesso da invito singolo

1. l'utente apre `/c/:clubSlug/play/invite/:token`
2. il frontend mostra contesto invito e richiede email obbligatoria se non presente
3. il backend genera challenge OTP email
4. l'utente inserisce OTP
5. il backend verifica OTP
6. solo ora crea o recupera il `Player`, marca l'invito `USED`, emette il cookie player e redirige a `/c/:clubSlug/play`

### Accesso da link di gruppo

1. l'utente apre `/c/:clubSlug/play/access/:groupToken`
2. il frontend richiede `profile_name`, `phone`, `email`, privacy
3. il backend genera challenge OTP email
4. l'utente inserisce OTP
5. il backend verifica OTP
6. il backend crea o recupera il `Player`, emette sessione player e porta a `/c/:clubSlug/play`

### Rientro da home prenotazioni

1. in `PublicBookingPage` compare un bottone esplicito tipo `Entra o rientra nella community`
2. il bottone preserva il tenant e porta al flusso accesso community
3. se esiste gia sessione valida, il sistema instrada rapidamente alla `PlayPage`
4. se la sessione manca, richiede email OTP
5. dopo OTP valida l'utente entra nella community senza password

## Home prenotazioni: requisito obbligatorio

Il bottone in home prenotazioni non e opzionale.

Chiudi almeno:

- CTA visibile in `frontend/src/pages/PublicBookingPage.tsx`
- etichetta esplicita orientata al rientro community
- preservazione del tenant corrente
- comportamento coerente sia per utente nuovo sia per utente di ritorno

Non accetto una soluzione in cui il rientro community continui a dipendere solo dall'apertura della `PlayPage` anonima e dal click su azioni secondarie come `Unisciti` o `Crea nuova partita`.

## File reali che devi trattare come superfici primarie

Backend:

- `backend/app/models/__init__.py`
- `backend/app/schemas/play.py`
- `backend/app/api/routers/play.py`
- `backend/app/api/routers/public_play.py`
- `backend/app/services/play_service.py`
- `backend/app/services/email_service.py`
- eventuale nuova migrazione Alembic

Frontend:

- `frontend/src/App.tsx`
- `frontend/src/types.ts`
- `frontend/src/services/playApi.ts`
- `frontend/src/pages/PublicBookingPage.tsx`
- `frontend/src/pages/PlayPage.tsx`
- `frontend/src/pages/InviteAcceptPage.tsx`
- eventuale nuova pagina accesso community dedicata

Se serve un helper piccolo e dedicato per OTP o accesso community, aggiungilo, ma evita frammentazione gratuita.

## Cose da NON fare

- non introdurre password, magic link, social login o provider esterni di auth
- non spostare la route canonica community fuori da `/c/:clubSlug/play`
- non rompere il significato di `PlayerAccessToken`
- non rifondare il flusso di invite share match o i match public/shared gia chiusi, salvo il minimo necessario per allineare il login OTP
- non trasformare il link di gruppo in un invito nominativo monouso
- non aggiungere dashboard marketing, lead funnel, campagne o analytics admin
- non introdurre dipendenze email esterne se l'SMTP gia presente basta
- non modificare il flusso di prenotazione pubblica su `/` oltre l'aggiunta del bottone di ingresso/rientro community

## Strategia di backfill obbligatoria

Dato che esistono player legacy senza email nel modello attuale, devi prevedere un backfill sobrio.

Regole:

- nessun fake backfill con email inventate
- `email` puo nascere nullable per compatibilita legacy se serve davvero
- i player legacy si consolidano al primo nuovo accesso OTP riuscito
- documenta in modo esplicito l'impatto su tenant esistenti e default club

## Test richiesti

Backend, almeno:

- start challenge OTP email con invio email mockato
- verify OTP valido con emissione sessione player
- verify OTP invalido o scaduto
- limite tentativi OTP
- resend OTP con rate limit sobrio
- recupero accesso di player esistente via email OTP
- nessuna duplicazione player se email/phone esistono gia nello stesso club
- invito singolo non segnato `USED` prima della verifica OTP finale
- link di gruppo multiuso che non crea sessione senza OTP
- nessuna regressione su sessione player httpOnly esistente

Frontend, almeno:

- rendering del bottone community/rientro in `PublicBookingPage`
- navigazione corretta dal bottone home al flusso accesso community
- flusso OTP email per utente nuovo
- flusso OTP email per rientro utente esistente
- flusso invito singolo aggiornato con email OTP
- flusso link di gruppo condivisibile
- nessuna regressione evidente su `PlayPage`, `InviteAcceptPage`, routing e tenant propagation
- build finale frontend

## Validazione obbligatoria

Se tocchi il backend:

- usa `D:/Padly/PadelBooking/.venv/Scripts/python.exe`
- esegui i test mirati del perimetro OTP/accesso
- valida migrazione Alembic up/down se aggiungi tabelle o colonne

Se tocchi il frontend:

- esegui test mirati delle pagine o componenti toccati
- esegui `npm run build` se tocchi route, contratti o tipi

## Ordine di output obbligatorio

Usa esattamente l'ordine di `play_master.md`:

## 1. Prerequisiti verificati
- elenco PASS / FAIL reale

## 2. Mappa del repository rilevante
- file reali trovati e superfici toccate

## 3. Gap analysis della fase
- cosa manca oggi rispetto all'obiettivo OTP/accesso

## 4. File coinvolti
- file creati o modificati

## 5. Implementazione
- codice completo dei file necessari

## 6. Migrazioni e backfill
- nome migrazione
- strategia dati legacy
- impatto su default club e tenant esistenti

## 7. Test aggiunti o modificati
- codice completo dei test

## 8. Verifica di fine fase
- controlli eseguiti
- esito PASS / FAIL / NOT APPLICABLE
- criticita residue
- gate finale:
  - `FASE VALIDATA - si puo procedere`
  - `FASE NON VALIDATA - non procedere`

## 9. STATO_OTP.md
- stato compatto per l'eventuale fase successiva

## Controllo qualita obbligatorio

Alla fine del lavoro devi anche verificare esplicitamente che:

- l'output rispetti tutti i vincoli sopra
- non siano state introdotte password o provider auth esterni
- il booking pubblico e la business logic `/play` non siano stati alterati fuori scope
- il flusso link di gruppo sia davvero individuale e non condivida sessioni tra utenti diversi
- l'invito singolo non venga consumato prima della verifica OTP finale
- il bottone di rientro dalla home prenotazioni sia reale, visibile e tenant-aware
- non vengano inventati dati mancanti
- eventuali ambiguita residue siano segnalate solo se davvero bloccanti

Se in un punto il requisito puo essere soddisfatto con una soluzione piccola e coerente oppure con una soluzione piu ampia ma invasiva, scegli sempre la soluzione piu piccola, verificabile e coerente col repository reale.