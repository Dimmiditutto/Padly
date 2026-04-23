# Prompt Master - Chat AI PadelBooking

Leggi prima:

1. `chat_ai.md`
2. `README.md`
3. `backend/app/api/deps.py`
4. `backend/app/services/booking_service.py`
5. `frontend/src/pages/PublicBookingPage.tsx`

Obiettivo: implementare la feature Chat AI descritta in `chat_ai.md` come nuova esperienza pubblica `/play`, coerente con la logica di business reale del repository e senza rompere i flussi booking/admin gia esistenti.

## Decisione modello OpenAI

Usa `gpt-4.1-mini` come modello runtime della chat AI.

Motivazione:

- il dominio e chiuso e tool-based
- il modello deve interpretare linguaggio naturale e restituire JSON strutturato, non fare ragionamento open-ended
- serve latenza bassa e costo controllato
- il backend resta la sola fonte di verita

Vincolo architetturale:

- rendi il modello configurabile via env `OPENAI_MODEL`, ma usa `gpt-4.1-mini` come default iniziale
- usa una sola integrazione OpenAI centralizzata, non chiamate sparse nel codice
- nessuna chiamata reale a OpenAI nei test

## Verita del repo attuale da rispettare

1. Il backend reale e FastAPI multi-tenant shared-database con `Club` come tenant root.
2. Le route admin operative usano `get_current_admin_enforced`.
3. Le route public operative critiche usano `get_current_club_enforced`.
4. Oggi non esistono route `/api/play/*`, `/api/chat/*`, modelli `Match`, `Player`, `ChatSession` o layer LLM di prodotto.
5. La logica di availability e lock vive gia nel booking engine corrente, in particolare nel perimetro di `booking_service.py`.
6. La UI pubblica esistente e tenant-aware via query param e axios layer; la nuova `/play` deve seguire la stessa logica.
7. Il dominio booking attuale non va sostituito: la chat AI deve aggiungere un nuovo dominio applicativo sopra il motore esistente.

## Vincoli non negoziabili

1. Nessun chatbot generico.
2. Nessuna scrittura diretta a database da parte del modello.
3. Nessuna decisione finale di disponibilita presa dal modello.
4. Nessuna booking finale prima di 4 giocatori confermati.
5. Durata match fissa a 90 minuti nella prima iterazione.
6. Tutte le query e scritture restano scope-aware per `club_id`.
7. Nessun refactor trasversale del booking pubblico/admin gia esistente.
8. Nessun overengineering: patch minime ma complete.

## Scelta di design coerente con il codice attuale

1. Mantieni separato il dominio `Match` dal dominio `Booking`.
2. Non forzare i 4 giocatori nella tabella `customers`: i partecipanti vivono in `Player` e `MatchPlayer`.
3. La booking finale puo restare con `customer_id = null` se serve, ma deve essere collegata al match e tracciata in modo esplicito.
4. Se serve distinguere la booking creata dal match, aggiungi un nuovo source esplicito al dominio booking invece di riusare in modo ambiguo `ADMIN_MANUAL` o `PUBLIC`.
5. Riusa il motore slot esistente tramite un service deterministic wrapper, non duplicare la logica availability.

## Sequenza corretta di implementazione

### Step 1 - Fondamenta backend deterministiche

- modelli nuovi: `Player`, `PlayerAuthToken`, `Match`, `MatchPlayer`, `ChatSession`, `ChatMessage`
- migration Alembic unica e coerente con la chain attuale
- servizi: identity, match, join, complete_match, chat session storage
- route public nuove: `/api/play/*` e `/api/chat/matches/*`

### Step 2 - Frontend pubblico `/play`

- pagina `PlayPage`
- board partite aperte
- chat panel
- action cards
- join rapido con identita leggera persistente
- piena compatibilita tenant-aware

### Step 3 - Integrazione LLM leggera

- adapter OpenAI isolato
- output strutturato `{ text, actions[] }`
- tool calling chiuso su pochi tool deterministici
- history corta
- fallback sicuro in caso di ambiguita

### Step 4 - Hardening e test

- test backend su create/join/complete/rollback/token
- test frontend su `/play`, azioni, riconoscimento player
- test integrazione con LLM mockato
- zero regressioni sulle suite attuali

## Handoff obbligatorio tra i prompt

Per mantenere coerenza tra backend foundation e fase frontend/LLM, usa un file di stato intermedio come nelle fasi SaaS del repository.

Regola:

1. `chat_ai_1.md` deve chiudersi creando o aggiornando `STATO_CHAT_AI_1.md`
2. `chat_ai_2.md` deve iniziare leggendo `STATO_CHAT_AI_1.md`
3. `chat_ai_2.md` non deve ridefinire contratti backend gia chiusi in `chat_ai_1.md` senza prima verificare il file di stato e il codice reale
4. se `STATO_CHAT_AI_1.md` manca o e incoerente col codice, va prima riallineato e solo dopo puo partire la fase 2

## Deliverable attesi

1. Nuovo dominio dati coerente con il repo attuale.
2. Nuove route public `/api/play/*` e `/api/chat/*` coerenti con multi-tenant e subscription enforcement.
3. Nuova pagina frontend `/play` mobile-first.
4. Adapter OpenAI configurabile con default `gpt-4.1-mini`.
5. Prompt runtime ristretto e tool-based, senza testo libero come unica fonte di UI.
6. Test mirati backend e frontend.

## Cose da non fare

- non cambiare i flussi di prenotazione pubblica esistenti come entrypoint principale
- non spostare la chat dentro l'admin
- non introdurre login/password classico per i player
- non fare chiamate OpenAI direttamente dai componenti React
- non usare il modello per leggere o scrivere dati arbitrari
- non creare una prima versione multi-campo o multi-match complessa

## Output richiesto al coding agent

Quando esegui questo prompt:

1. implementa prima il backend deterministico
2. valida con test mirati
3. implementa poi il frontend `/play`
4. integra infine il layer OpenAI con mock testabile
5. riporta i file toccati, i test eseguiti e gli eventuali tradeoff residui

Se serve dividere il lavoro, usa in sequenza:

1. `chat_ai_1.md` per backend, dominio e API, con chiusura obbligatoria in `STATO_CHAT_AI_1.md`
2. `chat_ai_2.md` per frontend, orchestrazione LLM e test finali, leggendo prima `STATO_CHAT_AI_1.md`
