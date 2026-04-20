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
- in locale/test il repository puo continuare a usare SQLite se gia presente; non cambiare questa base solo per questa fase
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
- controllo finale disponibilita prima della conferma
- timeout default prenotazioni `PENDING_PAYMENT`: 15 minuti
- scaduta la prenotazione, lo slot torna disponibile
- policy operativa attuale: annullamento pubblico consentito fino all'inizio; refund automatico della caparra solo prima di `cancellation_window_hours`, mai nelle ultime ore
- admin puo creare prenotazioni ricorrenti:
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
- scegli la soluzione piu pratica e implementabile
- produci output concreti
- niente pseudo-codice spacciato per codice
- niente TODO vuoti
- niente placeholder finti

## Regola di validazione obbligatoria

Alla fine di ogni fase devi aggiungere una sezione chiamata `Verifica di fine fase` con:
- controlli eseguiti
- esito PASS / FAIL / NOT APPLICABLE
- criticita rilevate
- correzioni applicate
- gate finale:
  - `FASE VALIDATA - si puo procedere`
  - `FASE NON VALIDATA - non procedere alla fase successiva`

Non considerare completata una fase solo perche il codice e stato scritto. Una fase e completata solo se il codice o la progettazione della fase sono coerenti, verificati e senza blocchi evidenti per la fase successiva.

Mantieni sempre il focus sull’implementazione reale.

# PROMPT FASE 8 — COMPLETAMENTO OPERATIVO: CANCELLAZIONE PUBBLICA CON REFUND, RIPROGRAMMAZIONE ADMIN, VERIFICA NOTIFICA ADMIN

Usa il blocco comune come contesto fisso e considera validate le Fasi 1, 2, 3, 4, 5, 6 e 7.

Considera inoltre questo stato attuale del repository come vincolo operativo reale:
- esiste gia backend pubblico per cancellazione cliente via token in `backend/app/api/routers/public.py` con route `GET/POST /api/public/bookings/cancel/{cancel_token}` e la policy corrente consente l'annullamento fino all'inizio con refund automatico solo prima della soglia configurata
- esiste gia `cancel_booking(...)` in `backend/app/services/booking_service.py` e la logica di business di cancellazione va riusata e corretta in modo mirato, non riscritta da zero
- esiste gia refund automatico della caparra online nel flusso di cancellazione pubblica quando dovuto, con esito persistito sul pagamento
- il frontend espone gia un percorso self-service di cancellazione utente con riepilogo booking e stato refund
- esistono gia login admin e area admin completi in prima forma:
  - backend `backend/app/api/routers/admin_auth.py`, `backend/app/api/routers/admin_bookings.py`, `backend/app/api/routers/admin_ops.py`
  - frontend `frontend/src/pages/AdminLoginPage.tsx`, `frontend/src/pages/AdminDashboardPage.tsx`, `frontend/src/pages/AdminBookingDetailPage.tsx`
- l’admin puo gia:
  - autenticarsi
  - creare prenotazioni singole manuali
  - creare serie ricorrenti
  - creare blackout
  - cambiare stato delle prenotazioni
  - segnare saldo al campo
- le serie ricorrenti e le prenotazioni admin create oggi occupano gia gli slot tramite le regole esistenti di disponibilita; non reimplementare da zero il blocco slot
- il backend admin espone gia anche `PUT /api/admin/bookings/{id}` per aggiornare data, orario, durata e nota di una prenotazione esistente
- esiste gia `email_service.admin_notification(...)` in `backend/app/services/email_service.py`
- la notifica admin e gia inviata nel flusso di conferma pagamento tramite `backend/app/services/payment_service.py`; non duplicare questo meccanismo senza prova di un gap reale
- l’email admin contiene gia riferimento prenotazione, data, orario, durata, nome, email e telefono cliente; tratta quindi il punto email come verifica/completamento minimo e non come reimplementazione completa del sistema email
- esistono gia test backend e frontend significativi; estendili solo dove i gap reali lo richiedono

Ora esegui solo la **Fase 8** come fase di completamento operativo dei gap residui reali. Non ripartire da zero e non riscrivere funzionalita gia presenti e corrette.

## Obiettivo della fase

Chiudere solo i gap effettivi ancora aperti:
- dare all’utente esterno una cancellazione self-service realmente usabile, coerente con la policy attuale: annullamento fino all'inizio e refund automatico solo prima della soglia configurata
- permettere all’admin di modificare/riprogrammare prenotazioni esistenti senza ricrearle a mano
- verificare e completare in modo minimo la notifica email admin gia presente, evitando duplicazioni o seconda logica parallela

## Regole specifiche per questa fase

- non ricreare login admin, dashboard admin, blacklist/blackout, ricorrenze, report o auth cookie: esistono gia
- non riscrivere da zero il backend di cancellazione pubblica: esiste gia e va riusato/corretto
- non introdurre login utente pubblico
- non aggiungere nuovi provider di pagamento
- tocca Stripe o PayPal solo quanto basta per implementare il refund automatico in modo corretto e minimale
- non creare un secondo sistema email oltre a `EmailService`
- non cambiare architettura routing se non per le route frontend strettamente necessarie al nuovo flusso pubblico di cancellazione
- se una richiesta dell’utente e gia soddisfatta dal repository, documentalo implicitamente nel codice finale evitando di duplicarla
- preferisci patch minime ma complete end-to-end

## Perimetro file previsto

Lavora prima sui file esistenti. Crea nuovi file solo se davvero necessari per la UX pubblica di cancellazione.

File probabilmente coinvolti:
- `backend/app/api/routers/public.py`
- `backend/app/api/routers/admin_bookings.py`
- `backend/app/schemas/public.py`
- `backend/app/schemas/admin.py`
- `backend/app/schemas/common.py` solo se strettamente necessario
- `backend/app/services/booking_service.py`
- `backend/app/services/email_service.py` solo se emerge un gap reale nei contenuti o nel trigger
- `backend/app/services/payment_service.py` per il refund automatico e per non rompere il trigger email admin gia esistente
- `frontend/src/App.tsx`
- `frontend/src/types.ts`
- `frontend/src/services/publicApi.ts`
- `frontend/src/services/adminApi.ts`
- `frontend/src/pages/PaymentStatusPage.tsx`
- `frontend/src/pages/AdminBookingDetailPage.tsx`
- `frontend/src/pages/AdminDashboardPage.tsx` solo se davvero necessario per coerenza UX
- eventuale nuova pagina frontend dedicata alla cancellazione pubblica, solo se migliora davvero il flusso
- `backend/tests/test_booking_api.py`
- `backend/tests/test_admin_and_recurring.py`
- `backend/tests/test_payment_flows.py`
- `frontend/src/pages/PaymentStatusPage.test.tsx`
- `frontend/src/pages/AdminBookingDetailPage.test.tsx`
- eventuali nuovi test frontend sulla cancellazione pubblica solo se necessari
- `README.md` solo se serve un richiamo minimo al nuovo flusso pubblico di cancellazione

## Output richiesto

Implementa o completa solo i gap reali.

## 1. Cancellazione pubblica self-service con refund condizionato

Il backend ha gia una cancellazione via token con refund automatico quando dovuto. Il punto da preservare e documentare correttamente e la policy no-refund nelle ultime `cancellation_window_hours` ore.

Il gap reale da chiudere e mantenere il flusso pubblico realmente usabile end-to-end, esplicitando che l'annullamento resta disponibile fino all'inizio ma il refund automatico vale solo prima della soglia configurata.

Richieste:
- riusa `GET/POST /api/public/bookings/cancel/{cancel_token}` esistente, estendendolo solo se servono metadati o response piu chiari
- aggiungi o preserva un percorso UX reale e coerente per permettere al cliente di annullare senza login una prenotazione confermata fino all'inizio dello slot
- su cancellazione pubblica riuscita di una prenotazione confermata con pagamento online gia acquisito, attiva automaticamente il refund della caparra tramite il provider originario
- supporta in modo coerente i provider gia presenti nel repository, senza introdurne di nuovi
- per booking senza pagamento online o creati/admin che non hanno una caparra online da rimborsare, non tentare refund e restituisci un esito coerente
- usa `cancellation_window_hours` come soglia refund: prima della soglia rimborso automatico, nelle ultime ore nessun rimborso automatico
- la soluzione preferita deve essere sicura e minimale:
  - evita di esporre il `cancel_token` in lookup pubblici generici per `public_reference` se non e strettamente necessario
  - preferisci un link di cancellazione tokenizzato inviato o mostrato in punti gia coerenti con il flusso reale
- valuta in modo pragmatico i punti di ingresso migliori e implementane almeno uno davvero usabile:
  - link nella email di conferma prenotazione utente
  - schermata pubblica success/cancelled/error quando il token e gia disponibile in modo sicuro
  - eventuale pagina dedicata di conferma annullamento con CTA chiara
- mostra all’utente:
  - riepilogo prenotazione essenziale
  - regola di cancellazione applicata e stato del refund automatico
  - esito chiaro: annullata con refund eseguito o avviato, annullata senza refund necessario, prenotazione non trovata, prenotazione gia annullata, prenotazione gia scaduta, errore tecnico, errore refund
- mantieni la UX mobile-first, con messaggi chiari e senza esporre dettagli interni del backend
- se serve un nuovo response model o un minimo metadato aggiuntivo, aggiungilo con cautela e in modo retrocompatibile

Vincoli di business da rispettare:
- il cliente puo annullare senza login fino all'inizio della prenotazione; entro le ultime `cancellation_window_hours` ore l'annullamento resta consentito ma senza refund automatico
- una booking pubblica confermata con pagamento online acquisito deve generare refund automatico della caparra solo fuori dalla finestra no-refund
- se il refund fallisce, non restituire un falso successo silenzioso: gestisci stato ed errore in modo coerente, sicuro e verificabile
- nessuna cancellazione di booking gia cancellati o gia scaduti come se fossero casi felici
- lo slot deve tornare disponibile in modo coerente con la logica gia esistente quando l’annullamento va a buon fine
- non introdurre una seconda logica di cancellazione parallela

## 2. Riprogrammazione/modifica prenotazioni esistenti lato admin

Non ricreare login admin, manual booking o ricorrenze: esistono gia.

Il gap reale e consentire all’admin di modificare una prenotazione esistente, soprattutto data/orario/durata, senza doverla cancellare e ricreare a mano.

Richieste:
- aggiungi un endpoint admin minimale per aggiornare una prenotazione esistente
- implementa una request dedicata e tipizzata per la modifica admin
- supporta almeno questi campi:
  - `booking_date`
  - `start_time`
  - `duration_minutes`
  - `note`
  - se e davvero banale e coerente, anche dati cliente essenziali come nome, cognome, telefono, email
- integra la modifica nella UI admin esistente, preferibilmente in `AdminBookingDetailPage.tsx`, senza creare una seconda dashboard parallela
- la UX deve permettere:
  - apertura del dettaglio
  - passaggio in modalita modifica o form inline
  - salvataggio con feedback chiaro
  - visualizzazione degli errori reali backend

Regole di business da rispettare:
- usa i lock e le validazioni server-side gia esistenti dove possibile
- la modifica non deve permettere conflitti con booking gia presenti o blackout
- la modifica deve rispettare durate valide, timezone `Europe/Rome`, eventuali edge case DST gia gestiti e vincoli sullo slot futuro dove richiesto
- non permettere aggiornamenti incoerenti su stati terminali se non esiste un caso d’uso reale
- proponi una policy pragmatica e implementala in modo esplicito, ad esempio:
  - modificabile: `PENDING_PAYMENT`, `CONFIRMED`
  - non modificabile: `CANCELLED`, `COMPLETED`, `NO_SHOW`, `EXPIRED`
- se una prenotazione viene riprogrammata con successo:
  - il vecchio slot deve liberarsi
  - il nuovo slot deve risultare occupato correttamente
  - il booking event log deve registrare la modifica con payload utile e non rumoroso

Non fare un refactor ampio dei service booking. Riusa il piu possibile le validazioni esistenti con patch mirate.

## 3. Notifica email admin: verifica e completamento minimo

Tratta questo punto come verifica pragmatica, non come riscrittura da zero.

Stato attuale noto del repository:
- esiste `email_service.admin_notification(...)`
- il trigger attuale passa da `payment_service._notify_booking_confirmed(...)`
- l’email admin gia include data, orario, durata, nome, email e telefono cliente

Richieste:
- prima verifica tecnicamente il percorso reale esistente e non duplicarlo se gia corretto
- se il trigger e corretto, non aggiungere una seconda email admin su booking pending o su altri rami non richiesti
- se emerge un gap reale nei contenuti, applica solo patch minime, ad esempio:
  - includere la nota cliente se disponibile
  - rendere piu esplicita la sorgente booking se utile
  - migliorare subject o testo introduttivo senza cambiare la logica di invio
- verifica che il log su `EmailNotificationLog` resti coerente
- aggiungi test solo se servono davvero a coprire il trigger o il contenuto minimo richiesto

Importante:
- se il problema reale e solo di configurazione SMTP o di ambiente, non compensarlo con nuovo codice inutile
- il focus e garantire che il codice gia esistente copra davvero il requisito e che non manchi un ramo reale di invio

## 4. UX/UI da rispettare in Fase 8

La UX deve chiudere i gap senza introdurre schermate disallineate col resto dell’app.

Per il flusso pubblico di cancellazione:
- visual sobrio, rassicurante e leggibile
- card di riepilogo prenotazione
- CTA unica e chiara
- copy esplicito su annullamento fino all'inizio e su assenza di refund automatico nelle ultime `cancellation_window_hours` ore
- esiti distinti e non ambigui, compreso il caso di refund fallito o non necessario

Per il flusso admin di modifica prenotazione:
- non trasformare `AdminBookingDetailPage` in un form ingestibile
- privilegia un pannello edit compatto, chiaro e mobile-friendly
- separa bene azioni distruttive, azioni di stato e azioni di modifica dati/orario
- evita duplicazione di moduli gia presenti nella dashboard se basta riusare pochi campi coerenti

## 5. Test richiesti

Non riscrivere la suite esistente. Estendi solo i punti necessari.

Copri almeno:

Backend:
- cancellazione pubblica riuscita fuori dalla soglia no-refund con refund automatico su booking pagato online
- cancellazione pubblica riuscita senza tentare refund su booking che non ha caparra online da rimborsare
- errore di refund gestito in modo coerente senza falso esito positivo
- cancellazione pubblica di booking gia cancellato o scaduto con esito coerente
- riprogrammazione admin riuscita su slot valido
- riprogrammazione admin bloccata su slot in conflitto o blackout
- riprogrammazione admin bloccata su stato non modificabile
- verifica che il vecchio slot si liberi e il nuovo risulti occupato dopo la modifica
- verifica che la notifica admin esistente continui a partire sul ramo corretto, senza duplicazioni, se tocchi il relativo codice

Frontend:
- flusso pubblico di cancellazione con successo e messaggio refund coerente
- messaggio coerente su token non valido o booking non disponibile
- messaggio coerente su errore tecnico o refund fallito
- `AdminBookingDetailPage` con modalita modifica/salvataggio riuscito
- `AdminBookingDetailPage` con errore backend su salvataggio modifica
- nessuna regressione sulle azioni admin gia presenti

## 6. Vincoli di non regressione

Devi preservare esplicitamente cio che e gia corretto:
- login admin esistente
- dashboard admin esistente
- creazione prenotazione manuale admin
- creazione ricorrenze admin
- blackout admin
- status transitions admin gia supportate
- balance paid al campo
- flussi Stripe e PayPal esistenti
- reminder, expiry e release slot gia presenti
- email utente/admin gia funzionanti salvo piccoli completamenti motivati

Se durante i test emerge un bug reale in questi flussi, applica solo la patch minima necessaria e dichiarala chiaramente.

## 7. Validazione obbligatoria

Esegui una validazione reale della fase. Copri almeno:
- `cd /workspaces/PadelBooking && (cd backend && ../.venv/bin/python -m pytest tests -q) && (cd frontend && npm run build && npm run test:run)`
- se il terminale del workspace fallisce con il provider filesystem, usa il workaround equivalente gia verificato nel repository e dichiaralo esplicitamente
- verifica manuale o semi-manuale del nuovo flusso di cancellazione pubblica
- verifica manuale o semi-manuale della riprogrammazione admin
- verifica che il dettaglio booking admin resti coerente dopo modifica o annullamento

## Requisiti di qualita

- nessun refactor architetturale ampio
- nessuna seconda implementazione di feature gia esistenti
- patch minime ma complete end-to-end
- test mirati ai gap reali
- nessuna esposizione inutile di token sensibili in API pubbliche generiche
- nessuna duplicazione delle email admin gia corrette
- nessun cambiamento cosmetico non motivato

## Verifica di fine fase

Riporta almeno:
- controlli eseguiti
- esito PASS / FAIL / NOT APPLICABLE
- criticita rilevate
- correzioni applicate
- gate finale:
  - `FASE VALIDATA - si puo procedere`
  - `FASE NON VALIDATA - non procedere alla fase successiva`

Chiudi con:
- `FASE VALIDATA - si puo procedere` e fermati
oppure
- `FASE NON VALIDATA - non procedere alla fase successiva`