# Matchinn — Implementazione LLM V1 Admin

## Obiettivo

Inserire un LLM in Matchinn senza trasformarlo nel motore dell’app.

L’LLM deve essere usato come **assistente operativo laterale** per aiutare il club a capire cosa sta succedendo, quali partite spingere e come comunicare meglio con gli utenti.

Il motore core resta deterministico:

- disponibilità campo;
- join partita;
- completamento match 4/4;
- lock transazionale;
- creazione booking;
- caparre;
- pagamenti;
- tenant/club;
- notifiche effettive;
- rate limit;
- privacy;
- permessi admin.

L’LLM non deve mai decidere o modificare direttamente questi elementi.

---

## Funzioni LLM da implementare per prime

Le prime 3 funzioni AI consigliate sono:

1. **Assistente admin per il club**
2. **Suggerimenti operativi per completare match**
3. **Generatore testi per WhatsApp / email / notifiche**

Queste tre funzioni hanno alto valore pratico, basso rischio tecnico e sono vendibili ai club perché risolvono problemi reali:

- capire velocemente la situazione del club;
- completare più partite;
- scrivere messaggi migliori senza perdere tempo.

---

# 1. Assistente admin per il club

## Scopo

L’Assistente admin deve aiutare il gestore del club a leggere la situazione senza consultare mille tabelle.

Deve rispondere a domande operative come:

- cosa sta succedendo oggi;
- quali partite sono quasi complete;
- quali match rischiano di non completarsi;
- quali fasce orarie stanno funzionando meglio;
- quali partite meritano un alert;
- se ci sono cancellazioni, no-show o anomalie rilevanti.

## Cosa deve fare

L’assistente deve produrre un riepilogo leggibile e azionabile.

Esempio:

```text
Oggi hai 5 partite aperte.

2 partite sono quasi complete:
- 19:30, Intermedio medio, 3/4
- 20:00, Intermedio alto, 3/4

La partita delle 18:00 è ferma a 2/4 da oltre 3 ore.
Potrebbe essere utile inviare un alert agli utenti compatibili.

La fascia più attiva oggi è 19:30–21:00.
```

## Cosa non deve fare

Non deve:

- creare booking;
- modificare match;
- inviare notifiche;
- cambiare livelli utenti;
- approvare utenti;
- annullare partite;
- calcolare disponibilità;
- calcolare caparre;
- decidere autonomamente chi notificare.

L’assistente può solo leggere dati già filtrati dal backend e generare un testo di sintesi.

## Dati necessari

Il backend deve passare all’LLM solo dati strutturati, già filtrati per club e permessi admin.

Dati consigliati:

```json
{
  "club": {
    "id": "club_123",
    "slug": "padel-savona",
    "name": "Padel Savona"
  },
  "period": {
    "from": "2026-05-04T00:00:00+02:00",
    "to": "2026-05-04T23:59:59+02:00",
    "timezone": "Europe/Rome"
  },
  "matches": [
    {
      "id": "match_1",
      "date": "2026-05-04",
      "start_time": "19:30",
      "duration_minutes": 90,
      "level": "INTERMEDIATE_MID",
      "status": "OPEN",
      "players_count": 3,
      "max_players": 4,
      "created_at": "2026-05-04T10:15:00+02:00",
      "hours_open": 5.2,
      "booking_id": null
    }
  ],
  "bookings": {
    "confirmed_today": 8,
    "cancelled_today": 1,
    "no_show_last_7_days": 2
  },
  "activity": {
    "new_players_last_7_days": 12,
    "joins_today": 9,
    "matches_completed_today": 3
  }
}
```

## Output atteso

L’output deve essere breve, pratico e diviso in sezioni.

Formato consigliato:

```json
{
  "summary": "Oggi il club ha una buona attività serale, con 2 partite quasi complete.",
  "highlights": [
    "2 partite sono a 3/4",
    "La fascia 19:30–21:00 è la più attiva",
    "Una partita è ferma a 2/4 da oltre 3 ore"
  ],
  "suggested_actions": [
    {
      "type": "SEND_ALERT",
      "title": "Spingi la partita delle 19:30",
      "reason": "Manca solo 1 giocatore e il livello è compatibile con molti utenti attivi.",
      "requires_admin_confirmation": true
    }
  ],
  "warnings": [
    "Non risultano anomalie gravi."
  ]
}
```

Il frontend può renderizzare:

- riepilogo;
- punti principali;
- azioni consigliate;
- eventuali alert/warning.

## UX admin

Dentro la dashboard admin aggiungere una card:

```text
Assistente club

[Riassumi oggi]
[Partite da spingere]
[Problemi da controllare]
```

La card deve mostrare:

- caricamento breve;
- risposta sintetica;
- pulsanti azione solo se esistono azioni deterministiche già supportate;
- nessuna azione automatica senza conferma admin.

## Endpoint consigliato

```text
POST /api/admin/ai/club-summary
```

Request:

```json
{
  "club_id": "club_123",
  "period": "today"
}
```

Response:

```json
{
  "summary": "...",
  "highlights": [],
  "suggested_actions": [],
  "warnings": []
}
```

## Regole di sicurezza

- Solo admin autenticato.
- Il club_id deve essere validato rispetto ai permessi dell’admin.
- Nessun dato di altri club.
- Non inviare dati personali inutili all’LLM.
- Evitare telefono/email giocatori nel prompt.
- Usare solo dati aggregati o pseudonimizzati, salvo necessità reale.
- Loggare la richiesta e la risposta AI per audit minimo.

---

# 2. Suggerimenti operativi per completare match

## Scopo

Questa funzione serve a individuare quali match hanno più probabilità di essere completati e quali azioni può fare il club per spingerli.

L’obiettivo è aumentare il numero di partite completate senza introdurre automazioni rischiose.

## Logica generale

Il backend calcola in modo deterministico una lista di match candidati.

L’LLM riceve solo i candidati già calcolati e genera una spiegazione comprensibile per l’admin.

Flusso:

```text
Backend calcola candidati
↓
Backend calcola segnali numerici
↓
LLM spiega la situazione e suggerisce priorità
↓
Admin conferma eventuale azione
↓
Backend esegue azione deterministica
```

## Candidati prioritari

Priorità match:

```text
1. Match 3/4
2. Match 2/4
3. Match 1/4 solo se molto interessante
```

Segnali utili:

- numero giocatori attuali;
- ore mancanti all’inizio;
- ore da quando il match è aperto;
- livello;
- fascia oraria;
- giorno settimana;
- utenti compatibili disponibili;
- storico join su quel club/fascia/livello;
- eventuali club follower compatibili;
- distanza solo per discovery vicino;
- no-show/cancellazioni recenti, se utili.

## Scoring deterministico

Prima dell’LLM serve uno score semplice nel backend.

Esempio:

```text
base_score = 0

+50 se match 3/4
+30 se match 2/4
+10 se match 1/4

+20 se in fascia oraria molto attiva
+15 se ci sono almeno 10 utenti compatibili
+10 se il match inizia entro 24 ore
+5 se il club ha alta attività recente

-20 se match troppo lontano nel tempo
-15 se pochi utenti compatibili
-10 se orario storicamente debole
```

Lo score serve per ordinare.  
L’LLM non deve inventare la priorità.

## Input LLM

```json
{
  "club": {
    "name": "Padel Savona",
    "slug": "padel-savona"
  },
  "candidate_matches": [
    {
      "id": "match_123",
      "start_at": "2026-05-04T19:30:00+02:00",
      "level": "INTERMEDIATE_MID",
      "players_count": 3,
      "max_players": 4,
      "time_bucket": "SERA",
      "hours_until_start": 8,
      "hours_open": 4,
      "compatible_players_count": 18,
      "score": 95,
      "reasons": [
        "Manca 1 giocatore",
        "Fascia oraria molto attiva",
        "18 utenti compatibili"
      ]
    }
  ]
}
```

## Output atteso

```json
{
  "recommendations": [
    {
      "match_id": "match_123",
      "priority": "HIGH",
      "title": "Spingi il match delle 19:30",
      "reason": "Manca solo 1 giocatore, la fascia serale è attiva e ci sono 18 utenti compatibili.",
      "suggested_action": "SEND_MATCH_ALERT",
      "requires_admin_confirmation": true
    }
  ]
}
```

## UX admin

Nella dashboard admin aggiungere una sezione:

```text
Partite da completare
```

Per ogni match candidato mostrare:

```text
19:30 · Intermedio medio · 3/4
Alta priorità

Manca solo 1 giocatore. Ci sono 18 utenti compatibili nella fascia serale.

[Genera messaggio]
[Invia alert]
```

Il pulsante **Invia alert** deve usare sempre la logica deterministica già esistente:

- livello compatibile;
- fascia oraria;
- club seguito;
- distanza se digest vicino;
- rate limit;
- consenso utente;
- preferenze notifiche.

## Endpoint consigliato

```text
POST /api/admin/ai/match-completion-suggestions
```

Request:

```json
{
  "club_id": "club_123",
  "date_range": {
    "from": "2026-05-04",
    "to": "2026-05-05"
  }
}
```

Response:

```json
{
  "recommendations": []
}
```

## Regole non negoziabili

- L’LLM non sceglie direttamente gli utenti da notificare.
- L’LLM non invia alert.
- L’LLM non decide se una partita può essere completata.
- L’LLM non tocca disponibilità o booking.
- Ogni invio richiede conferma admin, salvo automazioni deterministiche già approvate.
- Gli utenti notificati vengono selezionati dal backend con regole esistenti.

---

# 3. Generatore testi per WhatsApp / email / notifiche

## Scopo

Aiutare il club a scrivere messaggi brevi, chiari e commerciali per:

- completare un match;
- invitare utenti nella community;
- ricordare una partita quasi completa;
- comunicare cancellazioni o modifiche;
- invitare utenti inattivi a tornare a giocare;
- generare copy per email token/accesso community.

Questa funzione è molto utile perché i club comunicano spesso a mano su WhatsApp e hanno bisogno di testi pronti.

## Tipi di messaggi V1

Implementare inizialmente 3 tipi:

```text
1. MATCH_ALMOST_FULL
2. COMMUNITY_INVITE
3. MATCH_REMINDER
```

### 1. MATCH_ALMOST_FULL

Quando un match è a 2/4 o 3/4.

Esempio:

```text
Manca solo 1 giocatore per il match di oggi alle 19:30.
Livello intermedio medio.
Se vuoi giocare, entra ora e completa la partita.
```

Versione più commerciale:

```text
Il match delle 19:30 è quasi pronto.
Manca 1 giocatore, livello intermedio medio.
Entra ora e vai in campo.
```

### 2. COMMUNITY_INVITE

Quando il club invita un utente nella community.

Esempio:

```text
Entra nella community Matchinn di Padel Savona.
Trovi partite aperte, ti unisci in pochi tap e giochi quando vuoi.
Accedi da qui:
{invite_link}
```

### 3. MATCH_REMINDER

Promemoria per match già creato/completato.

Esempio:

```text
Promemoria: il tuo match è confermato per oggi alle 20:00.
Presentati al club qualche minuto prima dell’inizio.
```

## Canali supportati

Canali iniziali:

```text
WHATSAPP_MANUAL
EMAIL
IN_APP_NOTIFICATION
```

Importante:

- WhatsApp resta manuale/copy-to-clipboard nella V1.
- Email viene inviata tramite provider tipo Resend.
- Notifiche in-app/feed alert seguono le regole deterministiche.
- Web Push eventuale usa template controllati.

## Input LLM

```json
{
  "message_type": "MATCH_ALMOST_FULL",
  "channel": "WHATSAPP_MANUAL",
  "tone": "friendly",
  "club": {
    "name": "Padel Savona"
  },
  "match": {
    "date": "2026-05-04",
    "start_time": "19:30",
    "level_label": "Intermedio medio",
    "players_count": 3,
    "missing_players": 1,
    "link": "https://join.matchinn.app/c/padel-savona/play/matches/abc123"
  },
  "constraints": {
    "max_chars": 320,
    "no_names": true,
    "include_link": true,
    "language": "it"
  }
}
```

## Output atteso

```json
{
  "subject": null,
  "body": "Il match delle 19:30 è quasi pronto: manca solo 1 giocatore, livello intermedio medio. Entra ora e vai in campo: https://join.matchinn.app/...",
  "variants": [
    {
      "label": "Più diretta",
      "body": "Manca 1 giocatore per il match delle 19:30. Livello intermedio medio. Entra ora: https://join.matchinn.app/..."
    },
    {
      "label": "Più commerciale",
      "body": "Il campo ti aspetta: match quasi completo alle 19:30. Manca 1 giocatore. Unisciti qui: https://join.matchinn.app/..."
    }
  ]
}
```

## UX admin

Nella scheda di un match aggiungere:

```text
Genera messaggio
```

Apre una modal:

```text
Canale
- WhatsApp
- Email
- Notifica

Tono
- Diretto
- Amichevole
- Commerciale

[Genera testo]
```

Output:

```text
Testo generato
[Modifica]
[Copia per WhatsApp]
[Invia email]
[Usa come notifica]
```

Per WhatsApp V1:

- copia testo negli appunti;
- oppure apri link `wa.me` se numero specifico disponibile;
- non fare broadcast automatici.

## Template deterministici come fallback

Ogni messaggio generato dall’LLM deve avere fallback template.

Se LLM non risponde:

```text
Manca 1 giocatore per il match delle 19:30.
Livello intermedio medio.
Entra qui: {link}
```

Quindi il sistema resta funzionante anche senza AI.

## Regole copy

Il generatore deve rispettare queste regole:

- lingua italiana;
- tono chiaro e sportivo;
- niente promesse false;
- niente pressione eccessiva;
- niente nomi giocatori nelle notifiche pubbliche;
- niente telefoni/email utenti;
- link sempre generato dal backend;
- messaggi brevi;
- su WhatsApp massimo 300–400 caratteri;
- su notifiche push massimo 120 caratteri;
- su email può essere più completo.

## Endpoint consigliato

```text
POST /api/admin/ai/generate-message
```

Request:

```json
{
  "club_id": "club_123",
  "message_type": "MATCH_ALMOST_FULL",
  "channel": "WHATSAPP_MANUAL",
  "match_id": "match_123",
  "tone": "friendly"
}
```

Response:

```json
{
  "subject": null,
  "body": "...",
  "variants": []
}
```

---

# Architettura AI consigliata

## Nuovo service backend

Creare un service dedicato:

```text
backend/app/services/ai_assistant_service.py
```

Responsabilità:

- costruire payload pulito;
- chiamare provider LLM;
- validare output;
- applicare fallback;
- loggare audit minimo;
- non eseguire azioni di dominio.

## Nuovo router admin

Creare router:

```text
backend/app/api/routers/admin_ai.py
```

Endpoint:

```text
POST /api/admin/ai/club-summary
POST /api/admin/ai/match-completion-suggestions
POST /api/admin/ai/generate-message
```

## Configurazione env

Variabili consigliate:

```env
AI_ENABLED=false
AI_PROVIDER=openai
AI_MODEL=gpt-5.5-mini
AI_API_KEY=...
AI_REQUEST_TIMEOUT_SECONDS=20
AI_MAX_OUTPUT_TOKENS=1200
```

Default:

```env
AI_ENABLED=false
```

L’AI deve essere attivabile solo quando pronta.

## Provider

Il provider deve essere incapsulato.  
Il codice applicativo non deve dipendere direttamente da un SDK specifico ovunque.

Struttura consigliata:

```text
ai_assistant_service.py
llm_client.py
```

`llm_client.py` gestisce:

- provider;
- timeout;
- retry minimo;
- error handling;
- response parsing.

## Output strutturato

Evitare output libero non validato.

Usare schema Pydantic per:

```text
ClubSummaryAIResponse
MatchCompletionSuggestionAIResponse
GeneratedMessageAIResponse
```

Se l’output non passa validazione:

- log errore;
- usare fallback;
- non mostrare testo rotto all’admin.

---

# Privacy e sicurezza

## Dati da non inviare all’LLM

Evitare:

- numeri di telefono;
- email;
- dati di pagamento;
- token invito;
- token accesso;
- indirizzi IP;
- note private;
- dati di altri club;
- dati personali non necessari.

## Dati ammessi

Ammessi:

- nome club;
- giorno/orario match;
- livello match;
- stato match;
- numero giocatori;
- numero utenti compatibili aggregato;
- statistiche aggregate;
- link pubblico già costruito per share;
- dati pseudonimizzati.

## Log

Loggare:

```text
ai_request_id
admin_id
club_id
feature
created_at
model
success/failure
latency_ms
```

Non loggare prompt completi se contengono dati sensibili.  
In alternativa loggare solo payload sanificato.

## Permessi

Ogni endpoint deve verificare:

- admin autenticato;
- admin autorizzato per quel club;
- club_id coerente;
- nessun accesso cross-club.

---

# Guardrail prodotto

Regole fisse:

```text
1. L’LLM suggerisce, non esegue.
2. L’admin approva ogni azione.
3. Il backend valida sempre permessi e stato attuale.
4. Nessun dato sensibile inutile nel prompt.
5. Fallback deterministico sempre disponibile.
6. Nessuna modifica alla disponibilità campo via LLM.
7. Nessun pagamento/caparra gestito dall’LLM.
8. Nessuna selezione utenti affidata all’LLM.
9. Nessun invio massivo WhatsApp automatico in V1.
```

---

# Implementazione per fasi

## Fase 1 — Infrastruttura AI minima

Obiettivo:

- aggiungere service AI;
- feature flag;
- client provider;
- schema output;
- logging minimo;
- fallback.

File indicativi:

```text
backend/app/services/ai_assistant_service.py
backend/app/services/llm_client.py
backend/app/api/routers/admin_ai.py
backend/app/schemas/ai.py
```

## Fase 2 — Generatore messaggi

Implementare per primo perché è la funzione più semplice e utile.

Endpoint:

```text
POST /api/admin/ai/generate-message
```

UI:

```text
Genera messaggio
Copia per WhatsApp
```

Nessuna azione automatica obbligatoria.

## Fase 3 — Suggerimenti completamento match

Implementare scoring deterministico backend.

Poi usare LLM solo per spiegazione.

Endpoint:

```text
POST /api/admin/ai/match-completion-suggestions
```

UI:

```text
Partite da completare
Priorità alta/media/bassa
Motivo
Azione suggerita
```

## Fase 4 — Assistente admin riepilogo club

Endpoint:

```text
POST /api/admin/ai/club-summary
```

UI:

```text
Assistente club
Riassumi oggi
Riassumi settimana
```

## Fase 5 — Ottimizzazione

Solo dopo test reale:

- caching breve delle risposte;
- tono configurabile per club;
- template personalizzati;
- digest admin mattutino;
- suggerimenti settimanali.

---

# Priorità consigliata

Ordine migliore:

```text
1. Generatore messaggi
2. Suggerimenti per completare match
3. Assistente admin riepilogo club
```

Motivo:

- il generatore messaggi è facile, utile e non rischioso;
- i suggerimenti match aumentano valore operativo;
- il riepilogo admin diventa più utile quando i dati e gli score sono già pronti.

---

# Esempi UX finali

## Generatore messaggio

```text
Match 19:30 · Intermedio medio · 3/4

Manca solo 1 giocatore.
[Genera messaggio]

Testo suggerito:
Il match delle 19:30 è quasi pronto: manca solo 1 giocatore, livello intermedio medio.
Entra ora e vai in campo:
{link}

[Copia per WhatsApp]
[Modifica]
```

## Suggerimento completamento match

```text
Partite da completare

Priorità alta
19:30 · Intermedio medio · 3/4

Manca solo 1 giocatore.
Ci sono 18 utenti compatibili e la fascia serale è molto attiva.

[Genera messaggio]
[Invia alert]
```

## Assistente admin

```text
Assistente club

Oggi hai 5 partite aperte.
2 sono quasi complete.
La fascia 19:30–21:00 è la più attiva.

Azione consigliata:
spingi il match delle 19:30, manca solo 1 giocatore.

[Genera messaggio]
```

---

# KPI da misurare

Misurare se l’AI serve davvero.

KPI:

```text
messaggi generati
messaggi copiati
alert inviati dopo suggerimento
match completati dopo suggerimento
tempo medio completamento match
percentuale match 3/4 completati
utilizzo assistente admin
feedback admin positivo/negativo
```

Non misurare solo “uso AI”.  
Misurare impatto operativo sulle partite completate.

---

# Decisione finale

L’LLM in Matchinn deve entrare come:

```text
Assistente operativo del club
```

Non come:

```text
motore di booking
motore di matching
motore di pagamenti
chat utente generalista
```

La prima versione AI deve fare tre cose:

```text
1. Generare messaggi
2. Suggerire quali match spingere
3. Riassumere la situazione del club
```

Questa è la strada più utile, vendibile e sicura.
