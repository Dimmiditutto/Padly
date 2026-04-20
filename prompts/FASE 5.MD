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
- in locale/test il repository può continuare a usare SQLite se già presente; non cambiare questa base solo per questa fase
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

# PROMPT FASE 5 — CONSOLIDAMENTO OPERATIVO: EMAIL, LOG, JOB, REMINDER, SCADENZE

Usa il blocco comune come contesto fisso e considera validate le Fasi 1, 2, 3 e 4.

Considera inoltre questo stato attuale del repository come vincolo operativo:
- esiste già `backend/app/services/email_service.py` con `EmailService` e `EmailNotificationLog`
- esiste già `backend/app/services/booking_service.py` con `log_event`, `expire_pending_booking_if_needed`, `expire_pending_bookings` e `upcoming_reminders`
- esiste già `backend/app/core/scheduler.py` con APScheduler in-process avviato da `backend/app/main.py`
- esiste già `backend/app/services/payment_service.py` che invia conferma prenotazione e notifica admin dopo conferma pagamento
- esiste già un report admin sintetico in `backend/app/services/report_service.py` e nella route `GET /api/admin/reports/summary`
- esistono già test backend su pagamenti, expiry e coerenza base delle email

Ora esegui solo la **Fase 5** come fase di consolidamento, rifinitura e validazione operativa. Non ripartire da zero.

## Obiettivo della fase

Portare la parte operativa già esistente a uno stato coerente, verificato e pronto per Railway:
- qualità reale dei template email
- audit/business log coerente
- reminder e scadenze affidabili
- scheduler/job coerenti con il deploy reale
- gestione errori operativa chiara e testata

## Regole specifiche per questa fase

- non riscrivere ciò che è già corretto
- non introdurre Celery, Redis, code, worker separati o cron esterni se non sono davvero indispensabili
- mantieni l’approccio pragmatico attuale: scheduler semplice, in-process, compatibile con deploy singolo
- se una capacità esiste già, completala o induriscila; non duplicarla con una seconda implementazione
- non peggiorare API, nomi template o nomi evento già corretti senza un motivo reale

## Output richiesto

Implementa o completa solo i gap reali.

## 1. Email templates
Parti dai template già esistenti e portali a un livello professionale.

Template oggi presenti nel codice:
- `booking_confirmation`
- `booking_cancelled`
- `booking_expired`
- `booking_reminder`
- `admin_new_booking`

Richieste:
- mantieni template HTML reali, leggibili, puliti e in italiano
- rendi i contenuti coerenti tra utente e admin
- inserisci dati realmente disponibili nel dominio: riferimento prenotazione, data, orario, durata, caparra, saldo al campo, provider se utile
- se separare `pagamento caparra riuscito` da `prenotazione confermata` è davvero necessario rispetto al flusso attuale, aggiungi un template dedicato e collegalo al punto corretto del codice; altrimenti esplicita chiaramente che la conferma pagamento coincide con la conferma prenotazione
- non introdurre template inutili o scollegati dal flusso reale

## 2. Email service
Parti dall’`EmailService` esistente e completalo senza cambiare approccio di base.

Requisiti:
- mantieni il logging su `EmailNotificationLog`
- gestione esplicita degli esiti `SENT`, `FAILED`, `SKIPPED`
- nessun crash del flusso business se un’email fallisce
- comportamento chiaro quando SMTP non è configurato:
  - in locale/test è ammesso loggare `SKIPPED`
  - in ambienti operativi non deve restare una simulazione opaca
- migliora i log applicativi solo dove serve davvero

## 3. Booking events log
Parti da `BookingEventLog` e `log_event` già presenti.

Verifica la copertura reale degli eventi già gestiti:
- booking creato
- booking confermato via pagamento
- booking scaduto
- booking cancellato
- booking completato
- no-show
- ricorrenza creata
- saldo segnato al campo

Completa solo gli eventi mancanti davvero utili, con priorità a:
- conflitto o occorrenza ricorrente saltata con motivo
- eventuali casi limite operativi già presenti nel codice ma non ancora tracciati

Non trasformare il log in rumore.

## 4. Scheduler / jobs
Non sostituire lo scheduler corrente: esiste già APScheduler in-process.

Obiettivi:
- verificare coerenza di `expire_pending_job` e `reminder_job`
- garantire che la scadenza delle `PENDING_PAYMENT` resti idempotente
- garantire che i reminder partano solo per booking `CONFIRMED`, future e senza reminder già inviato
- evitare reminder su booking `CANCELLED`, `EXPIRED`, `COMPLETED`, `NO_SHOW`
- aggiungere job tecnici ulteriori solo se c’è un bisogno concreto già dimostrabile nel repository
- non inventare un report admin periodico se il report summary esistente è già sufficiente

## 5. Strategia Railway per job
Il repository oggi avvia lo scheduler dentro il processo web. Mantieni questa strategia semplice salvo blocchi reali.

Implementa o documenta in modo esplicito:
- deploy previsto con una sola istanza backend attiva per evitare job duplicati
- nessun secondo scheduler parallelo
- healthcheck invariato
- eventuali limiti noti dell’approccio e come gestirli in modo pragmatico su Railway

Non introdurre cambi architetturali se non sono strettamente necessari.

## 6. Error handling operativo
Definisci e verifica comportamento chiaro per:
- email fallita
- email `SKIPPED` per SMTP assente
- job fallito
- reminder su booking annullata, scaduta o non confermata
- eventi pagamento duplicati e idempotenti
- expiry invocata sia a runtime sia da scheduler senza duplicare email o eventi

Preferisci fallback espliciti e log utili, non silenzi ambigui.

## 7. Test e validazione obbligatoria
Aggiungi o aggiorna test reali solo sui gap residui.

Copri almeno:
- `EmailNotificationLog` con esiti attesi
- `BookingEventLog` per gli eventi chiave della fase
- scadenza `PENDING_PAYMENT`
- reminder corretti
- esclusione reminder su booking non eleggibili
- coerenza dello scheduler attuale
- assenza di duplicazione su expiry, reminder o webhook idempotenti se toccati

Non fermarti a test superficiali.

## Requisiti di qualità
- niente template finti o testo da demo
- niente seconda infrastruttura di job se quella attuale basta
- niente log inutili o ridondanti
- niente refactor ampio fuori perimetro
- implementazione concreta, minima e verificabile

## Verifica di fine fase
Esegui una validazione della fase verificando almeno:
- qualità e coerenza dei template email esistenti
- corretto popolamento di `EmailNotificationLog`
- corretto popolamento di `BookingEventLog`
- scadenza `PENDING_PAYMENT` via funzione e via job
- reminder corretti e non duplicati
- esclusione reminder su booking cancellate, scadute o non confermate
- coerenza della strategia Railway scelta con il deploy reale del repository
- assenza di blocchi per la fase 6

Nella sezione `Verifica di fine fase` devi riportare:
- controlli eseguiti
- esito PASS / FAIL / NOT APPLICABLE
- criticità rilevate
- correzioni applicate
- gate finale:
  - `FASE VALIDATA - si può procedere`
  - `FASE NON VALIDATA - non procedere alla fase successiva`

Chiudi con:
- `FASE VALIDATA - si può procedere` e fermati
oppure
- `FASE NON VALIDATA - non procedere alla fase successiva`