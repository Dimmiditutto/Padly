# VERIFICA PLAY FASE 4

## 1. Esito sintetico generale

PASS

La Fase 4 `/play` e ora chiusa anche sui tre difetti emersi nella review precedente. I fix applicati sono rimasti locali, non hanno riaperto la logica di business del dominio e hanno mantenuto il perimetro previsto della fase.

Validazioni reali eseguite dopo i fix:

- frontend: `npm run test:run -- src/pages/PlayPage.test.tsx` -> PASS, `17 passed`
- backend: `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_play_phase3.py -k "leave or cancel"` -> PASS, `4 passed`
- backend: `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_play_phase4.py -k "notification_dispatch"` -> PASS, `3 passed`
- backend: `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_play_phase4_migration.py` -> PASS, `1 passed`
- controllo statico sui file toccati con `get_errors` -> nessun errore rilevato

Nota di perimetro confermata:

- il delivery server-side delle web push resta `SIMULATED` in v1; questa chiusura riguarda coerenza del flusso, timezone tenant-aware e idempotenza del dispatch, non l invio reale a provider esterni

## 2. Fix chiusi

### 1. Semantica push e revoca UI rese coerenti

- La UI non presenta piu lo stato aggregato del profilo come se fosse necessariamente lo stato del browser corrente.
- Il path `Disattiva web push` non invia piu una revoca globale quando il browser locale non restituisce un endpoint valido.
- Il backend mantiene il contratto esistente, ma il percorso utente corrente non puo piu azzerare involontariamente le subscription di altri device.

Esito: CHIUSO

### 2. Timezone del club propagata nei flow leave/cancel

- I router `/play` ora inoltrano `current_club.timezone` anche ai service `leave_play_match()` e `cancel_play_match()`.
- `record_player_activity()` e il dispatch del match riaperto usano la timezone reale del tenant anche in questi branch.
- Il fallback implicito a `Europe/Rome` non rientra piu da questi path.

Esito: CHIUSO

### 3. Dispatch notifiche reso idempotente sotto concorrenza

- `NotificationLog` e ora blindato da un vincolo DB-level per campagna su `club_id + player_id + match_id + channel + kind`.
- Il dispatcher usa insert race-safe con savepoint locale e degrada a no-op su duplicate insert, senza far fallire il job o la request concorrente.
- E stata aggiunta una migration dedicata che ripulisce eventuali duplicati storici prima di creare il vincolo.

Esito: CHIUSO

## 3. Verdetto finale

La review precedente e superata. Il modulo `/play` Fase 4 resta con web push server-side simulata in v1, ma non ha piu criticita aperte nel perimetro verificato di semantica push, propagazione timezone e idempotenza del dispatch.

## 4. Rischi residui reali

- nessuna criticita bloccante residua emersa nel perimetro corretto in questa chiusura
- backlog volutamente fuori scope e gia separati: `revoca_token.md` e `kpi.md`