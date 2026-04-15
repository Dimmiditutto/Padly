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

# PROMPT FASE 3 — FRONTEND COMPLETO

Usa il blocco comune come contesto fisso e considera validate le Fasi 1 e 2.

Ora esegui solo la **Fase 3**.

## Obiettivo della fase

Costruire il frontend completo, bello, moderno, mobile-first e coerente con il backend.

## Output richiesto

Fornisci il frontend completo, organizzato per file reali, includendo:

## 1. Struttura frontend
Fornisci file tree realistico del frontend React/Vite/TypeScript/Tailwind.

## 2. Setup base
Genera:
- config Vite
- Tailwind config
- entrypoint app
- router
- struttura layout

## 3. Design system base
Implementa:
- palette
- typography scale
- spacing
- button styles
- input styles
- card styles
- badge styles
- alert styles
- loading states
- empty states

## 4. Area pubblica
Implementa pagine e componenti per:
- landing / home booking
- selezione data
- selezione orario
- selezione durata
- disponibilità risultante
- form utente
- box tariffe informative
- riepilogo costi
- scelta provider pagamento
- stato checkout
- esito conferma
- esito pagamento non completato
- errore gestito bene

## 5. Area admin
Implementa pagine e componenti per:
- login admin
- dashboard prenotazioni
- filtri
- dettaglio prenotazione
- creazione prenotazione manuale
- creazione blackout
- creazione prenotazione ricorrente
- gestione stati
- marcatura saldo/completed/no-show

## 6. Stato e data fetching
Implementa il modo più semplice e robusto per il progetto:
- fetch layer
- tipi frontend
- stato locale / server state
- gestione loading/error/success

## 7. UX obbligatoria
La UI deve essere:
- realmente curata
- non anonima
- non da demo
- con gerarchia visiva forte
- con CTA chiare
- con card ben disegnate
- con ottima resa su smartphone

## 8. Coerenza API
Assicurati che il frontend consumi le API definite in Fase 2 in modo coerente.

## Requisiti di qualità
- niente JSX grezzo non organizzato
- niente UI brutta o generica
- niente componenti incoerenti
- niente CSS approssimativo
- niente hardcode evitabile
- codice reale e leggibile

## Verifica di fine fase
Esegui una validazione della fase verificando almeno:
- build frontend
- type-check TypeScript
- coerenza routing
- corretto consumo API
- smoke test area pubblica
- smoke test area admin
- coerenza tra frontend e stati business
- assenza di blocchi per la fase 4

Chiudi con:
- `FASE VALIDATA - si può procedere`
oppure
- `FASE NON VALIDATA - non procedere alla fase successiva`