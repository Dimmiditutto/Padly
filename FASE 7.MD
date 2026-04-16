Agisci come un Senior Full-Stack Engineer, Software Architect pragmatico, Product Designer mobile-first, Payments Integrator e DevOps Engineer per Railway.

Stai costruendo una web app completa di prenotazione per 1 solo campo da padel, pronta per essere sviluppata in repository e deployata su Railway.

## Contesto fisso del prodotto

L’app deve permettere a utenti esterni di:
- vedere disponibilità e slot prenotabili
- scegliere data, orario e durata
- inserire i propri dati
- pagare una caparra online
- scegliere se pagare la caparra con Stripe oppure PayPal
- ricevere conferma prenotazione

Il saldo residuo viene pagato manualmente al campo.

L’admin deve poter gestire:
- disponibilità
- chiusure/blocchi
- prenotazioni manuali
- prenotazioni ricorrenti
- stati delle prenotazioni
- report essenziali
- pagamenti caparra e saldo al campo

## Vincoli fissi

- 1 solo campo da padel
- niente multi-club
- niente multi-campo
- niente marketplace
- niente social/chat/classifiche
- niente app nativa
- utenti esterni senza login obbligatorio nella prima versione
- area admin protetta
- campo aperto 24/7
- durata prenotabile minima: 60 minuti
- durata prenotabile massima: 5 ore
- durata selezionabile solo in blocchi da 30 minuti
- timezone: Europe/Rome
- valuta: EUR
- deploy su Railway
- backend: FastAPI + SQLAlchemy + PostgreSQL + Alembic + Pydantic v2
- frontend: React + TypeScript + Vite + Tailwind CSS
- niente overengineering
- niente dipendenze inutili

## Regole di business fisse

### Durate valide
- 60
- 90
- 120
- 150
- 180
- 210
- 240
- 270
- 300

### Caparra
- €20 fino a 90 minuti inclusi
- +€10 per ogni ulteriore blocco di 30 minuti oltre i 90 minuti

Esempi:
- 60 min = €20
- 90 min = €20
- 120 min = €30
- 150 min = €40
- 180 min = €50
- 210 min = €60
- 240 min = €70
- 270 min = €80
- 300 min = €90

### Tariffe informative da mostrare all’utente
- Tesserati: €7/ora per giocatore
- Non tesserati: €9/ora per giocatore
- 90 minuti: €10 tesserati per giocatore, €13 non tesserati per giocatore

Queste tariffe sono solo informative e non sostituiscono la caparra.

### Stati prenotazione minimi
- `PENDING_PAYMENT`
- `CONFIRMED`
- `CANCELLED`
- `COMPLETED`
- `NO_SHOW`
- `EXPIRED`

### Regole critiche
- nessuna doppia prenotazione confermata sullo stesso slot
- validazione server-side forte
- controllo finale disponibilità prima della conferma
- timeout default prenotazioni `PENDING_PAYMENT`: 15 minuti
- scaduta la prenotazione, lo slot torna disponibile
- finestra cancellazione default: 24 ore prima
- admin può creare prenotazioni ricorrenti:
  - stesso giorno della settimana
  - stesso orario
  - stessa durata
  - per N settimane
  - entro lo stesso anno solare
  - creare solo occorrenze valide
  - saltare quelle in conflitto
  - restituire report finale con create / saltate / motivi

## Regole UX/UI fisse

La UI deve essere:
- moderna
- bella
- pulita
- mobile-first
- ordinata
- con card ben disegnate
- con pulsanti grandi e chiari
- con forte gerarchia visiva
- con feedback comprensibili
- con look professionale e non da demo tecnica

Il frontend non deve sembrare:
- una demo
- un template cheap
- un backend travestito
- un form grezzo con poco CSS
- una UI anonima generata automaticamente

## Regola di comportamento

- non divagare
- non fare teoria inutile
- non proporre 10 alternative
- non cambiare stack
- non cambiare perimetro
- scegli la soluzione più pratica e implementabile
- produci output concreti
- niente pseudo-codice spacciato per codice
- niente TODO vuoti
- niente placeholder finti

## Regola di validazione obbligatoria

Alla fine di ogni fase devi aggiungere una sezione chiamata `Verifica di fine fase` con:
- controlli eseguiti
- esito PASS / FAIL / NOT APPLICABLE
- criticità rilevate
- correzioni applicate
- gate finale:
  - `FASE VALIDATA - si può procedere`
  - `FASE NON VALIDATA - non procedere alla fase successiva`

Non considerare completata una fase solo perché il codice è stato scritto. Una fase è completata solo se il codice o la progettazione della fase sono coerenti, verificati e senza blocchi evidenti per la fase successiva.

Mantieni sempre il focus sull’implementazione reale.

# PROMPT FASE 7 — RELEASE READINESS FINALE: REGRESSIONI, FRONTEND CRITICO, QA E CHECKLIST

Usa il blocco comune come contesto fisso e considera validate le Fasi 1, 2, 3, 4, 5 e 6.

Considera inoltre questo stato attuale del repository come vincolo operativo:
- esistono gia suite backend in `backend/tests/test_booking_api.py`, `backend/tests/test_payment_flows.py`, `backend/tests/test_admin_and_recurring.py` e `backend/tests/test_security.py`
- la suite backend copre gia concorrenza sullo stesso slot, provider non disponibili, webhook Stripe e PayPal idempotenti, endpoint mock disabilitato fuori development/test, expiry runtime e via scheduler, reminder, email log, ricorrenze create/saltate e hardening produzione su `SECRET_KEY`, `ADMIN_EMAIL` e `ADMIN_PASSWORD`
- esistono gia test frontend Vitest solo per `frontend/src/pages/PaymentStatusPage.test.tsx`, `frontend/src/pages/AdminDashboardPage.test.tsx`, `frontend/src/utils/adminBookingActions.test.ts` e `frontend/src/utils/format.test.ts`
- non esistono ancora test dedicati per `frontend/src/pages/PublicBookingPage.tsx`, `frontend/src/pages/AdminLoginPage.tsx` e `frontend/src/pages/AdminBookingDetailPage.tsx`, che oggi sono i tre componenti UI piu critici ancora scoperti
- esistono gia `Dockerfile`, `railway.json`, `.env.example`, `README.md`, `GET /api/health` e smoke test container documentato
- lo scheduler APScheduler in-process con `SCHEDULER_ENABLED` e lock single-court e gia coerente con il deploy Railway e non va sostituito
- la produzione gia fallisce se `SECRET_KEY`, `ADMIN_EMAIL` o `ADMIN_PASSWORD` restano placeholder, vuoti o mancanti
- questa fase non deve reinventare la strategia test: deve chiudere i gap residui e produrre il gate finale di rilascio

Ora esegui solo la **Fase 7** come fase finale di release readiness. Non ripartire da zero.

## Obiettivo della fase

Chiudere i gap residui realmente presenti prima del rilascio:
- copertura UI critica lato frontend
- ultime regression backend ad alto rischio ancora poco o non coperte
- checklist di rilascio concreta e aderente al repository
- validazione finale pragmatica con gli strumenti gia presenti

## Regole specifiche per questa fase

- non introdurre Playwright, Cypress, Selenium, CI/CD, GitHub Actions o un nuovo framework E2E se non emerge un blocker reale
- usa la base attuale: `pytest` + FastAPI `TestClient` sul backend, Vitest + Testing Library sul frontend, Docker smoke test a livello container
- non riscrivere suite backend gia robuste solo per uniformita
- se i nuovi test scoprono un bug reale, applica solo la patch minima ai file direttamente coinvolti
- non cambiare architettura pagamenti, scheduler, deploy o auth
- non aggiungere dipendenze se i tool gia presenti bastano
- evita checklist teoriche: tutto deve mappare a file, route e flussi gia presenti nel repository

## Perimetro file previsto

Lavora prima sui file esistenti e crea nuovi file solo se davvero necessari:
- `frontend/src/pages/PublicBookingPage.test.tsx`
- `frontend/src/pages/AdminLoginPage.test.tsx`
- `frontend/src/pages/AdminBookingDetailPage.test.tsx`
- `backend/tests/test_booking_api.py`
- `backend/tests/test_admin_and_recurring.py`
- `backend/tests/test_payment_flows.py`
- `README.md` solo se serve un richiamo minimo alla checklist finale
- `RELEASE_CHECKLIST.md` in root come artefatto finale della fase

## Output richiesto

Implementa o completa solo i gap reali.

## 1. Copertura frontend critica

Parti dall’implementazione reale di:
- `frontend/src/pages/PublicBookingPage.tsx`
- `frontend/src/pages/AdminLoginPage.tsx`
- `frontend/src/pages/AdminBookingDetailPage.tsx`

Aggiungi test Vitest + Testing Library mirati, senza snapshot inutili.

Copri almeno:

Per `PublicBookingPage`:
- caricamento configurazione pubblica e disponibilita iniziale
- fallback corretto del provider selezionato quando e disponibile solo Stripe, solo PayPal o nessuno dei due
- submit bloccato con feedback chiaro se non e stato scelto uno slot
- submit felice: `createPublicBooking` -> `createPublicCheckout` -> redirect via `window.location.assign`
- errore backend con `detail` esplicito mostrato all’utente
- stato “pagamenti non disponibili” con CTA disabilitata quando non ci sono provider attivi

Per `AdminLoginPage`:
- campi iniziali vuoti, nessuna credenziale precaricata
- submit con loading state e bottone disabilitato
- redirect a `/admin` su login riuscito
- messaggio di errore backend mostrato senza fallback opaco
- nessun doppio submit accidentale mentre la richiesta e in corso

Per `AdminBookingDetailPage`:
- redirect a `/admin/login` su `401` della sessione
- errore leggibile se il dettaglio booking non si carica per cause non-auth
- update stato con feedback di successo e clearing di errori precedenti
- `mark balance paid` con feedback coerente
- errore backend mostrato correttamente su action failure
- presenza condizionale del bottone `Ripristina confermata` quando lo stato lo consente

Non testare dettagli cosmetici. Testa solo il comportamento critico e i rami che proteggono il rilascio.

## 2. Regression backend residue

Non riscrivere la suite esistente. Estendi solo i gap ancora utili.

Copri almeno:

- report summary admin:
  - verifica coerenza di `GET /api/admin/reports/summary` o del service collegato con un mix reale di booking `CONFIRMED`, `PENDING_PAYMENT`, `CANCELLED` e depositi incassati
  - verifica che booking admin/manuali senza pagamento online non gonfino `collected_deposits`

- regressione temporale `Europe/Rome`:
  - aggiungi almeno un test mirato su parse o generazione slot attorno ai cambi ora legale o solare
  - se il comportamento attuale e gia corretto, lascia invariata la logica e conserva il test come guardia
  - se emerge un bug reale, correggi solo le funzioni tempo direttamente coinvolte

- coerenza finale dei flussi gia hardenizzati:
  - non rompere idempotenza webhook
  - non rompere scheduler reminder o expiry
  - non rompere fail-fast produzione sulle credenziali placeholder

Se per coprire questi punti basta aggiungere test e non serve cambiare codice, non cambiare codice.

## 3. Artefatto finale di release

Crea in root `RELEASE_CHECKLIST.md`.

Deve essere concreto, breve e operativo. Deve coprire almeno:
- env vars minime reali per produzione
- conferma che `SECRET_KEY`, `ADMIN_EMAIL` e `ADMIN_PASSWORD` non siano placeholder
- `APP_URL`, `DATABASE_URL`, SMTP, Stripe, PayPal, `SCHEDULER_ENABLED`
- healthcheck `/api/health`
- strategia Railway a singola istanza scheduler
- verifica webhook URL Stripe e PayPal
- verifiche manuali minime:
  - booking pubblico felice
  - checkout annullato
  - login admin
  - creazione booking manuale admin
  - cancellazione admin
  - completed, no-show e saldo al campo
  - report summary
- gate go/no-go finale

Non duplicare il `README.md` per intero. Il file deve essere una checklist eseguibile, non documentazione marketing.

## 4. README finale solo se serve

Aggiorna `README.md` solo se, dopo la creazione di `RELEASE_CHECKLIST.md`, manca un collegamento minimo alla checklist finale o manca una nota essenziale sui comandi di validazione finale.

Non riscrivere il README da zero.

## 5. Validazione obbligatoria

Esegui una validazione reale della fase. Copri almeno:
- backend: `cd backend && ../.venv/bin/python -m pytest tests -q`
- frontend: `cd frontend && npm run build`
- frontend: `cd frontend && npm run test:run`
- `docker build` del repository
- smoke test container su:
  - `GET /api/health`
  - `GET /`
- verifica che i nuovi test frontend siano verdi
- verifica che `RELEASE_CHECKLIST.md` sia coerente con `README.md`, `.env.example`, `Dockerfile` e `railway.json`

Se un controllo non e eseguibile nel contesto corrente, dichiaralo esplicitamente e usa il controllo equivalente piu vicino. Non segnare PASS senza evidenza.

## Requisiti di qualità

- niente nuovo framework E2E pesante se Vitest + Testing Library + pytest bastano
- niente refactor ampio di componenti o servizi solo per “pulire”
- niente checklist generica non ancorata ai flussi reali
- niente test fragili su testo casuale o markup irrilevante
- patch minime, concrete e difendibili
- nessun cambiamento a scheduler, deploy o provider di pagamento salvo bug reale emerso dai test

## Verifica di fine fase

Esegui e riporta almeno:
- controlli eseguiti
- esito PASS / FAIL / NOT APPLICABLE
- criticità rilevate
- correzioni applicate
- gate finale:
  - `FASE VALIDATA - progetto pronto per rilascio controllato`
  - `FASE NON VALIDATA - correggere prima del rilascio`

Chiudi con:
- `FASE VALIDATA - progetto pronto per rilascio controllato` e fermati
oppure
- `FASE NON VALIDATA - correggere prima del rilascio`