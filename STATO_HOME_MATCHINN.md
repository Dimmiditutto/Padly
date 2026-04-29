# STATO_HOME_MATCHINN

- Stato: PASS
- Gate finale: FASE VALIDATA - si puo procedere
- Data: 2026-04-29

## Scope completato

- La root `/` non punta piu al booking pubblico: ora rende una home prodotto dedicata `MatchinnHomePage` con gerarchia centrata su community, discovery, match aperti e area club.
- Il booking pubblico esistente e stato preservato senza cambiarne la business logic ed e ora raggiungibile in modo esplicito su `/booking`.
- La sezione `Le tue community` e alimentata da sessioni Play valide gia presenti nel browser corrente, senza introdurre account globali, password o nuovi modelli di membership.
- Il backend supporta ora un endpoint read-only per la home che ricostruisce le community riconosciute dal browser usando i cookie club-specifici e, in fallback, il cookie legacy.
- Il backend espone ora un endpoint read-only minimale per `Partite aperte vicino a te`, riusando discovery pubblica, finestra pubblica esistente dei match open e ordinamento leggero 3/4 -> 2/4 -> 1/4 -> distanza -> tempo.
- La home riusa la directory pubblica esistente per `Trova campi vicino a te`, con geolocalizzazione esplicita o coordinate gia salvate nella sessione discovery.
- `Area club` resta secondaria e punta a `/admin`.
- Tutti i link che assumevano implicitamente che `/` fosse il booking sono stati riallineati a `/booking` solo dove necessario.

## Compromessi espliciti

- In V1 la lista `Le tue community` resta derivata dalle sessioni Play valide del browser corrente, non da un account Matchinn globale: e il compromesso minimo e coerente col repository attuale.
- Nello stato anonimo la CTA `Ottieni codice OTP dal tuo club` porta a `/clubs`, perche non esiste un ingresso OTP globale indipendente dal `club_slug` e non e stata introdotta nuova auth app-level.
- La sezione `Partite aperte vicino a te` resta volutamente leggera e pubblica: nessun nome player, share token, note private o azioni private esposte in home.

## Privacy e coerenza

- Nessuna modifica alla business logic di booking pubblico, OTP, inviti, group access, join match, notifiche o ranking pubblico gia validato.
- Nessun dato personale o interno e stato esposto nella parte pubblica della nuova home.
- Il confine `pubblico read-only / community privata` e stato mantenuto.

## File toccati

- `backend/app/services/play_service.py`
- `backend/app/api/routers/public.py`
- `backend/app/schemas/public.py`
- `backend/tests/test_play_phase7_public_discovery.py`
- `frontend/src/App.tsx`
- `frontend/src/services/publicApi.ts`
- `frontend/src/types.ts`
- `frontend/src/pages/MatchinnHomePage.tsx`
- `frontend/src/pages/MatchinnHomePage.test.tsx`
- `frontend/src/pages/PlayPage.tsx`
- `frontend/src/pages/PlayAccessPage.tsx`
- `frontend/src/pages/PublicCancellationPage.tsx`
- `frontend/src/pages/PaymentStatusPage.tsx`
- `frontend/src/pages/AdminLoginPage.tsx`
- `frontend/src/pages/PlayPage.test.tsx`
- `frontend/src/pages/PublicDiscoveryPages.test.tsx`
- `frontend/src/pages/PublicCancellationPage.test.tsx`
- `frontend/src/pages/PaymentStatusPage.test.tsx`
- `frontend/src/pages/AdminLoginPage.test.tsx`

## Verifiche eseguite

- Backend sessione Play legacy + cookie club-specifici:
  - `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_play_phase1.py -k "play_me or identify or cross_tenant or public_play_access"`
  - esito: `3 passed, 5 deselected`
- Backend OTP + directory pubblica + discovery + home endpoints:
  - `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_play_access_otp.py tests/test_play_phase6_public_directory.py tests/test_play_phase7_public_discovery.py`
  - esito: `17 passed`
- Frontend test mirati routing/home:
  - `npm run test:run -- src/pages/MatchinnHomePage.test.tsx src/pages/PublicDiscoveryPages.test.tsx src/pages/AdminLoginPage.test.tsx src/pages/PaymentStatusPage.test.tsx src/pages/PublicCancellationPage.test.tsx src/pages/PlayPage.test.tsx`
  - esito: `58 passed`
- Build frontend completa:
  - `npm run build`
  - esito: `PASS`

## Rischi residui non bloccanti

- La home usa la geolocalizzazione solo su azione esplicita dell utente oppure coordinate discovery gia salvate: e una scelta voluta per non forzare prompt browser all ingresso.
- La CTA OTP anonima richiede ancora la scelta del club prima dell accesso: e coerente con l architettura V1 ma non e ancora un onboarding globale Matchinn.
- La nuova root non modifica `PublicBookingPage`: il booking resta integro ma continua ad avere una UX separata dalla nuova home prodotto.