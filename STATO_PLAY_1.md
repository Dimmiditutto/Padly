# STATO PLAY 1

## Esito

PASS

Gate finale: FASE VALIDATA - si puo procedere

## Prerequisiti verificati

- PASS: il tenant root resta `Club`
- PASS: `Court` e il dominio multi-campo esistono gia e non sono stati rotti
- PASS: il booking engine esistente non e stato modificato nella logica di business
- PASS: il tenant routing backend continua a passare da host/query/header
- PASS: prima della fase non esistevano ancora `Player`, `Match`, `MatchPlayer`, invite token community e player access token

## File toccati

- `backend/app/models/__init__.py`
- `backend/app/api/deps.py`
- `backend/app/schemas/play.py`
- `backend/app/services/play_service.py`
- `backend/app/api/routers/play.py`
- `backend/app/api/routers/public_play.py`
- `backend/app/api/routers/__init__.py`
- `backend/app/main.py`
- `backend/alembic/versions/20260424_0009_play_phase1_foundation.py`
- `backend/tests/test_play_phase1.py`
- `backend/tests/test_play_phase1_migration.py`

## Migrazione creata

- `20260424_0009_play_phase1_foundation.py`

Tabelle introdotte:
- `players`
- `community_invite_tokens`
- `player_access_tokens`
- `matches`
- `match_players`

Enum introdotti:
- `PlayLevel`
- `MatchStatus`

## Nuovi modelli ed enum applicativi

- `Player`
- `CommunityInviteToken`
- `PlayerAccessToken`
- `Match`
- `MatchPlayer`
- `PlayLevel`
- `MatchStatus`

## Cookie e token strategy adottata

- cookie player: `padel_play_session`
- token player opaco, generato con `secrets.token_urlsafe`
- lato DB viene salvato solo `sha256(token)`
- cookie host-only perche non imposta `domain`
- cookie `httpOnly`, `SameSite=Lax`, `secure` solo in production
- durata cookie/token: 90 giorni
- su nuova identify o accept invite i token attivi precedenti del player vengono revocati
- il token player e tenant-scoped tramite `club_id`

## Endpoint chiusi in Fase 1

- `GET /api/play/me`
- `POST /api/play/identify`
- `GET /api/play/matches`
- `GET /api/play/matches/{id}`
- `POST /api/public/community-invites/{token}/accept`

## Contratto principale `/api/play/matches`

Response shape:

- `player`: player corrente oppure `null`
- `open_matches`: lista partite aperte del tenant corrente, ordinate per riempimento decrescente e poi per data
- `my_matches`: lista partite future del player corrente nel tenant corrente

Ogni match espone almeno:

- `id`
- `court_id`
- `court_name`
- `court_badge_label`
- `created_by_player_id`
- `creator_profile_name`
- `start_at`
- `end_at`
- `duration_minutes`
- `status`
- `level_requested`
- `note`
- `participant_count`
- `available_spots`
- `joined_by_current_player`
- `created_at`
- `participants[]` con `player_id`, `profile_name`, `declared_level`, `effective_level`

## Decisione su BookingSource

Nessun nuovo `BookingSource` introdotto in Fase 1.

Decisione esplicita:
- la foundation dati del match e pronta
- la creazione della booking finale da match viene rimandata alla Fase 3
- la decisione su un eventuale source dedicato del flusso `/play` resta aperta fino alla chiusura del completamento transazionale del quarto player

## Test eseguiti

Comando eseguito da `backend` con virtualenv del repo:

- `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_play_phase1.py tests/test_play_phase1_migration.py -q --tb=short --maxfail=5`

Esito:

- `6 passed`

Copertura validata:

- identify player con cookie persistente
- `GET /api/play/me` con e senza cookie
- token hash-only a database
- ordinamento e scoping tenant di `/api/play/matches`
- accept invite valido, scaduto e gia usato
- smoke upgrade/downgrade della migration `20260424_0009`

## Rischi residui per Fase 2

- non esiste ancora la route frontend `/c/:clubSlug/play`
- non esistono ancora `PlayPage`, `InviteAcceptPage` e `SharedMatchPage`
- il payload match non espone ancora un token share pubblico consumabile dal frontend
- non esistono ancora endpoint write per create/join/leave match
- `effective_level` e solo foundation dati: nessuna logica di calcolo ancora attiva
- la generazione operativa degli invite community esiste solo come service/helper, non come endpoint admin UI

## Prossima fase corretta

- `play_2.md`