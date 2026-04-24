# STATO PLAY 2

## Esito

PASS

La Fase 2 frontend del modulo `/play` e stata implementata nel repo reale, validata con test mirati Vitest e con build frontend completa.

## Superficie consegnata

### Route frontend attive

- `/play`
- `/play/invite/:token`
- `/play/matches/:matchId`
- `/c/:clubSlug/play`
- `/c/:clubSlug/play/invite/:token`
- `/c/:clubSlug/play/matches/:matchId`

Le route alias `/play/*` redirezionano alla forma canonica `/c/:clubSlug/play/*` preservando la risoluzione tenant da path o query.

### Pagine e componenti aggiunti

- `frontend/src/pages/PlayPage.tsx`
- `frontend/src/pages/InviteAcceptPage.tsx`
- `frontend/src/pages/SharedMatchPage.tsx`
- `frontend/src/components/play/JoinConfirmModal.tsx`
- `frontend/src/components/play/MatchCard.tsx`
- `frontend/src/components/play/MatchBoard.tsx`
- `frontend/src/components/play/MyMatches.tsx`
- `frontend/src/components/play/CreateMatchForm.tsx`
- `frontend/src/services/playApi.ts`
- `frontend/src/utils/play.ts`

### Integrazioni aggiornate

- `frontend/src/App.tsx`
- `frontend/src/types.ts`
- `frontend/src/utils/tenantContext.ts`
- `frontend/src/services/api.ts`

## Comportamento effettivo rilasciato

### PlayPage

- Hero dedicato `/play`, separato dalla homepage booking `/`
- Bacheca `Partite da completare` con rendering dell ordine backend `3/4 -> 2/4 -> 1/4`
- CTA `Unisciti` per ogni match aperto
- Se utente anonimo: apertura `JoinConfirmModal` con nome, telefono, livello, privacy
- Se utente riconosciuto: sezione `Le mie partite` visibile nel tenant corrente
- Sezione `Crea nuova partita` con giorno, durata, campo reale, slot reale, livello, nota
- Share action che costruisce link canonico tenant-aware verso la pagina condivisa

### InviteAcceptPage

- Onboarding da token su `/c/:clubSlug/play/invite/:token`
- Form con livello dichiarato e privacy obbligatoria
- Success state con accesso diretto alla bacheca play del club

### SharedMatchPage

- Pagina pubblica condivisibile per singola partita
- Stato distinto tra player gia riconosciuto e visitatore anonimo
- Visitore anonimo: CTA `Identificati per unirti`
- Player riconosciuto: CTA `Unisciti`
- Il path pubblico usa oggi `matchId` come identificativo reale della partita condivisa

## API e contratti realmente usati

La Fase 2 usa i contratti backend disponibili dalla Fase 1, senza introdurre write endpoint nuovi per join o create match.

### Endpoint letti dal frontend

- `GET /api/play/me`
- `GET /api/play/matches`
- `GET /api/play/matches/{match_id}`
- `POST /api/play/identify`
- `POST /api/public/community-invites/{token}/accept`

### Motore disponibilita riusato per CreateMatchForm

- `GET /api/public/availability`

Il form `Crea nuova partita` prepara un intent UI completo ma non esegue ancora la creazione persistente del match, perche l endpoint write dedicato non fa parte della Fase 1 backend.

## Test e validazione eseguiti

### Test frontend mirati

Comando eseguito:

`npx vitest run src/pages/PlayPage.test.tsx`

Esito:

- `6 passed`

Copertura verificata:

- render route canonica `/c/:clubSlug/play`
- propagazione tenant slug al client API
- ordine visuale dei match aperti
- onboarding obbligatorio su join anonimo
- privacy obbligatoria su invite accept
- differenza shared page anonimo vs riconosciuto
- alias `/play` verso route canonica

### Build frontend

Comando eseguito:

`npm run build`

Esito:

- build completata con successo

## Deviazioni intenzionali da traccia ideale

### Identificativo pubblico match

La pagina condivisa `/c/:clubSlug/play/matches/:matchId` usa oggi esplicitamente `match.id` come identificativo reale instradato dal frontend.

Motivo:

- la Fase 1 backend persiste `public_share_token_hash`
- il raw token pubblico non e ricostruibile dal frontend
- non era corretto introdurre in Fase 2 una migrazione o un nuovo contratto backend non richiesto da `play_1.md`

Impatto:

- il wiring UX e completo
- il naming lato route/UI ora e coerente con il comportamento reale attuale
- la sostituzione con vero token pubblico potra avvenire in una fase successiva, ma richiedera un contratto backend esplicito

## Rischi residui per la fase successiva

- manca ancora il write backend per `join match`
- manca ancora il write backend per `create match`
- la shared page non usa ancora un vero raw public share token consumabile esternamente
- la feedback UX su join/create e attualmente informativa, non conclusiva, finche gli endpoint write non vengono esposti

## File di test aggiunto

- `frontend/src/pages/PlayPage.test.tsx`