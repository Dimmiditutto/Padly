# FASE 9 — TIMEZONE TENANT-AWARE END-TO-END

Includi: prompt_master.md + STATO_FASE_1.MD + STATO_FASE_2.MD + STATO_FASE_3.MD + STATO_FASE_4.MD + STATO_FASE_5.MD + STATO_FASE_6.MD + STATO_FASE_7.MD se esiste + STATO_FASE_8.MD se esiste + istanze.md

## Obiettivo

Eliminare le ultime assunzioni globali sulla timezone e rendere tenant-aware end-to-end la logica piu sensibile: slot, blackout, recurring, reminder e parsing admin delle date locali.

Questa fase e volutamente separata perche tocca il cuore del dominio booking e non va mescolata con rate limiting o governance dati.

## Stato reale da considerare prima di scrivere codice

Fatti verificati nel repository reale:

- [backend/app/services/booking_service.py](backend/app/services/booking_service.py) usa ancora una costante globale `ROME_TZ = ZoneInfo(settings.timezone)` in punti critici della generazione slot e della conversione locale/UTC
- [backend/app/api/routers/admin_ops.py](backend/app/api/routers/admin_ops.py) parse-a i datetime naive con `ZoneInfo(settings.timezone)` invece che con la timezone del tenant corrente
- [backend/app/core/scheduler.py](backend/app/core/scheduler.py) inizializza `AsyncIOScheduler(timezone=settings.timezone)` su una timezone globale di app
- [backend/app/services/email_service.py](backend/app/services/email_service.py) e gia parzialmente tenant-aware sul formatting email, ma il dominio booking non lo e ancora end-to-end
- [prompts SaaS/STATO_FASE_6.MD](prompts%20SaaS/STATO_FASE_6.MD) dichiara correttamente la timezone per-tenant come rischio residuo

## Aree da coprire

### 1. Slot engine tenant-aware

Porta la logica di slot e parsing locale a usare la timezone del club reale.

Superfici candidate:

- generazione slot disponibili
- parse di slot selezionati e DST edge case
- booking pubblico e admin
- finestre locali usate da blackout e recurring

### 2. Parsing admin coerente col tenant

Le date naive inserite dall'admin devono essere interpretate nella timezone del tenant corrente, non nella timezone globale di app.

### 3. Scheduler e reminder coerenti

Il sistema deve continuare a usare UTC internamente dove serve, ma le finestre e i calcoli lato tenant devono rispettare `club.timezone`.

### 4. Test DST e multi-timezone

Questa fase richiede test seri e mirati su tenant con timezone differenti e su casi di cambio ora.

## Regole

- non riscrivere l'intero dominio booking se bastano helper timezone-aware e propagazione mirata del club
- non rompere i test DST gia presenti
- mantieni UTC come rappresentazione persistita quando gia e la scelta del repository
- evita scorciatoie che rientroducono fallback globali opachi

## Test e verifiche obbligatorie

- test multi-tenant con timezone differenti
- test DST sui casi gia coperti e sui nuovi edge case tenant-aware
- test admin blackout/recurring con timezone tenant-specifica
- test reminder/scheduler coerenti con la timezone del tenant
- PASS/FAIL reale su test mirati e, se tocchi il cuore del dominio booking, su regressioni backend rilevanti

## Output obbligatorio

- file toccati
- punti del dominio booking resi timezone-aware
- eventuali deviazioni o limiti residui
- test aggiunti o aggiornati
- PASS/FAIL reale
- STATO_FASE_9.MD con:
  - cosa e finalmente tenant-aware end-to-end
  - cosa resta ancora globale, se qualcosa resta
  - rischi residui prima del go-live pieno