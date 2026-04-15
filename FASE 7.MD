# PROMPT FASE 6 — DOCKER, RAILWAY, README, DEPLOY

Usa il blocco comune come contesto fisso e considera validate le Fasi 1, 2, 3, 4 e 5.

Ora esegui solo la **Fase 6**.

## Obiettivo della fase

Rendere il progetto realmente deployabile su Railway.

## Output richiesto

Fornisci tutto ciò che serve per build, deploy e gestione ambiente:

## 1. Docker e runtime
Genera:
- `Dockerfile` reale e funzionante
- eventuale `.dockerignore`
- strategia build frontend + backend
- start command chiaro
- serving static frontend in produzione

## 2. Environment
Genera:
- `.env.example`
- elenco variabili ambiente con spiegazione sintetica
- configurazioni per database, auth, Stripe, PayPal, email, app URLs, webhook URLs

## 3. Migrazioni e startup
Definisci e implementa:
- comando migrazioni
- comando avvio
- eventuali script helper
- strategia coerente per avvio su Railway

## 4. Healthcheck
Implementa endpoint healthcheck reale e utile.

## 5. README
Genera un README serio che includa:
- overview progetto
- stack
- avvio locale
- setup env
- migrazioni
- run backend/frontend o run unificato
- test principali
- deploy Railway

## 6. Guida deploy Railway passo passo
Scrivi guida concreta, sequenziale e precisa per:
- creazione progetto Railway
- collegamento repo
- aggiunta PostgreSQL
- set env vars
- build
- deploy
- migrazioni
- verifica healthcheck
- verifica frontend
- verifica pagamenti
- eventuale dominio/custom domain

## Requisiti di qualità
- niente deploy “teorico”
- niente file Docker incompleti
- niente env vaghe
- tutto coerente con repo reale

## Verifica di fine fase
Esegui una validazione della fase verificando almeno:
- build completa
- Docker build
- avvio container
- variabili ambiente coerenti
- connessione database
- migrazioni
- healthcheck
- coerenza deploy Railway
- assenza di blocchi per la fase 7

Chiudi con:
- `FASE VALIDATA - si può procedere`
oppure
- `FASE NON VALIDATA - non procedere alla fase successiva`

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
- `FASE VALIDATA - progetto pronto per uso e test reale`
oppure
- `FASE NON VALIDATA - correggere prima del rilascio`