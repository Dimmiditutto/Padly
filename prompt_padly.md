Leggi prompt_master.md

# Patch operativa — Padel Booking

Agisci come un Senior Full-Stack Engineer esperto di FastAPI, SQLAlchemy, PostgreSQL, React, TypeScript e Alembic.
Applica in sequenza le patch descritte di seguito, **patch minima, nessun refactor aggiuntivo**.
Ogni sezione indica: file, problema risolto, modifica esatta.

---

## Parte 1 — Compatibilità driver PostgreSQL su Railway

### Problema
Railway (e altri provider cloud) espongono la variabile `DATABASE_URL` con prefisso `postgresql://`.
Il progetto usa **psycopg v3**, che richiede `postgresql+psycopg://`.
Senza questa conversione il motore SQLAlchemy e le migrazioni Alembic falliscono al primo tentativo di connessione.

### 1.1 — `backend/app/core/db.py`

Sostituisci la riga che costruisce `engine` con:

```python
_db_url = settings.database_url
# Railway (e altri provider) forniscono "postgresql://" ma il progetto usa psycopg v3;
# SQLAlchemy richiede il prefisso "postgresql+psycopg://" per il driver corretto.
if _db_url.startswith('postgresql://'):
    _db_url = _db_url.replace('postgresql://', 'postgresql+psycopg://', 1)

connect_args = {'check_same_thread': False} if _db_url.startswith('sqlite') else {}
engine = create_engine(_db_url, future=True, pool_pre_ping=True, connect_args=connect_args)
```

### 1.2 — `backend/alembic/env.py`

Sostituisci la riga `config.set_main_option('sqlalchemy.url', settings.database_url)` con:

```python
_alembic_db_url = settings.database_url
if _alembic_db_url.startswith('postgresql://'):
    _alembic_db_url = _alembic_db_url.replace('postgresql://', 'postgresql+psycopg://', 1)
config.set_main_option('sqlalchemy.url', _alembic_db_url)
```

### 1.3 — `backend/alembic/versions/20260415_0001_initial.py`

**Problema aggiuntivo:** la migrazione iniziale usava `sa.Enum(...).create()` e `CREATE TYPE IF NOT EXISTS` che non funzionano correttamente su Railway PostgreSQL (conflitti con tipi già esistenti da deployment precedenti, `IF NOT EXISTS` non supportato in tutte le versioni).

**Soluzione finale verificata:**

1. Aggiungi l'import in cima al file:
   ```python
   from sqlalchemy.dialects import postgresql
   ```

2. Sostituisci le definizioni degli Enum a livello modulo con oggetti `postgresql.ENUM` distinti:
   - Oggetti `_enum` per la **creazione** (senza `create_type=False`)
   - Alias con `create_type=False` per il **riuso nelle colonne** (evita ricreazioni implicite)

   ```python
   admin_role_enum = postgresql.ENUM('SUPERADMIN', name='adminrole')
   booking_status_enum = postgresql.ENUM('PENDING_PAYMENT', 'CONFIRMED', 'CANCELLED', 'COMPLETED', 'NO_SHOW', 'EXPIRED', name='bookingstatus')
   payment_provider_enum = postgresql.ENUM('STRIPE', 'PAYPAL', 'NONE', name='paymentprovider')
   payment_status_enum = postgresql.ENUM('UNPAID', 'INITIATED', 'PAID', 'FAILED', 'CANCELLED', 'EXPIRED', name='paymentstatus')
   booking_source_enum = postgresql.ENUM('PUBLIC', 'ADMIN_MANUAL', 'ADMIN_RECURRING', name='bookingsource')

   admin_role = postgresql.ENUM('SUPERADMIN', name='adminrole', create_type=False)
   booking_status = postgresql.ENUM('PENDING_PAYMENT', 'CONFIRMED', 'CANCELLED', 'COMPLETED', 'NO_SHOW', 'EXPIRED', name='bookingstatus', create_type=False)
   payment_provider = postgresql.ENUM('STRIPE', 'PAYPAL', 'NONE', name='paymentprovider', create_type=False)
   payment_status = postgresql.ENUM('UNPAID', 'INITIATED', 'PAID', 'FAILED', 'CANCELLED', 'EXPIRED', name='paymentstatus', create_type=False)
   booking_source = postgresql.ENUM('PUBLIC', 'ADMIN_MANUAL', 'ADMIN_RECURRING', name='bookingsource', create_type=False)
   ```

3. Nel blocco `upgrade()`, dopo `op.execute('CREATE EXTENSION IF NOT EXISTS btree_gist')`, sostituisci qualsiasi `CREATE TYPE` manuale con:
   ```python
   admin_role_enum.create(bind, checkfirst=True)
   booking_status_enum.create(bind, checkfirst=True)
   payment_provider_enum.create(bind, checkfirst=True)
   payment_status_enum.create(bind, checkfirst=True)
   booking_source_enum.create(bind, checkfirst=True)
   ```

4. Correggi i `server_default` delle colonne booleane: PostgreSQL richiede `'true'`/`'false'`, non `'1'`/`'0'`:
   - `admins.is_active`: `server_default=sa.text('true')`
   - `blackout_periods.is_active`: `server_default=sa.text('true')`

5. Nel blocco `downgrade()`, sostituisci `booking_source.drop(bind, checkfirst=True)` e simili con:
   ```python
   if is_postgresql:
       op.execute('DROP TYPE IF EXISTS bookingsource')
       op.execute('DROP TYPE IF EXISTS paymentstatus')
       op.execute('DROP TYPE IF EXISTS paymentprovider')
       op.execute('DROP TYPE IF EXISTS bookingstatus')
       op.execute('DROP TYPE IF EXISTS adminrole')
   ```
   Nota: `is_postgresql` deve essere dichiarato anche nel blocco `downgrade()` (`bind = op.get_bind()` / `is_postgresql = bind.dialect.name == 'postgresql'`).

---

## Parte 2 — UI admin: pulsante logout e navigazione

### Problema
Le pagine admin secondarie (`AdminBookingsPage`, `AdminCurrentBookingsPage`, `AdminLogsPage`) non avevano un pulsante "Esci" visibile. Il nav link attivo non si distingueva visivamente. La Dashboard mostrava il link "Log" nel nav header (ridondante per l'admin).

### 2.1 — `frontend/src/components/AdminNav.tsx`

1. Il link attivo usava `className='btn-primary'` — sostituisci con la classe Tailwind inline completa per evitare dipendenze indirette:
   ```tsx
   className={isActive
     ? 'inline-flex min-h-12 items-center justify-center gap-2 rounded-2xl border border-brand-700 bg-brand-700 px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-600 focus:outline-none focus:ring-2 focus:ring-cyan-200'
     : 'btn-secondary'}
   ```

2. Aggiungi la prop `showLog` (opzionale, default `true`) per nascondere il link "Log" in certi contesti:
   ```tsx
   export function AdminNav({ showLog = true }: { showLog?: boolean }) {
     const location = useLocation();
     const visibleNavItems = showLog ? navItems : navItems.filter((item) => item.to !== '/admin/log');
     // ... usa visibleNavItems nel map invece di navItems
   }
   ```

### 2.2 — `frontend/src/pages/AdminBookingsPage.tsx`

1. Aggiungi costanti di stile per i pulsanti hero area (sticky bar):
   ```tsx
   const HERO_ACTION_BUTTON_CLASS = 'inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-2xl border border-brand-100 bg-brand-100 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:border-brand-700 hover:text-brand-700 ... sm:w-auto';
   const HERO_LOGOUT_BUTTON_CLASS = 'inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-2xl border border-[#f6c206] bg-[#f6c206] px-4 py-3 text-sm font-semibold text-slate-950 transition hover:brightness-95 focus:outline-none focus:ring-2 focus:ring-[#f6c206]/50 disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto';
   const HERO_ACTIONS_WRAPPER_CLASS = 'sticky top-3 z-20 -mx-1 flex w-full flex-col gap-3 rounded-[24px] bg-slate-950/95 p-1 backdrop-blur sm:static sm:mx-0 sm:flex-row sm:justify-end sm:bg-transparent sm:p-0';
   ```

2. Aggiungi la funzione `logout()` e importa `logoutAdmin` da adminApi.

3. Nella hero area: wrap i bottoni nel `HERO_ACTIONS_WRAPPER_CLASS` e aggiungi:
   ```tsx
   <button className={HERO_LOGOUT_BUTTON_CLASS} type='button' onClick={() => void logout()}>Esci</button>
   ```

4. Usa `formatDate` (non solo `formatDateTime`) per le date nelle descrizioni delle serie ricorrenti.

### 2.3 — `frontend/src/pages/AdminCurrentBookingsPage.tsx` e `AdminLogsPage.tsx`

Stessa logica: aggiungi import `logoutAdmin`, aggiungi funzione `logout()`, aggiungi pulsante "Esci" nella hero area con stile `HERO_LOGOUT_BUTTON_CLASS`.

### 2.4 — `frontend/src/pages/AdminDashboardPage.tsx`

1. Usa `<AdminNav showLog={false} />` nella Dashboard per nascondere il link "Log" (già raggiungibile da `AdminBookingsPage`).

2. Nel form serie ricorrenti, sostituisci eventuali componenti `DateFieldWithDay` con `<input type="date">` nativi (label + input separati) per `start_date` e `end_date`. Questo rimuove la dipendenza dal componente custom e consente controllo diretto degli stili.

---

## Parte 3 — Eliminazione serie ricorrenti già annullate

### Problema
L'admin non poteva eliminare definitivamente dall'elenco una serie ricorrente completamente annullata. Le serie annullate restavano visibili per sempre.

### 3.1 — `backend/app/services/booking_service.py`

Aggiungi alla fine del file la funzione:

```python
def delete_cancelled_recurring_series(
    db: Session,
    *,
    series_id: str,
    actor: str,
) -> tuple[str, str, list[str]]:
    series = db.scalar(select(RecurringBookingSeries).where(RecurringBookingSeries.id == series_id))
    if not series:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Serie ricorrente non trovata')

    bookings = db.scalars(
        select(Booking)
        .where(
            Booking.recurring_series_id == series_id,
            Booking.source == BookingSource.ADMIN_RECURRING,
        )
        .order_by(Booking.start_at.asc())
    ).all()

    if len(bookings) == 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='La serie ricorrente non contiene occorrenze eliminabili')

    if any(booking.status != BookingStatus.CANCELLED for booking in bookings):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Puoi eliminare dall\'elenco solo serie ricorrenti già annullate')

    deleted_booking_ids = [booking.id for booking in bookings]
    series_label = series.label

    for booking in bookings:
        db.delete(booking)

    db.flush()
    db.delete(series)

    log_event(
        db,
        None,
        'RECURRING_SERIES_DELETED',
        f'Serie ricorrente eliminata dall\'elenco: {series_label}',
        actor=actor,
        payload={
            'series_id': series_id,
            'deleted_count': len(deleted_booking_ids),
            'booking_ids': deleted_booking_ids,
        },
    )

    return series_id, series_label, deleted_booking_ids
```

### 3.2 — `backend/app/schemas/admin.py`

Aggiungi lo schema di risposta:

```python
class RecurringDeleteResponse(BaseModel):
    message: str
    series_id: str
    deleted_count: int
    booking_ids: list[str] = Field(default_factory=list)
```

### 3.3 — `backend/app/api/routers/admin_ops.py`

Aggiungi import di `RecurringDeleteResponse` e `delete_cancelled_recurring_series`, poi aggiungi la route:

```python
@router.delete('/recurring/{series_id}', response_model=RecurringDeleteResponse)
def delete_recurring_series(series_id: str, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)) -> RecurringDeleteResponse:
    with acquire_single_court_lock(db):
        deleted_series_id, _, deleted_booking_ids = delete_cancelled_recurring_series(db, series_id=series_id, actor=admin.email)
        db.commit()

    return RecurringDeleteResponse(
        message="Serie ricorrente eliminata dall'elenco.",
        series_id=deleted_series_id,
        deleted_count=len(deleted_booking_ids),
        booking_ids=deleted_booking_ids,
    )
```

### 3.4 — `frontend/src/services/adminApi.ts`

Aggiungi la funzione:

```typescript
export async function deleteRecurringSeries(seriesId: string) {
  const response = await api.delete<{ message: string; series_id: string; deleted_count: number; booking_ids: string[] }>(`/admin/recurring/${seriesId}`);
  return response.data;
}
```

### 3.5 — `frontend/src/pages/AdminBookingsPage.tsx`

1. Importa `deleteRecurringSeries` da adminApi.

2. Aggiungi costante di stile:
   ```tsx
   const DELETE_SERIES_BUTTON_CLASS = 'inline-flex min-h-10 items-center justify-center rounded-full border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-semibold text-rose-700 transition hover:border-rose-300 hover:bg-rose-100 focus:outline-none focus:ring-2 focus:ring-rose-200';
   ```

3. Aggiungi handler:
   ```tsx
   async function handleDeleteSeries(seriesId: string, seriesLabel: string) {
     if (!window.confirm(`Confermi l'eliminazione definitiva della serie annullata "${seriesLabel}" dall'elenco admin?`)) {
       return;
     }
     setFeedback(null);
     try {
       const response = await deleteRecurringSeries(seriesId);
       setSelectedOccurrences((prev) => ({ ...prev, [seriesId]: [] }));
       setExpandedSeries((prev) => ({ ...prev, [seriesId]: false }));
       setFeedback({ tone: 'success', message: `Serie eliminata dall'elenco: ${response.deleted_count} occorrenze rimosse.` });
       await loadBookings();
     } catch (error: any) {
       if (getRequestStatus(error) === 401) { navigate('/admin/login'); return; }
       setFeedback({ tone: 'error', message: getRequestMessage(error, 'Eliminazione serie non riuscita.') });
     }
   }
   ```

4. Nel render delle serie ricorrenti, usa logica condizionale: se la serie è completamente annullata (`entry.isFullyCancelled`), mostra il bottone "Elimina serie" (`DELETE_SERIES_BUTTON_CLASS`) al posto dei bottoni "Annulla selezionate" / "Annulla tutta la serie".

---

## Parte 4 — Tariffe informative giocatori configurabili

### Problema
Le tariffe per giocatore erano hardcoded nel frontend (`PublicBookingPage.tsx`). Non erano modificabili dall'admin. Il pannello booking pubblico non mostrava i valori aggiornati dall'admin.

### 4.1 — `backend/app/services/settings_service.py`

1. Aggiungi costante con valori di default:
   ```python
   DEFAULT_INFORMATIVE_PLAYER_RATES = [
       'Tesserati: € 7/ora per giocatore',
       'Non tesserati: € 9/ora per giocatore',
       '90 minuti: € 10 per giocatore tesserato',
       '90 minuti: € 13 per giocatore non tesserato',
   ]
   ```

2. Aggiungi `informative_player_rates` al dizionario di default in `default_booking_rules()`.

3. Aggiorna `get_booking_rules()` per gestire la chiave `informative_player_rates` (è una lista, non un intero — trattamento distinto nel merge).

4. Aggiungi parametro `informative_player_rates: list[str]` a `update_booking_rules()` e includilo nel valore salvato.

### 4.2 — `backend/app/schemas/admin.py`

1. Aggiungi validatore helper:
   ```python
   def _normalize_non_empty_rate(value: object) -> str:
       normalized = str(value).strip()
       if not normalized:
           raise ValueError('Le tariffe informative non possono essere vuote')
       return normalized
   ```

2. Aggiungi campo a `AdminSettingsResponse`:
   ```python
   informative_player_rates: list[str]
   ```

3. Aggiungi campo a `AdminSettingsUpdateRequest` con validatore:
   ```python
   informative_player_rates: list[str] = Field(min_length=1, max_length=8)

   @field_validator('informative_player_rates')
   @classmethod
   def validate_informative_player_rates(cls, value: list[object]) -> list[str]:
       return [_normalize_non_empty_rate(item) for item in value]
   ```

### 4.3 — `backend/app/schemas/public.py`

Aggiungi a `PublicConfigResponse`:
```python
informative_player_rates: list[str]
```

### 4.4 — `backend/app/api/routers/admin_settings.py`

Passa `informative_player_rates=payload.informative_player_rates` a `update_booking_rules(...)`.

### 4.5 — `backend/app/api/routers/public.py`

Includi `informative_player_rates=booking_rules['informative_player_rates']` nella costruzione di `PublicConfigResponse`.

### 4.6 — `frontend/src/pages/AdminDashboardPage.tsx`

1. Nel submit `handleSaveSettings()`: includi `informative_player_rates: settings.informative_player_rates` nel payload.

2. Nella sezione "Regole operative": aggiungi un pannello editabile con la lista delle tariffe. Ogni tariffa ha un `<input>` modificabile. L'onChange aggiorna `settings.informative_player_rates[index]`.

3. Aggiorna la description della SectionCard per menzionare le tariffe informative.

### 4.7 — `frontend/src/pages/PublicBookingPage.tsx`

1. Le tariffe hardcoded diventano fallback:
   ```tsx
   const defaultPlayerRates = [ /* stessi valori di prima */ ];
   const playerRates = publicConfig?.informative_player_rates?.length
     ? publicConfig.informative_player_rates
     : defaultPlayerRates;
   ```

2. Aggiungi navigazione giorno precedente/successivo accanto al campo data:
   ```tsx
   const canGoToPreviousDay = bookingDate > today;

   function moveBookingDate(days: number) {
     setBookingDate((previous) => {
       const nextDate = addDaysToDateInput(previous, days);
       return nextDate < today ? today : nextDate;
     });
   }
   ```
   Nel JSX, wrap l'`<input type="date">` con bottoni `<ChevronLeft>` / `<ChevronRight>` (da lucide-react). Il bottone sinistro è `disabled={!canGoToPreviousDay}`.

---

## Parte 5 — Performance: bulk query per disponibilità giornaliera

### Problema
`build_daily_slots()` in `booking_service.py` chiamava `assert_slot_available()` per ogni slot del giorno (es. 16 slot/giorno = 32 query DB per una sola chiamata a `GET /public/availability`). Con Railway/PostgreSQL remoto ogni query costa ~30-80ms.

### 5.1 — `backend/app/services/booking_service.py` — `build_daily_slots()`

Prima del loop sugli slot, calcola la finestra del giorno ed esegui 2 query bulk:

```python
all_local_starts = iter_local_slot_starts(booking_date)
if not all_local_starts:
    return slots

day_start_utc = all_local_starts[0].astimezone(UTC)
day_end_utc = all_local_starts[-1].astimezone(UTC) + timedelta(minutes=duration_minutes)

blocking_bookings = db.scalars(
    select(Booking).where(
        Booking.start_at < day_end_utc,
        Booking.end_at > day_start_utc,
        Booking.status.in_(BLOCKING_STATUSES),
    )
).all()

active_blackouts = db.scalars(
    select(BlackoutPeriod).where(
        BlackoutPeriod.is_active.is_(True),
        BlackoutPeriod.start_at < day_end_utc,
        BlackoutPeriod.end_at > day_start_utc,
    )
).all()
```

Nel loop, sostituisci `assert_slot_available()` con check in-memoria:

```python
conflict_booking = next(
    (b for b in blocking_bookings if b.start_at < end_at and b.end_at > start_at),
    None,
)
if conflict_booking:
    available = False
    reason = 'Lo slot non è più disponibile'
else:
    conflict_blackout = next(
        (bl for bl in active_blackouts if bl.start_at < end_at and bl.end_at > start_at),
        None,
    )
    if conflict_blackout:
        available = False
        reason = "Fascia bloccata dall'admin"
```

**Non toccare `assert_slot_available()`** — è usata da altri flussi (booking singolo, etc.).

### 5.2 — Nuova migration: `backend/alembic/versions/20260421_0003_availability_indexes.py`

Crea il file con:
- `revision = '20260421_0003'`
- `down_revision = '20260417_0002'`
- `upgrade()`: crea indice `ix_bookings_overlap_status` su `bookings(start_at, end_at, status)` e `ix_blackout_periods_active_overlap` su `blackout_periods(is_active, start_at, end_at)`
- `downgrade()`: drop degli stessi indici

### 5.3 — `frontend/src/components/AdminTimeSlotPicker.tsx`

1. Aggiungi early-return nel `useEffect` quando `bookingDate` è vuoto:
   ```tsx
   if (!bookingDate) {
     setSlots([]);
     setError('');
     return;
   }
   ```

2. Aggiungi `AbortController` per cancellare le richieste in-flight al cambio data:
   ```tsx
   const controller = new AbortController();
   // passa controller.signal a getAvailability(bookingDate, durationMinutes, controller.signal)
   // nella cleanup: controller.abort()
   ```

3. Nel `catch`, silenzia gli errori di abort (non mostrare il banner "Non riesco a caricare"):
   ```tsx
   if (
     err instanceof Error && err.name === 'AbortError' ||
     axios.isCancel(err) ||
     (err instanceof Error && (err as { code?: string }).code === 'ERR_CANCELED')
   ) {
     return;
   }
   ```
   Aggiungi `import axios from 'axios'` in cima.

### 5.4 — `frontend/src/services/publicApi.ts`

Aggiungi parametro `signal` opzionale a `getAvailability()`:

```typescript
export async function getAvailability(date: string, durationMinutes: number, signal?: AbortSignal) {
  const response = await api.get<AvailabilityResponse>('/public/availability', {
    params: { date, duration_minutes: durationMinutes },
    signal,
  });
  return response.data;
}
```

---

## Parte 6 — Performance: bulk query per serie ricorrenti

### Problema
`preview_recurring_occurrences()` chiamava `assert_slot_available()` (2 query DB) per ciascuna delle N occorrenze della serie. Per 26 settimane: **52 query DB** solo in preview.
`create_recurring_series()` e `update_recurring_series()` chiamavano `db.flush()` dopo ogni singolo booking inserito (N round-trip su PostgreSQL remoto).

### 6.1 — `backend/app/services/booking_service.py` — `preview_recurring_occurrences()`

Prima del loop sulle date, calcola la finestra complessiva ed esegui 2 bulk query:

```python
first_local_start = datetime.combine(dates[0], parsed_time).replace(tzinfo=ROME_TZ)
last_local_start = datetime.combine(dates[-1], parsed_time).replace(tzinfo=ROME_TZ)
range_start_utc = first_local_start.astimezone(UTC)
range_end_utc = last_local_start.astimezone(UTC) + timedelta(minutes=duration_minutes)

booking_overlap_filters = [
    Booking.start_at < range_end_utc,
    Booking.end_at > range_start_utc,
    Booking.status.in_(BLOCKING_STATUSES),
]
if exclude_recurring_series_id:
    booking_overlap_filters.append(
        or_(Booking.recurring_series_id.is_(None), Booking.recurring_series_id != exclude_recurring_series_id)
    )
blocking_bookings = db.scalars(select(Booking).where(and_(*booking_overlap_filters))).all()

active_blackouts = db.scalars(
    select(BlackoutPeriod).where(
        BlackoutPeriod.is_active.is_(True),
        BlackoutPeriod.start_at < range_end_utc,
        BlackoutPeriod.end_at > range_start_utc,
    )
).all()
```

Nel loop per occorrenza, sostituisci `assert_slot_available(...)` con check in-memoria:

```python
conflicting = next(
    (b for b in blocking_bookings if b.start_at < end_at and b.end_at > start_at),
    None,
)
if conflicting:
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Lo slot non è più disponibile')
blackout = next(
    (bp for bp in active_blackouts if bp.start_at < end_at and bp.end_at > start_at),
    None,
)
if blackout:
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Fascia bloccata dall'admin")
```

**Non modificare `assert_slot_available()`** — continua ad essere usata da altri flussi.

### 6.2 — `backend/app/services/booking_service.py` — `create_recurring_series()` e `update_recurring_series()`

In entrambe le funzioni, sostituisci il pattern `db.add(booking)` + `db.flush()` per singola occorrenza con:

```python
bookings_to_create: list[Booking] = []
bookings_meta: list[tuple[Booking, dict]] = []  # (booking, occurrence)

for occurrence in occurrences:
    if not occurrence['available']:
        # ... log_event skipped come prima ...
        continue
    # ... costruisci booking come prima ...
    bookings_to_create.append(booking)
    bookings_meta.append((booking, occurrence))

# Un solo flush per ottenere tutti gli id generati dal DB
db.add_all(bookings_to_create)
db.flush()

for booking, occurrence in bookings_meta:
    log_event(
        db, booking, 'RECURRING_OCCURRENCE_CREATED', '...',
        actor=actor,
        payload={
            'series_id': series.id,
            'label': label,
            'booking_date': occurrence['booking_date'].isoformat(),  # usa occurrence, non booking_date locale
            'start_time': occurrence['start_time'],
            'end_time': occurrence['end_time'],
        },
    )
    created.append(booking)
```

Il `db.commit()` resta nel **router** (`admin_ops.py`), non nel service.

### 6.3 — `frontend/src/services/adminApi.ts`

Aumenta il timeout per `createRecurring()` e `updateRecurringSeries()` a 120 secondi (override del default 15s dell'istanza axios):

```typescript
export async function createRecurring(payload: RecurringSeriesPayload) {
  const response = await api.post<RecurringCreateResponse>('/admin/recurring', payload, {
    timeout: 120000,
  });
  return response.data;
}

export async function updateRecurringSeries(seriesId: string, payload: RecurringSeriesPayload) {
  const response = await api.put<RecurringCreateResponse>(`/admin/recurring/${seriesId}`, payload, {
    timeout: 120000,
  });
  return response.data;
}
```

### 6.4 — `frontend/src/pages/AdminDashboardPage.tsx`

1. Aggiungi helper per riconoscere timeout/cancellazione:
   ```typescript
   function isCanceledOrTimedOut(error: any) {
     const code = error?.code;
     const name = error?.name;
     const message = String(error?.message || '').toLowerCase();
     return (
       code === 'ECONNABORTED' ||
       code === 'ERR_CANCELED' ||
       name === 'AbortError' ||
       message.includes('timeout') ||
       message.includes('canceled') ||
       message.includes('cancelled') ||
       message.includes('network error')
     );
   }
   ```

2. Aggiungi state:
   ```tsx
   const [creatingRecurring, setCreatingRecurring] = useState(false);
   ```

3. In `createRecurringSeries()`:
   - Prima del try: `setCreatingRecurring(true)`
   - Nel catch, se `isCanceledOrTimedOut(error)`: mostra feedback con `tone: 'success'` e messaggio di guida ("La creazione della serie ha richiesto più tempo del previsto. Verifica in Prenotazioni attuali o in Elenco prenotazioni: la serie potrebbe essere già stata salvata.") e ritorna
   - In `finally`: `setCreatingRecurring(false)`

4. Il pulsante "Crea serie":
   ```tsx
   <button
     className='btn-primary'
     type='button'
     disabled={creatingRecurring}
     onClick={() => void createRecurringSeries()}
   >
     {creatingRecurring ? 'Creazione in corso…' : 'Crea serie'}
   </button>
   ```

---

## Criteri di accettazione globali

- Deploy su Railway funzionante senza errori di connessione DB
- Migrazione iniziale idempotente (rieseguibile senza duplicare tipi ENUM)
- `GET /public/availability`: da N query per slot a **2 query bulk** per giornata
- `POST /api/admin/recurring`: da ~52+ query per preview a **2 query bulk**; da N flush a **1 flush**
- Tutte le pagine admin hanno pulsante "Esci"
- Serie ricorrenti completamente annullate eliminabili dall'elenco
- Tariffe giocatori configurabili da admin e visibili nel booking pubblico
- Navigazione giorno precedente/successivo nella pagina booking pubblico
- Timeout frontend per creazione serie: 120s; su timeout mostra messaggio orientativo, non errore
- Nessuna modifica a business logic di booking, pagamenti, annullamenti
- Nessuna modifica alla response shape delle API esistenti