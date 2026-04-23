Leggi prompts SaaS/prompt_master.md

# Patch UX/UI coerente con il repo attuale - Padel Booking

Agisci come un Senior Frontend Engineer e Product UI Engineer esperto di React, TypeScript, Tailwind e design systems applicati a prodotti SaaS operativi.
Applica solo patch minime e locali.
L'obiettivo non e rifare il prodotto: devi allineare UX e UI tra schede, tab, CTA, bottoni, hero actions, card header e stati visivi, restando coerente con il codice attuale.

---

## Obiettivo reale

Allineare l'esperienza visiva e interattiva delle superfici frontend gia esistenti, in particolare:

- schede e card operative
- navigazione admin tipo tab/pill
- CTA primarie e secondarie
- bottoni di stato, azione e filtro
- header hero e barre azioni delle pagine admin
- stati visivi coerenti per alert, loading, empty state, selected/active/disabled

Il risultato deve sembrare un unico sistema UI coerente, non una somma di pagine con micro-varianti locali.

---

## Vincoli globali obbligatori

1. Non modificare la logica di business.
2. Non toccare backend, router, schema, service, persistenza, policy commerciali o workflow di dominio.
3. Non cambiare contratti API, tipi dati di business, payload HTTP, route, dependency enforced o regole tenant-aware.
4. Non cambiare la semantica delle azioni: stesso comportamento, stessi permessi, stessi stati, stessa logica di abilitazione/disabilitazione.
5. Non introdurre un design system nuovo da zero: devi partire dai token, colori, font e componenti gia presenti nel repo.
6. Non fare refactor ampi dell'albero componenti se basta allineare classi, props o piccole utility UI.
7. Mantieni piena compatibilita responsive mobile/desktop.
8. Mantieni la tenant-awareness esistente in link, query param e navigazione.

---

## Base reale del design corrente da rispettare

Prima di modificare il codice, allinea ogni decisione a queste sorgenti reali del repository:

- [frontend/tailwind.config.ts](frontend/tailwind.config.ts)
- [frontend/src/index.css](frontend/src/index.css)
- [frontend/src/components/SectionCard.tsx](frontend/src/components/SectionCard.tsx)
- [frontend/src/components/AdminNav.tsx](frontend/src/components/AdminNav.tsx)
- [frontend/src/components/StatusBadge.tsx](frontend/src/components/StatusBadge.tsx)
- [frontend/src/components/AlertBanner.tsx](frontend/src/components/AlertBanner.tsx)
- [frontend/src/components/AdminBookingCard.tsx](frontend/src/components/AdminBookingCard.tsx)
- [frontend/src/pages/AdminDashboardPage.tsx](frontend/src/pages/AdminDashboardPage.tsx)
- [frontend/src/pages/AdminBookingsPage.tsx](frontend/src/pages/AdminBookingsPage.tsx)
- [frontend/src/pages/AdminCurrentBookingsPage.tsx](frontend/src/pages/AdminCurrentBookingsPage.tsx)
- [frontend/src/pages/AdminLogsPage.tsx](frontend/src/pages/AdminLogsPage.tsx)
- [frontend/src/pages/AdminBookingDetailPage.tsx](frontend/src/pages/AdminBookingDetailPage.tsx)
- [frontend/src/pages/PublicBookingPage.tsx](frontend/src/pages/PublicBookingPage.tsx)

Vincoli estetici da preservare:

- font attuali: Manrope e Space Grotesk
- palette attuale brand/cyan/slate gia definita in Tailwind
- linguaggio visuale attuale: card morbide, radius ampio, hero scure, accenti cyan/brand, contrasto alto sulle CTA operative

---

## Fuori scope esplicito

- Nessuna modifica a logica prenotazioni, blackout, recurring, pagamenti, billing SaaS o policy commerciali.
- Nessuna nuova route, nessun nuovo campo backend, nessuna migration.
- Nessuna modifica alla semantica di AdminNav tenant-aware.
- Nessuna sostituzione totale di SectionCard, AlertBanner, StatusBadge o DateFieldWithDay per gusto personale.
- Nessuna riscrittura completa delle pagine admin o public.
- Non riaprire il tema logout: i pulsanti Esci sono gia presenti e funzionanti.
- Non introdurre nuove librerie UI se il problema e risolvibile con Tailwind e componenti gia presenti.

---

## Problemi UX/UI concreti da risolvere

### 1. CTA e gerarchia azioni non ancora pienamente uniformi

Problema reale:

- nelle pagine admin esistono piu varianti locali di hero action bar e bottoni operativi
- la gerarchia tra CTA primaria, secondaria, ghost e azione distruttiva non e sempre percepita in modo uniforme
- alcuni pulsanti hanno linguaggio e peso visivo coerente solo localmente, non a livello di prodotto

Correzione richiesta:

- allinea peso visivo, spaziatura, altezza, focus, hover e disabled state di tutte le CTA operative gia esistenti
- chiarisci in modo coerente la gerarchia tra:
  - CTA primaria
  - CTA secondaria
  - CTA ghost/link-action
  - azioni potenzialmente distruttive o reversibili
- non cambiare l'ordine funzionale delle azioni se non serve a chiarire la gerarchia visiva

### 2. AdminNav deve comportarsi come sistema di tab/pill piu coerente

Problema reale:

- oggi AdminNav e funzionale, ma va trattato come navigazione primaria tipo tab/pill del workspace admin
- il legame visivo tra nav attiva, hero di pagina e contenuto sottostante non e ancora pienamente uniforme tra Dashboard, Elenco, Attuali e Log

Correzione richiesta:

- mantieni la logica attuale di routing e tenant slug
- allinea stile attivo/inattivo/hover/focus delle pill di navigazione
- rendi piu chiara la relazione tra nav primaria e contesto della pagina senza cambiare contenuti o comportamento
- se serve, migliora anche il contenitore informativo del tenant attivo per coerenza con il resto del sistema

### 3. Schede, card header e barre azioni hanno micro-varianze non necessarie

Problema reale:

- SectionCard definisce gia un buon pattern, ma le pagine usano header, actions, blocchi muted e wrapper con micro-varianze ripetute
- alcune card mettono bene in evidenza titolo, descrizione e azione; altre meno

Correzione richiesta:

- rendi piu coerenti:
  - card header
  - distanza titolo/descrizione
  - posizione e wrapping delle actions
  - spacing tra blocchi informativi interni
  - trattamenti surface-card vs surface-muted
- preferisci riuso dei pattern esistenti rispetto a nuova componentizzazione non necessaria

### 4. Stati visivi e feedback devono sembrare parte dello stesso sistema

Problema reale:

- AlertBanner, LoadingBlock, EmptyState, StatusBadge e i blocchi selected/currently active sono gia presenti, ma il ritmo visivo e il contrasto non e sempre uniforme tra pagine

Correzione richiesta:

- uniforma il modo in cui vengono presentati:
  - stato attivo/selezionato
  - stato disabilitato
  - stato caricamento
  - stato vuoto
  - stato successo/errore
  - badge di stato booking
- non cambiare i testi business se non per microcopy puramente UI e solo se davvero necessario alla chiarezza

### 5. Booking pubblico e area admin devono sembrare lo stesso prodotto

Problema reale:

- il booking pubblico ha gia una buona hero e una buona gerarchia, ma il passaggio visivo tra pubblico e admin puo ancora sembrare troppo separato in certe superfici
- l'obiettivo non e uniformare tutto, ma far percepire una stessa identita di prodotto

Correzione richiesta:

- mantieni differenze sane tra pubblico e admin
- allinea comunque:
  - linguaggio delle CTA
  - raggi, ombre e superfici
  - ritmo verticale tra blocchi
  - uso dei colori accent
  - leggibilita su mobile

---

## Strategia di intervento richiesta

Agisci in questo ordine:

1. Parti dai token esistenti in Tailwind e dalle utility gia presenti in index.css.
2. Verifica se le differenze possono essere risolte riusando o ritoccando classi gia esistenti.
3. Se ci sono duplicazioni evidenti di classi CTA/header tra piu pagine admin, valuta una minima centralizzazione solo se riduce davvero il drift visivo.
4. Tocca prima i componenti/shared primitive che governano il look comune, poi solo le pagine che restano disallineate.
5. Non aprire refactor di struttura se il problema e risolvibile con styling, props o estrazioni molto piccole.

---

## Superfici prioritarie da allineare

Priorita alta:

- [frontend/src/components/AdminNav.tsx](frontend/src/components/AdminNav.tsx)
- [frontend/src/components/SectionCard.tsx](frontend/src/components/SectionCard.tsx)
- [frontend/src/components/AdminBookingCard.tsx](frontend/src/components/AdminBookingCard.tsx)
- [frontend/src/components/StatusBadge.tsx](frontend/src/components/StatusBadge.tsx)
- [frontend/src/components/AlertBanner.tsx](frontend/src/components/AlertBanner.tsx)
- [frontend/src/index.css](frontend/src/index.css)

Priorita media:

- [frontend/src/pages/AdminDashboardPage.tsx](frontend/src/pages/AdminDashboardPage.tsx)
- [frontend/src/pages/AdminBookingsPage.tsx](frontend/src/pages/AdminBookingsPage.tsx)
- [frontend/src/pages/AdminCurrentBookingsPage.tsx](frontend/src/pages/AdminCurrentBookingsPage.tsx)
- [frontend/src/pages/AdminLogsPage.tsx](frontend/src/pages/AdminLogsPage.tsx)
- [frontend/src/pages/AdminBookingDetailPage.tsx](frontend/src/pages/AdminBookingDetailPage.tsx)

Priorita di coerenza cross-area:

- [frontend/src/pages/PublicBookingPage.tsx](frontend/src/pages/PublicBookingPage.tsx)

---

## Regole pratiche di implementazione

1. Non cambiare nessuna condizione booleana che abilita o disabilita azioni business.
2. Non cambiare il significato di etichette come Completed, No-show, Annulla, Saldo al campo, Ripristina confermata, se non per micro-allineamenti formali minimi.
3. Se introduci nuove utility CSS o classi condivise, devono restare poche, leggibili e aderenti al naming gia presente.
4. Se una pagina usa costanti locali duplicate per hero action buttons o wrapper, puoi consolidarle solo se il risultato riduce il drift senza spostare logica applicativa.
5. Le pill/tab di navigazione e gli action button devono restare facilmente tappabili su mobile.
6. Mantieni focus state chiari e coerenti con l'attuale uso di cyan/brand.
7. Non introdurre dark mode switch, theme toggle o varianti estetiche fuori scope.

---

## Criteri di accettazione

- tutte le principali CTA admin usano una gerarchia visiva coerente
- la navigazione admin primaria appare come un sistema di tab/pill uniforme tra le pagine
- card, section header e action bar mostrano spacing e trattamento coerenti
- gli stati selected, active, disabled, loading, empty e feedback sono omogenei tra le superfici principali
- booking pubblico e admin condividono un'identita visiva chiaramente correlata, senza perdere il loro ruolo diverso
- nessuna modifica a business logic, API, contratti dati o route

---

## Verifica obbligatoria

Esegui almeno:

```powershell
Set-Location D:/Padly/PadelBooking/frontend
npm run build
npm run test:run
```

Se tocchi solo styling e componenti, non serve rilanciare il backend.

---

## Output obbligatorio

- file toccati
- primitive UI riallineate
- pagine riallineate
- eventuali micro-utility o classi condivise introdotte
- PASS/FAIL reale di build e test frontend
- eventuali limiti residui solo se davvero restano