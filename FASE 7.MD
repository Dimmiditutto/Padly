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

# PROMPT FASE 7 — TEST, HARDENING, CASI LIMITE, RELEASE CHECKLIST

Usa il blocco comune come contesto fisso e considera validate tutte le fasi precedenti.

Ora esegui solo la **Fase 7**.

## Obiettivo della fase

Chiudere il progetto con:
- test strutturati
- casi limite
- smoke test reali
- test E2E/integration-like
- checklist finale di rilascio
- note di hardening successive

## Output richiesto

Fornisci:

## 1. Strategia test
Definisci una strategia pragmatica e reale per:
- unit test
- integration test
- API test
- test DB
- test E2E o smoke test
- test pagamenti simulati dove opportuno

## 2. Test suite minima
Specifica e, dove richiesto, genera i test minimi davvero necessari per il progetto.

## 3. Casi limite obbligatori
Copri almeno:
- due utenti quasi contemporanei sullo stesso slot
- pagamento Stripe riuscito con callback lenta
- pagamento PayPal completato con stato frontend non aggiornato subito
- utente che abbandona checkout
- booking `PENDING_PAYMENT` che scade
- admin che crea blackout in conflitto
- ricorrenza con alcune occorrenze in conflitto
- reminder che non devono partire su prenotazioni cancellate
- timezone estate/inverno Europe/Rome
- webhook duplicato

## 4. Release checklist
Genera checklist finale completa per:
- backend
- frontend
- pagamenti
- email
- scheduler
- deploy Railway
- variabili ambiente
- healthcheck
- DB
- webhook URLs
- test manuali finali

## 5. Hardening roadmap
Indica solo i miglioramenti successivi davvero utili, separando:
- non bloccanti per MVP
- consigliati prima di crescere di traffico

## Requisiti di qualità
- niente checklist superficiali
- niente casi limite banali
- test e verifiche orientati ai veri rischi del progetto

## Verifica di fine fase
Esegui una validazione finale verificando almeno:
- coerenza complessiva progetto
- copertura dei flussi critici
- assenza di blocchi evidenti al rilascio
- readiness per deploy e test reale
- consistenza tra backend, frontend, pagamenti, job ed email

Chiudi con:
- `FASE VALIDATA - progetto pronto per uso e test reale` e fermati
oppure
- `FASE NON VALIDATA - correggere prima del rilascio`