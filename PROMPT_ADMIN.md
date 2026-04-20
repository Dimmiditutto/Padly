# PROMPT ADMIN OPERATIVO PER COPILOT — CALIBRATO SUL REPOSITORY REALE

Agisci come un Senior Full Stack Engineer React/TypeScript/Tailwind + FastAPI/SQLAlchemy + UX/UI Specialist.

Devi eseguire una patch minima, precisa e coerente sull’area admin del repository reale PadelBooking.

## Obiettivo

Implementa esclusivamente le modifiche richieste qui sotto, senza refactor generali e senza toccare parti non coinvolte.

## Contesto reale del codice

- Frontend:
  - frontend/src/App.tsx oggi espone /admin, /admin/login, /admin/reset-password e /admin/bookings/:bookingId. Non esistono ancora /admin/prenotazioni e /admin/log.
  - frontend/src/pages/AdminDashboardPage.tsx è una dashboard monolitica con sezioni Prenotazioni, Log essenziali, Prenotazione manuale, Blocca fascia oraria, Serie ricorrente, Regole operative.
  - frontend/src/pages/AdminLoginPage.tsx e frontend/src/pages/AdminPasswordResetPage.tsx usano frontend/src/components/AppBrand.tsx.
  - frontend/src/components/AppBrand.tsx oggi mostra icona razzo + payoff “PadelBooking / 1 campo, 1 flusso chiaro, conferma rapida”.
  - frontend/src/pages/PublicBookingPage.tsx e frontend/src/components/SlotGrid.tsx contengono già il pattern UI più coerente per selezione data, giorno e orari.
  - frontend/src/services/adminApi.ts non espone ancora API per eliminare occorrenze ricorrenti singole, multiple o l’intera serie.
  - frontend/src/types.ts espone source, ma non ancora recurring_series_id o recurring_series_label in modo esplicito.
- Backend:
  - backend/app/api/routers/admin_bookings.py supporta lista prenotazioni, create/update/status/balance.
  - backend/app/api/routers/admin_ops.py supporta blackouts, recurring preview/create, report, eventi.
  - backend/app/services/booking_service.py in list_bookings filtra solo per booking_date, status, payment_provider e customer_query.
  - backend/app/models/__init__.py contiene già RecurringBookingSeries e Booking.recurring_series_id.
  - backend/app/services/booking_service.py crea le ricorrenze con source ADMIN_RECURRING, note “Serie ricorrente: {label}” e deposit_amount calcolata come una prenotazione standard: questa parte va allineata alla richiesta “sulle partite ricorrenti non serve la caparra”.

## Vincoli non negoziabili

- Patch minima e mirata, niente refactor ampi.
- Non introdurre librerie nuove se non strettamente indispensabili.
- Non cambiare il flusso pubblico salvo eventuale riuso di pattern o componenti già esistenti.
- Mantieni compatibilità dove possibile con contratti e route esistenti.
- Evita di dedurre i dati di ricorrenza parsando la note: se il frontend ha bisogno di metadati, esponili esplicitamente via schema/API.
- Per l’eliminazione delle ricorrenze preferisci un approccio coerente con il dominio attuale basato su stato, audit e log. Evita hard delete distruttivi se una cancellazione tracciabile soddisfa il requisito.
- Se puoi soddisfare la richiesta usando i campi/modelli già presenti, evita migrazioni DB inutili.
-Mantenere coerenza con UX/UI attuale, senza introdurre design nuovi o stili discordanti. 

## Modifiche obbligatorie

### 1. Header e branding admin

- In AdminDashboardPage elimina il payoff “PadelBooking 1 campo, 1 flusso chiaro, conferma rapida” e l’icona razzo.
- Aumenta il testo “Dashboard admin” di circa 10px rispetto allo stato attuale, mantenendo una gerarchia tipografica coerente con la UI esistente.
- In AdminLoginPage elimina lo stesso payoff, elimina l’icona razzo e rimuovi anche la frase “Gestisci prenotazioni, blackout, ricorrenze e report essenziali.”
- Se tocchi AppBrand in modo condiviso, mantieni coerente anche AdminPasswordResetPage senza introdurre regressioni visive.

### 2. Eliminazione ricorrenze: singola, multipla, intera serie

- Nella gestione delle ricorrenze aggiungi tre azioni distinte:
  - elimina una singola occorrenza
  - elimina più occorrenze selezionate
  - elimina tutta la serie
- Mantieni l’operazione tracciabile: preferisci cancellare o annullare le prenotazioni ricorrenti e loggare l’azione, invece di cancellare fisicamente i record se non è strettamente necessario.
- L’azione “tutta la serie” deve colpire tutte le occorrenze future collegate alla recurring_series_id, senza toccare prenotazioni non correlate.
- Esplicita bene lato UI quale ambito stai eliminando e richiedi una conferma prima di operazioni multiple o totali.
- Estendi adminApi frontend e i router/schemas backend solo quanto serve.

### 3. Filtri più chiari per occupazione slot

- Nella vista prenotazioni aggiungi un filtro libero che consenta di cercare per:
  - nome o cognome utente sulle prenotazioni normali
  - label della serie sulle prenotazioni ricorrenti
- Aggiungi un filtro periodo con data inizio e data fine per avere una vista più chiara di quando gli slot sono occupati.
- Mantieni, se utile, i filtri status e payment provider già presenti, ma non lasciare il sistema limitato alla sola singola booking_date.
- Lato backend estendi list_bookings e i query param dell’endpoint admin bookings in modo backward-compatible se possibile.
- La vista risultante deve ordinare e presentare le prenotazioni in modo leggibile per periodo, non come lista confusa.

### 4. Ricorrenti compattate ed espandibili

- Le prenotazioni provenienti da serie ricorrenti non devono apparire come lista piatta indistinguibile.
- Raggruppa le occorrenze ricorrenti per recurring_series_id, mostrando una card o accordion compatta con header leggibile:
  - nome serie
  - eventuale utente se presente
  - periodo o prossima occorrenza utile
  - numero occorrenze nel gruppo
- L’espansione deve mostrare le singole occorrenze e le relative azioni.
- Le prenotazioni non ricorrenti restano visibili come card singole.
- Se oggi al frontend mancano recurring_series_id o recurring_series_label, esponili in modo esplicito dal backend.

### 5. Niente caparra sulle ricorrenti

- Le prenotazioni create da una serie ricorrente non devono avere caparra.
- Allinea backend e frontend:
  - backend: nelle creazioni ricorrenti non assegnare deposit_amount come per le prenotazioni standard
  - frontend: nelle liste e nel dettaglio admin non mostrare caparra, pagamento o azioni “saldo al campo” come se fossero prenotazioni con caparra
- Non alterare invece il comportamento di prenotazioni pubbliche o admin manuali.

### 6. Giorno automatico nella scheda serie ricorrenti

- Nella sezione Serie ricorrente il giorno deve derivare automaticamente dalla data scelta.
- Evita la situazione attuale in cui start_date e weekday possono divergere.
- Se serve, rendi il giorno un campo derivato o read-only oppure sincronizzato automaticamente con la data.
- Mantieni però la logica business corretta: la serie deve partire dal primo slot coerente con la data selezionata, senza ambiguità tra data e giorno.

### 7. Schede data coerenti con la UI del sito

- Le schede o input data dell’admin devono allinearsi visivamente al pattern già usato in PublicBookingPage:
  - label chiara
  - input data ben separato
  - riepilogo del giorno in italiano
  - card o box coerente con il look attuale del sito
- Non fare redesign generale: riusa le classi già presenti.

### 8. Scelta orario come nel booking pubblico, con espansione

- Sostituisci dove opportuno gli input time nativi dell’admin con un pattern coerente con SlotGrid e PublicBookingPage.
- Mostra inizialmente solo le prime 6 mezz’ore disponibili e aggiungi un controllo per espandere la lista completa degli orari.
- Riusa getAvailability e il pattern esistente, evitando logica duplicata inutile.
- Applica questa UX almeno a:
  - prenotazione manuale admin
  - sezione serie ricorrente
  - modifica slot nel dettaglio admin, se la modifica resta coerente con la patch minima
- Se per la serie ricorrente serve la stessa robustezza DST già usata altrove, valuta l’estensione minima del payload con slot_id opzionale invece di basarti solo su HH:MM.

### 9. Descrizioni sopra le singole schede o campi

- Rendi più leggibili i form admin aggiungendo label e descrizioni esplicite sopra i campi oggi troppo impliciti.
- Esempio minimo richiesto: sopra weeks_count deve comparire una label chiara come “Nr. settimane”.
- Applica lo stesso criterio anche agli altri input chiave di prenotazione manuale, ricorrenze e blackout se oggi sono poco descritti.
- Preferisci field-label e copy breve già coerente col progetto.

### 10. Ordine sezioni e nuove route admin

- Nella dashboard principale posiziona “Serie ricorrente” sopra “Blocca fascia oraria”.
- Sposta la vista prenotazioni in una pagina dedicata su /admin/prenotazioni.
- Sposta la vista log in una pagina dedicata su /admin/log.
- Mantieni /admin come dashboard operativa principale, con riepilogo e form principali.
- Aggiorna App.tsx e la navigazione admin in modo coerente, senza rompere la route esistente del dettaglio prenotazione /admin/bookings/:bookingId.
- La navigazione tra dashboard, prenotazioni e log deve essere chiara e coerente con lo stile attuale.

## Indicazioni tecniche preferite

- Frontend, da considerare come target principali:
  - frontend/src/App.tsx
  - frontend/src/components/AppBrand.tsx
  - frontend/src/components/AdminBookingCard.tsx
  - frontend/src/pages/AdminDashboardPage.tsx
  - frontend/src/pages/AdminLoginPage.tsx
  - frontend/src/pages/AdminBookingDetailPage.tsx
  - frontend/src/services/adminApi.ts
  - frontend/src/types.ts
- Se il refactor minimo lo richiede, crea nuove pagine dedicate per /admin/prenotazioni e /admin/log invece di sovraccaricare ancora di più AdminDashboardPage.
- Backend, da considerare come target principali:
  - backend/app/api/routers/admin_bookings.py
  - backend/app/api/routers/admin_ops.py
  - backend/app/schemas/admin.py
  - backend/app/schemas/common.py
  - backend/app/services/booking_service.py
- Se puoi evitare una migration, preferiscilo.
- Se devi aggiungere metadati per il frontend, esponi recurring_series_id e recurring_series_label in modo esplicito invece di riusare campi semantici impropri.

## Test richiesti

Aggiungi solo i test davvero necessari, senza allargare la suite inutilmente.
Copri almeno:

- backend: eliminazione singola di occorrenza ricorrente
- backend: eliminazione multipla e totale della serie
- backend: filtro per periodo + label serie o nome utente
- backend: creazione ricorrenza senza caparra
- frontend: nuova navigazione /admin, /admin/prenotazioni e /admin/log
- frontend: grouping o accordion delle ricorrenti
- frontend: filtro periodo + ricerca serie o utente
- frontend: assenza di caparra per ricorrenti nelle card o nel dettaglio, se tocchi entrambe le viste
- frontend: rimozione del copy branding dalla login e aggiornamento header admin

## Validazione finale obbligatoria

Dopo i fix esegui almeno:

- frontend: npm run build
- frontend: npm run test:run
- backend: dalla cartella backend esegui /workspaces/PadelBooking/.venv/bin/python -m pytest -q

Se qualche comando fallisce per limiti dell’ambiente VS Code, usa il workaround già noto del workspace, ma non saltare la validazione.

## Output atteso

- Applica le modifiche direttamente nel repository.
- Mantieni la patch piccola e leggibile.
- Alla fine riassumi:
  - cosa hai cambiato
  - quali file hai toccato
  - quali test hai aggiunto
  - quali comandi hai eseguito e con che esito
  - eventuali tradeoff residui

Non fare redesign generale e non fare refactor non richiesti.
Fai una patch admin mirata, coerente con il codice attuale e completa rispetto ai 10 punti sopra.