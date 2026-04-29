# STATO REVOCA TOKEN /play

## Esito

PASS

## Strategia finale di lifecycle del link

- Nessuna nuova tabella dedicata: il lifecycle del link condiviso resta sul modello `Match`, coerente con il codice gia esistente.
- `matches.public_share_token_hash` continua a essere il punto di lookup hash-based.
- La rotazione ora emette un token opaco nuovo costruito da nonce randomico + firma server-side, senza persistere il raw token in chiaro.
- `Match` traccia i metadati minimi necessari al lifecycle:
  - `public_share_token_nonce`
  - `public_share_token_created_at`
  - `public_share_token_revoked_at`
- Un match ha al massimo un link attivo alla volta.
- Revoca e rotazione invalidano sempre il link precedente.

## Compatibilita legacy implementata

- I match legacy continuano a risolvere il vecchio token deterministico finche non subiscono una revoca o una rotazione esplicita.
- Dopo la prima rotazione o revoca, il vecchio link legacy smette di funzionare.
- Il lookup pubblico risponde in modo sobrio con `404` e dettaglio `Link partita non disponibile` per link invalidi o revocati.

## API introdotte

- `POST /api/play/matches/{match_id}/share-token/rotate`
- `POST /api/play/matches/{match_id}/share-token/revoke`

## Regole applicate

- Solo il creator del match puo gestire il link condiviso.
- La gestione del link e consentita solo per match ancora futuri e aperti.
- I match gia trasformati in booking o non piu condivisibili restano fuori perimetro.

## Frontend applicato

- `Le mie partite` espone `Rigenera link` e `Disattiva link` per il creator.
- Quando il link e disattivato la card mostra `Link disattivato` e nasconde le azioni di share/open.
- La shared page mostra il messaggio backend sobrio quando il link non e piu disponibile.

## Verifica reale eseguita

- Backend: `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_play_phase3.py -q --tb=short --maxfail=5` -> PASS (18 test)
- Migration: upgrade head -> downgrade `20260428_0014` -> upgrade head su SQLite temporaneo -> PASS
- Frontend: `npm run test:run -- src/pages/PlayPage.test.tsx` -> PASS (29 test)
- Frontend build: `npm run build` -> PASS

## Backlog residuo

- Nessun blocker residuo emerso nella scope chiusa del prompt.