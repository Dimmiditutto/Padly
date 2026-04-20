# PROMPT WEEK OPERATIVO PER COPILOT — CALIBRATO SUL REPOSITORY REALE

Agisci come un Senior Frontend / Full Stack Engineer React + TypeScript + Tailwind + FastAPI, con attenzione specifica alla UX/UI admin gia presente nel repository.

Devi implementare una patch minima, coerente e non distruttiva nell'area admin del progetto reale PadelBooking.

## Obiettivo

Implementa una nuova pagina admin dedicata alle prenotazioni settimanali in formato calendario, aggiorna i nomi dei pulsanti/tab admin per eliminare ambiguita e mantieni una UX/UI coerente con quella gia esistente.

Non fare refactor generali. Non rompere le route admin gia presenti. Non introdurre conflitti con la dashboard admin, con la pagina elenco prenotazioni gia esistente o con la pagina log.

## Contesto reale del codice

- Frontend:
  - frontend/src/App.tsx espone gia queste route admin:
    - /admin
    - /admin/prenotazioni
    - /admin/log
    - /admin/bookings/:bookingId
  - frontend/src/pages/AdminDashboardPage.tsx e la vera pagina operativa di creazione, con:
    - prenotazione manuale
    - serie ricorrente
    - blackout
    - regole operative
  - frontend/src/pages/AdminBookingsPage.tsx esiste gia ed e una vista elenco / ricerca avanzata con:
    - filtro periodo
    - ricerca libera
    - raggruppamento ricorrenze
    - azioni su occorrenze e serie
  - frontend/src/pages/AdminLogsPage.tsx esiste gia.
  - frontend/src/components/AdminNav.tsx oggi mostra tre voci: Dashboard, Prenotazioni, Log.
  - frontend/src/services/adminApi.ts espone gia listAdminBookings(filters).
  - frontend/src/types.ts / backend/app/schemas/common.py espongono gia i dati utili per un calendario:
    - start_at
    - end_at
    - booking_date_local
    - status
    - recurring_series_id
    - recurring_series_label
- Backend:
  - backend/app/api/routers/admin_bookings.py supporta gia start_date, end_date, status, payment_provider e query.
  - Questo significa che la nuova vista settimanale deve preferibilmente riusare l'endpoint admin bookings esistente, senza introdurre una nuova API se non strettamente necessario.

## Vincoli non negoziabili

- Mantieni la patch piccola e leggibile.
- Non introdurre nuove librerie calendario o date-picker se puoi farlo con il codice gia presente e con utility leggere.
- Non trasformare o rompere la pagina /admin/prenotazioni gia esistente: trattala come vista elenco / ricerca avanzata, non come pagina da sostituire.
- Non spostare la logica di creazione fuori da /admin: la dashboard attuale resta la pagina dove si creano prenotazioni manuali e serie ricorrenti.
- Non cambiare contratti backend se la pagina settimanale puo essere costruita con listAdminBookings e i dati gia disponibili.
- Mantieni classi, componenti e pattern UI coerenti con quelli gia in uso:
  - page-shell
  - SectionCard
  - btn-primary / btn-secondary
  - AlertBanner
  - LoadingBlock
  - AdminNav
- Mantieni una UX/UI coerente sia desktop sia mobile.

## Decisione architetturale obbligatoria

Per evitare conflitti con il codice attuale:

1. /admin deve restare la pagina di creazione e gestione operativa.
2. Devi aggiungere una nuova pagina separata per il calendario settimanale.
3. Non devi sostituire /admin/prenotazioni con il nuovo calendario: quella pagina esiste gia ed e utile come vista elenco / filtro avanzato.

## Modifiche obbligatorie

### 1. Nuova pagina admin per il calendario settimanale

Aggiungi una nuova pagina admin dedicata alle prenotazioni attuali in formato calendario settimanale.

Requisiti minimi:

- Crea una nuova route dedicata, preferibilmente:
  - /admin/prenotazioni-attuali
- Crea una nuova pagina dedicata, ad esempio:
  - frontend/src/pages/AdminCurrentBookingsPage.tsx
  - oppure un nome equivalente ma chiaro
- La pagina deve mostrare per default la settimana corrente da lunedi a domenica.
- Il calendario deve mostrare tutte le partite / prenotazioni presenti in quella settimana usando i dati reali provenienti dall'endpoint admin bookings gia esistente.
- Per ogni prenotazione mostra almeno:
  - orario inizio-fine
  - nome cliente o riferimento leggibile
  - indicazione discreta se appartiene a una serie ricorrente
  - stato solo se utile a capire l'occupazione
- Il click su una prenotazione deve portare alla route gia esistente del dettaglio:
  - /admin/bookings/:bookingId

### 2. Navigazione settimanale con limiti chiari

La pagina calendario deve avere freccia sinistra e freccia destra per cambiare settimana.

Vincoli:

- dalla settimana corrente si puo andare massimo:
  - 2 settimane indietro
  - 4 settimane avanti
- quando si raggiunge il limite, il pulsante relativo deve essere disabilitato o chiaramente non attivo
- il range visualizzato resta sempre lunedi-domenica

### 3. Filtro per mese / settimana del mese / anno

Oltre alle frecce, aggiungi un filtro esplicito per saltare a una settimana desiderata.

Per evitare ambiguita di UX e logica, il filtro deve includere:

- mese
- settimana del mese
- anno

Vincoli:

- anno selezionabile da 1 anno solare precedente a 1 anno solare successivo rispetto all'anno corrente
- settimana del mese espressa in modo semplice e leggibile, ad esempio:
  - 1a settimana
  - 2a settimana
  - 3a settimana
  - 4a settimana
  - 5a settimana se valida
- quando la combinazione mese / settimana / anno non produce una settimana pienamente valida, usa il comportamento piu prevedibile e stabile possibile, ad esempio clamp all'ultima settimana valida del mese, senza generare errori runtime
- il salto tramite filtro deve aggiornare sempre la griglia al corrispondente intervallo lunedi-domenica

### 4. Rinomina coerente dei pulsanti/tab admin

Oggi nel codice la navigazione admin ha etichette non piu allineate alla nuova struttura.

Applica questa logica:

- la voce che punta a /admin non deve piu chiamarsi Dashboard, ma:
  - Crea Prenotazioni
- la nuova voce che punta alla pagina del calendario settimanale deve chiamarsi:
  - Prenotazioni Attuali

Per la pagina gia esistente /admin/prenotazioni:

- non lasciarla con un nome ambiguo uguale o troppo simile agli altri due
- se la mantieni nella nav primaria, rinominala in modo esplicito, ad esempio:
  - Elenco Prenotazioni
  - oppure Ricerca Prenotazioni
- se invece preferisci non appesantire la nav primaria, puoi lasciarla raggiungibile tramite CTA secondaria dalla pagina calendario o dalla dashboard

Regola importante:

- non devono restare due pulsanti che sembrano fare la stessa cosa
- non devi etichettare come Crea Prenotazioni una pagina che mostra solo elenco o calendario

### 5. UX/UI coerenti con l'admin esistente

Mantieni uno stile allineato alle pagine admin gia presenti.

Indicazioni pratiche:

- riusa header, spaziature, card e bottoni gia esistenti
- evita un calendario da gestionale generico o una UI completamente diversa dal resto del sito
- il layout deve restare leggibile anche su schermi piccoli
- se su mobile sette colonne risultano troppo strette, usa una soluzione coerente e sobria:
  - scroll orizzontale contenuto
  - oppure card verticali per giorno mantenendo pero la semantica della settimana
- evidenzia il giorno corrente in modo discreto
- non usare colori o pattern visivi in contrasto con il design attuale

### 6. Reuse dati e logica gia esistenti

Preferisci una patch frontend-first.

Usa il piu possibile cio che esiste gia:

- listAdminBookings(filters)
- filtri start_date / end_date
- BookingSummary con start_at, end_at, recurring_series_id, recurring_series_label

Se serve logica di supporto, aggiungi helper piccoli e locali per:

- calcolare il lunedi della settimana corrente
- generare l'intervallo lunedi-domenica
- navigare avanti / indietro di 7 giorni
- costruire il salto mese / settimana / anno

Evita invece:

- nuove API backend dedicate al calendario, se non davvero necessarie
- duplicazione della logica di filtro gia presente nell'admin bookings esistente
- refactor ampi di App.tsx, AdminDashboardPage.tsx o AdminBookingsPage.tsx

### 7. Stati mostrati nel calendario

Il calendario deve rappresentare le prenotazioni realmente utili a capire l'occupazione.

Comportamento preferito:

- non mostrare come slot occupati le prenotazioni CANCELLED o EXPIRED
- se mantieni COMPLETED o NO_SHOW per continuita operativa, mostrali in modo leggibile ma senza confondere la vista
- non alterare la logica business backend: se fai filtri di presentazione, falli nel livello piu leggero possibile

### 8. Compatibilita con la pagina elenco gia esistente

La nuova pagina calendario non deve rompere o cannibalizzare la vista /admin/prenotazioni gia attuale.

Quindi:

- non eliminare funzionalita dalla pagina elenco esistente
- non duplicare dentro il calendario tutte le azioni avanzate gia presenti li, a meno che siano davvero necessarie
- la pagina calendario deve essere una vista di consultazione operativa rapida
- la pagina elenco puo restare la vista avanzata per ricerca, azioni multiple e gestione dettagliata

## File target consigliati

Frontend principali:

- frontend/src/App.tsx
- frontend/src/components/AdminNav.tsx
- frontend/src/pages/AdminDashboardPage.tsx
- frontend/src/pages/AdminBookingsPage.tsx
- frontend/src/pages/AdminCurrentBookingsPage.tsx oppure file equivalente nuovo
- frontend/src/services/adminApi.ts soltanto se serve qualche adattamento minimo
- frontend/src/types.ts solo se realmente necessario
- eventuali utility frontend minime per la gestione settimana

Backend:

- non toccarlo se non serve davvero
- se scopri che manca un dato indispensabile, fai la patch minima possibile

## Test richiesti

Aggiungi solo i test davvero necessari per evitare regressioni.

Copri almeno:

- nuova route admin della pagina settimanale
- nuova navigazione con etichette coerenti:
  - Crea Prenotazioni
  - Prenotazioni Attuali
- rendering di default sulla settimana corrente
- limite navigazione 2 settimane indietro e 4 avanti
- salto tramite filtro mese / settimana / anno
- apertura del dettaglio prenotazione dal calendario, se implementata tramite link o click card
- assenza di regressioni sulla pagina elenco prenotazioni gia esistente, se tocchi AdminNav o App.tsx

Se non tocchi il backend, non aggiungere test backend inutili.

## Validazione finale obbligatoria

Esegui la validazione completa usando il comando gia documentato nel repository:

```bash
cd /workspaces/PadelBooking && (cd backend && ../.venv/bin/python -m pytest tests -q) && (cd frontend && npm run build && npm run test:run)
```

Se l'ambiente VS Code ha problemi col terminal provider, usa il workaround gia noto del workspace, ma non saltare la validazione.

## Output atteso

Applica direttamente le modifiche nel repository.

Alla fine riassumi in modo concreto:

- cosa hai cambiato
- quali file hai toccato
- se hai aggiunto una nuova route e con quale nome
- come hai gestito la distinzione tra:
  - Crea Prenotazioni
  - Prenotazioni Attuali
  - eventuale Elenco Prenotazioni
- quali test hai aggiunto o aggiornato
- esito dei comandi finali di build e test

## Regole finali

- Non fare redesign generale.
- Non introdurre librerie nuove senza reale necessita.
- Non rompere le route admin esistenti.
- Non eliminare la vista /admin/prenotazioni attuale.
- Fai una patch minima ma completa rispetto ai requisiti sopra.