# STATO_GEOHOME

- Stato: PASS
- Gate finale: FASE VALIDATA - si puo procedere
- Data: 2026-04-29

## Scope completato

- Esteso il summary pubblico dei club con i contatori derivati `open_matches_three_of_four_count`, `open_matches_two_of_four_count`, `open_matches_one_of_four_count` senza cambiare business logic o schema dati.
- Aggiunta in home pubblica una sezione non invasiva `Club vicini a te` in `PublicBookingPage`, basata su geolocalizzazione esplicita e fallback manuale verso la directory pubblica.
- Aggiornata `PublicClubPage` per presentare le partite come `Partite da chiudere`, raggruppate in ordine 3/4, 2/4, 1/4, mantenendo la vista pubblica read-only.
- Resa coerente la CTA community:
  - community aperta -> accesso a `/c/:clubSlug/play`
  - community chiusa -> `Richiedi accesso` verso il form pubblico esistente

## Privacy e coerenza

- Nessun nome partecipante, chat, recapito privato o dettaglio interno e stato esposto nella parte pubblica.
- Il modello `club pubblico visibile / community privata` e stato preservato.
- La riga conflittuale del prompt che chiedeva di mostrare i nomi partecipanti non e stata seguita, per restare coerenti con `geo.md`, repository attuale e vincoli di privacy.

## File toccati

- `backend/app/schemas/public.py`
- `backend/app/services/play_service.py`
- `backend/app/api/routers/public.py`
- `backend/tests/test_play_phase6_public_directory.py`
- `frontend/src/types.ts`
- `frontend/src/pages/PublicBookingPage.tsx`
- `frontend/src/pages/PublicClubPage.tsx`
- `frontend/src/pages/PublicBookingPage.test.tsx`
- `frontend/src/pages/PublicClubPage.test.tsx`
- `frontend/src/pages/PublicDiscoveryPages.test.tsx`

## Verifiche eseguite

- Backend: `pytest tests/test_play_phase6_public_directory.py` -> PASS
- Frontend test mirati: `vitest --run src/pages/PublicBookingPage.test.tsx src/pages/PublicClubPage.test.tsx` -> PASS
- Frontend test riallineati: `vitest --run src/pages/PublicBookingPage.test.tsx src/pages/PublicClubPage.test.tsx src/pages/PublicDiscoveryPages.test.tsx` -> PASS
- Build frontend: `npm run build` -> PASS

## Rischi residui

- La sezione home geolocalizzata richiede attivazione esplicita della posizione; e una scelta voluta per evitare prompt browser invasivi all ingresso.
- I contatori 3/4, 2/4, 1/4 nel summary club sono aggregati pubblici sulla finestra match pubblica standard, non filtrati per livello.