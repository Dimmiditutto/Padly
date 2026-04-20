# PROMPT UX/UI OPERATIVO PER COPILOT — CALIBRATO SUL REPOSITORY REALE

Agisci come un **Senior Product Designer** + **Senior Frontend Engineer React/TypeScript/Tailwind** + UX/UI Specialist Senior.

Devi eseguire una **patch UX/UI minima, precisa e coerente** sul frontend attuale della web app di prenotazione padel.

## Obiettivo

Migliorare la qualità visiva del frontend **senza rifare il design system**, lavorando solo sui punti realmente deboli del codebase attuale:

1. **stati semantici hardcoded** non coerenti con il sistema esistente
2. **feedback inline** visivamente deboli o inconsistenti
3. **empty states** mancanti o troppo poveri
4. **skeleton / loading states** mancanti o insufficienti
5. piccoli punti UI ad alta visibilità nell’area booking e nell’area admin

## Contesto reale del repository

Queste regole hanno priorità alta e vanno rispettate:

- il progetto **non implementa dark mode**
- ignora completamente ogni riferimento a:
  - dark mode
  - dark/light switching
  - dark override
  - theme hook
  - token light/dark
- lavora **solo sulla mode esistente**

Inoltre:

- il progetto ha già un **design system funzionante**
- `index.css` contiene già classi semantiche utili, come ad esempio:
  - `surface-card`
  - `btn-primary`
  - `btn-secondary`
  - `text-input`
  - `field-label`
  - `section-title`
- queste classi vanno **riusate e rafforzate**
- non duplicare il design system con un nuovo layer di CSS variables o token se non strettamente indispensabile

## Regola fondamentale

Devi invece fare una **patch UX/UI chirurgica**, usando e completando il sistema già presente.

## Vincoli non negoziabili


Quindi:

- non fare refactor cromatici inutili

Intervieni **solo** sui colori semantici realmente fuori sistema o hardcoded in modo disallineato, ad esempio:

- `emerald-*`
- `amber-*`
- `rose-*`
- `red-*`
- `cyan-*`
- più pulito
- più coerente
- più leggibile
Ma senza sembrare un redesign.

## Priorità reali di intervento

Lavora in quest’ordine:

### 1. StatusBadge e badge semantici
  - confirmed
  - pending
  - cancelled

- `PublicBookingPage.tsx`
- esito prenotazione
- messaggi errore
- stato pagamento
- loop di rendering prenotazioni
- box errore/successo
- indicatori rapidi
- messaggi di conflitto o stato ricorrenze
- eventuali badge locali hardcoded

### 4. Empty states
Aggiungi o migliora gli **empty states** dove oggi mancano o sono troppo poveri.

Target principali:
- nessuna prenotazione trovata

Gli empty states devono essere:
- sobri
- senza illustrazioni o dipendenze inutili

### 5. Skeleton / loading states
Aggiungi o migliora i **loading states** solo nei punti ad alta visibilità, ad esempio:


Se il progetto non ha una strategia skeleton già pronta:
- usa placeholder semplici e coerenti

Lavora prima su questi file, se esistono con questi nomi:

- `frontend/src/components/StatusBadge.tsx`
- `frontend/src/pages/PublicBookingPage.tsx`
Se i nomi reali differiscono, modifica gli equivalenti esistenti nel repository, senza creare nuovi file inutili.

## Strategia di patch preferita
Riusa le classi semantiche già presenti in `index.css`.

### Preferenza 2
- non introdurre CSS variables globali nuove per tutto il progetto
- non creare un nuovo token system
- non sostituire la palette slate di base
- non fare redesign della shell o del layout
- non cambiare header/sidebar/routing salvo necessità visuale minima
- non toccare logica del booking flow
- non rifattorizzare componenti già buoni solo per “uniformità teorica”

## Cosa devi cercare davvero nel codice

Cerca e correggi solo i punti realmente problematici, come:

- badge con colori semantici hardcoded
- alert inline incoerenti
- box errore/successo improvvisati

## Regola componente per componente

- non cambiare logica
- non cambiare struttura JSX salvo minimo indispensabile
- non cambiare comportamento
- non cambiare naming
- non estrarre nuovi componenti, salvo mini helper davvero necessari
Controlla i bottoni principali solo se in quei file target risultano visivamente incoerenti.

Ma:

## Output atteso

- quale problema UX/UI reale risolve
- cosa lasci invariato

### 3. Patch file per file
Mostra le modifiche file per file.
## Chiarimento sui loading states

Non distribuire miglioramenti ai loading states in modo generico.

Il **loading state prioritario** da introdurre o migliorare è quello della **lista prenotazioni in `AdminDashboardPage.tsx`** o nel componente equivalente reale, perché è il punto che oggi manca davvero di uno stato intermedio chiaro.

I loading states già presenti nel flusso pubblico, come:
- caricamento slot in `PublicBookingPage.tsx`
- polling/stato in `PaymentStatusPage.tsx`

sono già sostanzialmente sufficienti e **non devono essere oggetto di redesign**, salvo minime correzioni visive strettamente necessarie.

## Priorità aggiuntiva — PaymentStatusPage

Aggiungi tra i target prioritari anche `PaymentStatusPage.tsx` o il componente equivalente reale.
- in particolare, **non usare icone di warning/errore per uno stato di pagamento riuscito o prenotazione confermata**
- mantenere invariata la logica del componente
- intervenire solo sulla parte visuale e semantica del feedback utente

Se il componente mostra una schermata di successo con un’icona semanticamente errata, sostituiscila con una più coerente con uno stato positivo/confermato.

## Checklist di verifica richiesta

Verifica almeno:

- [ ] nessun riferimento a dark mode è stato introdotto
- [ ] la palette slate di base è rimasta invariata
- [ ] `StatusBadge.tsx` non usa più colori semantici hardcoded fuori sistema
- [ ] i feedback inline in `PublicBookingPage.tsx` sono più chiari e coerenti

- la patch è piccola
- i punti deboli reali del codebase sono migliorati
- non hai toccato parti sane inutilmente
- la UI migliora davvero nei punti visibili
Non fare un refactor estetico generale.  
Non inseguire la purezza teorica del design system.

Fai una **patch UX/UI chirurgica, concreta e coerente** sul repository reale, concentrata su:
- `StatusBadge`
- feedback inline
- empty states
- skeleton/loading states
- piccoli punti hardcoded davvero fuori sistema