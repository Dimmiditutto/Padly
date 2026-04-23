# Prompt 1 - Backend, dominio e API della Chat AI

Agisci come Senior Backend Engineer su questo repository FastAPI/SQLAlchemy.

Obiettivo: introdurre la foundation deterministica della Chat AI descritta in `chat_ai.md`, senza rompere il booking engine esistente e senza bypassare i vincoli multi-tenant gia attivi.

## Ancora il lavoro al codice reale

Prima di modificare il codice, allinea le scelte a questi fatti del repo:

1. `Club` esiste gia: non ricrearlo, estendilo solo se serve davvero.
2. Le route public critiche oggi usano `get_current_club_enforced`.
3. La logica slot/booking/lock e gia nel perimetro `backend/app/services/booking_service.py`.
4. Il database e shared-database multi-tenant: ogni nuova tabella applicativa deve essere scoped da `club_id`.
5. Oggi non esiste alcun dominio `play/chat` nel backend.

## Obiettivo funzionale della prima iterazione

La chat AI deve poter appoggiare questi flussi deterministici:

1. identificare un player in modo leggero e persistente
2. vedere slot disponibili nei prossimi 5 giorni per match da 90 minuti
3. vedere partite aperte
4. creare una partita aperta
5. unirsi a una partita
6. modificare una partita aperta se consentito
7. trasformare il match in booking reale solo al quarto giocatore

## Modelli da introdurre

Introduci solo il minimo dominio necessario.

### `Player`

- `id`
- `club_id`
- `name`
- `email`
- `phone` nullable
- `created_at`
- unique consigliato: `(club_id, email)`

### `PlayerAuthToken`

- `id`
- `club_id`
- `player_id`
- `token_hash`
- `type` con almeno `access` e `magic_link`
- `created_at`
- `expires_at`
- `last_used_at` nullable
- `revoked_at` nullable
- `user_agent` nullable
- `ip_address` nullable

### `Match`

- `id`
- `club_id`
- `booking_id` nullable
- `start_at`
- `end_at`
- `duration_minutes` fisso 90 nella prima iterazione
- `status` con almeno `OPEN`, `FULL`, `CANCELLED`, `COMPLETED`
- `level` nullable o enum leggero
- `notes` nullable
- `created_by_player_id`
- `max_players = 4`
- `created_at`
- `updated_at`

### `MatchPlayer`

- `id`
- `club_id`
- `match_id`
- `player_id`
- `joined_at`
- `status` con almeno `CONFIRMED`, `CANCELLED`
- unique `(match_id, player_id)`

### `ChatSession`

- `id`
- `club_id`
- `session_token`
- `metadata` nullable
- `created_at`
- `updated_at`

### `ChatMessage`

- `id`
- `club_id`
- `session_id`
- `role` con almeno `USER`, `ASSISTANT`, `TOOL`
- `content`
- `tool_name` nullable
- `tool_input` nullable
- `tool_result` nullable
- `created_at`

## Booking finale: scelta coerente con il repo attuale

Non deformare il modello booking esistente per rappresentare 4 giocatori.

Regola:

1. i partecipanti restano in `MatchPlayer`
2. la booking finale rappresenta l'occupazione del campo, non la lista completa giocatori
3. se serve distinguere il canale, aggiungi un source esplicito tipo `CHAT_MATCH` al dominio booking
4. evita di riusare `Customer` come contenitore forzato dei 4 player

## Servizi da introdurre

### `play_identity_service`

Responsabilita:

- get/create player per email scoped a club
- emissione token persistente
- hash token, non salvataggio in chiaro
- consumo magic link monouso
- revoke del token attuale

### `match_service`

Responsabilita:

- listare match aperti
- creare match su slot valido
- leggere dettaglio match
- modificare match aperti

Vincoli:

- match sempre da 90 minuti
- max 4 player
- nessuna creazione se slot occupato
- nessuna modifica se match non piu `OPEN`

### `join_match_service`

Responsabilita:

- inserire il player nel match in modo atomico
- bloccare join duplicati
- bloccare join su match full
- se si raggiunge il quarto player, attivare `complete_match`

### `complete_match_service`

Responsabilita:

- ricontrollare disponibilita reale
- usare il lock gia esistente del booking engine
- creare la booking finale una sola volta
- collegare `booking_id` al match
- aggiornare `status = FULL`
- scrivere audit log
- notificare il club senza rompere il flusso se l'email fallisce
- fare rollback coerente se lo slot non e piu disponibile

Nota importante:

non duplicare il motore availability. Crea semmai un wrapper deterministico che riusi il codice esistente con `duration_minutes = 90`.

## Route backend minime

### Identita player

- `GET /api/play/me`
- `POST /api/play/identify`
- `POST /api/play/logout`
- `POST /api/play/magic-link/request`
- `POST /api/play/magic-link/consume`

### Sessione chat

- `POST /api/chat/session`
- `POST /api/chat/message`

### Match

- `GET /api/chat/matches`
- `GET /api/chat/matches/{match_id}`
- `POST /api/chat/matches`
- `POST /api/chat/matches/{match_id}/join`
- `PATCH /api/chat/matches/{match_id}`

## Vincoli HTTP e security

1. Le route public operative devono restare coerenti con `get_current_club_enforced`.
2. Non riusare il cookie admin.
3. Introduci un cookie dedicato player, httpOnly se possibile.
4. Aggiungi rate limit almeno su:
   - `/api/play/identify`
   - `/api/play/magic-link/request`
   - `/api/play/magic-link/consume`
   - `/api/chat/message`
   - `/api/chat/matches/{match_id}/join`

## Integrazione email

Usa il provider centralizzato gia esistente del progetto.

Regola:

- nessuna configurazione SMTP per-club
- usa `notification_email` del tenant come destinatario operativo
- se l'email fallisce, il flusso principale non deve andare in errore 500 per questo motivo

## Test backend obbligatori

1. create match su slot disponibile
2. create match su slot occupato
3. join match ok
4. join duplicato rifiutato
5. quarto player crea una sola booking finale
6. rollback se lo slot non e piu disponibile
7. `GET /api/play/me` con token valido
8. re-identificazione con token assente o invalido
9. magic link request/consume
10. isolamento tenant su player, match e chat session

## Regole di implementazione

1. patch minime
2. nessun refactor generale del booking engine
3. migration Alembic unica e coerente con la head corrente
4. nomi chiari, niente layer astratti non necessari
5. se per creare la booking finale serve estrarre un helper interno dal booking engine, fallo in modo locale e testato

## Chiusura obbligatoria della fase 1

Quando la fase backend e chiusa, crea o aggiorna `STATO_CHAT_AI_1.md` nella root del repository.

Quel file non e opzionale: serve come handoff formale verso `chat_ai_2.md`.

Compilalo in modo aderente al codice realmente implementato, non alla sola intenzione iniziale.

Sezioni minime obbligatorie del file di stato:

1. `Data`
2. `Stato esecuzione` con valore chiaro tipo `PASS`, `PARTIAL` o `BLOCKED`
3. `Decisioni chiuse`
4. `Modelli introdotti o modificati`
5. `Migrazioni Alembic`
6. `Route e contratti backend disponibili`
7. `Variabili environment introdotte`
8. `Test eseguiti e risultato`
9. `Open issues o limiti residui`
10. `Prerequisiti soddisfatti per chat_ai_2`

Nel blocco `Prerequisiti soddisfatti per chat_ai_2` indica esplicitamente:

- se le route `/api/play/*` sono operative
- se le route `/api/chat/*` sono operative
- se i type contract sono stabili per il frontend
- se il layer OpenAI puo partire oppure deve attendere fix backend residui

## Criterio di completamento

Questo prompt e chiuso solo quando:

1. il backend deterministico e completo
2. le nuove route sono protette correttamente lato tenant/subscription
3. i test mirati backend passano
4. non hai rotto le suite booking/admin esistenti piu vicine al perimetro toccato
5. `STATO_CHAT_AI_1.md` esiste ed e aggiornato in modo coerente col codice realmente prodotto
