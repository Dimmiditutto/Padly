# PROMPT OPERATIVO PER COPILOT - SUPPORTO MULTI CAMPO

Agisci come un Senior Full-Stack Engineer esperto di FastAPI, SQLAlchemy, Alembic, React, TypeScript e Tailwind.

Devi implementare il supporto a piu campi nel repository reale PadelBooking, con patch minime ma complete, coerenti con la logica di business esistente e senza rompere i flussi booking/admin/public gia presenti.

## Obiettivo prodotto

Il sistema oggi lavora di fatto come single-court.

Devi estenderlo per consentire:

1. creazione di piu campi lato admin tramite bottone `Crea Campo`
2. assegnazione di un `nome` a ogni campo
3. gestione indipendente per campo di:
   - prenotazioni singole
   - serie ricorrenti
   - blackout / blocchi orari
   - vista settimanale
   - elenco prenotazioni
   - dettaglio prenotazione
4. visualizzazione lato utente degli slot disponibili per ogni campo nella home pubblica

Il comportamento desiderato e: ogni campo deve funzionare come il campo unico attuale, ma con isolamento corretto per disponibilita, conflitti e operazioni admin.

## Contesto reale del repository da rispettare

Prima di modificare il codice, allinea ogni decisione a questi fatti reali del repo:

1. Il backend e FastAPI multi-tenant shared-database con `Club` come tenant root.
2. Le route admin operative usano `get_current_admin_enforced`.
3. Le route public operative critiche usano `get_current_club_enforced`.
4. Il dominio booking attuale non ha ancora un'entita `Court` o `Field`.
5. `Booking`, `RecurringBookingSeries` e `BlackoutPeriod` oggi non hanno ancora un riferimento esplicito al campo.
6. La logica di availability e lock sta in `backend/app/services/booking_service.py` ed e oggi calibrata su un solo campo.
7. La home pubblica usa `GET /api/public/availability` e mostra una sola griglia di slot.
8. L'admin dashboard gestisce gia prenotazione manuale, serie ricorrente, blackout e regole operative.

## Vincoli non negoziabili

1. Non fare refactor generali.
2. Mantieni la patch coerente con il repository reale, non con una versione ideale del prodotto.
3. Ogni query nuova o modificata deve restare filtrata per `club_id`.
4. Nessuna route admin nuova deve aggirare `get_current_admin_enforced`.
5. Nessuna route public nuova o modificata deve aggirare `get_current_club_enforced` quando l'operazione e critica.
6. Non rompere i contratti tenant-aware gia introdotti nel frontend.
7. Non trattare i campi come pura UI: il modello dati e la concorrenza devono essere corretti.

## Decisione architetturale obbligatoria

Per implementare correttamente il multi-campo devi introdurre una vera entita di dominio, ad esempio `Court`.

Il supporto multi-campo non puo essere fatto solo aggiungendo un nome in frontend.

### Entita minima richiesta

`Court` o nome equivalente, con almeno:

- `id`
- `club_id`
- `name`
- `sort_order` o equivalente per ordinamento stabile
- `is_active`
- `created_at`
- `updated_at`

Vincoli consigliati:

- unique `(club_id, name)`

## Modifiche dati obbligatorie

Introduci `court_id` nei punti minimi dove oggi il dominio e implicitamente single-court:

1. `Booking`
2. `RecurringBookingSeries`
3. `BlackoutPeriod`

Se nel repository esistono altre entita direttamente legate all'occupazione di un campo, valuta se vanno collegate anch'esse ma senza allargare scope inutilmente.

## Migrazione e backfill obbligatori

Poiche il sistema esistente ha gia dati single-court, devi gestire la retrocompatibilita.

Implementa una migration che:

1. crea la tabella `courts`
2. crea per ogni `Club` esistente un campo iniziale di default, con nome chiaro tipo `Campo 1`
3. aggiunge `court_id` alle tabelle necessarie
4. backfill dei record esistenti assegnandoli al campo iniziale del rispettivo tenant
5. rende `court_id` non nullable dopo il backfill

Regola fondamentale:

- nessun booking/ricorrenza/blackout legacy deve restare senza campo assegnato

## Lock e conflitti: comportamento obbligatorio

Oggi la logica e sostanzialmente single-court. Questo va corretto.

### Nuova regola business

- due prenotazioni in overlap sullo stesso campo sono vietate
- due prenotazioni in overlap su campi diversi sono consentite

Quindi devi aggiornare:

1. lock applicativo
2. query di availability
3. controlli di overlap
4. create/update booking
5. create/update serie ricorrenti
6. blackout

Il lock deve diventare per-campo, non globale per tutto il club.

## Funzionalita admin obbligatorie

### 1. Gestione campi

Aggiungi una sezione admin per la gestione campi con almeno:

- bottone `Crea Campo`
- input per nome campo
- elenco campi esistenti
- possibilita di vedere quali campi sono attivi

Per la prima iterazione sono sufficienti:

- creazione campo
- rinomina campo
- eventuale attivazione/disattivazione se utile e semplice

### 2. Dashboard admin

Nelle card operative esistenti devi introdurre la scelta del campo per:

- prenotazione manuale
- serie ricorrente
- blackout

La scelta del campo deve essere obbligatoria e chiara.

Se esiste un solo campo, il comportamento puo restare pre-selezionato per evitare attrito UX.

### 3. Elenco prenotazioni

La vista elenco deve mostrare chiaramente anche il nome del campo.

Se utile, aggiungi filtro per campo, ma solo se la patch resta sobria e coerente.

### 4. Vista settimanale

La vista settimanale deve rendere evidente su quale campo ricade ogni prenotazione.

Soluzioni accettabili:

- gruppo per campo
- badge campo
- righe separate per campo

Non introdurre un calendario enorme o ingestibile se non serve.

### 5. Dettaglio prenotazione

Nel dettaglio booking deve risultare il campo associato.

Se la prenotazione e modificabile, deve essere possibile cambiare campo solo se il nuovo slot su quel campo e realmente disponibile.

## Funzionalita public obbligatorie

### Home utente

La home pubblica non deve piu mostrare una singola griglia indistinta.

Deve far vedere chiaramente quali slot sono disponibili per ogni campo.

### Requisiti minimi UX lato utente

Mostra gli slot raggruppati per campo, ad esempio:

- card per campo
- titolo con nome campo
- griglia slot per quel campo

L'utente deve capire subito:

1. quali campi esistono
2. quali orari sono disponibili per ciascun campo
3. quale campo sta selezionando

Quando l'utente seleziona uno slot, il payload di booking deve includere anche il campo scelto.

## API e contratti backend da estendere

Modifica i contratti minimi in modo coerente tra backend e frontend.

### Admin

Servono endpoint o estensioni per:

- listare campi del tenant
- creare campo
- rinominare campo se previsto
- usare `court_id` nei payload di create/update booking, recurring e blackout

### Public

`GET /api/public/availability` deve restituire disponibilita per campo, non piu una lista piatta unica.

Scegli una shape chiara e minimale, ad esempio una lista di campi con relativa lista slot.

Esempio logico:

```json
{
  "date": "2026-04-23",
  "duration_minutes": 90,
  "deposit_amount": 20,
  "courts": [
    {
      "court_id": "...",
      "court_name": "Campo 1",
      "slots": []
    }
  ]
}
```

Non introdurre campi superflui se non servono alla UI.

## Scelte consigliate ma utili

Se lo ritieni utile e sostenibile nella patch, aggiungi anche:

1. `sort_order` per ordinare stabilmente i campi
2. `is_active` per disattivare un campo senza cancellarlo
3. blocco alla cancellazione di un campo se ha booking future, serie o blackout collegati
4. seed automatico di `Campo 1` per nuovi tenant oltre al backfill legacy

Questi punti sono consigliati per evitare debito tecnico immediato.

## Cose da non fare

1. Non implementare la creazione campi solo lato frontend.
2. Non lasciare il lock globale single-court se esistono piu campi.
3. Non permettere collisioni silenziose tra campi diversi o tra stesso campo.
4. Non duplicare intere pagine admin quando basta estendere quelle esistenti.
5. Non rompere il booking pubblico esistente per il caso con un solo campo.

## File probabili da toccare

Backend:

- `backend/app/models/__init__.py`
- `backend/alembic/versions/...`
- `backend/app/services/booking_service.py`
- `backend/app/services/settings_service.py` solo se davvero necessario
- `backend/app/api/routers/public.py`
- `backend/app/api/routers/admin_bookings.py`
- `backend/app/api/routers/admin_ops.py`
- eventuale nuovo router admin per i campi
- `backend/app/schemas/common.py`
- `backend/app/schemas/public.py`
- `backend/app/schemas/admin.py`

Frontend:

- `frontend/src/types.ts`
- `frontend/src/services/publicApi.ts`
- `frontend/src/services/adminApi.ts`
- `frontend/src/pages/PublicBookingPage.tsx`
- `frontend/src/components/SlotGrid.tsx`
- `frontend/src/pages/AdminDashboardPage.tsx`
- `frontend/src/pages/AdminBookingsPage.tsx`
- `frontend/src/pages/AdminCurrentBookingsPage.tsx`
- `frontend/src/pages/AdminBookingDetailPage.tsx`
- eventuale componente/admin section per creare e gestire i campi

## Test obbligatori

### Backend

Copri almeno:

1. creazione campo per tenant
2. booking overlap rifiutato sullo stesso campo
3. booking overlap consentito su campi diversi
4. recurring series scoped per campo
5. blackout scoped per campo
6. availability public che restituisce slot separati per campo
7. backfill/migration coerente per i dati legacy
8. isolamento tenant corretto dei campi

### Frontend

Copri almeno:

1. rendering degli slot raggruppati per campo nella home pubblica
2. selezione slot con campo corretto nel payload
3. presenza del bottone `Crea Campo` e creazione campo in admin
4. selezione campo nelle card admin operative
5. visualizzazione del nome campo nelle liste o nel dettaglio dove tocchi il rendering

## Validazione finale obbligatoria

Esegui una validazione reale sul repository:

1. test backend mirati per multi-campo
2. build frontend
3. test frontend toccati

Se il repository lo consente, esegui anche la suite completa. Se emergono failure preesistenti fuori scope, non aprire refactor collaterali: segnalale soltanto.

## Output atteso

Applica direttamente le modifiche nel repository.

Alla fine riassumi in modo concreto:

1. quali file hai toccato
2. come hai modellato i campi
3. come hai gestito il backfill legacy single-court -> multi-campo
4. come hai corretto lock e availability per campo
5. quali test hai eseguito
6. eventuali limiti residui
