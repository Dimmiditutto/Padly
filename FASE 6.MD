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

# PROMPT FASE 6 — CONSOLIDAMENTO DEPLOY: DOCKER, RAILWAY, README, HEALTHCHECK

Usa il blocco comune come contesto fisso e considera validate le Fasi 1, 2, 3, 4 e 5.

Considera inoltre questo stato attuale del repository come vincolo operativo:
- esistono già `Dockerfile`, `.dockerignore`, `.env.example`, `README.md` e `railway.json` in root
- il `Dockerfile` fa già build del frontend Vite e copia l’output in `frontend_dist`
- `backend/app/main.py` serve già la SPA buildata e gestisce fallback su `frontend_dist` o `frontend/dist`
- esiste già `GET /api/health`
- `backend/app/core/config.py` espone già le env principali, incluso `SCHEDULER_ENABLED`
- l’avvio container esegue già migrazioni Alembic e poi Uvicorn
- il deploy previsto dal repository è un solo servizio applicativo che serve backend API + frontend statico, con PostgreSQL Railway separato

Ora esegui solo la **Fase 6** come fase di consolidamento deploy e documentazione operativa. Non ripartire da zero.

## Obiettivo della fase

Portare gli artefatti di deploy già presenti a uno stato realmente coerente, verificato e pronto per Railway.

## Regole specifiche per questa fase

- non rigenerare file già corretti solo per uniformità
- non introdurre `docker-compose`, `Procfile`, Nginx, supervisor, CI/CD, servizi separati frontend/backend o altre infrastrutture se non esiste un blocker reale
- mantieni l’architettura corrente: un solo container applicativo che serve API e frontend buildato
- mantieni SQLite in locale/test se il repository la usa già; PostgreSQL resta il target Railway
- non aggiungere env vars non consumate dal codice
- se un’informazione è derivabile da `APP_URL` o dalle route esistenti, documentala nel `README.md` invece di inventare nuove config
- non spostare endpoint o bootstrap esistenti per ragioni estetiche
- preferisci patch minime e verificabili

## Perimetro file previsto

Lavora prima sui file già presenti. Modificali solo se emerge un gap reale:
- `Dockerfile`
- `.dockerignore`
- `.env.example`
- `railway.json`
- `README.md`
- `backend/app/main.py`
- `backend/app/core/config.py`
- file backend direttamente coinvolti in healthcheck o startup solo se davvero necessario

## Output richiesto

Implementa o completa solo i gap reali.

## 1. Docker e runtime

Parti da `Dockerfile` e `.dockerignore` esistenti.

Verifica e correggi solo se serve:
- build multi-stage frontend + backend coerente con la struttura reale del repository
- copia dell’output frontend in `frontend_dist`
- start command coerente con il runtime reale: migrazioni Alembic + Uvicorn
- uso corretto di `PORT` in ambiente Railway
- dipendenze di sistema davvero necessarie e niente step inutili
- `.dockerignore` coerente con root repo, build output, cache, virtualenv e database locali
- nessun secondo runtime dedicato al frontend

Non introdurre script helper separati se il `CMD` attuale basta già.

## 2. Serving frontend e bootstrap applicazione

Parti da `backend/app/main.py` e `backend/app/core/config.py`.

Verifica e correggi solo se serve:
- serving della SPA da `/`
- fallback corretto per asset statici e route frontend
- compatibilità tra `frontend_dist` in container e `frontend/dist` in locale
- coerenza CORS con `APP_URL` e sviluppo locale
- bootstrap scheduler già esistente senza rompere il deploy Railway

Non creare un frontend service separato se il backend serve già correttamente la build.

## 3. Environment reale

Parti da `.env.example` e dalle settings esistenti.

Allinea e completa solo ciò che il codice usa davvero:
- app name, env, url e api prefix
- secret/admin auth
- database
- timezone e scheduler
- SMTP
- Stripe
- PayPal
- rate limit

Richieste:
- distingui chiaramente variabili minime obbligatorie da variabili opzionali
- mantieni chiara la differenza tra locale/test e produzione
- non forzare PostgreSQL in locale se il repository continua a funzionare con SQLite
- se gli URL webhook sono derivati da `APP_URL` e dalle route esistenti, documentali nel README senza introdurre env dedicate inutili

## 4. Railway config e startup

Parti da `railway.json`, `Dockerfile`, README e startup reale.

Verifica e correggi solo se serve:
- builder `DOCKERFILE`
- `healthcheckPath` coerente con `/api/health`
- restart policy sensata
- strategia deploy con un solo servizio applicativo + database Railway
- strategia migrazioni coerente con il comando di start già presente
- strategia `SCHEDULER_ENABLED` coerente con il deploy reale:
  - una sola istanza designata con scheduler attivo
  - eventuali repliche web con `SCHEDULER_ENABLED=false`

Non introdurre worker, cron separati o process types aggiuntivi se il repository non li richiede davvero.

## 5. README operativo

Parti dal `README.md` esistente e portalo a livello operativo senza riscriverlo inutilmente da zero.

Deve includere in modo coerente con i file reali:
- overview progetto
- stack
- struttura repository
- setup env
- avvio locale backend e frontend
- migrazioni Alembic
- test backend e frontend
- build Docker
- smoke test container
- deploy Railway passo-passo
- healthcheck
- strategia scheduler su Railway
- note pratiche su Stripe, PayPal, SMTP e URL webhook reali
- eventuali limiti noti reali, senza teoria inutile

## 6. Guida deploy Railway concreta

Scrivi o completa una guida sequenziale e precisa che copra almeno:
1. creazione progetto Railway
2. collegamento repository
3. aggiunta PostgreSQL Railway
4. configurazione env vars minime
5. build Docker
6. primo deploy
7. esecuzione migrazioni tramite start command già previsto
8. verifica `GET /api/health`
9. verifica SPA servita dal backend
10. verifica login admin
11. verifica pagamenti Stripe e PayPal con URL reali coerenti al dominio Railway
12. eventuale custom domain

La guida deve essere coerente con un solo servizio applicativo che serve frontend + API.

## 7. Validazione obbligatoria

Esegui una validazione reale della fase. Copri almeno:
- test backend
- build frontend
- test frontend
- `docker build`
- smoke test del container
- coerenza env vars/settings
- coerenza `railway.json`
- coerenza `README.md`
- assenza di blocchi per la fase 7

Se un controllo non è eseguibile nel contesto corrente, dichiaralo esplicitamente e usa il controllo equivalente più vicino. Non segnare PASS senza evidenza.

## Requisiti di qualità

- niente deploy teorico o scollegato dal repository reale
- niente env inventate
- niente file Docker incompleti
- niente refactor ampio fuori perimetro
- niente documentazione che contraddice il runtime effettivo
- patch minime, concrete e verificabili

## Verifica di fine fase

Esegui e riporta almeno:
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