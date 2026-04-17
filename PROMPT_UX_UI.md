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

Non devi “tokenizzare tutto”.  
Non devi introdurre un nuovo sistema tema.  
Non devi sostituire la palette di base del progetto.

Devi invece fare una **patch UX/UI chirurgica**, usando e completando il sistema già presente.

## Vincoli non negoziabili

- patch minima
- non toccare logica di business
- non toccare routing
- non toccare autenticazione
- non toccare API
- non toccare stato applicativo salvo minimo indispensabile per rendering/UI
- non rinominare file
- non spostare file
- non riscrivere pagine da zero
- non introdurre librerie UI nuove
- non introdurre framework di theming
- non introdurre dark mode
- non sostituire la palette base slate del progetto
- non fare refactor ampi

## Regola sulla palette

La **palette slate è la base del progetto** e va lasciata invariata.

Quindi:

- non sostituire classi `slate-*` solo perché sono `slate-*`
- non convertire `text-slate-*`, `bg-slate-*`, `border-slate-*` in CSS variables
- non fare refactor cromatici inutili

Intervieni **solo** sui colori semantici realmente fuori sistema o hardcoded in modo disallineato, ad esempio:

- `emerald-*`
- `amber-*`
- `rose-*`
- `red-*`
- `cyan-*`
- colori inline hardcoded nei badge o nei feedback
- combinazioni locali non coerenti con il design system esistente

## Obiettivo visivo reale

Il risultato deve essere:

- più pulito
- più coerente
- più leggibile
- più “product-like”
- più professionale
- più solido nelle schermate principali
- più curato negli stati di feedback

Ma senza sembrare un redesign.

## Priorità reali di intervento

Lavora in quest’ordine:

### 1. StatusBadge e badge semantici
Correggi per primi i componenti che usano colori semantici hardcoded non governati dal sistema.

Priorità assoluta:
- `StatusBadge.tsx` o equivalente reale

Obiettivo:
- mantenere stessa logica e stesse props
- migliorare solo l’aspetto
- usare classi semantiche esistenti o aggiungerne di minime in `index.css` se davvero necessario
- rendere coerenti gli stati tipo:
  - confirmed
  - pending
  - cancelled
  - expired
  - completed
  - no_show
  - warning/info/success/error equivalenti

### 2. Feedback inline nel booking flow pubblico
Intervieni poi sui box o messaggi inline nelle schermate pubbliche, in particolare gli equivalenti reali di:

- `PublicBookingPage.tsx`
- esito prenotazione
- messaggi errore
- stato pagamento
- disponibilità non trovata
- provider non disponibili
- prenotazione confermata / annullata / scaduta

Obiettivo:
- rendere questi feedback più chiari e visivamente coerenti
- evitare blocchi di testo anonimi
- usare uno stile uniforme per success / warning / error / info

### 3. Feedback inline area admin
Intervieni poi sui punti visivi equivalenti in:

- `AdminDashboardPage.tsx`
- loop di rendering prenotazioni
- box errore/successo
- indicatori rapidi
- messaggi di conflitto o stato ricorrenze
- eventuali badge locali hardcoded

### 4. Empty states
Aggiungi o migliora gli **empty states** dove oggi mancano o sono troppo poveri.

Target principali:
- nessuna prenotazione trovata
- nessuno slot disponibile
- nessun risultato per filtri admin
- nessuna ricorrenza valida
- nessun provider disponibile
- nessun dato ancora caricato, se utile

Gli empty states devono essere:
- sobri
- ordinati
- leggibili
- coerenti col progetto
- senza illustrazioni o dipendenze inutili

### 5. Skeleton / loading states
Aggiungi o migliora i **loading states** solo nei punti ad alta visibilità, ad esempio:

- caricamento disponibilità slot
- caricamento stato prenotazione
- caricamento lista prenotazioni admin

Se il progetto non ha una strategia skeleton già pronta:
- usa placeholder semplici e coerenti
- non creare un framework dedicato
- non introdurre complessità

## File da considerare prioritari

Lavora prima su questi file, se esistono con questi nomi:

- `frontend/src/components/StatusBadge.tsx`
- `frontend/src/pages/PublicBookingPage.tsx`
- `frontend/src/pages/AdminDashboardPage.tsx`
- `frontend/src/index.css`

Se i nomi reali differiscono, modifica gli equivalenti esistenti nel repository, senza creare nuovi file inutili.

## Strategia di patch preferita

Usa questa gerarchia:

### Preferenza 1
Riusa le classi semantiche già presenti in `index.css`.

### Preferenza 2
Se manca una classe semantica utile, aggiungi una piccola estensione in `index.css`, ad esempio per:
- alert semantic
- badge semantic
- empty state container
- skeleton utility minima

### Preferenza 3
Usa classi Tailwind locali solo se restano coerenti con il sistema esistente e non introducono caos.

## Cosa NON devi fare

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
- messaggi senza contenitore visivo
- assenza di empty state
- assenza di skeleton/loading state nei punti critici
- piccoli blocchi UI nei loop admin con colori locali fuori sistema

Non trattare come bug semplice uso di `slate-*` coerente col progetto.

## Regola componente per componente

Per ogni componente modificato:

- cambia solo la parte visuale
- non cambiare props
- non cambiare logica
- non cambiare struttura JSX salvo minimo indispensabile
- non cambiare comportamento
- non cambiare naming
- non estrarre nuovi componenti, salvo mini helper davvero necessari

## Bottoni e azioni

Controlla i bottoni principali solo se in quei file target risultano visivamente incoerenti.

Ma:
- non rifare il sistema bottoni da zero
- non toccare `btn-primary` / `btn-secondary` se sono già corretti
- intervieni solo se un bottone locale usa classi hardcoded fuori sistema

## Output atteso

Voglio un output disciplinato e concreto.

### 1. Mappa file reali
Indica i file reali che hai identificato come target della patch.

### 2. Piano patch minimo
Per ogni file:
- perché lo tocchi
- quale problema UX/UI reale risolve
- cosa lasci invariato

### 3. Patch file per file
Mostra le modifiche file per file.

Per ogni file:
- mostra solo il codice realmente modificato oppure il file completo se necessario
- non mostrare codice invariato inutile
- non inventare file

## Chiarimento sui loading states

Non distribuire miglioramenti ai loading states in modo generico.

Il **loading state prioritario** da introdurre o migliorare è quello della **lista prenotazioni in `AdminDashboardPage.tsx`** o nel componente equivalente reale, perché è il punto che oggi manca davvero di uno stato intermedio chiaro.

I loading states già presenti nel flusso pubblico, come:
- caricamento slot in `PublicBookingPage.tsx`
- polling/stato in `PaymentStatusPage.tsx`

sono già sostanzialmente sufficienti e **non devono essere oggetto di redesign**, salvo minime correzioni visive strettamente necessarie.

## Priorità aggiuntiva — PaymentStatusPage

Aggiungi tra i target prioritari anche `PaymentStatusPage.tsx` o il componente equivalente reale.

Obiettivo:
- correggere eventuali incoerenze semantiche di icone e feedback visivi
- in particolare, **non usare icone di warning/errore per uno stato di pagamento riuscito o prenotazione confermata**
- mantenere invariata la logica del componente
- intervenire solo sulla parte visuale e semantica del feedback utente

Se il componente mostra una schermata di successo con un’icona semanticamente errata, sostituiscila con una più coerente con uno stato positivo/confermato.

### 4. Verifica finale
Chiudi con checklist concreta.

## Checklist di verifica richiesta

Verifica almeno:

- [ ] nessun riferimento a dark mode è stato introdotto
- [ ] la palette slate di base è rimasta invariata
- [ ] `StatusBadge.tsx` non usa più colori semantici hardcoded fuori sistema
- [ ] i feedback inline in `PublicBookingPage.tsx` sono più chiari e coerenti
- [ ] i feedback inline in `AdminDashboardPage.tsx` sono più coerenti
- [ ] gli empty states principali esistono e sono leggibili
- [ ] i loading states principali sono migliorati o introdotti
- [ ] nessuna regressione su props, logica, routing o API
- [ ] nessun refactor fuori scope
- [ ] il design system esistente è stato riusato, non duplicato

## Criterio finale di qualità

Il lavoro è corretto solo se:

- la patch è piccola
- i punti deboli reali del codebase sono migliorati
- non hai toccato parti sane inutilmente
- la UI migliora davvero nei punti visibili
- il design system esistente resta il centro del frontend
- non hai introdotto complessità gratuita

## Regola finale

Non fare un redesign totale.  
Non fare un refactor estetico generale.  
Non inseguire la purezza teorica del design system.

Fai una **patch UX/UI chirurgica, concreta e coerente** sul repository reale, concentrata su:
- `StatusBadge`
- feedback inline
- empty states
- skeleton/loading states
- piccoli punti hardcoded davvero fuori sistema