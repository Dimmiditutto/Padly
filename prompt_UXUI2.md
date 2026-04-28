Leggi prompts SaaS/prompt_master.md

# Patch UX/UI coerente con il repo attuale e con il flusso Play/OTP - Padel Booking

Agisci come un Senior Frontend Engineer e Product UI Engineer esperto di React, TypeScript, Tailwind e design systems applicati a prodotti SaaS operativi.
Applica solo patch minime e locali.
L'obiettivo non e rifare il prodotto: devi allineare UX e UI tra hero, tab, CTA, card header, section wrapper, stati visivi, slot picker e superfici Play/community, restando coerente con il codice attuale.

---

## Obiettivo reale

Allineare l'esperienza visiva e interattiva delle superfici frontend gia esistenti, in particolare:

- booking pubblico tenant-aware
- accesso community Play via OTP nelle modalita RECOVERY, DIRECT, GROUP e INVITE
- bacheca Play e rientro community dal booking pubblico
- navigazione admin tipo tab/pill e hero operative delle pagine admin
- schede, card e barre azioni dei flussi admin e booking
- stati visivi coerenti per alert, loading, empty state, selected, active, disabled e azioni distruttive

Il risultato deve sembrare un unico sistema UI coerente, non una somma di pagine con micro-varianti locali.

---

## Contesto gia integrato da preservare

Le seguenti integrazioni sono gia presenti e non vanno rifatte o snaturate:

- esistono le route community [frontend/src/pages/PlayAccessPage.tsx](frontend/src/pages/PlayAccessPage.tsx) e il rientro da [frontend/src/pages/PublicBookingPage.tsx](frontend/src/pages/PublicBookingPage.tsx)
- [frontend/src/pages/PlayPage.tsx](frontend/src/pages/PlayPage.tsx) usa gia un access path dedicato per utenti anonimi
- [frontend/src/pages/AdminDashboardPage.tsx](frontend/src/pages/AdminDashboardPage.tsx) include gia gestione inviti community e link gruppo
- il design system leggero e gia definito in [frontend/tailwind.config.ts](frontend/tailwind.config.ts) e [frontend/src/index.css](frontend/src/index.css)
- [frontend/src/pages/PlayAccessPage.test.tsx](frontend/src/pages/PlayAccessPage.test.tsx) esiste gia con copertura diretta dei rami principali
- il warning React act(...) della dashboard admin e gia stato chiuso: non reintrodurlo con nuove patch UI

---

## Vincoli globali obbligatori

1. Non modificare la logica di business.
2. Non toccare backend, router, schema, service, persistenza, policy commerciali o workflow di dominio.
3. Non cambiare contratti API, tipi dati di business, payload HTTP, route, redirect o regole tenant-aware.
4. Non cambiare la semantica delle azioni: stessi permessi, stessi stati, stessa logica di enable/disable, stesso comportamento OTP/community.
5. Non introdurre un design system nuovo da zero: devi partire dai token, colori, font, utility e componenti gia presenti nel repo.
6. Non fare refactor ampi dell'albero componenti se basta allineare classi, props o piccole utility UI.
7. Mantieni piena compatibilita responsive mobile/desktop.
8. Mantieni intatti i flussi booking pubblico -> play/access -> play e admin tenant-aware.
9. Non peggiorare la copertura test esistente e non reintrodurre warning evitabili nelle suite frontend gia pulite.

---

## Base reale del design corrente da rispettare

Prima di modificare il codice, allinea ogni decisione a queste sorgenti reali del repository:

- [frontend/tailwind.config.ts](frontend/tailwind.config.ts)
- [frontend/src/index.css](frontend/src/index.css)
- [frontend/src/components/SectionCard.tsx](frontend/src/components/SectionCard.tsx)
- [frontend/src/components/AdminNav.tsx](frontend/src/components/AdminNav.tsx)
- [frontend/src/components/StatusBadge.tsx](frontend/src/components/StatusBadge.tsx)
- [frontend/src/components/AlertBanner.tsx](frontend/src/components/AlertBanner.tsx)
- [frontend/src/components/LoadingBlock.tsx](frontend/src/components/LoadingBlock.tsx)
- [frontend/src/components/EmptyState.tsx](frontend/src/components/EmptyState.tsx)
- [frontend/src/components/AdminBookingCard.tsx](frontend/src/components/AdminBookingCard.tsx)
- [frontend/src/components/AdminTimeSlotPicker.tsx](frontend/src/components/AdminTimeSlotPicker.tsx)
- [frontend/src/pages/AdminDashboardPage.tsx](frontend/src/pages/AdminDashboardPage.tsx)
- [frontend/src/pages/AdminBookingsPage.tsx](frontend/src/pages/AdminBookingsPage.tsx)
- [frontend/src/pages/AdminCurrentBookingsPage.tsx](frontend/src/pages/AdminCurrentBookingsPage.tsx)
- [frontend/src/pages/AdminLogsPage.tsx](frontend/src/pages/AdminLogsPage.tsx)
- [frontend/src/pages/AdminBookingDetailPage.tsx](frontend/src/pages/AdminBookingDetailPage.tsx)
- [frontend/src/pages/PublicBookingPage.tsx](frontend/src/pages/PublicBookingPage.tsx)
- [frontend/src/pages/PlayAccessPage.tsx](frontend/src/pages/PlayAccessPage.tsx)
- [frontend/src/pages/PlayPage.tsx](frontend/src/pages/PlayPage.tsx)

Vincoli estetici da preservare:

- font attuali: Manrope per il corpo, Space Grotesk per headline e sezioni chiave
- palette attuale brand/ink/sand gia definita in Tailwind
- background reale del prodotto: gradienti scuri con accenti cyan e warm highlights, non superfici piatte neutre
- primitive esistenti da riusare dove possibile: `surface-card`, `surface-muted`, `admin-hero-panel`, `admin-nav`, `btn-primary`, `btn-secondary`, `btn-ghost`, `btn-soft-success`, `btn-soft-warning`, `btn-soft-danger`, `status-pill-*`, `alert-*`
- linguaggio visuale attuale: card morbide, radius ampio, hero scure, accenti cyan/brand, contrasto alto sulle CTA operative

---

## Fuori scope esplicito

- Nessuna modifica a logica prenotazioni, blackout, recurring, pagamenti, billing SaaS o policy commerciali.
- Nessuna nuova route, nessun nuovo campo backend, nessuna migration.
- Nessuna modifica alla semantica tenant-aware di [frontend/src/components/AdminNav.tsx](frontend/src/components/AdminNav.tsx).
- Nessuna modifica alla logica OTP/community, al binding identitario o ai messaggi di sicurezza se non per micro-allineamenti UI davvero minimi e coerenti con i test.
- Nessuna sostituzione totale di SectionCard, AlertBanner, LoadingBlock, EmptyState, StatusBadge, SlotGrid o DateFieldWithDay per gusto personale.
- Nessuna riscrittura completa delle pagine admin, public o play.
- Non riaprire il tema logout: i pulsanti Esci sono gia presenti e funzionanti.
- Non introdurre nuove librerie UI se il problema e risolvibile con Tailwind e componenti gia presenti.
- Non rimuovere o snaturare la CTA `Entra o rientra nella community` e le superfici gia allineate del flusso access/community.

---

## Problemi UX/UI concreti da risolvere

### 1. CTA e gerarchia azioni cross-area non ancora pienamente uniformi

Problema reale:

- nelle pagine admin esistono hero action bar e bottoni operativi gia abbastanza coerenti, ma il peso relativo tra primaria, secondaria, ghost e azione distruttiva puo ancora driftare tra page hero, section action e card action
- tra booking pubblico, accesso community e area Play il linguaggio CTA non sempre comunica con la stessa forza le azioni principali vs secondarie

Correzione richiesta:

- allinea peso visivo, spaziatura, altezza, hover, focus e disabled state di tutte le CTA operative gia esistenti
- chiarisci in modo coerente la gerarchia tra:
  - CTA primaria
  - CTA secondaria
  - CTA ghost/link-action
  - azioni distruttive o irreversibili
  - azioni stato-positive o stato-warning
- non cambiare l'ordine funzionale delle azioni se non serve a chiarire la gerarchia visiva

### 2. Continuita visuale tra booking pubblico, accesso community e bacheca Play

Problema reale:

- oggi [frontend/src/pages/PublicBookingPage.tsx](frontend/src/pages/PublicBookingPage.tsx), [frontend/src/pages/PlayAccessPage.tsx](frontend/src/pages/PlayAccessPage.tsx) e [frontend/src/pages/PlayPage.tsx](frontend/src/pages/PlayPage.tsx) appartengono allo stesso funnel utente, ma possono ancora sembrare tre superfici progettate separatamente
- il passaggio booking -> access/community -> play deve risultare continuo in hero, CTA, helper block, alert e spacing verticale

Correzione richiesta:

- mantieni differenze sane tra pubblico, accesso e community board
- allinea comunque:
  - linguaggio delle CTA e link-action
  - ritmo verticale tra hero, info pills, card e blocchi form
  - uso di superfici scure vs chiare
  - trattamento dei messaggi di accesso, lockout OTP, resend e sessione gia attiva
  - leggibilita e tappabilita mobile

### 3. Admin hero, nav primaria e SectionCard devono sembrare un unico sistema

Problema reale:

- [frontend/src/components/AdminNav.tsx](frontend/src/components/AdminNav.tsx) e i blocchi `admin-hero-panel` sono gia buoni, ma il legame visivo tra nav attiva, hero di pagina e contenuto sottostante puo ancora avere micro-varianze tra Dashboard, Elenco, Attuali, Dettaglio e Log
- [frontend/src/components/SectionCard.tsx](frontend/src/components/SectionCard.tsx) definisce il pattern, ma header, actions, blocchi muted e wrapper interni possono ancora divergere tra pagine

Correzione richiesta:

- mantieni logica attuale di routing e tenant slug
- allinea stile attivo/inattivo/hover/focus delle pill di navigazione
- rendi piu chiara la relazione tra nav primaria, hero, context strip e contenuto
- uniforma distanza titolo/descrizione, wrapping actions, spacing interno e trattamenti `surface-card` vs `surface-muted`
- preferisci riuso dei pattern esistenti rispetto a nuova componentizzazione non necessaria

### 4. Stati visivi e feedback devono sembrare parte dello stesso sistema

Problema reale:

- AlertBanner, LoadingBlock, EmptyState, StatusBadge, i selected blocks e gli stati slot-grid sono gia presenti, ma il ritmo visivo e il contrasto non sono sempre uniformi tra admin, booking pubblico e Play/community

Correzione richiesta:

- uniforma il modo in cui vengono presentati:
  - stato attivo/selezionato
  - stato disabilitato
  - stato caricamento
  - stato vuoto
  - stato successo/errore/warning
  - badge di stato booking e match
  - blocchi helper e info pill
- non cambiare i testi business se non per microcopy puramente UI e solo se davvero necessario alla chiarezza

### 5. Card operative, slot picker e barre azioni non devono reintrodurre drift locale

Problema reale:

- card admin, booking card, slot picker e blocchi form hanno gia pattern validi, ma sono superfici dove e facile reintrodurre differenze minime che poi frammentano il sistema
- [frontend/src/components/AdminTimeSlotPicker.tsx](frontend/src/components/AdminTimeSlotPicker.tsx), [frontend/src/components/AdminBookingCard.tsx](frontend/src/components/AdminBookingCard.tsx) e le card Play devono restare coerenti tra spacing, density e call-to-action

Correzione richiesta:

- rendi piu coerenti:
  - card header e footer action
  - distanza tra campi form e picker slot
  - blocchi informativi interni
  - selected state e highlight slot
  - densita mobile delle card operative
- non introdurre fix che riaprano warning o test fragili gia chiusi

---

## Strategia di intervento richiesta

Agisci in questo ordine:

1. Parti dai token esistenti in Tailwind e dalle utility gia presenti in [frontend/src/index.css](frontend/src/index.css).
2. Verifica se le differenze possono essere risolte riusando o ritoccando classi esistenti come `admin-hero-*`, `admin-nav-*`, `btn-*`, `surface-*`, `alert-*` e `status-pill-*`.
3. Se ci sono duplicazioni evidenti di classi CTA/header tra piu pagine, valuta una minima centralizzazione solo se riduce davvero il drift visivo.
4. Tocca prima i componenti/shared primitive che governano il look comune, poi solo le pagine che restano disallineate.
5. Non aprire refactor di struttura se il problema e risolvibile con styling, props o estrazioni molto piccole.
6. Se intervieni sul funnel pubblico/community, considera sempre la continuita tra [frontend/src/pages/PublicBookingPage.tsx](frontend/src/pages/PublicBookingPage.tsx), [frontend/src/pages/PlayAccessPage.tsx](frontend/src/pages/PlayAccessPage.tsx) e [frontend/src/pages/PlayPage.tsx](frontend/src/pages/PlayPage.tsx), non solo la singola pagina.

---

## Superfici prioritarie da allineare

Priorita alta:

- [frontend/src/index.css](frontend/src/index.css)
- [frontend/src/components/SectionCard.tsx](frontend/src/components/SectionCard.tsx)
- [frontend/src/components/AdminNav.tsx](frontend/src/components/AdminNav.tsx)
- [frontend/src/components/AlertBanner.tsx](frontend/src/components/AlertBanner.tsx)
- [frontend/src/components/AdminBookingCard.tsx](frontend/src/components/AdminBookingCard.tsx)
- [frontend/src/pages/PublicBookingPage.tsx](frontend/src/pages/PublicBookingPage.tsx)
- [frontend/src/pages/PlayAccessPage.tsx](frontend/src/pages/PlayAccessPage.tsx)
- [frontend/src/pages/PlayPage.tsx](frontend/src/pages/PlayPage.tsx)

Priorita media:

- [frontend/src/components/StatusBadge.tsx](frontend/src/components/StatusBadge.tsx)
- [frontend/src/components/AdminTimeSlotPicker.tsx](frontend/src/components/AdminTimeSlotPicker.tsx)
- [frontend/src/pages/AdminDashboardPage.tsx](frontend/src/pages/AdminDashboardPage.tsx)
- [frontend/src/pages/AdminBookingsPage.tsx](frontend/src/pages/AdminBookingsPage.tsx)
- [frontend/src/pages/AdminCurrentBookingsPage.tsx](frontend/src/pages/AdminCurrentBookingsPage.tsx)
- [frontend/src/pages/AdminLogsPage.tsx](frontend/src/pages/AdminLogsPage.tsx)
- [frontend/src/pages/AdminBookingDetailPage.tsx](frontend/src/pages/AdminBookingDetailPage.tsx)

Priorita di coerenza cross-area:

- [frontend/src/components/play/MatchCard.tsx](frontend/src/components/play/MatchCard.tsx)
- [frontend/src/components/play/CreateMatchForm.tsx](frontend/src/components/play/CreateMatchForm.tsx)
- [frontend/src/components/play/CommunityMatchinnBrand.tsx](frontend/src/components/play/CommunityMatchinnBrand.tsx)

---

## Regole pratiche di implementazione

1. Non cambiare nessuna condizione booleana che abilita o disabilita azioni business.
2. Non cambiare il significato di etichette come Completed, No-show, Annulla, Saldo al campo, Ripristina confermata, OTP, Rientra con email, Primo accesso, se non per micro-allineamenti formali minimi.
3. Se introduci nuove utility CSS o classi condivise, devono restare poche, leggibili e aderenti al naming gia presente.
4. Se una pagina usa costanti locali duplicate per hero button, wrapper o action group, puoi consolidarle solo se il risultato riduce il drift senza spostare logica applicativa.
5. Le pill/tab di navigazione, le CTA principali e le action bar devono restare facilmente tappabili su mobile.
6. Mantieni focus state chiari e coerenti con l'attuale uso di cyan/brand.
7. Non introdurre dark mode switch, theme toggle o varianti estetiche fuori scope.
8. Se tocchi il funnel access/community, verifica sempre la coerenza tra helper text, warning, success state e CTA secondarie senza snaturare il lockout OTP gia definito.
9. Se tocchi AdminDashboardPage o AdminTimeSlotPicker, non reintrodurre warning `act(...)` nelle suite test.

---

## Criteri di accettazione

- le principali CTA admin, public e play usano una gerarchia visiva coerente
- la navigazione admin primaria appare come un sistema di tab/pill uniforme tra le pagine
- booking pubblico, accesso community e bacheca Play condividono un'identita visiva chiaramente correlata
- card, section header, slot picker e action bar mostrano spacing e trattamento coerenti
- gli stati selected, active, disabled, loading, empty e feedback sono omogenei tra le superfici principali
- nessuna modifica a business logic, API, contratti dati o route
- i test frontend pertinenti restano verdi e non vengono reintrodotti warning evitabili nelle suite gia pulite

---

## Verifica obbligatoria

Esegui almeno queste validazioni minime, scegliendo quelle pertinenti ai file toccati:

```powershell
Set-Location D:/Padly/PadelBooking/frontend
npm run build
npm run test:run -- src/pages/PlayAccessPage.test.tsx src/pages/PlayPage.test.tsx src/pages/PublicBookingPage.test.tsx src/pages/AdminDashboardPage.test.tsx
```

Se tocchi anche superfici admin di elenco, attuali, dettaglio o log, aggiungi le suite mirate corrispondenti:

```powershell
npm run test:run -- src/pages/AdminBookingsPage.test.tsx src/pages/AdminCurrentBookingsPage.test.tsx src/pages/AdminBookingDetailPage.test.tsx src/pages/AdminLogsPage.test.tsx
```

Se tocchi solo styling e componenti frontend, non serve rilanciare il backend.

---

## Output obbligatorio

- file toccati
- primitive UI riallineate
- pagine riallineate
- eventuali micro-utility o classi condivise introdotte
- suite frontend eseguite davvero
- PASS/FAIL reale di build e test frontend
- eventuali limiti residui solo se davvero restano