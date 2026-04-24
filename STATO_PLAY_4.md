# STATO PLAY 4

## Esito

PASS

La Fase 4 `/play` e stata implementata sul repository reale con foundation persistita per notifiche v1, web push subscription, memoria compatta a retention breve e profilo probabilistico aggregato leggero. La logica di business delle fasi precedenti non e stata riaperta.

## Modelli introdotti

Backend dati introdotti in [backend/app/models/__init__.py](backend/app/models/__init__.py) e persistiti via migration [backend/alembic/versions/20260424_0010_play_phase4_notification_foundation.py](backend/alembic/versions/20260424_0010_play_phase4_notification_foundation.py), con blindatura post-review del dispatch in [backend/alembic/versions/20260424_0011_play_notification_dispatch_idempotency.py](backend/alembic/versions/20260424_0011_play_notification_dispatch_idempotency.py):

- `PlayerActivityEvent`
- `PlayerPlayProfile`
- `PlayerPushSubscription`
- `PlayerNotificationPreference`
- `NotificationLog`

Enum e semantiche introdotte:

- `PlayerActivityEventType`
- `NotificationChannel`
- `NotificationKind`
- `NotificationDeliveryStatus`

## API e superfici chiuse

Estese le API `/play` in [backend/app/api/routers/play.py](backend/app/api/routers/play.py):

- `GET /api/play/me`
  - ora restituisce anche `notification_settings` del player corrente
- `PUT /api/play/notifications/preferences`
  - aggiorna le preferenze essenziali delle notifiche v1
- `POST /api/play/push-subscriptions`
  - registra o riattiva la subscription web push del browser corrente
- `POST /api/play/push-subscriptions/revoke`
  - revoca la subscription web push indicata; il percorso UI corrente non invia piu revoche globali quando il browser locale non ha un endpoint attivo

Frontend reale chiuso in:

- [frontend/src/pages/PlayPage.tsx](frontend/src/pages/PlayPage.tsx)
- [frontend/src/services/playApi.ts](frontend/src/services/playApi.ts)
- [frontend/src/types.ts](frontend/src/types.ts)
- [frontend/src/utils/playPush.ts](frontend/src/utils/playPush.ts)
- [frontend/public/play-service-worker.js](frontend/public/play-service-worker.js)

UX minima completata:

- attivazione/disattivazione subscription web push dal browser corrente
- preferenze notifiche essenziali salvabili dalla pagina `/play`
- feed notifiche in-app nella pagina `/play`
- feedback utente sullo stato subscription e sulla configurazione push disponibile, con copy account-scoped coerente con il backend aggregato

## Profilo probabilistico leggero

Servizio introdotto in [backend/app/services/play_notification_service.py](backend/app/services/play_notification_service.py).

Profilo aggregato implementato con:

- `weekday_scores`
- `time_slot_scores`
- `level_compatibility_scores`
- `useful_events_count`
- `engagement_score`
- `declared_level`
- `observed_level`
- `effective_level`

Regole effettive:

- aggiornamento incrementale sugli eventi utili di create/join/leave/cancel/complete
- decay leggero ogni 14 giorni con fattore `0.85`
- sync interno di `Player.effective_level` con il profilo aggregato
- `observed_level` e `effective_level` non sono piu esposti nei payload pubblici `/play` o nella UI

## Trigger notifiche chiusi in v1

Trigger applicativi cablati in [backend/app/services/play_service.py](backend/app/services/play_service.py):

- `identify` registra evento di attivazione profilo
- `create match` registra attivita e valuta subito notifiche sul match creato
- `join match` registra attivita e valuta notifiche sul nuovo stato del match aperto
- `complete match` registra evento `MATCH_COMPLETED` per tutti i partecipanti
- `leave` registra attivita e rivaluta il match aperto residuo
- `cancel` registra attivita e chiude il match senza nuove notifiche

Fix post-review chiusi sul dominio:

- `leave` e `cancel` propagano sempre `current_club.timezone` fino a record attivita e dispatch del match riaperto
- il pannello `/play` non puo piu provocare una revoca push globale involontaria quando manca una subscription locale del browser
- il dispatch notifiche e ora blindato anche sotto concorrenza reale con guard DB-level e inserimento race-safe

Trigger scheduler cablati in [backend/app/core/scheduler.py](backend/app/core/scheduler.py):

- `play_notification_job` ogni 15 minuti
- `play_retention_job` ogni giorno alle 03:10 UTC

## Regole finali notifiche v1

Selezione destinatari deterministica:

- priorita `3/4`, poi `2/4`, poi `1/4`
- `1/4` attivato solo se il match e vicino nel tempo e il punteggio profilo supera una soglia minima
- ordinamento destinatari per punteggio deterministico basato su priorita match, giorno settimana, fascia oraria, compatibilita livello ed engagement
- limite massimo destinatari per singolo match:
  - `3/4` -> 6 player
  - `2/4` -> 4 player
  - `1/4` -> 2 player

Regole di compatibilita e cap:

- notifiche mirate solo dopo almeno `5` eventi utili del player
- filtro livello attivo quando `level_compatibility_only=true`
- cap giornaliero massimo `3` campagne notifiche per player
- deduplica per campagna blindata anche a livello DB su `club_id + player_id + match_id + channel + kind`, quindi lo stesso player non riceve piu di una `IN_APP` e una `WEB_PUSH` per lo stesso match e la stessa campagna anche sotto race concorrente

Canali v1:

- `IN_APP` sempre disponibile se abilitato nelle preferenze
- `WEB_PUSH` disponibile quando esiste una subscription attiva del browser
- i log `WEB_PUSH` sono marcati `SIMULATED` nella prima iterazione, mentre la persistenza della subscription e i flussi browser sono reali

## Retention effettiva implementata

Retention compatta chiusa in [backend/app/services/play_notification_service.py](backend/app/services/play_notification_service.py):

- `PlayerActivityEvent`: purge oltre `90` giorni
- `NotificationLog`: purge oltre `90` giorni

La purge e automatica via scheduler e disponibile anche come funzione di servizio riusabile nei test.

## Validazione eseguita

Backend:

- `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_play_phase1.py tests/test_play_phase3.py tests/test_play_phase4.py -q --tb=short --maxfail=5`
  - esito finale: `19 passed`

Validazione mirata post-review:

- `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_play_phase3.py -k "leave or cancel"`
  - esito finale: `4 passed`
- `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_play_phase4.py -k "notification_dispatch"`
  - esito finale: `3 passed`
- `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_play_phase4_migration.py`
  - esito finale: `1 passed`

Smoke test migration Alembic su DB SQLite temporaneo:

- upgrade `20260424_0010`
- downgrade `20260424_0009`
- re-upgrade `head`
  - esito finale: PASS

Frontend:

- `npm exec vitest run src/pages/PlayPage.test.tsx`
  - esito finale implementazione iniziale: `16 passed`
- `npm run test:run -- src/pages/PlayPage.test.tsx`
  - esito finale post-review: `17 passed`
- `npm run build`
  - esito finale: PASS

## Note operative finali

- il feed notifiche in-app e reale e persistito in `NotificationLog`
- la subscription web push browser e reale e persistita in `PlayerPushSubscription`
- la consegna web push server-side resta simulata nella prima iterazione, ma la foundation dati, le preferenze, i job e i trigger applicativi sono chiusi e testati

## Backlog esplicito per una futura v2 notifiche mirate

- invio web push server-side reale con VAPID private key e dispatch non simulato
- mark-as-read esplicito e centro notifiche piu ricco lato UI
- tuning ulteriore del punteggio profilo con segnali di accettazione/rifiuto piu espliciti
- eventuale throttling piu granulare per fasce orarie o quiet hours