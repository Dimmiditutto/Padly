# BLOCCO COMUNE DA TENERE IN TESTA A OGNI FASE

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

# PROMPT FASE 1 — ARCHITETTURA, REPO, DATABASE, BUSINESS RULES

Usa il blocco comune come contesto fisso.

Ora esegui solo la **Fase 1**.

## Obiettivo della fase

Definire in modo rigoroso e implementabile:
- architettura completa
- struttura del repository
- file tree iniziale
- decisioni tecniche chiave
- schema database
- modello dati
- API surface iniziale
- regole di business formalizzate
- flussi principali utente/admin
- design system base e mappa schermate

## Output richiesto

Fornisci, in quest’ordine:

## 1. Architettura applicativa
Descrivi in modo concreto:
- backend FastAPI
- frontend React/Vite/TypeScript/Tailwind
- PostgreSQL
- migrazioni Alembic
- integrazione Stripe
- integrazione PayPal
- scheduler/job
- gestione webhooks
- auth admin
- serving frontend/backend in produzione
- config env
- strategia deploy Railway

## 2. Struttura repository
Fornisci un file tree chiaro e realistico, ad esempio:
- `backend/`
- `frontend/`
- `infra/` o equivalente se davvero utile
- file root come `Dockerfile`, `docker-compose.yml` se utile solo per locale, `README.md`, `.env.example`

Il file tree deve essere coerente con un progetto vero.

## 3. Decisioni tecniche chiave
Spiega solo le decisioni davvero importanti, ad esempio:
- auth admin
- gestione concorrenza prenotazioni
- scelta struttura API
- strategia webhook
- scheduler
- gestione timezone Europe/Rome
- strategia deploy Railway

## 4. Schema database
Definisci le tabelle minime necessarie, almeno:
- `admins`
- `customers`
- `bookings`
- `booking_payments`
- `booking_events_log`
- `blackout_periods`
- `recurring_booking_series`
- `app_settings`

Se utili, aggiungi:
- `payment_webhook_events`
- `email_notifications_log`

Per ogni tabella fornisci:
- scopo
- campi
- tipi
- vincoli
- indici
- unique constraints
- relazioni

## 5. Modello dati prenotazione
Formalizza il modello dati della prenotazione con tutti i campi necessari, compresi:
- id
- reference code
- start_at
- end_at
- duration_minutes
- status
- deposit_amount
- payment provider
- payment status
- source
- recurring_series_id
- audit timestamps
- metadata utili

## 6. Business rules formalizzate
Scrivi in modo preciso:
- durate valide
- formula caparra
- gestione caparra Stripe/PayPal
- tariffe informative
- timeout `PENDING_PAYMENT`
- regole di conferma
- regole anti-overlap
- regole blackout
- regole ricorrenze admin
- regole cancellazione
- regole reminder
- regole stato prenotazione
- logica di rilascio slot

## 7. Superficie API iniziale
Elenca gli endpoint previsti, divisi in:
- public
- admin
- payments/webhooks
- health

Per ogni endpoint indica:
- metodo
- path
- scopo
- auth richiesta o no

## 8. Flussi funzionali principali
Descrivi in modo operativo i flussi:
- booking pubblico
- pagamento Stripe
- pagamento PayPal
- conferma prenotazione
- timeout mancato pagamento
- prenotazione manuale admin
- ricorrenza admin
- cancellazione
- marking saldo/completed/no-show

## 9. Mappa UX/UI
Fornisci:
- pagine pubbliche
- pagine admin
- componenti principali
- stati UI principali
- box tariffe informative
- box caparra
- layout mobile-first
- design system base

## 10. Rischi tecnici reali
Segnala solo i rischi veri e come intendi neutralizzarli.

## Verifica di fine fase
Esegui una validazione della fase verificando almeno:
- coerenza architettura
- coerenza schema database
- coerenza repository structure
- coerenza tra business rules e modello dati
- assenza di conflitti evidenti con pagamenti e ricorrenze
- assenza di blocchi per la fase 2

Chiudi con:
- `FASE VALIDATA - si può procedere`
oppure
- `FASE NON VALIDATA - non procedere alla fase successiva`