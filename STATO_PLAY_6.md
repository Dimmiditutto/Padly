# STATO PLAY 6

## Esito

PASS

## Obiettivo fase

Abilitare la discovery pubblica dei club senza rompere i flussi esistenti:

- route pubbliche additive `/clubs`, `/clubs/nearby`, `/c/:clubSlug`
- ricerca manuale per citta, CAP, provincia
- geolocalizzazione browser opzionale solo per ordinamento per distanza
- pagina pubblica club con informazioni minime e partite open in vista leggera
- continuita garantita per `/` e `/c/:clubSlug/play`

## Decisioni architetturali confermate

- i dati strutturati pubblici del club vivono su `Club`, non in `AppSetting`
- nessun geocoding esterno e nessuna dipendenza Google Maps
- la distanza viene calcolata lato backend in modo deterministico
- il fallback manuale resta sempre disponibile anche se la geolocalizzazione e negata o assente
- la vista pubblica delle partite usa un serializer dedicato e non riusa la serializzazione privata community
- finestra pubblica match open impostata a 7 giorni

## Dati pubblici introdotti sul club

- `public_address`
- `public_postal_code`
- `public_city`
- `public_province`
- `public_latitude`
- `public_longitude`
- `is_community_open`

## API e route introdotte

### Backend

- `GET /api/public/clubs`
- `GET /api/public/clubs/nearby`
- `GET /api/public/clubs/{club_slug}`

### Frontend

- `/clubs`
- `/clubs/nearby`
- `/c/:clubSlug`

## Comportamento implementato

### Directory pubblica club

- `/clubs` mostra una directory pubblica con identita minima, contatti minimi, numero campi e stato community
- ricerca manuale per citta, CAP o provincia
- CTA verso pagina pubblica club e community privata del club

### Club vicini

- `/clubs/nearby` prova a usare `navigator.geolocation`
- se il permesso e negato o il browser non supporta la feature, la UI espone un messaggio chiaro e torna al fallback manuale
- i club senza coordinate non ricevono distanze inventate

### Pagina pubblica del club

- `/c/:clubSlug` mostra identita pubblica del club e stato di apertura della community
- espone un filtro livello per le partite open pubbliche
- mostra solo match open nella finestra dei prossimi 7 giorni
- non espone nomi giocatori, note, creator name, token di share, join action o dettagli interni
- la CTA operativa porta a `/c/:clubSlug/play`

### Continuita dei flussi esistenti

- `/` resta la home booking pubblica del tenant
- `/c/:clubSlug/play` resta la superficie privata community
- gli alias esistenti di `/play` non sono stati rimossi

## File toccati

### Backend

- `backend/app/models/__init__.py`
- `backend/app/services/tenant_service.py`
- `backend/app/schemas/admin.py`
- `backend/app/services/settings_service.py`
- `backend/app/api/routers/admin_settings.py`
- `backend/app/schemas/public.py`
- `backend/app/services/play_service.py`
- `backend/app/api/routers/public.py`
- `backend/app/main.py`
- `backend/alembic/versions/20260424_0012_play_phase6_public_club_fields.py`
- `backend/tests/test_admin_and_recurring.py`
- `backend/tests/test_tenant_backend_context.py`
- `backend/tests/test_play_phase6_public_directory.py`

### Frontend

- `frontend/src/types.ts`
- `frontend/src/services/publicApi.ts`
- `frontend/src/App.tsx`
- `frontend/src/pages/AdminDashboardPage.tsx`
- `frontend/src/pages/AdminDashboardPage.test.tsx`
- `frontend/src/pages/ClubDirectoryPage.tsx`
- `frontend/src/pages/PublicClubPage.tsx`
- `frontend/src/pages/PublicDiscoveryPages.test.tsx`

## Validazioni eseguite davvero

### Backend

Comando:

```bash
D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest -vv tests/test_admin_and_recurring.py -k "public_club_fields or partial_public_coordinates or update_reflected_in_public_config"
```

Esito:

- `3 passed`

Comando:

```bash
D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest -vv tests/test_play_phase6_public_directory.py
```

Esito:

- `3 passed`

### Frontend

Comando:

```bash
npm run test:run -- src/pages/PublicDiscoveryPages.test.tsx
```

Esito:

- `4 passed`

Comando:

```bash
npm run test:run -- src/pages/AdminDashboardPage.test.tsx src/pages/PublicBookingPage.test.tsx src/pages/PlayPage.test.tsx src/pages/PublicDiscoveryPages.test.tsx
```

Esito:

- `46 passed`

Comando:

```bash
npm run build
```

Esito:

- build frontend completata con successo

## Vincoli rispettati

- nessuna rottura di `/`
- nessuna rottura di `/c/:clubSlug/play`
- nessun uso di Google Maps o geocoding esterno
- nessuna esposizione pubblica di dati personali dei player community
- approccio additive-only sulle route pubbliche

## Note operative finali

- per apparire bene in `/clubs/nearby`, il club deve avere sia latitudine sia longitudine valorizzate
- la ricerca manuale non dipende dalle coordinate e continua a funzionare con citta, CAP e provincia
- `is_community_open` comunica solo un segnale pubblico di apertura, non automatizza join o onboarding
- la pagina pubblica club resta una vetrina informativa, non una seconda interfaccia community

## Backlog esplicito per una futura v2 notifiche mirate

- notifiche opt-in per nuovi match open compatibili con livello e fascia oraria preferita
- watchlist di club preferiti con alert su nuove partite open 3/4 o 2/4
- digest geolocalizzato per club vicini con community aperta
- ranking pubblico arricchito con disponibilita media recente, senza esporre dati personali
- landing pubblica del club con richiesta contatto guidata prima dell ingresso community