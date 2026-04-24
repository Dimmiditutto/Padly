# PROMPT MASTER - MODULO /play

Agisci come:
- Senior Prompt Engineer orientato all'implementazione reale
- Senior Software Architect pragmatico
- Senior Full-Stack Engineer su FastAPI + React + TypeScript
- Senior QA tecnico rigoroso

Il tuo compito non e produrre teoria. Devi guidare l'implementazione reale del modulo `/play` nel repository corrente di PadelBooking, rispettando il codice esistente, i vincoli di business gia decisi e la roadmap incrementale piu sicura.

## Obiettivo prodotto

Implementare un modulo community play deterministico, club-specifico e coerente con il repository reale.

Il cuore del prodotto target e:
- pagina canonica `/c/{club_slug}/play`
- motore di consolidamento delle partite aperte
- focus sul completamento di match esistenti prima della creazione di nuovi match
- nessun uso di LLM o AI come motore principale

## Decisioni consolidate da rispettare

Queste decisioni sono gia prese e non vanno rimesse in discussione salvo conflitto tecnico reale col repository:

- `/play` e deterministica, non chat-centrica
- il percorso canonico e club-specifico: `/c/{club_slug}/play`
- `/play` semplice puo esistere solo come alias o redirect verso il club di default, non come route canonica
- ordine di priorita in pagina:
  1. match 3/4
  2. match 2/4
  3. match 1/4
  4. solo dopo slot liberi o creazione nuovo match
- match da 90 minuti fissi
- match completo a 4 giocatori
- completamento del match al quarto giocatore in modo transazionale e deterministico
- onboarding leggero senza password tradizionale
- player access token persistente in cookie httpOnly
- due onboarding distinti:
  - invito community del club via WhatsApp
  - self-service onboarding da share match
- privacy obbligatoria prima dell'ingresso in community
- profilo probabilistico utente attivo da subito ma semplice
- notifiche v1 semplici e deterministiche; notifiche mirate solo in fase successiva
- niente chat generale stile WhatsApp
- niente LLM nel flusso v1

## Stato reale del repository da rispettare

Questi fatti sono gia verificati nel codice attuale e vanno presi come ground truth:

- il repository e gia multi-tenant shared-database con `Club` come tenant root
- esistono gia `Club`, `ClubDomain`, `Admin`, `Customer`, `Court`, `Booking`, `BookingPayment`, `BookingEventLog`, `BlackoutPeriod`, `RecurringBookingSeries`, `AppSetting`, `PaymentWebhookEvent`, `EmailNotificationLog`, `ClubSubscription`
- esiste gia il supporto multi-campo con `Court`, `court_id` e disponibilita raggruppata per campo
- il booking pubblico attuale vive su `/` e non va rotto
- il frontend attuale usa React Router e oggi non espone ancora `/play`
- il frontend propaga il tenant via query `?tenant=` e header `x-tenant-slug`
- il backend risolve il tenant via host o slug query/header, non via route path backend dedicata
- l'area admin usa cookie httpOnly e non va rotta
- esiste gia logica critica di booking in `backend/app/services/booking_service.py`
- esistono gia scheduler, email operative, pagamenti Stripe/PayPal e test backend/frontend consistenti
- oggi non esistono ancora `Player`, `Match`, `MatchPlayer`, invite token community, player access token, push subscription o profilo probabilistico nel codice reale

## Vincoli architetturali obbligatori

- non sostituire o rompere il booking pubblico attuale su `/` nella prima iterazione
- non eliminare o rifondare la logica booking esistente
- non introdurre chat AI, ranking fantasy, marketplace, classifiche o feature fuori scope
- non cambiare stack
- non creare una seconda app separata
- non inventare integrazioni che il repo non supporta gia senza motivazione forte
- riusa Club come tenant root e Court come risorsa reale prenotabile
- ogni nuova entita del modulo play deve essere tenant-scoped tramite `club_id`
- i route param frontend `:clubSlug` devono convivere con la propagazione tenant gia esistente via query/header verso le API

## Decisioni implementative da trattare come default

Se non emerge un conflitto reale nel repository, usa questi default:

- aggiungi nuove route frontend senza rimuovere quelle attuali
- route canoniche frontend:
  - `/c/:clubSlug/play`
  - `/c/:clubSlug/play/invite/:token`
  - `/c/:clubSlug/play/matches/:shareToken`
- eventuale `/play` semplice solo come redirect verso `default-club`
- il modulo `/play` non usa checkout online per completare il match in v1
- quando il quarto giocatore completa il match, il backend crea una booking finale coerente con il motore esistente, preferendo il pattern piu vicino alle prenotazioni manuali/admin e introducendo un source dedicato solo se serve davvero
- non sovraccaricare `Customer` per rappresentare il giocatore community: usa una entita `Player` dedicata
- il token player deve essere opaco, persistente, host-only, httpOnly, `SameSite=Lax`, `secure` quando appropriato, durata 90 giorni, hash salvato lato server
- l'invite token deve essere opaco, monouso, con scadenza, audit e revoca

## Fasi consigliate

Implementa il modulo `/play` in 4 fasi collegate:

1. `play_1.md` - foundation backend, dominio, migrazioni, contratti API e identita base
2. `play_2.md` - frontend `/play`, UX deterministica, invite accept e shared match page
3. `play_3.md` - join/create/complete transaction-safe, anti-frammentazione e share flow completo
4. `play_4.md` - notifiche v1, web push foundation, profilo probabilistico leggero e retention

Ogni fase deve creare un file stato dedicato:
- `STATO_PLAY_1.md`
- `STATO_PLAY_2.md`
- `STATO_PLAY_3.md`
- `STATO_PLAY_4.md`

La fase successiva deve leggere il file stato precedente prima di proporre o modificare codice.

## Regola di collegamento tra fasi

La fase N+1 non parte da zero. Deve:
- leggere `play_master.md`
- leggere `STATO_PLAY_N.md`
- verificare che la fase precedente sia `PASS`
- riusare contratti dati, route, naming, migrazioni e decisioni gia consolidate
- non ridefinire modelli o API gia chiusi senza motivazione tecnica esplicita

## Regole di output obbligatorie per ogni fase

Ogni fase deve produrre output con questo ordine:

## 1. Prerequisiti verificati
- elenco PASS / FAIL reale

## 2. Mappa del repository rilevante
- file reali trovati e superfici toccate

## 3. Gap analysis della fase
- cosa manca oggi rispetto all'obiettivo della fase

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

## 9. STATO_PLAY_N.md
- stato compatto per la fase successiva

## Validazione obbligatoria

Se tocchi il backend:
- usa `D:/Padly/PadelBooking/.venv/Scripts/python.exe`
- verifica almeno i test mirati del modulo toccato
- valida migrazioni Alembic up/down quando introduci tabelle o colonne

Se tocchi il frontend:
- esegui test mirati della/e pagina/e toccata/e
- esegui build con `npm run build` se la fase tocca contratti o routing

## Qualita attesa dei prompt di fase

Ogni prompt di fase deve essere:
- completo ma non verboso inutilmente
- concreto sui file reali
- rigido sui vincoli di business gia decisi
- esplicito su cio che non va rotto
- progettato per evitare refactor ampi non necessari

Non lasciare ambiguita su:
- route canoniche e alias
- modelli dati
- cookie/token
- strategia di completamento del match
- compatibilita con booking esistente
- tenant propagation

Questo file e la source of truth dei prompt `/play`. Le singole fasi devono specializzarlo, non contraddirlo.