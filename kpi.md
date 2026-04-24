# PROMPT MIRATO - KPI E REPORTISTICA CHIARA PER BOOKING /play

Usa `play_master.md` come contesto fisso. Non rimettere in discussione la logica di business gia chiusa nelle fasi precedenti. Mantieni il codice coerente col repository reale.

Agisci come:
- Senior Prompt Engineer orientato all'implementazione reale
- Senior Software Architect pragmatico
- Senior Backend Engineer su FastAPI + SQLAlchemy
- Senior Frontend Engineer su React + TypeScript
- Senior QA tecnico rigoroso

Prima di iniziare devi leggere obbligatoriamente:
- `play_master.md`
- `STATO_PLAY_3.md`
- `backend/app/models/__init__.py`
- `backend/app/services/play_service.py`
- `backend/app/services/report_service.py`
- `backend/app/api/routers/admin_ops.py`
- `backend/app/schemas/admin.py`
- `backend/tests/test_play_phase3.py`
- `frontend/src/utils/bookingOrigin.ts`
- `frontend/src/pages/AdminBookingsPage.tsx`
- `frontend/src/pages/AdminBookingDetailPage.tsx`
- `frontend/src/components/AdminBookingCard.tsx`
- `frontend/src/pages/AdminBookingsPage.test.tsx`
- `frontend/src/pages/AdminBookingDetailPage.test.tsx`

Se `STATO_PLAY_3.md` non e `PASS`, fermati e non procedere.

## Obiettivo

Chiudere una base esplicita e robusta per il controllo dei report `/play`, eliminando la dipendenza da inferenze fragili e rendendo la provenienza delle booking interrogabile in modo chiaro sia lato backend sia lato admin UI.

Il risultato atteso e:
- una booking nata da `/play` deve risultare esplicitamente riconoscibile nei dati persistiti
- i report devono poter distinguere in modo diretto booking `/play`, booking pubbliche e booking admin
- la UI admin deve leggere una semantica chiara, non una convenzione nascosta

## Problema reale da chiudere

Oggi la distinzione `/play` e utile ma indiretta:
- il booking finale del match usa `ADMIN_MANUAL`
- la UI capisce che la booking viene da `/play` tramite `created_by=play:<match_id>`
- questa soluzione e sufficiente per la Fase 3, ma non e la base migliore per KPI, report backend, export e analisi future

## Decisione implementativa da seguire

Implementa una distinzione persistita e interrogabile per l'origine `/play`.

Default obbligatorio da seguire salvo conflitto tecnico reale:
- introduci un source dedicato per le booking create dal completamento di un match `/play`
- mantieni `created_by=play:<match_id>` come informazione di audit e compatibilita, ma non come classificatore primario
- usa la UI e i report backend per leggere prima il source esplicito e solo in fallback i dati legacy storici

La forma piu diretta attesa e una nuova voce enum, ad esempio `PLAY`, nel source booking. Se trovi una soluzione equivalente ma piu sicura nel repository reale, documentala chiaramente e mantienila semplice.

## Perimetro funzionale minimo

### Backend dati

Chiudi una soluzione persistita per l'origine booking `/play`.

Default atteso:
- aggiungi un source dedicato nel modello booking
- aggiorna la migration necessaria
- mantieni la compatibilita con i dati esistenti

Valuta anche un backfill minimo per i record storici gia riconoscibili tramite `created_by=play:` se il repository lo consente in modo sicuro. Se non fai backfill, lascia un fallback esplicito e documentato per i dati legacy.

### Backend dominio

Aggiorna il completamento del match `/play` in modo che la booking finale nasca gia con il source corretto.

Non alterare le altre semantiche di booking:
- stato booking
- depositi
- audit log
- lock e comportamento transazionale

### Backend report

Estendi il report summary admin in modo minimale ma utile.

Chiudi almeno KPI espliciti per:
- totale booking
- booking `/play`
- booking pubbliche
- booking admin manuali
- booking admin ricorrenti

Se utile e coerente, aggiungi anche almeno uno tra:
- depositi raccolti da booking `/play`
- booking `/play` confermate
- rapporto percentuale booking `/play` sul totale

Non costruire una BI complessa. Fai solo la base chiara e interrogabile.

### Frontend admin

Aggiorna la UI admin per leggere la nuova semantica in modo esplicito:
- lista booking
- dettaglio booking
- badge o label origine
- eventuale riepilogo KPI se gia esiste una superficie adatta

Mantieni comunque un fallback legacy per record storici non migrati, ma il percorso primario deve essere il source persistito.

## Regole di prodotto da rispettare

- non rompere la logica booking esistente fuori dal perimetro `/play`
- non cambiare il significato delle booking admin manuali reali
- non usare inferenze string-based come fonte primaria del reporting nuovo
- non fare refactor ampi dell'area admin se non strettamente necessario
- non introdurre dashboard fantasiose o fuori stile rispetto al frontend attuale

## File probabilmente coinvolti

Valuta questi file prima di modificare il codice:
- `backend/app/models/__init__.py`
- `backend/app/services/play_service.py`
- `backend/app/services/report_service.py`
- `backend/app/api/routers/admin_ops.py`
- `backend/app/schemas/admin.py`
- `backend/alembic/versions/*`
- `backend/tests/test_play_phase3.py`
- eventuale nuovo test backend dedicato alla reportistica `/play`
- `frontend/src/utils/bookingOrigin.ts`
- `frontend/src/pages/AdminBookingsPage.tsx`
- `frontend/src/pages/AdminBookingDetailPage.tsx`
- `frontend/src/components/AdminBookingCard.tsx`
- `frontend/src/pages/AdminBookingsPage.test.tsx`
- `frontend/src/pages/AdminBookingDetailPage.test.tsx`

## Test richiesti

Aggiungi test reali almeno per:
- booking finale creata da `/play` con source esplicito corretto
- report summary admin con breakdown coerente delle booking per origine
- compatibilita legacy per record storici ancora classificati via `created_by=play:` se scegli fallback o backfill parziale

Se tocchi il frontend, aggiungi anche test mirati per:
- label origine corretta in lista admin
- label origine corretta in dettaglio booking
- eventuale riepilogo KPI aggiornato se esposto in UI

## Verifica obbligatoria

Se tocchi il backend:
- usa `D:/Padly/PadelBooking/.venv/Scripts/python.exe`
- valida migration Alembic up/down se modifichi enum o schema
- esegui test mirati su `/play` e report admin

Se tocchi il frontend:
- esegui i test mirati delle pagine admin toccate
- esegui `npm run build`

Comandi minimi attesi:
- `Set-Location 'D:/Padly/PadelBooking/backend'`
- `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_play_phase3.py tests/test_admin_and_recurring.py -q --tb=short --maxfail=5`
- `Set-Location 'D:/Padly/PadelBooking/frontend'`
- `npm exec vitest run src/pages/AdminBookingsPage.test.tsx src/pages/AdminBookingDetailPage.test.tsx`
- `npm run build`

Se scegli file test backend diversi o aggiungi una suite dedicata alla reportistica, mantieni comunque verifiche mirate equivalenti.

## Output obbligatorio

Restituisci l'output con questo ordine:

## 1. Prerequisiti verificati
- PASS / FAIL reale

## 2. Mappa del repository rilevante
- file reali toccati

## 3. Strategia scelta
- source persistito introdotto
- eventuale compatibilita legacy
- KPI esposti realmente in backend e UI

## 4. File coinvolti
- file creati o modificati

## 5. Implementazione
- codice completo dei file necessari

## 6. Migrazioni e backfill
- nome migration
- strategia dati storici

## 7. Test aggiunti o modificati
- codice completo dei test

## 8. Verifica finale
- comandi eseguiti
- esito PASS / FAIL reale
- eventuali limiti residui reali

## 9. STATO_KPI.md
- esito PASS / FAIL
- source finale adottato per booking `/play`
- KPI finali esposti
- fallback legacy eventualmente mantenuto
- backlog esplicito solo se resta davvero