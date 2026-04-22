Leggi prompts SaaS/prompt_master.md

# Patch operativa coerente con il repo attuale - Padel Booking

Agisci come un Senior Full-Stack Engineer esperto di FastAPI, SQLAlchemy, PostgreSQL, React, TypeScript e Alembic.
Applica solo patch minime, nessun refactor generale.
Prima di modificare il codice, allinea ogni intervento al repository reale attuale e non a versioni precedenti del progetto.

---

## Vincoli globali obbligatori

1. Il backend e shared-database multi-tenant. Ogni nuova query su bookings, blackout, recurring series, report o availability deve restare filtrata per club_id.
2. Il layer commerciale FASE 5 e gia attivo. Ogni nuova route admin operativa deve usare get_current_admin_enforced. Ogni route public operativa deve preservare get_current_club_enforced.
3. Il frontend e tenant-aware via query param e interceptor axios. Se estendi getAvailability o altre API condivise, non rompere la firma corrente che accetta tenantSlug. Se aggiungi AbortSignal, aggiungilo come parametro opzionale finale.
4. La chain Alembic attuale termina a 20260422_0004_billing_saas. Non creare revision duplicate e non riusare revision_id gia presenti nel repository.
5. Se aggiungi campi a PublicConfig o AdminSettings, aggiorna in modo coerente backend schemas, router, frontend types e test. Questo cambia intenzionalmente la response shape e va trattato come modifica esplicita, non come side effect.
6. I pulsanti Esci nelle pagine admin sono gia presenti. Non riaprire quel lavoro e non duplicare markup o logica di logout.
7. Non indebolire la policy commerciale gia cablata. Nessuna nuova route admin o public deve aggirare i dependency enforced.
8. Mantieni separati billing SaaS e booking payments legacy.

---

## Fuori scope esplicito

- Non ricreare il lavoro gia fatto sui pulsanti Esci delle pagine admin.
- Non sostituire DateFieldWithDay in tutto il progetto per preferenza stilistica. Se lo tocchi, fallo solo dove c'e un problema concreto e senza aprire refactor trasversali.
- Non creare migration con revision 20260421_0003: esiste gia nel repo.
- Non rimuovere tenantSlug dalle firme dei service frontend gia tenant-aware.
- Non introdurre route admin operative con get_current_admin al posto di get_current_admin_enforced.

---

## Parte 1 - Compatibilita PostgreSQL su Railway con psycopg v3

### Problema

Railway e altri provider possono esporre DATABASE_URL con prefisso postgresql://.
Il progetto usa psycopg v3 e SQLAlchemy deve ricevere postgresql+psycopg://.

### 1.1 - backend/app/core/db.py

Normalizza settings.database_url prima di creare engine.

Usa questa logica:

```python
_db_url = settings.database_url
if _db_url.startswith('postgresql://'):
    _db_url = _db_url.replace('postgresql://', 'postgresql+psycopg://', 1)

connect_args = {'check_same_thread': False} if _db_url.startswith('sqlite') else {}
engine = create_engine(_db_url, future=True, pool_pre_ping=True, connect_args=connect_args)
```

### 1.2 - backend/alembic/env.py

Normalizza allo stesso modo anche la URL usata da Alembic:

```python
_alembic_db_url = settings.database_url
if _alembic_db_url.startswith('postgresql://'):
    _alembic_db_url = _alembic_db_url.replace('postgresql://', 'postgresql+psycopg://', 1)
config.set_main_option('sqlalchemy.url', _alembic_db_url)
```

### 1.3 - Alembic migrations: enum e boolean default compatibili con PostgreSQL

Audit e correggi le migration che definiscono enum PostgreSQL o server_default booleani non portabili.

Minimo richiesto:

1. In backend/alembic/versions/20260415_0001_initial.py:
   - usa sqlalchemy.dialects.postgresql.ENUM per i tipi enum PostgreSQL
   - separa gli oggetti enum usati per create da quelli usati nelle colonne con create_type=False
   - crea i tipi con checkfirst=True nel blocco upgrade
   - nel downgrade usa DROP TYPE IF EXISTS solo in ambito PostgreSQL
   - sostituisci i server_default booleani testuali non portabili con true o false

2. Controlla anche le migration successive gia presenti nel repo, in particolare:
   - backend/alembic/versions/20260421_0003_tenant_foundation.py
   - backend/alembic/versions/20260422_0004_billing_saas.py

Se trovi server_default booleani espressi come 1 o 0, normalizzali in true o false in modo coerente con PostgreSQL.

Vincolo: nessuna migration deve introdurre revision duplicate o branch multipli non necessari.

---

## Parte 2 - UI admin residua, senza riaprire lavoro gia chiuso

### Problema reale rimasto

La navigazione admin puo ancora nascondere il link Log nella Dashboard, ma i pulsanti Esci non vanno toccati: sono gia presenti.

### 2.1 - frontend/src/components/AdminNav.tsx

1. Mantieni lo stile attuale del link attivo.
2. Aggiungi la prop opzionale showLog con default true.
3. Filtra navItems in visibleNavItems quando showLog e false.
4. Non cambiare la logica tenant-aware del componente.

Esempio di firma attesa:

```tsx
export function AdminNav({
  session,
  notificationEmail,
  showLog = true,
}: {
  session?: AdminSession | null;
  notificationEmail?: string | null;
  showLog?: boolean;
}) {
  const visibleNavItems = showLog ? navItems : navItems.filter((item) => item.to !== '/admin/log');
}
```

### 2.2 - frontend/src/pages/AdminDashboardPage.tsx

Usa AdminNav con showLog={false} nella Dashboard.

Non riaggiungere pulsanti Esci e non rifare la hero bar.

---

## Parte 3 - Eliminazione serie ricorrenti gia annullate

### Problema

Una serie ricorrente completamente annullata deve poter essere rimossa dall'elenco admin.

### 3.1 - backend/app/services/booking_service.py

Aggiungi una funzione delete_cancelled_recurring_series con questi vincoli:

1. Deve ricevere club_id oltre a series_id e actor.
2. Deve cercare la serie filtrando per id e club_id.
3. Deve cercare le occorrenze filtrando per:
   - Booking.club_id == resolved_club_id
   - Booking.recurring_series_id == series_id
   - Booking.source == BookingSource.ADMIN_RECURRING
4. Deve permettere l'eliminazione solo se tutte le occorrenze della serie sono gia CANCELLED.
5. Deve cancellare prima le occorrenze e poi la serie.
6. Deve registrare un log_event con club_id coerente.

Shape consigliata:

```python
def delete_cancelled_recurring_series(
    db: Session,
    *,
    series_id: str,
    actor: str,
    club_id: str | None = None,
) -> tuple[str, str, list[str]]:
```

### 3.2 - backend/app/schemas/admin.py

Aggiungi:

```python
class RecurringDeleteResponse(BaseModel):
    message: str
    series_id: str
    deleted_count: int
    booking_ids: list[str] = Field(default_factory=list)
```

### 3.3 - backend/app/api/routers/admin_ops.py

Aggiungi la route DELETE per la serie ricorrente, ma usa get_current_admin_enforced, non get_current_admin.

Firma attesa:

```python
@router.delete('/recurring/{series_id}', response_model=RecurringDeleteResponse)
def delete_recurring_series(
    series_id: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin_enforced),
) -> RecurringDeleteResponse:
```

Chiama il service passando club_id=admin.club_id e mantieni acquire_single_court_lock.

### 3.4 - frontend/src/services/adminApi.ts

Aggiungi:

```typescript
export async function deleteRecurringSeries(seriesId: string) {
  const response = await api.delete<{ message: string; series_id: string; deleted_count: number; booking_ids: string[] }>(`/admin/recurring/${seriesId}`);
  return response.data;
}
```

### 3.5 - frontend/src/pages/AdminBookingsPage.tsx

1. Importa deleteRecurringSeries.
2. Aggiungi handler dedicato per eliminare una serie completamente annullata.
3. Se entry.isFullyCancelled e true, mostra il bottone Elimina serie al posto dei bottoni di annullamento.
4. Mantieni la logica tenant-aware esistente su navigate e logout.

### 3.6 - Test minimi richiesti

Backend:
- test che una serie completamente cancellata venga eliminata correttamente
- test che una serie con almeno una occorrenza non cancellata restituisca 409
- test che l'endpoint resti nello scope del tenant corretto

Frontend:
- test mirato sulla visibilita del bottone Elimina serie solo per serie fully cancelled

---

## Parte 4 - Tariffe informative giocatori configurabili

### Problema

Le tariffe informative per giocatore sono hardcoded nel frontend. Devono diventare configurabili da admin e visibili nel booking pubblico.

### 4.1 - backend/app/services/settings_service.py

1. Aggiungi una costante default:

```python
DEFAULT_INFORMATIVE_PLAYER_RATES = [
    'Tesserati: EUR 7/ora per giocatore',
    'Non tesserati: EUR 9/ora per giocatore',
    '90 minuti: EUR 10 per giocatore tesserato',
    '90 minuti: EUR 13 per giocatore non tesserato',
]
```

2. Aggiungi informative_player_rates alle booking rules di default.
3. Aggiorna i type hint del service: con questo campo, default_booking_rules e get_booking_rules non sono piu dict[str, int].
4. Nel merge di get_booking_rules:
   - i campi numerici restano castati a int
   - informative_player_rates resta list[str]
5. update_booking_rules deve accettare informative_player_rates: list[str] e salvarlo nel payload.

### 4.2 - backend/app/schemas/admin.py

1. Aggiungi helper validator per rate non vuote.
2. Aggiungi informative_player_rates a AdminSettingsResponse.
3. Aggiungi informative_player_rates a AdminSettingsUpdateRequest con validator dedicato.

### 4.3 - backend/app/schemas/public.py

Aggiungi informative_player_rates a PublicConfigResponse.

### 4.4 - backend/app/api/routers/admin_settings.py

Passa informative_player_rates a update_booking_rules o update_tenant_settings in modo coerente con il design attuale.

### 4.5 - backend/app/api/routers/public.py

Includi informative_player_rates nel PublicConfigResponse.

### 4.6 - frontend/src/types.ts

Aggiorna tutti i contratti TypeScript coerentemente:

- PublicConfig
- AdminSettings
- AdminSettingsUpdatePayload

Senza questo pass il prompt non e valido: il frontend deve conoscere i nuovi campi.

### 4.7 - frontend/src/pages/AdminDashboardPage.tsx

1. Nel salvataggio settings includi informative_player_rates.
2. Aggiungi una UI minima per modificare la lista delle tariffe informative.
3. Mantieni patch locale: non rifare l'intero pannello settings.

### 4.8 - frontend/src/pages/PublicBookingPage.tsx

1. Le tariffe hardcoded diventano fallback.
2. Se publicConfig.informative_player_rates esiste ed e non vuota, usa quella lista.

Nota importante: questa parte modifica intenzionalmente la response shape delle API settings e public config. Aggiorna test e tipi di conseguenza.

---

## Parte 5 - Performance: bulk query per availability giornaliera

### Problema

build_daily_slots oggi usa assert_slot_available per ogni slot e genera troppe query.

### 5.1 - backend/app/services/booking_service.py - build_daily_slots()

Ottimizza con due query bulk per giornata, ma preserva il tenant scope.

Logica richiesta:

1. Calcola una sola volta all_local_starts = list(iter_local_slot_starts(booking_date)).
2. Se la lista e vuota, ritorna subito [].
3. Calcola day_start_utc e day_end_utc.
4. Esegui query bulk su bookings e blackout filtrando anche per resolved_club_id.

Le query devono includere almeno:

```python
Booking.club_id == resolved_club_id
Booking.start_at < day_end_utc
Booking.end_at > day_start_utc
Booking.status.in_(BLOCKING_STATUSES)
```

e

```python
BlackoutPeriod.club_id == resolved_club_id
BlackoutPeriod.is_active.is_(True)
BlackoutPeriod.start_at < day_end_utc
BlackoutPeriod.end_at > day_start_utc
```

Nel loop usa check in-memory per conflitti booking e blackout.

Non modificare assert_slot_available: resta usata da altri flussi.

### 5.2 - Nuova migration indici availability

Non creare 20260421_0003.

Crea una nuova migration con revision unica successiva alla chain attuale, ad esempio:

- file: backend/alembic/versions/20260422_0005_availability_indexes.py
- revision = '20260422_0005'
- down_revision = '20260422_0004'

Gli indici devono essere coerenti con le query tenant-scoped. Non usare indici che ignorano club_id.

Target minimo consigliato:

- bookings(club_id, status, start_at, end_at)
- blackout_periods(club_id, is_active, start_at, end_at)

### 5.3 - frontend/src/components/AdminTimeSlotPicker.tsx

1. Aggiungi early return quando bookingDate e vuoto.
2. Usa AbortController per annullare richieste in-flight.
3. Non mostrare error banner sugli abort.
4. Non rompere la compatibilita tenant-aware delle chiamate sottostanti.

### 5.4 - frontend/src/services/publicApi.ts

Estendi getAvailability mantenendo tenantSlug e aggiungendo signal come parametro finale.

Firma attesa:

```typescript
export async function getAvailability(
  date: string,
  durationMinutes: number,
  tenantSlug?: string | null,
  signal?: AbortSignal,
) {
  const response = await api.get<AvailabilityResponse>('/public/availability', {
    params: { date, duration_minutes: durationMinutes, ...withTenantParams(tenantSlug) },
    signal,
  });
  return response.data;
}
```

Non sostituire tenantSlug con signal.

---

## Parte 6 - Performance: bulk query per serie ricorrenti

### Problema

preview_recurring_occurrences e create/update recurring fanno troppe query e troppi flush.

### 6.1 - backend/app/services/booking_service.py - preview_recurring_occurrences()

Prima del loop sulle date:

1. calcola range_start_utc e range_end_utc
2. esegui 2 query bulk tenant-scoped
3. mantieni exclude_recurring_series_id dove necessario

Le query devono restare nel tenant scope. In particolare il filtro bookings deve includere Booking.club_id == resolved_club_id e quello blackout BlackoutPeriod.club_id == resolved_club_id.

Nel loop usa conflitti in-memory, non assert_slot_available ad ogni occorrenza.

### 6.2 - backend/app/services/booking_service.py - create_recurring_series() e update_recurring_series()

Sostituisci il pattern add + flush per ogni booking con:

1. raccolta in bookings_to_create
2. db.add_all(bookings_to_create)
3. un solo db.flush()
4. log_event successivo per ogni booking creato

Mantieni db.commit nei router, non nei service.

### 6.3 - frontend/src/services/adminApi.ts

Alza timeout solo per createRecurring e updateRecurringSeries a 120000 ms.

### 6.4 - frontend/src/pages/AdminDashboardPage.tsx

1. Aggiungi helper per riconoscere timeout e cancellazioni.
2. Aggiungi state creatingRecurring.
3. Mostra messaggio orientativo in caso di timeout o cancellazione lunga, non errore duro.
4. Disabilita il pulsante Crea serie mentre la richiesta e in corso.

---

## Validazione obbligatoria

Esegui almeno questi controlli dopo le patch:

1. Backend mirato su recurring, booking e availability.
2. Backend mirato sui nuovi endpoint o sui nuovi campi settings/public config.
3. Suite backend completa se tocchi migration, booking_service o dependency condivise.
4. Build frontend se tocchi types, services o pagine React.

Comandi attesi, adattando il path del Python del repo:

```powershell
Set-Location D:/Padly/PadelBooking/backend
D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_admin_and_recurring.py tests/test_booking_api.py -q -x --tb=short
D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/ -q -x --tb=short

Set-Location D:/Padly/PadelBooking/frontend
npm run build
```

---

## Criteri di accettazione globali aggiornati

- Deploy Railway funzionante con DATABASE_URL normalizzata per psycopg v3
- Nessuna migration con revision duplicate; nuova migration availability allineata a 20260422_0004
- Enum PostgreSQL e boolean default compatibili con Postgres nelle migration toccate
- GET /public/availability passa da query per slot a query bulk, ma resta scoped per club_id
- preview e create/update recurring usano query bulk e un solo flush dove possibile
- Nessuna regressione tenant-aware nel frontend: tenantSlug resta compatibile nelle API condivise
- La nuova route di delete recurring usa get_current_admin_enforced
- informative_player_rates e configurabile da admin e visibile nel booking pubblico
- I tipi frontend sono allineati ai nuovi campi backend
- Nessuna regressione della policy commerciale FASE 5
- Nessuna modifica non richiesta a booking payments legacy, annullamenti pubblici o flussi di billing SaaS