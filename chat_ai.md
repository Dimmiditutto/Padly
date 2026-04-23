# Chat AI — Riassunto implementativo completo

## Obiettivo della chat AI

La chat AI non deve essere un chatbot generico.  
Deve essere una **interfaccia conversazionale** sopra un motore applicativo rigoroso che consente agli utenti di:

- vedere slot disponibili nei successivi 5 giorni
- vedere partite aperte
- creare una partita
- unirsi a una partita
- modificare una partita aperta
- trasformare automaticamente una partita completa in una booking reale solo quando si raggiungono 4 giocatori

La chat deve quindi migliorare la UX, non sostituire la logica di business.

---

## Principio architetturale fondamentale

La chat AI deve essere costruita su **due livelli separati**:

### 1. Backend deterministico
È il motore vero dell’app.  
Decide e valida:

- disponibilità slot
- creazione match
- join match
- modifica match
- regole di capienza
- lock anti-doppia prenotazione
- creazione booking finale
- notifiche email
- audit log

### 2. LLM leggero
Serve solo a:

- interpretare linguaggio naturale
- capire l’intento dell’utente
- produrre una risposta breve in italiano
- restituire azioni strutturate da mostrare in UI
- proporre alternative se uno slot non è disponibile

L’LLM **non deve mai**:

- scrivere direttamente sul database
- decidere se uno slot è realmente disponibile
- creare booking da solo
- eseguire join direttamente senza passare da endpoint backend
- bypassare regole di business

Conclusione:  
**il backend è l’unica fonte di verità; l’LLM è solo uno strato di interpretazione e UX.**

---

## Modello di dominio corretto

La chat AI non deve lavorare direttamente sulle booking pubbliche esistenti.  
Deve lavorare su un dominio separato e più adatto alla logica “trova partita / unisciti / completa il match”.

## Entità principali

### Match
Rappresenta la partita aperta.

Campi chiave:
- `id`
- `club_id`
- `booking_id` nullable
- `start_at`
- `end_at`
- `duration_minutes = 90`
- `status = OPEN | FULL | CANCELLED | COMPLETED`
- `level`
- `notes`
- `created_by_player_id`
- `max_players = 4`
- `created_at`
- `updated_at`

Regole:
- durata fissa sempre 90 minuti
- capienza fissa sempre 4 giocatori
- la booking finale viene creata solo quando il match arriva a 4/4

### Player
Utente leggero, senza password.

Campi chiave:
- `id`
- `club_id`
- `name`
- `email`
- `phone` opzionale
- `created_at`

Vincolo consigliato:
- unique `(club_id, email)`

Ruolo:
- identificare l’utente in modo leggero
- riutilizzare lo stesso profilo per partite future

### MatchPlayer
Join table tra match e player.

Campi chiave:
- `id`
- `match_id`
- `player_id`
- `joined_at`
- `status = CONFIRMED | CANCELLED`

Vincolo:
- unique `(match_id, player_id)`

Ruolo:
- tracciare chi si è unito alla partita
- impedire doppio join dello stesso player

### ChatSession
Sessione conversazionale.

Campi chiave:
- `id`
- `club_id`
- `session_token`
- `metadata`
- `created_at`
- `updated_at`

Ruolo:
- mantenere il contesto della conversazione
- associare i messaggi di chat alla stessa sessione browser

### ChatMessage
Singolo messaggio della chat.

Campi chiave:
- `id`
- `session_id`
- `role = USER | ASSISTANT | TOOL`
- `content`
- `tool_name`
- `tool_input`
- `tool_result`
- `created_at`

Ruolo:
- cronologia conversazione
- auditabilità
- debugging
- ricostruzione tool calls

### Club
Contenitore tenant/configurazioni.

Campi minimi utili:
- `id`
- `name`
- `slug`
- `notification_email`
- `llm_enabled`
- `created_at`

Ruolo:
- configurazioni notifica
- base per evoluzione multi-tenant successiva

---

## Identità utente: soluzione corretta e veloce

La chat non deve richiedere login classico con password.  
La soluzione giusta è una **identità leggera persistente**.

## Fase 1 — Primo riconoscimento
La prima volta che l’utente crea o si unisce a una partita:

- inserisce `nome`
- inserisce `email`
- inserisce facoltativamente `telefono`

Il backend:
- cerca o crea il `Player`
- genera un `player_access_token`
- salva solo l’hash del token
- restituisce il token al client

Il frontend:
- salva il token in un cookie httpOnly se possibile
- oppure, solo come fallback, in storage lato client

Risultato:
- l’utente non deve più reinserire email ogni volta

## Fase 2 — Riconoscimento rapido
Quando l’utente torna nella pagina `/play`:

- il frontend chiama `GET /api/play/me`
- il backend legge il token
- se valido, risale al `Player`
- il frontend mostra il profilo già noto
- l’utente può unirsi con un click

Esperienza utente:
- bottone tipo `Unisciti come Silvio`
- nessun login tradizionale
- nessuna password

## Fase 3 — Recupero identità via magic link
Se il token è perso, scaduto o non valido:

- il sistema richiede di nuovo `nome + email`
- oppure offre il recupero via email con magic link

Flusso corretto:
- `POST /api/play/magic-link/request`
- invio email con link monouso
- `POST /api/play/magic-link/consume`
- generazione di un nuovo `player_access_token`
- salvataggio del nuovo token sul device/browser

Questo copre i casi:
- reset telefono
- reinstallazione app/PWA
- cambio browser
- cancellazione cache/localStorage
- cambio dispositivo

## Regola obbligatoria
Se il token è:
- assente
- non valido
- scaduto
- revocato

il sistema deve:
- richiedere di nuovo `nome + email`
- recuperare o creare il `Player`
- emettere un nuovo token
- continuare senza blocchi

---

## Gestione token consigliata

La soluzione pulita è una tabella dedicata.

## `player_auth_tokens`

Campi consigliati:
- `id`
- `player_id`
- `token_hash`
- `type = access | magic_link`
- `created_at`
- `expires_at`
- `last_used_at`
- `revoked_at`
- `user_agent` opzionale
- `ip_address` opzionale

## Regole
- mai salvare token in chiaro
- salvare solo hash
- `access` token con durata lunga, ad esempio 90 o 180 giorni
- `magic_link` con durata breve, ad esempio 10–15 minuti
- `magic_link` monouso
- possibilità di revoca
- audit minimo sulle operazioni di emissione e consumo

---

## Servizi backend necessari

La chat AI deve appoggiarsi a servizi applicativi chiari.

## 1. AvailabilityService
Responsabilità:
- calcolare gli slot disponibili per i prossimi 5 giorni
- usare la logica esistente di disponibilità
- filtrare slot già passati
- restituire solo disponibilità reali e valide

Output tipico:
- `start_at`
- `end_at`
- eventuale caparra
- disponibilità vera

Questo servizio deve essere totalmente deterministico.

## 2. MatchService
Responsabilità:
- creare partite
- leggere partite aperte
- leggere dettaglio partita
- modificare partite aperte
- validare livello, slot e regole di dominio

Regole:
- match creato solo su slot disponibile
- durata sempre 90 minuti
- status iniziale `OPEN`
- massimo 4 giocatori
- modifica consentita solo se il match è ancora aperto
- modifica orario solo se il nuovo slot è libero

## 3. JoinMatchService
Responsabilità:
- gestire il click del CTA `Unisciti`
- cercare o creare il player
- inserire la riga in `MatchPlayer`
- rifiutare join duplicati
- bloccare join su match full
- attivare il completamento se il quarto giocatore entra

Questo endpoint deve essere atomico e transazionale.

## 4. CompleteMatchService
È il punto più delicato.

Quando il match raggiunge 4 giocatori:
- ricontrolla che lo slot sia ancora libero
- usa il lock anti-doppia prenotazione esistente
- crea la booking finale
- imposta il match come `FULL`
- collega `booking_id`
- invia email al club
- scrive audit log
- se lo slot non è più libero, annulla completamento e gestisce rollback coerente

Importante:
`complete_match()` deve coordinare il flusso, ma internamente va spezzato in metodi più piccoli.

## 5. NotificationService
Responsabilità:
- inviare email al club
- inviare conferme o notifiche ai player quando necessario
- non bloccare il flusso principale se il provider email non è disponibile

Scelta corretta:
- il club inserisce solo l’email destinataria
- il sistema invia con provider centralizzato
- niente configurazione SMTP manuale del club

---

## Endpoint backend minimi

## Identità player

### `GET /api/play/me`
Scopo:
- restituire il player identificato dal token persistente

Response esempio:
- player presente -> profilo player
- player assente -> `null` o 401 controllato

### `POST /api/play/identify`
Body:
- `name`
- `email`
- `phone?`

Fa:
- get/create player
- genera nuovo `player_access_token`
- salva/aggiorna token
- restituisce profilo player

### `POST /api/play/logout`
Opzionale ma utile.
Fa:
- revoca token attuale
- pulisce sessione locale

### `POST /api/play/magic-link/request`
Body:
- `email`

Fa:
- se player esiste, genera magic link
- invia email
- restituisce risposta neutra in ogni caso

### `POST /api/play/magic-link/consume`
Body:
- `token`

Fa:
- valida token
- identifica player
- genera nuovo access token persistente
- invalida il magic link
- restituisce player

## Chat

### `POST /api/chat/session`
Crea una nuova `ChatSession`.

### `POST /api/chat/message`
Input:
- `session_token`
- `message`
- opzionale `player_context`

Output:
```json
{
  "text": "string",
  "actions": [],
  "messages_history_count": 0
}
```

La logica:
- carica sessione
- carica ultimi messaggi utili
- passa il contesto all’orchestratore LLM
- persiste messaggi e tool result
- restituisce testo + azioni

## Match

### `GET /api/chat/matches`
Lista partite aperte in intervallo date.

### `GET /api/chat/matches/{match_id}`
Dettaglio match.

### `POST /api/chat/matches/{match_id}/join`
Input:
- dati player oppure player già riconosciuto tramite token

Fa:
- join transazionale
- aggiorna player count
- se quarto giocatore entra, attiva `complete_match()`

### `POST /api/chat/matches`
Crea un nuovo match su slot disponibile.

### `PATCH /api/chat/matches/{match_id}`
Modifica un match aperto se consentito dalle regole.

---

## Ruolo dell’LLM

L’LLM deve essere leggero e con ambito ristretto.

## Compiti reali del modello
- interpretare frasi naturali
- capire data/orario richiesti
- capire se l’utente vuole:
  - vedere slot
  - vedere partite aperte
  - creare una partita
  - unirsi a una partita
  - modificare una partita
- formulare una risposta sintetica in italiano
- restituire azioni strutturate

## Non deve fare
- scrittura DB diretta
- query business arbitrarie
- decisioni finali di disponibilità
- costruzione di booking
- join impliciti

## Strategia corretta
- modello leggero o medio-leggero
- history corta
- tool calling chiuso
- massimo numero limitato di round
- output JSON strutturato
- fallback senza azione quando ambiguità o bassa confidenza

---

## Tool dell’LLM

L’LLM deve usare pochi tool chiari.

### `get_available_slots`
Input:
- `date_from`
- `date_to`
- `duration_minutes = 90`

Output:
- lista di slot liberi reali

### `get_open_matches`
Input:
- intervallo date

Output:
- partite aperte con player count, livello, note, orario

### `create_match`
Input:
- `start_at`
- `level`
- `notes`
- dati del player creatore

Output:
- `match_id`
- `start_at`
- `end_at`
- `player_count`
- dati utili per UI

### `join_match`
Input:
- `match_id`
- dati player oppure player riconosciuto via token

Output:
- esito
- player_count
- `is_full`

### `get_match_detail`
Input:
- `match_id`

Output:
- dettaglio match
- partecipanti
- stato

### `modify_match`
Input:
- `match_id`
- nuove proprietà consentite
- contesto player richiedente

Output:
- esito modifica
- eventuali alternative se slot non disponibile

---

## Formato corretto della risposta della chat

La risposta deve avere sempre due parti:

### `text`
Testo naturale breve, chiaro, in italiano.

### `actions`
Azioni tipizzate che il frontend renderizza come card o CTA.

Tipi minimi:
- `join_match`
- `create_match`
- `view_slots`
- `view_match`

Esempio logico:
- testo: “Ho trovato due slot liberi domani sera.”
- actions:
  - `view_slots`
  - eventuale `create_match`

Questo impedisce che la UI dipenda da testo ambiguo.

---

## Frontend corretto

La chat AI va esposta in una pagina pubblica tipo `/play`.

## Struttura pagina
- sezione partite aperte
- sezione chat
- mobile-first
- card chiare
- CTA grandi
- feedback visibili

## Componenti minimi

### `PlayPage`
Contenitore principale.

### `MatchBoard`
Mostra partite aperte nei prossimi 5 giorni.

### `MatchCard`
Mostra:
- data e ora
- livello
- stato
- progress giocatori
- note
- CTA `Unisciti`

### `JoinMatchModal`
Form join con:
- nome
- email
- telefono opzionale

Quando l’utente è già riconosciuto via token:
- precompila
- oppure salta del tutto il form
- mostra `Unisciti come [nome]`

### `ChatPanel`
Gestisce:
- input utente
- cronologia messaggi
- rendering risposta assistant
- rendering `ActionCard`
- typing/loading state
- autoscroll

### `ActionCard`
Renderizza azioni dell’LLM:
- crea partita
- vedi slot
- vedi dettaglio match
- unisciti a partita

---

## Flusso UX corretto

## Caso 1 — Utente riconosciuto
- entra su `/play`
- frontend chiama `GET /api/play/me`
- backend riconosce il player dal token
- UI mostra esperienza rapida
- join con un click

## Caso 2 — Utente nuovo
- entra su `/play`
- nessun player riconosciuto
- può chattare
- al momento dell’azione concreta inserisce nome + email
- backend crea player e token

## Caso 3 — Token scaduto o assente
- `/api/play/me` non identifica nessuno
- la UI richiede di nuovo nome + email
- oppure propone recupero via magic link
- backend emette un nuovo token

## Caso 4 — Creazione partita da linguaggio naturale
Utente scrive:
- “voglio giocare giovedì alle 19”

Flusso:
- LLM interpreta l’intento
- chiama `get_available_slots` o `create_match`
- se slot disponibile, backend crea match
- se non disponibile, backend propone alternative
- frontend mostra card cliccabili

## Caso 5 — Join partita
Utente clicca `Unisciti`.
- se riconosciuto, join immediato o quasi immediato
- se non riconosciuto, mini-form identità
- backend esegue join
- se entra il quarto giocatore, completa il match e crea booking

---

## Notifiche email

La chat AI deve attivare notifiche su eventi chiave:

- match creato
- match completato
- match modificato
- match cancellato
- conferma player join

Regola corretta:
- il club inserisce solo `notification_email`
- il sistema invia da provider centralizzato
- se il provider manca, il flusso principale non si rompe

---

## Sicurezza e qualità

## Regole obbligatorie
- validazione client + server
- transazioni sulle operazioni critiche
- lock sul completamento match
- rate limit su sessione chat, join, magic link
- token hashati
- magic link monouso
- zero chiamate reali al provider LLM nei test
- audit log su eventi importanti

## Test obbligatori
- create match su slot disponibile
- create match su slot occupato
- join match ok
- join duplicato rifiutato
- quarto giocatore crea booking una sola volta
- rollback se slot non più disponibile
- `GET /api/play/me` con token valido
- fallback nome+email con token invalido
- magic link request/consume
- risposta LLM mockata con `actions[]`
- zero regressioni sulle funzionalità esistenti

---

## Sequenza corretta di implementazione

### Fase 1
Fondamenta dati:
- `Match`
- `Player`
- `MatchPlayer`
- `ChatSession`
- `ChatMessage`
- `Club` minimo
- `player_auth_tokens`

### Fase 2
Backend deterministico:
- availability
- match create/read/join/modify
- complete match
- identity endpoints `/api/play/*`
- notification service

### Fase 3
Frontend `/play`:
- `PlayPage`
- `MatchBoard`
- `MatchCard`
- `JoinMatchModal`
- `ChatPanel`
- `ActionCard`

### Fase 4
Integrazione LLM leggera:
- parser intent
- tool calling chiuso
- output `{ text, actions[] }`
- history breve
- fallback sicuro

### Fase 5
Recupero identità:
- magic link
- nuovo token su nuovo device
- UX robusta cross-device

### Fase 6
Foundation multi-tenant:
- `club_id`
- slug route
- tenant resolution
- admin settings per club

---

## Definizione finale

La chat AI deve essere definita come:

> una pagina pubblica `/play` con identità leggera persistente, cronologia conversazionale, action cards e join one-click, costruita sopra un backend deterministico che gestisce slot, match, partecipanti, booking, notifiche e riconoscimento player; l’LLM deve essere un interprete leggero che restituisce testo e azioni strutturate, senza mai avere accesso diretto alla logica di dominio o al database.

