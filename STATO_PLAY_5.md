# STATO PLAY 5

## Esito

PASS

La Fase 5 `/play` e stata implementata sul repository reale mantenendo la logica di business decisa: il completamento community 4/4 e ora davvero offline di default, mentre la caparra community e opzionale, tenant-scoped e costruita riusando il motore booking/payment gia esistente.

## Regola default community implementata in modo finale

Quando la caparra community e `OFF`:

- il quarto player completa il match `/play`
- viene creata automaticamente una booking finale con `created_by=play:<match_id>`
- la booking nasce con `status=CONFIRMED`
- `deposit_amount=0`
- `payment_provider=NONE`
- `payment_status=UNPAID`
- il copy UI lato `/play` esplicita che il campo e confermato e che il saldo verra gestito al circolo

Questa semantica e chiusa in [backend/app/services/play_service.py](backend/app/services/play_service.py), con copertura reale in [backend/tests/test_play_phase3.py](backend/tests/test_play_phase3.py).

## Configurazione admin introdotta e valori di default

Configurazione tenant-scoped introdotta via `AppSetting` in [backend/app/services/settings_service.py](backend/app/services/settings_service.py) ed esposta da [backend/app/api/routers/admin_settings.py](backend/app/api/routers/admin_settings.py) con contratti aggiornati in [backend/app/schemas/admin.py](backend/app/schemas/admin.py).

Campi admin introdotti:

- `play_community_deposit_enabled`
- `play_community_deposit_amount`
- `play_community_payment_timeout_minutes`

Valori di default effettivi:

- caparra community `OFF`
- importo default `20.00`
- timeout default `15` minuti

Lato UI admin i campi sono chiusi in [frontend/src/pages/AdminDashboardPage.tsx](frontend/src/pages/AdminDashboardPage.tsx), con test in [frontend/src/pages/AdminDashboardPage.test.tsx](frontend/src/pages/AdminDashboardPage.test.tsx).

## Stato pending della caparra community

La fase riusa esplicitamente `PENDING_PAYMENT` e non introduce un nuovo enum `PENDING_DEPOSIT`.

Motivazione:

- il repository aveva gia una semantica stabile per timeout, expiry e conferma pagamento
- `start_payment_for_booking` e `expire_pending_bookings` erano gia pronti per governare il ciclo di vita della booking in attesa
- il riuso evita stack paralleli o eccezioni architetturali dedicate solo a `/play`

Quando la caparra community e `ON`:

- il match 4/4 crea la booking in `PENDING_PAYMENT`
- viene impostato `expires_at` con timeout dedicato community
- al pagamento mock/provider completato la booking passa a `CONFIRMED`
- alla scadenza passa a `EXPIRED`

Per supportare importi community configurabili, [backend/app/services/payment_service.py](backend/app/services/payment_service.py) ora accetta per le booking create da `/play` l importo `deposit_amount` effettivamente registrato sulla booking, senza rompere la validazione standard dei booking pubblici.

## Regola esplicita sul pagatore della prima iterazione

Il pagatore online della caparra community e il player che completa il `4/4`.

Implementazione effettiva:

- il backend registra `payer_player_id` nel payload audit `PLAY_MATCH_COMPLETED`
- il nuovo endpoint `/api/play/bookings/{booking_id}/checkout` consente il checkout solo a quel player
- un altro player riconosciuto sullo stesso tenant riceve `403`

La regola e chiusa in [backend/app/services/play_service.py](backend/app/services/play_service.py) e coperta in [backend/tests/test_play_phase3.py](backend/tests/test_play_phase3.py).

## Strategia provider adottata nel flusso `/play`

Strategia effettiva adottata:

- se la caparra community e `ON` ma non esiste alcun provider online disponibile, la configurazione admin viene rifiutata in fail-closed
- se al momento del completamento 4/4 esiste un solo provider disponibile, il backend lo pre-seleziona come `payment_provider` della booking
- se i provider disponibili sono piu di uno, il backend restituisce nel payload `/play` il minimo necessario per mostrare la scelta lato player pagatore
- il frontend `/play` mostra CTA immediate nello stesso flusso, senza dashboard pagamenti separata

Superfici toccate:

- [backend/app/schemas/play.py](backend/app/schemas/play.py)
- [backend/app/api/routers/play.py](backend/app/api/routers/play.py)
- [frontend/src/types.ts](frontend/src/types.ts)
- [frontend/src/services/playApi.ts](frontend/src/services/playApi.ts)
- [frontend/src/pages/PlayPage.tsx](frontend/src/pages/PlayPage.tsx)
- [frontend/src/pages/PlayPage.test.tsx](frontend/src/pages/PlayPage.test.tsx)

## File principali toccati

Backend:

- [backend/app/services/play_service.py](backend/app/services/play_service.py)
- [backend/app/services/settings_service.py](backend/app/services/settings_service.py)
- [backend/app/services/payment_service.py](backend/app/services/payment_service.py)
- [backend/app/api/routers/admin_settings.py](backend/app/api/routers/admin_settings.py)
- [backend/app/api/routers/play.py](backend/app/api/routers/play.py)
- [backend/app/schemas/admin.py](backend/app/schemas/admin.py)
- [backend/app/schemas/play.py](backend/app/schemas/play.py)
- [backend/tests/test_admin_and_recurring.py](backend/tests/test_admin_and_recurring.py)
- [backend/tests/test_play_phase3.py](backend/tests/test_play_phase3.py)

Frontend:

- [frontend/src/pages/AdminDashboardPage.tsx](frontend/src/pages/AdminDashboardPage.tsx)
- [frontend/src/pages/PlayPage.tsx](frontend/src/pages/PlayPage.tsx)
- [frontend/src/services/playApi.ts](frontend/src/services/playApi.ts)
- [frontend/src/types.ts](frontend/src/types.ts)
- [frontend/src/pages/AdminDashboardPage.test.tsx](frontend/src/pages/AdminDashboardPage.test.tsx)
- [frontend/src/pages/PlayPage.test.tsx](frontend/src/pages/PlayPage.test.tsx)

## Validazione eseguita

Backend mirato Fase 5:

- `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest -vv tests/test_play_phase3.py -k "fourth_join or requires_community_deposit or checkout or mock_payment_confirms or expiry_marks or concurrent"`
  - esito finale: `6 passed`
- `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest -vv tests/test_admin_and_recurring.py -k "play_community_payment"`
  - esito finale: `1 passed`

Regressione `/play` backend sulle suite di fase:

- `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_play_phase1.py tests/test_play_phase3.py -q`
  - esito finale: `19 passed`

Frontend mirato:

- `npm run test:run -- src/pages/AdminDashboardPage.test.tsx src/pages/PlayPage.test.tsx`
  - esito finale: `29 passed`

Build frontend finale:

- `npm run build`
  - esito finale: PASS

## Note operative finali

- la foundation notifiche, web push, retention breve e profilo aggregato introdotta in Fase 4 non e stata riaperta sul piano architetturale
- la Fase 5 aggiunge solo la semantica pagamento community e il minimo payload/UI per il player pagatore, restando coerente con la foundation dati e applicativa gia chiusa
- il reporting basato su `created_by=play:<match_id>` resta invariato in questa fase

## Backlog esplicito per una futura v2 notifiche mirate

Rispetto a [STATO_PLAY_4.md](STATO_PLAY_4.md) non cambia nulla in questa fase. Restano validi e non assorbiti in Fase 5:

- invio web push server-side reale con VAPID private key e dispatch non simulato
- mark-as-read esplicito e centro notifiche piu ricco lato UI
- tuning ulteriore del punteggio profilo con segnali di accettazione/rifiuto piu espliciti
- eventuale throttling piu granulare per fasce orarie o quiet hours