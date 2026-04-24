# PROMPT MIRATO - REVOCA E ROTAZIONE SHARE TOKEN /play

Usa `play_master.md` come contesto fisso. Non rimettere in discussione la logica di business gia chiusa nelle fasi precedenti. Mantieni il codice coerente col repository reale.

Agisci come:
- Senior Prompt Engineer orientato all'implementazione reale
- Senior Software Architect pragmatico
- Senior Full-Stack Engineer su FastAPI + React + TypeScript
- Senior QA tecnico rigoroso

Prima di iniziare devi leggere obbligatoriamente:
- `play_master.md`
- `STATO_PLAY_3.md`
- `backend/app/models/__init__.py`
- `backend/app/services/play_service.py`
- `backend/app/api/routers/play.py`
- `backend/app/schemas/play.py`
- `backend/tests/test_play_phase3.py`
- `frontend/src/pages/PlayPage.tsx`
- `frontend/src/pages/SharedMatchPage.tsx`
- `frontend/src/services/playApi.ts`
- `frontend/src/types.ts`

Se `STATO_PLAY_3.md` non e `PASS`, fermati e non procedere.

## Obiettivo

Introdurre un controllo reale sui link condivisi dei match `/play` con:
- revoca esplicita del link attivo
- rotazione sicura del link attivo
- compatibilita con il flusso di share gia esistente

Il risultato atteso e semplice:
- oggi il link share di un match esiste e funziona
- dopo questa lavorazione deve essere possibile disattivarlo o rigenerarlo senza cancellare il match
- i vecchi link non devono restare validi dopo una revoca o una rotazione

## Problema reale da chiudere

Oggi il token pubblico match e stabile e derivato deterministicamente. Questo e sufficiente per la Fase 3, ma non consente controllo operativo sul singolo link:
- non puoi invalidare un link finito nel gruppo sbagliato
- non puoi rigenerare un link nuovo lasciando morto quello vecchio
- non puoi introdurre una policy chiara di lifecycle del link

## Decisione implementativa da seguire

Implementa una soluzione minima ma reale basata su token opachi persistiti e hash lato server.

Default obbligatori:
- il raw token condiviso deve essere opaco e randomico, non derivato deterministicamente da `club_id` e `match_id`
- il raw token non va persistito in chiaro nel database oltre il momento di emissione verso il client
- il backend deve persistere almeno hash, stato e metadati essenziali del token attivo
- ogni match puo avere zero o un token attivo alla volta
- la rotazione deve creare un nuovo token attivo e revocare quello precedente nella stessa operazione logica
- la revoca deve lasciare il match esistente ma senza un link attivo
- un token revocato o ruotato non deve piu risolvere la shared page
- per token invalidi o revocati rispondi in modo sobrio e non informativo, preferibilmente `404`

## Compatibilita obbligatoria

Non rompere i link gia esistenti in modo indiscriminato.

Strategia minima attesa:
- prevedi una compatibilita transitoria per i token legacy gia distribuiti, almeno per i match gia creati prima della migration
- la compatibilita legacy non deve impedire il controllo futuro: dopo la prima rotazione esplicita di un match, il vecchio token legacy di quel match non deve piu essere accettato
- documenta in modo chiaro la strategia scelta in un file stato dedicato

Se trovi una soluzione piu semplice ma equivalente che non rompe i link esistenti e consente vera revoca/rotazione per singolo match, puoi usarla. Non fare refactor ampi.

## Perimetro funzionale minimo

Chiudi in modo concreto almeno questi punti:

### Backend dati

Implementa una delle due strade minime, scegliendo la meno invasiva ma reale:
- una tabella dedicata, ad esempio `MatchShareToken`, tenant-scoped e collegata a `Match`
- oppure una estensione minimale del modello `Match` che consenta token opaco persistito via hash, stato e revoca/rotazione senza ambiguita

Il modello deve consentire almeno:
- match proprietario
- `club_id`
- token hash attivo
- timestamp creazione
- timestamp revoca o invalidazione
- stato minimo necessario a distinguere `active` da `revoked`

### Backend API

Mantieni intatto il lookup pubblico di lettura gia esistente su shared match, ma aggiungi controllo esplicito del lifecycle del token.

Chiudi almeno una API privata coerente per:
- ruotare il link del match
- revocare il link del match
- ottenere il link attivo aggiornato dopo la rotazione

Il naming puo essere adattato al repository, ma deve restare chiaro. Esempi accettabili:
- `POST /api/play/matches/{match_id}/share-token/rotate`
- `POST /api/play/matches/{match_id}/share-token/revoke`

### Regole di autorizzazione

Definisci e implementa regole chiare e documentate. Default consigliato:
- solo il creator del match puo revocare o ruotare il proprio link
- il match deve essere ancora condivisibile secondo regole esplicite e coerenti con stato/data
- per match chiusi o annullati non introdurre eccezioni implicite

### Frontend minimo

Se necessario, aggiungi il minimo indispensabile nella UI `/play` per rendere la feature realmente usabile:
- azione per rigenerare link
- azione per disattivare link
- feedback chiaro ma sobrio all'utente
- gestione elegante del caso link revocato sulla shared page

Non costruire un pannello admin complesso. Fai solo il minimo coerente con la UX attuale.

## Cose che non devi fare

- non introdurre email, notifiche o workflow extra fuori scope
- non rifondare il flusso share esistente se non serve davvero
- non rompere il join gia funzionante dalla pagina condivisa
- non trasformare questa lavorazione in una nuova fase di sicurezza generalista
- non esporre il token raw nei log o in payload non necessari

## File probabilmente coinvolti

Valuta questi file prima di modificare il codice:
- `backend/app/models/__init__.py`
- `backend/app/services/play_service.py`
- `backend/app/api/routers/play.py`
- `backend/app/schemas/play.py`
- `backend/alembic/versions/*`
- `backend/tests/test_play_phase3.py`
- `frontend/src/pages/PlayPage.tsx`
- `frontend/src/pages/SharedMatchPage.tsx`
- `frontend/src/services/playApi.ts`
- `frontend/src/types.ts`

## Test richiesti

Aggiungi test reali almeno per:
- token attivo valido e condivisibile
- revoca del token attivo con link che smette di funzionare
- rotazione del token con vecchio link invalido e nuovo link valido
- regole di autorizzazione su revoke/rotate
- compatibilita legacy per i match gia esistenti, se implementi una fase transitoria

Se tocchi il frontend, aggiungi anche test mirati per:
- rigenerazione link dal flusso `/play`
- messaggio o stato corretto su shared page quando il link e revocato

## Verifica obbligatoria

Se tocchi il backend:
- usa `D:/Padly/PadelBooking/.venv/Scripts/python.exe`
- valida migration Alembic up/down se introduci tabella o colonna nuova
- esegui almeno i test mirati del modulo `/play`

Se tocchi il frontend:
- esegui i test mirati delle pagine toccate
- esegui `npm run build`

Comandi minimi attesi:
- `Set-Location 'D:/Padly/PadelBooking/backend'`
- `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_play_phase3.py -q --tb=short --maxfail=5`
- `Set-Location 'D:/Padly/PadelBooking/frontend'`
- `npm exec vitest run src/pages/PlayPage.test.tsx`
- `npm run build`

Se introduci un nuovo file test dedicato alla shared page, eseguilo esplicitamente oltre ai test sopra. Se scegli file test diversi, mantieni comunque verifiche mirate equivalenti.

## Output obbligatorio

Restituisci l'output con questo ordine:

## 1. Prerequisiti verificati
- PASS / FAIL reale

## 2. Mappa del repository rilevante
- file reali toccati

## 3. Strategia scelta
- modello dati adottato
- compatibilita legacy scelta
- regole di revoca/rotazione implementate

## 4. File coinvolti
- file creati o modificati

## 5. Implementazione
- codice completo dei file necessari

## 6. Migrazioni e backfill
- nome migration
- strategia per i link legacy gia esistenti

## 7. Test aggiunti o modificati
- codice completo dei test

## 8. Verifica finale
- comandi eseguiti
- esito PASS / FAIL reale
- eventuali limiti residui reali

## 9. STATO_REVOCA_TOKEN.md
- esito PASS / FAIL
- strategia finale di lifecycle del link
- compatibilita legacy implementata
- eventuale backlog esplicito solo se resta davvero