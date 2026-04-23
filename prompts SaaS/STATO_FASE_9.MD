# STATO FASE 9 — TIMEZONE TENANT-AWARE END-TO-END

## Data

23-04-2026

## Esito reale

- PASS: il motore slot usa ora la timezone del club reale invece della timezone globale applicativa.
- PASS: booking pubblico, booking admin, recurring preview/create/update e parsing blackout admin interpretano le date locali nel contesto `club.timezone`.
- PASS: il frontend admin usa il timezone del tenant reale per prefill, edit e formatting nei flussi booking/admin timezone-sensitive.
- PASS: i blackout admin con datetime naive ambigui nel fallback DST non vengono piu interpretati implicitamente; sono rifiutati con errore esplicito.
- PASS: i test DST esistenti restano verdi e sono stati estesi con casi multi-tenant su timezone differenti.
- PASS: lo scheduler non assume piu una timezone globale di app per il proprio clock base; usa UTC come base neutra.
- PASS: nessuna migrazione Alembic necessaria.
- PASS: build frontend verde e suite frontend completa verde.
- PASS: regressione backend completa verde con 142 passed.

## Decisioni prese

- la persistenza resta in UTC dove era gia la scelta del repository
- la conversione locale/UTC del dominio booking viene resa tenant-aware al boundary di slot, blackout e recurring, senza rifondare il modello dati
- la timezone del tenant viene propagata con patch mirate dai router al service layer quando il club e gia disponibile
- nel service layer resta un fallback esplicito al club risolto via `club_id`, cosi i path interni e i test che non passano il club completo restano coerenti
- il contratto di sessione admin e stato esteso in modo minimo con `timezone`, cosi il frontend puo mostrare e ricostruire orari coerenti senza introdurre nuovi endpoint o refactor ampi
- per i blackout admin il caso fallback DST ambiguo viene gestito in modo esplicito con rifiuto del naive datetime ambiguo, invece di selezionare implicitamente la prima occorrenza
- lo scheduler usa UTC come timezone infrastrutturale neutra; le finestre reminder restano calcolate per tenant tramite `booking_rules` e club iterato

## Cosa e finalmente tenant-aware end-to-end

### Slot engine e booking

- `build_daily_slots()` genera gli slot giornalieri usando la timezone del club corrente
- `resolve_local_slot_start()`, `resolve_slot_window()` e `parse_slot()` supportano ora una timezone esplicita del tenant
- `create_public_booking()` e `create_admin_booking()` convertono gli slot locali nella timezone del tenant reale
- `update_booking_by_admin()` aggiorna gli slot futuri usando la timezone del tenant dell'admin

### Blackout e recurring admin

- [backend/app/api/routers/admin_ops.py](backend/app/api/routers/admin_ops.py) interpreta i datetime naive dei blackout nella timezone del tenant dell'admin
- il parsing admin dei blackout valida anche i casi DST non validi invece di accettare naive datetime sulla timezone globale
- i datetime naive ambigui nel fallback DST vengono rifiutati esplicitamente, con messaggio di errore comprensibile per l'operatore
- `preview_recurring_occurrences()`, `create_recurring_series()` e `update_recurring_series()` usano la timezone del club per preview e creazione delle occorrenze
- i casi fallback/gap DST restano gestiti in modo coerente con la timezone del tenant che sta operando, senza introdurre nuovi workflow di business

### Frontend admin

- [frontend/src/pages/AdminBookingDetailPage.tsx](frontend/src/pages/AdminBookingDetailPage.tsx) ricostruisce `start_time` nel timezone del tenant reale, in coerenza con `slot_id`
- [frontend/src/pages/AdminDashboardPage.tsx](frontend/src/pages/AdminDashboardPage.tsx), [frontend/src/pages/AdminBookingsPage.tsx](frontend/src/pages/AdminBookingsPage.tsx), [frontend/src/pages/AdminCurrentBookingsPage.tsx](frontend/src/pages/AdminCurrentBookingsPage.tsx) e [frontend/src/pages/AdminLogsPage.tsx](frontend/src/pages/AdminLogsPage.tsx) non mostrano piu timestamp admin in timezone browser-local o hardcoded `Europe/Rome`
- [frontend/src/utils/format.ts](frontend/src/utils/format.ts) espone formatter tenant-aware per timestamp e orari, mentre le label weekday date-only non dipendono piu da `Europe/Rome`
- [backend/app/api/routers/admin_auth.py](backend/app/api/routers/admin_auth.py) espone `timezone` nella sessione admin per permettere al frontend di riusare il contesto del tenant gia autenticato

### Reminder e scheduler

- `reminder_job()` continua a iterare i club attivi e a usare `reminder_window_hours` tenant-scoped
- la base timezone dello scheduler non dipende piu da `settings.timezone`; il clock del scheduler e UTC neutro
- il formatting email era gia tenant-aware e resta coerente con `booking.club.timezone`

## Cosa resta ancora globale o neutro

- la persistenza dei datetime resta UTC a database per booking, blackout, webhook e log tecnici
- le cadenze scheduler restano globali come meccanismo infrastrutturale, ma non dipendono piu da una timezone business globale del prodotto
- il job tecnico di retention continua ad avere una schedulazione unica di piattaforma; non fa parte del dominio booking timezone-sensitive
- [backend/app/services/billing_service.py](backend/app/services/billing_service.py) non e stato modificato in questa fase perche fuori dal perimetro booking/reminder richiesto

## File reali toccati per chiusura FASE 9

- [backend/app/services/booking_service.py](backend/app/services/booking_service.py)
- [backend/app/api/routers/public.py](backend/app/api/routers/public.py)
- [backend/app/api/routers/admin_bookings.py](backend/app/api/routers/admin_bookings.py)
- [backend/app/api/routers/admin_ops.py](backend/app/api/routers/admin_ops.py)
- [backend/app/api/routers/admin_auth.py](backend/app/api/routers/admin_auth.py)
- [backend/app/core/scheduler.py](backend/app/core/scheduler.py)
- [backend/app/schemas/admin.py](backend/app/schemas/admin.py)
- [backend/tests/test_tenant_backend_context.py](backend/tests/test_tenant_backend_context.py)
- [frontend/src/types.ts](frontend/src/types.ts)
- [frontend/src/utils/format.ts](frontend/src/utils/format.ts)
- [frontend/src/components/DateFieldWithDay.tsx](frontend/src/components/DateFieldWithDay.tsx)
- [frontend/src/pages/AdminBookingDetailPage.tsx](frontend/src/pages/AdminBookingDetailPage.tsx)
- [frontend/src/pages/AdminDashboardPage.tsx](frontend/src/pages/AdminDashboardPage.tsx)
- [frontend/src/pages/AdminBookingsPage.tsx](frontend/src/pages/AdminBookingsPage.tsx)
- [frontend/src/pages/AdminCurrentBookingsPage.tsx](frontend/src/pages/AdminCurrentBookingsPage.tsx)
- [frontend/src/pages/AdminLogsPage.tsx](frontend/src/pages/AdminLogsPage.tsx)
- [frontend/src/pages/AdminBookingDetailPage.test.tsx](frontend/src/pages/AdminBookingDetailPage.test.tsx)
- [frontend/src/pages/AdminDashboardPage.test.tsx](frontend/src/pages/AdminDashboardPage.test.tsx)

## Contratti introdotti o estesi

### API pubbliche e admin

- nessun endpoint nuovo
- esteso in modo minimo il payload di sessione admin con `timezone`
- nessuna modifica breaking ai payload booking/public/admin gia esposti al frontend
- i payload blackout non cambiano, ma i datetime naive ambigui nel fallback DST ora producono un errore esplicito invece di una scelta implicita lato backend
- il cambiamento e comportamentale: le date locali vengono interpretate rispetto a `club.timezone`

### Service layer

- le funzioni slot-critical di [backend/app/services/booking_service.py](backend/app/services/booking_service.py) accettano ora una timezone tenant esplicita o la risolvono da `club_id`
- la logica DST resta centralizzata nel service di booking per slot, preview e disambiguazione fallback

## Migrazioni e backfill

- nessuna migrazione Alembic necessaria
- nessun backfill dati richiesto: il cambiamento e nel calcolo runtime e nell'interpretazione locale dei datetime input

## Test aggiunti o aggiornati

- in [backend/tests/test_tenant_backend_context.py](backend/tests/test_tenant_backend_context.py):
  - availability pubblica tenant-aware su DST gap per tenant in `Europe/London`
  - parsing blackout admin naive su tenant in `America/New_York`
  - sessione admin estesa con `timezone` tenant-aware
  - rifiuto esplicito dei blackout admin con datetime naive ambigui nel fallback DST
  - recurring preview tenant-aware su DST gap per tenant in `Europe/London`
  - scheduler base timezone neutra in UTC
- regressioni DST esistenti mantenute verdi in [backend/tests/test_booking_api.py](backend/tests/test_booking_api.py) e [backend/tests/test_admin_and_recurring.py](backend/tests/test_admin_and_recurring.py)
- in [frontend/src/pages/AdminBookingDetailPage.test.tsx](frontend/src/pages/AdminBookingDetailPage.test.tsx):
  - edit booking per tenant non `Europe/Rome` con `start_time` derivato dal timezone reale del tenant
  - update recurring per tenant non `Europe/Rome` coerente con `slot_id`
- in [frontend/src/pages/AdminDashboardPage.test.tsx](frontend/src/pages/AdminDashboardPage.test.tsx):
  - verifica che le label weekday non dipendano piu da formatter Rome-only
  - verifica dell'errore esplicito sui blackout DST ambigui

## Verifica finale reale

- PASS: `Set-Location 'D:/Padly/PadelBooking/frontend'; npm run test:run -- AdminBookingDetailPage.test.tsx AdminDashboardPage.test.tsx`
- PASS: `Set-Location 'D:/Padly/PadelBooking/frontend'; npm run build`
- PASS: `Set-Location 'D:/Padly/PadelBooking/frontend'; npm run test:run`
- PASS: `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_tenant_backend_context.py -q --tb=short`
- PASS: `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_booking_api.py -q -k "dst" --tb=short`
- PASS: `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_admin_and_recurring.py -q -k "dst or recurring_preview_disambiguates_fallback" --tb=short`
- PASS: `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests -q -x --tb=short`

## Rischi residui prima del go-live pieno

- le cadenze scheduler restano una scelta infrastrutturale unica; se in futuro serviranno finestre cron davvero tenant-locali per processi di dominio, andranno modellate esplicitamente per club invece di riusare un cron globale
- il dominio booking e ora tenant-aware sulla timezone, ma il progetto mantiene ancora il lock single-court globale: e un rischio distinto, non coperto da questa fase
- eventuali superfici extra-booking che interpretano datetime naive fuori da booking/admin_ops vanno verificate separatamente quando entreranno in perimetro; non emergono blocchi aperti sulla chiusura della FASE 9