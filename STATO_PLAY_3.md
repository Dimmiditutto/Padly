# STATO PLAY 3

## Esito

PASS

La Fase 3 `/play` e stata implementata sul repository reale con write backend coerente, share token realmente utilizzabile, anti-frammentazione in creazione e join transazionale del quarto player con chiusura della prenotazione finale.

## Decisioni applicate

- Nessun checkout pubblico automatico: il completamento del match crea direttamente una `Booking` confermata sul percorso piu vicino alla logica manual/admin gia esistente.
- Nessun nuovo `BookingSource`: la prenotazione finale usa `source=ADMIN_MANUAL`, ma viene tracciata con `created_by=play:<match_id>` e `BookingEventLog.event_type=PLAY_MATCH_COMPLETED` per mantenere audit chiaro senza introdurre nuova enum/migrazione.
- Nessuna nuova migration: il token pubblico partita riusa la colonna esistente `matches.public_share_token_hash` con token deterministico stabile e lookup hash-based.
- Locking coerente con il repo: il join usa `acquire_single_court_lock(...)`, `SELECT ... FOR UPDATE` sul match e re-read in transazione fresca per evitare doppi vincitori sul quarto slot anche nei test SQLite.

## Backend

Implementato in `backend/app/services/play_service.py` e `backend/app/api/routers/play.py`:

- `GET /api/play/shared/{share_token}`
- `POST /api/play/matches`
- `POST /api/play/matches/{match_id}/join`
- `POST /api/play/matches/{match_id}/leave`
- `PATCH /api/play/matches/{match_id}`
- `POST /api/play/matches/{match_id}/cancel`

Comportamento effettivo:

- Create match:
  - accetta solo partite da 90 minuti
  - cerca partite compatibili gia aperte nello stesso orario prima di creare
  - restituisce `created=false` + `suggested_matches` quando esistono alternative
  - crea davvero solo con `force_create=true` o in assenza di alternative
  - blocca la creazione se esiste gia una partita sullo stesso campo e stesso slot
- Join match:
  - richiede profilo play
  - blocca doppio join dello stesso player
  - blocca join su match gia completo o non piu modificabile
  - al quarto player crea la prenotazione finale nella stessa boundary coerente
- Leave/update/cancel:
  - disponibili lato backend entro i limiti definiti
  - consentiti solo su partite future non ancora trasformate in `Booking`
  - update/cancel riservati al creator
  - leave del creator riassegna il creator al player rimanente piu vecchio; se non resta nessuno la partita viene annullata

## Share Flow

- Ogni `PlayMatchSummary` ora espone `share_token`
- Il frontend condivide `/c/:clubSlug/play/matches/:shareToken`
- Il backend risolve il link condiviso via hash del token, non via `match.id`
- Il token e deterministico per match e club, quindi stabile e realmente riutilizzabile senza colonna raw aggiuntiva

## Frontend

Implementato in:

- `frontend/src/pages/PlayPage.tsx`
- `frontend/src/pages/SharedMatchPage.tsx`
- `frontend/src/services/playApi.ts`
- `frontend/src/types.ts`
- `frontend/src/App.tsx`
- `frontend/src/components/play/CreateMatchForm.tsx`
- `frontend/src/components/play/MyMatches.tsx`
- `frontend/src/components/play/MatchCard.tsx`

Comportamento effettivo:

- La bacheca `/play` usa davvero gli endpoint write per create/join
- Se il backend propone partite compatibili, la UI mostra i suggerimenti e separa il bottone `Crea comunque una nuova partita`
- Il join da shared page e reale
- Il flusso anonimo shared page -> onboarding -> join continua automaticamente dopo l'identificazione
- La route canonical condivisa e tornata a usare `shareToken` reale
- Il form create e stato riallineato a 90 minuti fissi
- `Le mie partite` espone anche `leave`, `modifica` e `annulla match` entro i limiti gia imposti dal backend
- Il creator aggiorna livello e nota da un pannello di gestione leggero, senza aprire un flusso separato

## Admin / Reporting

Implementato in:

- `frontend/src/pages/AdminBookingsPage.tsx`
- `frontend/src/components/AdminBookingCard.tsx`
- `frontend/src/pages/AdminBookingDetailPage.tsx`
- `frontend/src/utils/bookingOrigin.ts`

Comportamento effettivo:

- L'elenco admin distingue esplicitamente le booking nate da `/play`
- E disponibile un filtro locale `Solo /play` / `Escludi /play` nel perimetro gia filtrato della pagina admin booking
- Il dettaglio booking mostra origine `Play community` e il riferimento al `match_id` quando la prenotazione nasce dal completamento `/play`

## Validazione eseguita

Backend:

- `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_play_phase1.py -q`
- `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_play_phase3.py -q`
- `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_play_phase1.py tests/test_play_phase3.py -q`

Frontend:

- `npm exec vitest run src/pages/PlayPage.test.tsx`
- `npm exec vitest run src/pages/AdminBookingsPage.test.tsx src/pages/AdminBookingDetailPage.test.tsx`
- `npm run build`

Esiti finali:

- backend `/play`: 10 test verdi
- frontend `/play`: 13 test verdi
- admin booking/reporting `/play`: 19 test verdi
- build frontend: verde

## Test aggiunti Phase 3

- create match con suggerimento anti-frammentazione e `force_create`
- share token valido / invalido
- doppio join dello stesso player
- match full non piu joinabile con booking finale creato
- join concorrente sul quarto player con un solo vincitore

## Rischi residui per Phase 4

- il token condiviso e stabile ma derivato deterministicamente: se in futuro servira rotazione/revoca per-link, andra introdotta una persistenza raw o una tabella token dedicata
- il booking finale usa `ADMIN_MANUAL` per evitare una nuova enum; oggi la distinzione `/play` vive in `created_by=play:<match_id>` e nella UI admin, quindi reportistica cross-backend piu granulare potrebbe in futuro richiedere un source dedicato o una proiezione persistita