# Prompt 2 - Frontend `/play`, orchestrazione LLM e test finali

Agisci come Senior Full-Stack Engineer su questo repository React + TypeScript + FastAPI.

Obiettivo: costruire la UX pubblica `/play` e integrare un layer OpenAI leggero sopra i nuovi endpoint deterministici del backend, restando coerente con il design, i vincoli tenant-aware e la logica di business reale del progetto.

## Precondizione obbligatoria: chiusura di chat_ai_1

Prima di qualunque edit, leggi in questo ordine:

1. `chat_ai_1.md`
2. `STATO_CHAT_AI_1.md`
3. i file reali backend toccati dalla fase 1

`STATO_CHAT_AI_1.md` e il file di handoff tra le due fasi e va trattato come memoria operativa della chiusura backend.

Regole:

1. non iniziare la fase 2 se `STATO_CHAT_AI_1.md` manca
2. non iniziare la fase 2 se `STATO_CHAT_AI_1.md` dice che i prerequisiti backend per il frontend non sono chiusi
3. usa `STATO_CHAT_AI_1.md` per allineare route, payload, env vars e test gia esistenti
4. se il file di stato e incoerente con il codice reale, riallinea prima il file di stato e poi procedi

Questa fase non deve reinventare il backend: deve continuare da cio che la fase 1 ha davvero consegnato.

## Decisione modello runtime

Usa `gpt-4.1-mini` come modello della chat AI.

Implementazione richiesta:

- env `OPENAI_API_KEY`
- env `OPENAI_MODEL` con default `gpt-4.1-mini`
- adapter unico lato backend per chiamare OpenAI
- zero chiamate reali in test

## Verita del frontend attuale da rispettare

1. La pagina pubblica esistente e `PublicBookingPage`.
2. Il frontend pubblico e gia tenant-aware tramite query param e service layer.
3. Oggi non esiste una route `/play` ne componenti `PlayPage`, `MatchBoard`, `ChatPanel`.
4. La UX deve essere mobile-first e non rompere il booking pubblico esistente.
5. I dettagli finali dei contratti `/api/play/*` e `/api/chat/*` vanno letti da `STATO_CHAT_AI_1.md` e confermati sul codice backend reale.

## Obiettivo UX della pagina `/play`

La pagina `/play` non deve essere una chat isolata. Deve unire:

1. elenco partite aperte
2. chat conversazionale
3. CTA chiare e tipizzate
4. join rapido per player gia riconosciuto
5. fallback semplice `nome + email` quando il player non e riconosciuto

## Componenti minimi da introdurre

### `PlayPage`

Contenitore principale della nuova esperienza.

### `MatchBoard`

Mostra le partite aperte nei prossimi 5 giorni.

### `MatchCard`

Mostra almeno:

- data
- orario
- livello
- stato
- player count
- note
- CTA `Unisciti`

### `JoinMatchModal`

Se il player non e riconosciuto:

- nome
- email
- telefono opzionale

Se il player e riconosciuto:

- CTA tipo `Unisciti come [nome]`

### `ChatPanel`

Gestisce:

- input utente
- cronologia messaggi
- stato loading
- render delle action cards
- autoscroll

### `ActionCard`

Renderizza azioni strutturate provenienti dal backend/LLM.

Tipi minimi:

- `view_slots`
- `view_match`
- `create_match`
- `join_match`

## Shape della risposta chat

La UI non deve dipendere da testo ambiguo.

Usa una response strutturata del tipo:

```json
{
  "text": "string",
  "actions": [
    {
      "type": "view_slots",
      "label": "string",
      "payload": {}
    }
  ],
  "messages_history_count": 0
}
```

Regola:

- `text` breve, chiaro, in italiano
- `actions[]` come fonte vera delle CTA UI

## Comportamento corretto dell'orchestratore LLM

L'LLM deve solo:

1. interpretare linguaggio naturale
2. scegliere il tool corretto
3. riassumere l'esito in italiano
4. restituire testo + azioni strutturate

L'LLM non deve:

1. scrivere direttamente sul DB
2. decidere se uno slot e davvero libero
3. creare booking senza backend
4. unire player senza endpoint dedicato
5. eseguire query arbitrarie fuori dai tool consentiti

## Tool calling chiuso

Esponi all'orchestratore solo pochi tool backend chiari:

1. `get_available_slots`
2. `get_open_matches`
3. `get_match_detail`
4. `create_match`
5. `join_match`
6. `modify_match`

Vincoli:

- massimo pochi round per richiesta
- history corta
- fallback senza azione se l'intento e ambiguo
- parsing date/orari prudente e localizzato sul tenant

## Prompt runtime del modello da implementare

Implementa nel backend un system prompt runtime ristretto, coerente con questo schema:

"Sei l'assistente conversazionale di un club di padel. Non sei un chatbot generico. Devi aiutare l'utente a vedere slot disponibili nei prossimi 5 giorni, vedere partite aperte, creare una partita, unirsi a una partita o modificare una partita aperta. Devi sempre usare solo i tool autorizzati quando servono dati reali o azioni applicative. Il backend e l'unica fonte di verita. Non inventare disponibilita, non promettere booking, non eseguire azioni implicite. Rispondi in italiano con testo breve e produci azioni strutturate per la UI. Se una richiesta e ambigua, chiedi un chiarimento minimo oppure proponi alternative sicure." 

Non costruire un prompt piu lungo del necessario. Mantienilo stretto e tool-based.

## Tenant awareness frontend

La nuova `/play` deve seguire la logica gia usata dal frontend pubblico:

1. preserva `?tenant=` nei link e nelle API
2. usa gli helper tenant context gia presenti
3. non introdurre una seconda strategia tenant-side

## Come usare il file di stato della fase 1

Prima di implementare `/play`:

1. estrai da `STATO_CHAT_AI_1.md` l'elenco reale delle route backend disponibili
2. estrai i payload reali di identify, session, message, match list, match detail, create, join e modify
3. estrai le env vars backend gia introdotte per OpenAI e identity player
4. estrai i limiti residui dichiarati dalla fase 1 e non contraddirli nel frontend

Se una parte del prompt iniziale di `chat_ai_2.md` confligge con `STATO_CHAT_AI_1.md`, prevale il codice reale confermato dal file di stato e dai file backend.

## Test frontend obbligatori

1. `/play` carica match aperti e stato player riconosciuto
2. join con player riconosciuto
3. join con form identita quando il player non e riconosciuto
4. rendering delle action cards
5. invio messaggio chat con risposta mockata `{ text, actions[] }`
6. preservazione `?tenant=` nella nuova route pubblica

## Test backend/LLM obbligatori

1. nessuna chiamata OpenAI reale
2. adapter OpenAI mockabile
3. parsing e tool routing verificabile con fixture stabili
4. fallback corretto in caso di tool error o risposta non valida

## Regole di implementazione

1. non spostare logica business nel frontend
2. non rendere la chat una dipendenza del booking pubblico classico
3. non introdurre stato globale complesso se non serve
4. non costruire una knowledge base o RAG: non serve a questa feature
5. non usare modelli piu grandi come default finche il dominio resta cosi chiuso

## Criterio di completamento

Questo prompt e chiuso solo quando:

1. `/play` esiste ed e usabile
2. il player puo essere riconosciuto in modo persistente
3. la chat restituisce testo + azioni strutturate
4. l'orchestrazione OpenAI usa `gpt-4.1-mini` come default configurabile
5. test frontend e test LLM mockati sono verdi
6. build frontend e controlli mirati backend restano verdi
7. l'implementazione realizzata resta coerente con `STATO_CHAT_AI_1.md` oppure aggiorna esplicitamente quel file prima di chiudere la fase 2

