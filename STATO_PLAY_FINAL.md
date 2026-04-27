# STATO PLAY FINAL

## Esito

PASS

La chiusura finale di `/play` e stata completata nel repository reale senza riaprire i perimetri gia stabilizzati di Fase 1-7.

## Backlog residuo assorbito da STATO_PLAY_4.md e play_7.md

- `WEB_PUSH` privato `/play` non e piu solo `SIMULATED`: il dispatch server-side usa ora VAPID reale con `pywebpush`, mantenendo test totalmente mockati.
- il feed notifiche private `/play` espone ora `unread_notifications_count`, stato `read/unread` e azione `mark-as-read` coerente lato backend e frontend.
- la `PlayPage` ha ora un centro notifiche minimo ma realmente usabile: badge non lette, distinzione visiva letta/non letta, azione `Segna come letta`, feedback coerente su fallback in-app e configurazione push.
- `/clubs` e `/c/:clubSlug` espongono un ranking pubblico read-only minimale basato solo su segnali pubblici aggregati dei match open visibili nei prossimi 7 giorni.

## Canali notifiche finali

### Dominio privato `/play`

- `IN_APP` persistito in `NotificationLog`, sempre disponibile quando abilitato.
- `WEB_PUSH` reale quando esistono subscription attive e configurazione VAPID completa (`play_push_vapid_public_key` + `play_push_vapid_private_key`).
- se la configurazione VAPID non e completa, il canale push viene esposto come non disponibile al client e il fallback resta il feed `IN_APP`.

### Dominio discovery pubblico

- discovery pubblica resta su feed persistito `IN_APP` per watchlist e digest.
- nessun web push pubblico discovery introdotto in questa fase finale, coerentemente col perimetro approvato.

## Strategia finale di dispatch WEB_PUSH privato

- dipendenza backend aggiunta: `pywebpush==2.3.0` in `backend/requirements.txt`.
- il dispatch usa `PlayerPushSubscription` gia persistite e invia payload compatibili con il service worker `/play` esistente.
- i log `NotificationLog` per `WEB_PUSH` riflettono ora stati reali del tentativo: `SENT`, `FAILED` oppure `SKIPPED`; il path effettivo non usa piu `SIMULATED`.
- gli errori definitivi coerenti con subscription invalida o scaduta (es. `404` o `410`) revocano la subscription corrispondente; se era l ultima attiva, `web_push_enabled` torna `False`.
- i test backend non fanno invii reali: il provider viene sempre mockato/stubbato.

## Endpoint aggiunti o estesi lato `/play` privato

- `GET /api/play/me`
  - `notification_settings` include ora anche `unread_notifications_count`.
- `POST /api/play/notifications/{notification_id}/read`
  - marca una notifica privata `IN_APP` come letta e restituisce lo stato notifiche aggiornato.

## Strategia finale di ranking pubblico

- i payload pubblici di directory e dettaglio club espongono ora:
  - `public_activity_score`
  - `recent_open_matches_count`
  - `public_activity_label`
- il punteggio e deterministico e read-only, basato solo sui match `OPEN` pubblicamente visibili nei prossimi 7 giorni:
  - peso `3` ai match `3/4`
  - peso `2` ai match `2/4`
  - peso `1` ai match `1/4`
- nessun dato personale o interno viene esposto: nessun nome player, `creator_profile_name`, `share_token` o `note` privata nei payload pubblici.
- la UI pubblica mostra badge e riepilogo della disponibilita recente senza introdurre nuovi endpoint ranking separati o superfici analytics dedicate.

## File principali toccati

### Backend

- `backend/app/services/play_notification_service.py`
- `backend/app/api/routers/play.py`
- `backend/app/schemas/play.py`
- `backend/app/services/play_service.py`
- `backend/app/api/routers/public.py`
- `backend/app/schemas/public.py`
- `backend/requirements.txt`
- `backend/tests/test_play_phase4.py`
- `backend/tests/test_play_phase6_public_directory.py`

### Frontend

- `frontend/src/types.ts`
- `frontend/src/services/playApi.ts`
- `frontend/src/pages/PlayPage.tsx`
- `frontend/src/pages/ClubDirectoryPage.tsx`
- `frontend/src/pages/PublicClubPage.tsx`
- `frontend/src/pages/PlayPage.test.tsx`
- `frontend/src/pages/PublicDiscoveryPages.test.tsx`

## Validazioni realmente eseguite

### Backend mirato read/unread

- `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_play_phase4.py -k "mark_as_read or play_me_hides_effective_level" -q --tb=short`
  - esito: `2 passed`

### Frontend mirato notifiche private

- `npm run test:run -- src/pages/PlayPage.test.tsx`
  - esito iniziale dopo read/unread UI: `21 passed`

### Backend e frontend mirati ranking pubblico

- `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_play_phase6_public_directory.py -q --tb=short`
  - esito finale: `3 passed`
- `npm run test:run -- src/pages/PublicDiscoveryPages.test.tsx`
  - esito finale: `6 passed`

### Backend mirato dispatch WEB_PUSH reale

- `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_play_phase4.py -k "push or notification_dispatch or mark_as_read or play_me_hides_effective_level" -q --tb=short`
  - esito finale: `8 passed, 2 deselected`

### Validazione finale del perimetro toccato

- `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_play_phase4.py tests/test_play_phase6_public_directory.py tests/test_play_phase7_public_discovery.py -q --tb=short`
  - esito: `20 passed`
- `npm run test:run -- src/pages/PlayPage.test.tsx src/pages/PublicDiscoveryPages.test.tsx`
  - esito: `27 passed`
- `npm run build`
  - esito: `PASS`

## Eventuali residui post-chiusura non bloccanti

- il ranking pubblico resta volutamente informativo e non introduce ordinamenti opachi, analytics persistite o nuove CTA private.
- il click sulle push puo essere ulteriormente raffinato in futuro con deep link dedicati nel payload, ma non blocca il canale push reale v1.
- discovery web push pubblica resta fuori scope e non blocca il `PASS` della fase finale.

## Note operative finali

- per vedere `WEB_PUSH` realmente disponibile nella `PlayPage`, il runtime deve avere configurate entrambe le chiavi VAPID private e pubbliche.
- il feed notifiche private `/play` resta il fallback affidabile anche senza configurazione push completa.
- il ranking pubblico usa solo la finestra pubblica gia approvata di 7 giorni e resta coerente con la separazione tra discovery pubblica e community privata.