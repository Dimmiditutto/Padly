# STATO PLAY 7

## Esito

PASS

## Obiettivo fase

Chiudere la discovery pubblica orientata alla community senza confondere i concetti con il profilo player interno:

- sessione discovery globale e minimale, separata da `Player`
- watchlist club pubblici
- feed persistente di alert discovery
- digest giornaliero dei club vicini con match compatibili
- richiesta contatto guidata dalla pagina pubblica del club

## Decisioni architetturali confermate

- la discovery pubblica usa entita dedicate e non riusa `Player`, `PlayerAccessToken` o le preferenze play interne
- il cookie discovery e separato dal cookie play e resta host-only con sessione server-side hashata
- gli alert discovery pubblici sono solo `IN_APP` nel feed persistente v1; nessun web push reale introdotto in questa fase
- i trigger reali riusano i punti di mutazione gia esistenti dei match play (`create`, `join`, `leave`, `update`)
- il digest nearby usa coordinate e preferenze salvate nel profilo discovery, non la tenant resolution
- la richiesta contatto club resta pubblica ma viene loggata e inviata via email operativa al club

## Dati introdotti

- `public_discovery_subscribers`
- `public_discovery_session_tokens`
- `public_club_watches`
- `public_discovery_notifications`
- `public_club_contact_requests`
- enum `PublicDiscoveryNotificationKind`

## API e route introdotte

### Backend

- `GET /api/public/discovery/me`
- `POST /api/public/discovery/identify`
- `POST /api/public/discovery/notifications/{notification_id}/read`
- `PUT /api/public/discovery/preferences`
- `GET /api/public/discovery/watchlist`
- `POST /api/public/discovery/watchlist/{club_slug}`
- `DELETE /api/public/discovery/watchlist/{club_slug}`
- `POST /api/public/clubs/{club_slug}/contact-request`

### Frontend

- estensione di `/clubs` con attivazione discovery, preferenze, watchlist e feed persistente con unread count e mark-as-read
- estensione di `/c/:clubSlug` con follow/unfollow e richiesta contatto guidata

## Comportamento implementato

### Sessione discovery pubblica

- onboarding leggero con livello, fasce orarie, coordinate opzionali, raggio digest e privacy
- cookie dedicato `padel_discovery_session`
- profilo modificabile senza creare un profilo community/player

### Watchlist e feed persistente

- ogni club pubblico puo essere seguito dalla directory o dalla pagina club
- quando un match del club raggiunge `2/4` o `3/4`, il backend crea un alert persistente compatibile con livello e fascia oraria
- il feed discovery resta disponibile via `GET /api/public/discovery/me` con `unread_notifications_count`
- ogni notifica `IN_APP` puo essere marcata letta via `POST /api/public/discovery/notifications/{notification_id}/read`

### Digest nearby

- job schedulato giornaliero lato backend
- seleziona club attivi con community aperta e match compatibili nel raggio configurato
- deduplica per subscriber e giorno

### Contact request guidata

- form pubblico nella pagina club con nome, contatto, livello, nota e privacy
- persistenza su `public_club_contact_requests`
- email operativa loggata in `email_notifications`

## Trigger e scheduler collegati

- `create_play_match`
- `join_play_match`
- `leave_play_match`
- `update_play_match`
- nuovo job scheduler `public_discovery_digest_job`

## File toccati

### Backend

- `backend/app/models/__init__.py`
- `backend/app/services/public_discovery_service.py`
- `backend/app/schemas/public.py`
- `backend/app/api/deps.py`
- `backend/app/api/routers/public.py`
- `backend/app/services/play_service.py`
- `backend/app/core/scheduler.py`
- `backend/alembic/versions/20260425_0013_play_phase7_public_discovery_foundation.py`
- `backend/tests/test_play_phase7_public_discovery.py`

### Frontend

- `frontend/src/types.ts`
- `frontend/src/services/publicApi.ts`
- `frontend/src/pages/ClubDirectoryPage.tsx`
- `frontend/src/pages/PublicClubPage.tsx`
- `frontend/src/pages/PublicDiscoveryPages.test.tsx`

## Validazioni eseguite davvero

### Backend

Comando:

```bash
D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest -q tests/test_play_phase7_public_discovery.py
```

Esito:

- `3 passed`

Comando:

```bash
D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest -q tests/test_play_phase3.py tests/test_play_phase6_public_directory.py tests/test_play_phase7_public_discovery.py
```

Esito:

- `20 passed`

Comando:

```bash
$env:DATABASE_URL='sqlite:///./tmp_alembic_smoke.sqlite'; D:/Padly/PadelBooking/.venv/Scripts/python.exe -m alembic upgrade head; D:/Padly/PadelBooking/.venv/Scripts/python.exe -m alembic downgrade 20260424_0012; D:/Padly/PadelBooking/.venv/Scripts/python.exe -m alembic upgrade head
```

Esito:

- smoke Alembic `upgrade -> downgrade -> re-upgrade` completato con successo

### Frontend

Comando:

```bash
npm run test:run -- src/pages/PublicDiscoveryPages.test.tsx
```

Esito:

- `6 passed`

Comando:

```bash
npm run build
```

Esito:

- build frontend completata con successo

## Vincoli rispettati

- nessuna rottura dei flussi `/`, `/clubs`, `/clubs/nearby`, `/c/:clubSlug`, `/c/:clubSlug/play`
- nessuna fusione impropria tra identita discovery pubblica e profilo player interno
- nessuna esposizione pubblica di nomi player o dettagli community privati
- approccio additive-only su modelli, API e UI pubblica

## Note operative finali

- il digest nearby resta disattivato se il profilo discovery non ha coordinate valide
- gli alert watchlist vengono deduplicati per subscriber, match e tipo evento
- il feed discovery espone contatore unread e mark-as-read per singola notifica, senza introdurre ancora cartelle o filtri avanzati
- la richiesta contatto puo vivere anche senza profilo discovery, ma se la sessione esiste viene collegata al subscriber corrente